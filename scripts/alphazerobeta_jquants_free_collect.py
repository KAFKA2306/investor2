#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import threading
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter

FREE_HISTORY_YEARS = 2
FREE_DELAY_WEEKS = 12
REQUEST_INTERVAL_SECONDS = 20.0
MIN_REQUEST_INTERVAL_SECONDS = 15.0
RATE_LIMIT_COOLDOWN_SECONDS = 70.0
MAX_HTTP_ATTEMPTS = 6
BENCHMARK_CODE = "13060"
CACHE_MAGIC = b"JQHF1"
CACHE_NONCE_BYTES = 12
CACHE_KEY_DOMAIN = b"investor2-jquants-hf-cache-v1\x00"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect all Japanese equity daily bars visible on the current J-Quants Free plan, "
            "encrypt them client-side, and persist a private Hugging Face snapshot."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hf-repo-id", required=True)
    parser.add_argument("--as-of", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--request-interval", type=float, default=REQUEST_INTERVAL_SECONDS)
    return parser.parse_args()


def resolve_window(as_of: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    visible_end = pd.Timestamp(as_of).normalize() - timedelta(weeks=FREE_DELAY_WEEKS)
    visible_start = visible_end - pd.DateOffset(years=FREE_HISTORY_YEARS)
    return visible_start, visible_end


def derive_cache_key(api_key: str) -> bytes:
    return hashlib.sha256(CACHE_KEY_DOMAIN + api_key.encode("utf-8")).digest()


def encrypt_blob(plaintext: bytes, *, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(CACHE_NONCE_BYTES)
    return CACHE_MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt_blob(payload: bytes, *, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not payload.startswith(CACHE_MAGIC):
        raise ValueError("invalid encrypted J-Quants cache blob")
    nonce_start = len(CACHE_MAGIC)
    nonce_end = nonce_start + CACHE_NONCE_BYTES
    nonce = payload[nonce_start:nonce_end]
    return AESGCM(key).decrypt(nonce, payload[nonce_end:], aad)


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False, compression="zstd")
    return buffer.getvalue()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_manifest(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def normalize_prices(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Code", "Date", "AdjC", "AdjVo"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise AssertionError(f"daily bars missing columns: {missing}")

    out = frame.copy()
    out["Code"] = out["Code"].astype(str)
    out["Ticker"] = out["Code"]
    out["Date"] = pd.to_datetime(out["Date"], errors="raise").dt.tz_localize(None)
    out["AdjClose"] = pd.to_numeric(out["AdjC"], errors="coerce")
    out["Volume"] = pd.to_numeric(out["AdjVo"], errors="coerce")
    out = out.dropna(subset=["Code", "Date", "AdjClose", "Volume"])
    return out.sort_values(["Code", "Date"]).reset_index(drop=True)


def normalize_master(frame: pd.DataFrame) -> pd.DataFrame:
    if "Code" not in frame.columns:
        raise AssertionError("listed-issue master is missing Code")
    out = frame.copy()
    out["Code"] = out["Code"].astype(str)
    out["Ticker"] = out["Code"]
    out["Region"] = "jp"
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.tz_localize(None)
    return out.sort_values("Code").reset_index(drop=True)


def benchmark_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    benchmark = prices[prices["Code"] == BENCHMARK_CODE].copy()
    if benchmark.empty:
        raise AssertionError(f"TOPIX ETF proxy {BENCHMARK_CODE} is absent from the cached J-Quants window")
    return benchmark.sort_values("Date").reset_index(drop=True)


def write_price_partitions(prices: pd.DataFrame, root: Path) -> None:
    price_root = root / "prices" / "jp"
    price_root.mkdir(parents=True, exist_ok=True)
    years = prices["Date"].dt.year
    for year, group in prices.groupby(years, observed=True):
        group.to_parquet(
            price_root / f"part-{int(year)}.parquet",
            index=False,
            compression="zstd",
        )


def make_rate_limited_client(api_key: str, request_interval: float) -> Any:
    import jquantsapi

    class RateLimitedClientV2(jquantsapi.ClientV2):
        def __init__(self, key: str) -> None:
            super().__init__(api_key=key)
            self._request_lock = threading.Lock()
            self._last_request = 0.0
            self.request_count = 0
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=0))
            self._session = session

        def _get(
            self,
            url: str,
            params: dict[str, Any] | None = None,
        ):
            with self._request_lock:
                for attempt in range(1, MAX_HTTP_ATTEMPTS + 1):
                    elapsed = time.monotonic() - self._last_request
                    if elapsed < request_interval:
                        time.sleep(request_interval - elapsed)
                    self.request_count += 1
                    try:
                        response = super()._get(url, params=params)
                    except requests.HTTPError as exc:
                        self._last_request = time.monotonic()
                        status = exc.response.status_code if exc.response is not None else None
                        if status == 429 and attempt < MAX_HTTP_ATTEMPTS:
                            retry_after = 0.0
                            if exc.response is not None:
                                raw_retry_after = exc.response.headers.get("Retry-After", "")
                                if raw_retry_after.isdigit():
                                    retry_after = float(raw_retry_after)
                            cooldown = max(RATE_LIMIT_COOLDOWN_SECONDS, retry_after)
                            print(
                                json.dumps(
                                    {
                                        "event": "rate_limit_cooldown",
                                        "attempt": attempt,
                                        "cooldown_seconds": cooldown,
                                        "http_requests": self.request_count,
                                    },
                                    sort_keys=True,
                                ),
                                flush=True,
                            )
                            time.sleep(cooldown)
                            continue
                        retryable = status is not None and 500 <= status < 600
                        if retryable and attempt < MAX_HTTP_ATTEMPTS:
                            time.sleep(max(request_interval, 30.0))
                            continue
                        raise
                    except requests.RequestException:
                        self._last_request = time.monotonic()
                        if attempt == MAX_HTTP_ATTEMPTS:
                            raise
                        time.sleep(max(request_interval, 30.0))
                        continue
                    self._last_request = time.monotonic()
                    return response
            raise AssertionError("unreachable J-Quants request state")

    return RateLimitedClientV2(api_key)


def ensure_private_hf_repo(repo_id: str, token: str) -> Any:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    if not bool(getattr(info, "private", False)):
        raise RuntimeError(f"refusing to cache J-Quants data in non-private dataset: {repo_id}")
    return api


def month_windows(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    windows: list[tuple[str, pd.Timestamp, pd.Timestamp]] = []
    cursor = start.normalize()
    while cursor <= end:
        month_end = min(cursor + pd.offsets.MonthEnd(0), end)
        windows.append((cursor.strftime("%Y-%m"), cursor, month_end))
        cursor = month_end + pd.Timedelta(days=1)
    return windows


def fetch_month(client: Any, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    candidates = pd.bdate_range(start=start, end=end)
    observed_days = 0
    for index, day in enumerate(candidates, start=1):
        frame = client.get_eq_bars_daily(date_yyyymmdd=day.strftime("%Y%m%d"))
        if not frame.empty:
            frames.append(frame)
            observed_days += 1
        if index == 1 or index % 5 == 0 or index == len(candidates):
            print(
                json.dumps(
                    {
                        "event": "month_progress",
                        "candidate_days_done": index,
                        "candidate_days_total": len(candidates),
                        "observed_market_days": observed_days,
                        "http_requests": client.request_count,
                        "last_candidate_date": str(day.date()),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def fetch_all_daily_bars_resumable(
    client: Any,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    hf_api: Any,
    repo_id: str,
    token: str,
    snapshot_id: str,
    cache_key: bytes,
    scratch_dir: Path,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    from huggingface_hub import hf_hub_download

    existing = set(hf_api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    frames: list[pd.DataFrame] = []
    resumed_months: list[str] = []
    fetched_months: list[str] = []
    scratch_dir.mkdir(parents=True, exist_ok=True)

    for month, month_start, month_end in month_windows(start, end):
        stage_raw_path = f"staging/{snapshot_id}/prices/{month}.parquet"
        stage_encrypted_path = f"{stage_raw_path}.enc"
        if stage_encrypted_path in existing:
            cached_path = hf_hub_download(
                repo_id=repo_id,
                repo_type="dataset",
                filename=stage_encrypted_path,
                token=token,
            )
            plaintext = decrypt_blob(
                Path(cached_path).read_bytes(),
                key=cache_key,
                aad=stage_raw_path.encode("utf-8"),
            )
            month_frame = pd.read_parquet(BytesIO(plaintext))
            resumed_months.append(month)
            print(
                json.dumps({"event": "resume_encrypted_month", "month": month, "rows": len(month_frame)}),
                flush=True,
            )
        else:
            month_frame = fetch_month(client, month_start, month_end)
            ciphertext = encrypt_blob(
                parquet_bytes(month_frame),
                key=cache_key,
                aad=stage_raw_path.encode("utf-8"),
            )
            local_stage = scratch_dir / f"{month}.parquet.enc"
            local_stage.write_bytes(ciphertext)
            hf_api.upload_file(
                repo_id=repo_id,
                repo_type="dataset",
                path_or_fileobj=str(local_stage),
                path_in_repo=stage_encrypted_path,
                commit_message=f"stage encrypted J-Quants Free {snapshot_id} {month}",
            )
            local_stage.unlink()
            fetched_months.append(month)
            print(
                json.dumps({"event": "cache_encrypted_month", "month": month, "rows": len(month_frame)}),
                flush=True,
            )
        if not month_frame.empty:
            frames.append(month_frame)

    if not frames:
        raise AssertionError("J-Quants Free returned no daily bars in the visible window")
    return pd.concat(frames, ignore_index=True), resumed_months, fetched_months


def build_encrypted_snapshot(root: Path, encrypted_root: Path, *, key: bytes) -> None:
    if encrypted_root.exists():
        shutil.rmtree(encrypted_root)
    encrypted_root.mkdir(parents=True)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        relative = path.relative_to(root)
        destination = encrypted_root / f"{relative.as_posix()}.enc"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            encrypt_blob(
                path.read_bytes(),
                key=key,
                aad=relative.as_posix().encode("utf-8"),
            )
        )
    shutil.copy2(root / "manifest.json", encrypted_root / "manifest.json")


def upload_private_snapshot(
    encrypted_root: Path,
    *,
    repo_id: str,
    snapshot_id: str,
    hf_api: Any,
) -> None:
    manifest_path = f"snapshots/{snapshot_id}/manifest.json"
    existing = set(hf_api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    if manifest_path in existing:
        raise RuntimeError(f"immutable snapshot already exists: {manifest_path}")
    hf_api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(encrypted_root),
        path_in_repo=f"snapshots/{snapshot_id}",
        commit_message=f"cache encrypted J-Quants Free snapshot {snapshot_id}",
    )


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required")
    if args.request_interval < MIN_REQUEST_INTERVAL_SECONDS:
        raise ValueError(
            f"request interval must be >= {MIN_REQUEST_INTERVAL_SECONDS}s; "
            "the default intentionally leaves headroom for the unpublished rate threshold"
        )

    start, end = resolve_window(args.as_of)
    snapshot_id = f"asof-{pd.Timestamp(args.as_of).date()}"
    root = args.output_dir
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    encrypted_root = root.parent / f"{root.name}-encrypted"
    cache_key = derive_cache_key(api_key)

    hf_api = ensure_private_hf_repo(args.hf_repo_id, hf_token)
    print(
        json.dumps(
            {
                "hf_repo_id": args.hf_repo_id,
                "hf_visibility": "private",
                "hf_plaintext_raw_data": False,
                "snapshot_id": snapshot_id,
                "nominal_start": str(start.date()),
                "nominal_end": str(end.date()),
                "request_interval_seconds": args.request_interval,
            },
            sort_keys=True,
        ),
        flush=True,
    )

    client = make_rate_limited_client(api_key, args.request_interval)
    raw_prices, resumed_months, fetched_months = fetch_all_daily_bars_resumable(
        client,
        start=start,
        end=end,
        hf_api=hf_api,
        repo_id=args.hf_repo_id,
        token=hf_token,
        snapshot_id=snapshot_id,
        cache_key=cache_key,
        scratch_dir=root / ".staging",
    )
    shutil.rmtree(root / ".staging", ignore_errors=True)
    prices = normalize_prices(raw_prices)

    actual_start = pd.Timestamp(prices["Date"].min())
    actual_end = pd.Timestamp(prices["Date"].max())
    master = normalize_master(client.get_eq_master(date=actual_end.strftime("%Y%m%d")))
    if master.empty:
        raise AssertionError("listed-issue master is empty")

    master.to_parquet(root / "universe.parquet", index=False, compression="zstd")
    write_price_partitions(prices, root)
    benchmark = benchmark_from_prices(prices)
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")

    manifest: dict[str, object] = {
        "schema_version": "investor2.alphazerobeta-jquants-free-source.v5",
        "source": "J-Quants API v2",
        "plan": "Free",
        "as_of": str(pd.Timestamp(args.as_of).date()),
        "fetched_at_utc": datetime.now(UTC).isoformat(),
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
        "master_rows": int(len(master)),
        "benchmark": {
            "code": BENCHMARK_CODE,
            "label": "NEXT FUNDS TOPIX ETF proxy",
            "exact_topix": False,
            "rows": int(len(benchmark)),
        },
        "request_count_current_run": int(client.request_count),
        "minimum_request_interval_seconds": float(args.request_interval),
        "rate_limit_threshold": "unpublished by current J-Quants FAQ; adaptive 429 cooldown enforced",
        "rate_limit_cooldown_seconds": RATE_LIMIT_COOLDOWN_SECONDS,
        "resumed_months": resumed_months,
        "fetched_months": fetched_months,
        "acquisition_method": (
            "one all-symbol date query per weekday with encrypted private monthly Hugging Face checkpoints; "
            "empty non-market dates create no price rows"
        ),
        "raw_scope": "all equity daily-bar rows returned by J-Quants for every visible market date in the Free window",
        "snapshot_id": snapshot_id,
        "hf_repo_id": args.hf_repo_id,
        "hf_path": f"snapshots/{snapshot_id}",
        "visibility_required": "private",
        "immutable": True,
        "encryption": {
            "algorithm": "AES-256-GCM",
            "key_derivation": "SHA-256 domain-separated JQUANTS_API_KEY",
            "key_id": hashlib.sha256(cache_key).hexdigest()[:16],
            "plaintext_raw_data_on_hf": False,
            "encrypted_suffix": ".enc",
        },
    }
    manifest["files"] = file_manifest(root)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    build_encrypted_snapshot(root, encrypted_root, key=cache_key)
    upload_private_snapshot(
        encrypted_root,
        repo_id=args.hf_repo_id,
        snapshot_id=snapshot_id,
        hf_api=hf_api,
    )
    shutil.rmtree(encrypted_root, ignore_errors=True)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
