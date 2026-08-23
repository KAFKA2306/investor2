#!/usr/bin/env python3
"""Owner-only persistent cache for the rolling J-Quants Free equity window.

The Hugging Face Dataset is a private personal storage surface, not a public or
shared distribution surface. J-Quants rows are encrypted client-side before
upload. Plaintext materialization exists only in the current runner working
directory and is deleted by the calling workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.alphazerobeta_jquants_free_ephemeral import (
    BENCHMARK_CODE,
    DEFAULT_REQUEST_INTERVAL_SECONDS,
    FREE_DELAY_WEEKS,
    FREE_HISTORY_YEARS,
    MIN_REQUEST_INTERVAL_SECONDS,
    RATE_LIMIT_COOLDOWN_SECONDS,
    benchmark_from_prices,
    file_manifest,
    make_rate_limited_client,
    month_windows,
    normalize_prices,
    resolve_window,
    write_price_partitions,
)

CACHE_PREFIX = "personal-cache/v1/daily"
CACHE_MAGIC = b"JQPERSONAL1"
CACHE_NONCE_BYTES = 12
CACHE_KEY_DOMAIN = b"investor2-jquants-personal-hf-cache-v1\x00"
EMPTY_MARKER = b"E"
PARQUET_MARKER = b"P"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the current J-Quants Free all-symbol daily-bar window from an owner-only "
            "encrypted private Hugging Face cache, fetching only missing weekdays from J-Quants."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hf-repo-id", required=True)
    parser.add_argument("--as-of", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--request-interval", type=float, default=DEFAULT_REQUEST_INTERVAL_SECONDS)
    parser.add_argument(
        "--require-cache-complete",
        action="store_true",
        help="Fail if any expected weekday shard is absent; never call J-Quants in this mode.",
    )
    return parser.parse_args()


def derive_cache_key(api_key: str) -> bytes:
    return hashlib.sha256(CACHE_KEY_DOMAIN + api_key.encode("utf-8")).digest()


def encrypt_blob(plaintext: bytes, *, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(CACHE_NONCE_BYTES)
    return CACHE_MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt_blob(payload: bytes, *, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not payload.startswith(CACHE_MAGIC):
        raise ValueError("invalid encrypted personal J-Quants cache blob")
    nonce_start = len(CACHE_MAGIC)
    nonce_end = nonce_start + CACHE_NONCE_BYTES
    if len(payload) <= nonce_end:
        raise ValueError("truncated encrypted personal J-Quants cache blob")
    nonce = payload[nonce_start:nonce_end]
    return AESGCM(key).decrypt(nonce, payload[nonce_end:], aad)


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False, compression="zstd")
    return buffer.getvalue()


def encode_day(frame: pd.DataFrame) -> bytes:
    if frame.empty:
        return EMPTY_MARKER
    return PARQUET_MARKER + parquet_bytes(normalize_prices(frame))


def decode_day(payload: bytes) -> pd.DataFrame:
    if payload == EMPTY_MARKER:
        return pd.DataFrame()
    if not payload.startswith(PARQUET_MARKER):
        raise ValueError("unknown personal J-Quants day-shard payload")
    frame = pd.read_parquet(BytesIO(payload[1:]))
    return normalize_prices(frame)


def cache_path(day: pd.Timestamp) -> str:
    date = pd.Timestamp(day).normalize()
    return f"{CACHE_PREFIX}/{date:%Y}/{date:%m}/{date:%Y-%m-%d}.bin.enc"


def ensure_private_personal_repo(repo_id: str, token: str) -> Any:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    if not bool(getattr(info, "private", False)):
        raise RuntimeError(f"refusing to use non-private Hugging Face Dataset: {repo_id}")
    return api


def download_cached_day(repo_id: str, token: str, path_in_repo: str, *, key: bytes) -> pd.DataFrame:
    from huggingface_hub import hf_hub_download

    local = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=path_in_repo,
        token=token,
    )
    plaintext = decrypt_blob(
        Path(local).read_bytes(),
        key=key,
        aad=path_in_repo.encode("utf-8"),
    )
    return decode_day(plaintext)


def materialize_window(
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    hf_api: Any,
    repo_id: str,
    hf_token: str,
    cache_key: bytes,
    api_key: str,
    request_interval: float,
    require_cache_complete: bool,
    scratch_root: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    existing = set(hf_api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    expected_days = list(pd.bdate_range(start=start, end=end))
    expected_paths = {cache_path(day) for day in expected_days}
    missing_paths = sorted(expected_paths - existing)

    if require_cache_complete and missing_paths:
        sample = missing_paths[:10]
        raise RuntimeError(
            f"private HF cache incomplete: missing={len(missing_paths)} sample={sample}; "
            "J-Quants access is disabled by --require-cache-complete"
        )

    client = None if require_cache_complete else make_rate_limited_client(api_key, request_interval)
    frames: list[pd.DataFrame] = []
    cache_hits = 0
    cache_misses = 0
    uploaded_shards = 0
    scratch_root.mkdir(parents=True, exist_ok=True)

    for month, month_start, month_end in month_windows(start, end):
        month_days = list(pd.bdate_range(start=month_start, end=month_end))
        upload_root = scratch_root / month
        if upload_root.exists():
            shutil.rmtree(upload_root)
        upload_root.mkdir(parents=True)
        month_uploaded = 0

        for day in month_days:
            path_in_repo = cache_path(day)
            if path_in_repo in existing:
                frame = download_cached_day(repo_id, hf_token, path_in_repo, key=cache_key)
                cache_hits += 1
            else:
                if client is None:
                    raise AssertionError("cache miss reached with J-Quants access disabled")
                raw = client.get_eq_bars_daily(date_yyyymmdd=day.strftime("%Y%m%d"))
                frame = normalize_prices(raw) if not raw.empty else pd.DataFrame()
                plaintext = encode_day(raw)
                encrypted = encrypt_blob(
                    plaintext,
                    key=cache_key,
                    aad=path_in_repo.encode("utf-8"),
                )
                destination = upload_root / day.strftime("%Y-%m-%d.bin.enc")
                destination.write_bytes(encrypted)
                cache_misses += 1
                month_uploaded += 1

            if not frame.empty:
                frames.append(frame)

        if month_uploaded:
            path_in_repo = f"{CACHE_PREFIX}/{month_start:%Y}/{month_start:%m}"
            hf_api.upload_folder(
                repo_id=repo_id,
                repo_type="dataset",
                folder_path=str(upload_root),
                path_in_repo=path_in_repo,
                commit_message=f"cache encrypted personal J-Quants weekdays {month}",
            )
            uploaded_shards += month_uploaded
            existing.update(cache_path(day) for day in month_days if (upload_root / day.strftime("%Y-%m-%d.bin.enc")).is_file())
        shutil.rmtree(upload_root)

        print(
            json.dumps(
                {
                    "event": "personal_cache_month_complete",
                    "month": month,
                    "cache_hits": cache_hits,
                    "cache_misses": cache_misses,
                    "api_requests": int(client.request_count) if client is not None else 0,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    if not frames:
        raise AssertionError("materialized J-Quants Free cache contains no market-day rows")

    prices = pd.concat(frames, ignore_index=True).sort_values(["Code", "Date"]).reset_index(drop=True)
    if prices.duplicated(["Code", "Date"]).any():
        raise AssertionError("duplicate J-Quants Code/Date rows after private-cache materialization")

    stats: dict[str, object] = {
        "expected_weekday_shards": len(expected_days),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "uploaded_shards": uploaded_shards,
        "api_requests": int(client.request_count) if client is not None else 0,
        "cache_complete_after_run": expected_paths.issubset(existing),
    }
    return prices, stats


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required")
    if args.request_interval < MIN_REQUEST_INTERVAL_SECONDS:
        raise ValueError(f"request interval must be >= {MIN_REQUEST_INTERVAL_SECONDS}s")

    start, end = resolve_window(args.as_of)
    root = args.output_dir
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    scratch = root.parent / f".{root.name}-hf-upload"
    if scratch.exists():
        shutil.rmtree(scratch)

    hf_api = ensure_private_personal_repo(args.hf_repo_id, hf_token)
    key = derive_cache_key(api_key)
    prices, cache_stats = materialize_window(
        start=start,
        end=end,
        hf_api=hf_api,
        repo_id=args.hf_repo_id,
        hf_token=hf_token,
        cache_key=key,
        api_key=api_key,
        request_interval=args.request_interval,
        require_cache_complete=args.require_cache_complete,
        scratch_root=scratch,
    )
    if scratch.exists():
        shutil.rmtree(scratch)

    actual_start = pd.Timestamp(prices["Date"].min())
    actual_end = pd.Timestamp(prices["Date"].max())
    write_price_partitions(prices, root)
    benchmark = benchmark_from_prices(prices)
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")

    manifest: dict[str, object] = {
        "schema_version": "investor2.alphazerobeta-jquants-personal-hf-cache.v1",
        "source": "J-Quants API v2 with owner-only encrypted private HF cache",
        "plan": "Free",
        "as_of": str(pd.Timestamp(args.as_of).date()),
        "materialized_at_utc": datetime.now(UTC).isoformat(),
        "nominal_free_window": {
            "start": str(start.date()),
            "end": str(end.date()),
            "history_years": FREE_HISTORY_YEARS,
            "delay_weeks": FREE_DELAY_WEEKS,
        },
        "actual_date_range": {
            "start": str(actual_start.date()),
            "end": str(actual_end.date()),
        },
        "observed_market_days": int(prices["Date"].nunique()),
        "ticker_count": int(prices["Code"].nunique()),
        "price_rows": int(len(prices)),
        "price_columns": list(prices.columns),
        "benchmark": {
            "code": BENCHMARK_CODE,
            "label": "NEXT FUNDS TOPIX ETF proxy",
            "exact_topix": False,
            "rows": int(len(benchmark)),
        },
        "request_count": cache_stats["api_requests"],
        "minimum_request_interval_seconds": float(args.request_interval),
        "rate_limit_cooldown_seconds": RATE_LIMIT_COOLDOWN_SECONDS,
        "cache": {
            "repo_id": args.hf_repo_id,
            "visibility": "private",
            "access_contract": "owner-only personal cache; do not share, add collaborators, or make public",
            "prefix": CACHE_PREFIX,
            "plaintext_jquants_rows_on_hf": False,
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_derivation": "SHA-256(domain || JQUANTS_API_KEY)",
                "key_persisted": False,
                "aad": "exact HF shard path",
            },
            **cache_stats,
        },
        "raw_scope": "all equity daily-bar rows returned by J-Quants for every visible market date in the Free window",
        "raw_retention": "encrypted owner-only private HF cache; plaintext only in the current runner working directory",
        "external_distribution": "none; private personal storage only",
    }
    manifest["files"] = file_manifest(root)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
