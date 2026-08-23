#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

FREE_HISTORY_YEARS = 2
FREE_DELAY_WEEKS = 12
REQUEST_INTERVAL_SECONDS = 12.5
MAX_HTTP_ATTEMPTS = 5
BENCHMARK_CODE = "13060"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect all Japanese equity daily bars visible on the current J-Quants Free plan "
            "and persist an immutable private Hugging Face snapshot."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hf-repo-id", required=True)
    parser.add_argument("--as-of", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--request-interval", type=float, default=REQUEST_INTERVAL_SECONDS)
    return parser.parse_args()


def resolve_window(as_of: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    visible_end = pd.Timestamp(as_of).normalize() - pd.Timedelta(days=FREE_DELAY_WEEKS * 7)
    visible_start = visible_end - pd.DateOffset(years=FREE_HISTORY_YEARS)
    return visible_start, visible_end


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
                        retryable = status == 429 or (status is not None and 500 <= status < 600)
                        if not retryable or attempt == MAX_HTTP_ATTEMPTS:
                            raise
                        continue
                    self._last_request = time.monotonic()
                    return response
            raise AssertionError("unreachable J-Quants request state")

    return RateLimitedClientV2(api_key)


def ensure_private_hf_repo(repo_id: str, token: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(
        repo_id=repo_id,
        repo_type="dataset",
        private=True,
        exist_ok=True,
    )
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    if not bool(getattr(info, "private", False)):
        raise RuntimeError(f"refusing to cache raw J-Quants data in non-private dataset: {repo_id}")


def fetch_all_daily_bars(client: Any, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    candidates = pd.bdate_range(start=start, end=end)
    observed_days = 0

    for index, day in enumerate(candidates, start=1):
        frame = client.get_eq_bars_daily(date_yyyymmdd=day.strftime("%Y%m%d"))
        if not frame.empty:
            frames.append(frame)
            observed_days += 1
        if index == 1 or index % 20 == 0 or index == len(candidates):
            print(
                json.dumps(
                    {
                        "candidate_business_days_done": index,
                        "candidate_business_days_total": len(candidates),
                        "observed_market_days": observed_days,
                        "http_requests": client.request_count,
                        "last_candidate_date": str(day.date()),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    if not frames:
        raise AssertionError("J-Quants Free returned no daily bars in the visible window")
    return pd.concat(frames, ignore_index=True)


def upload_private_snapshot(
    root: Path,
    *,
    repo_id: str,
    snapshot_id: str,
    token: str,
) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    manifest_path = f"snapshots/{snapshot_id}/manifest.json"
    existing = set(api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    if manifest_path in existing:
        raise RuntimeError(f"immutable snapshot already exists: {manifest_path}")

    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(root),
        path_in_repo=f"snapshots/{snapshot_id}",
        commit_message=f"cache J-Quants Free snapshot {snapshot_id}",
    )


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required")
    if args.request_interval < REQUEST_INTERVAL_SECONDS:
        raise ValueError(f"request interval must be >= {REQUEST_INTERVAL_SECONDS}s for the Free-plan limit")

    start, end = resolve_window(args.as_of)
    snapshot_id = f"asof-{pd.Timestamp(args.as_of).date()}"
    root = args.output_dir
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    ensure_private_hf_repo(args.hf_repo_id, hf_token)
    print(
        json.dumps(
            {
                "hf_repo_id": args.hf_repo_id,
                "hf_visibility": "private",
                "snapshot_id": snapshot_id,
                "nominal_start": str(start.date()),
                "nominal_end": str(end.date()),
            },
            sort_keys=True,
        ),
        flush=True,
    )

    client = make_rate_limited_client(api_key, args.request_interval)
    raw_prices = fetch_all_daily_bars(client, start, end)
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
        "schema_version": "investor2.alphazerobeta-jquants-free-source.v3",
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
        "request_count": int(client.request_count),
        "minimum_request_interval_seconds": float(args.request_interval),
        "acquisition_method": "one all-symbol date query per weekday; empty non-market dates retained only as request evidence",
        "raw_scope": "all equity daily-bar rows returned by J-Quants for every visible market date in the Free window",
        "snapshot_id": snapshot_id,
        "hf_repo_id": args.hf_repo_id,
        "hf_path": f"snapshots/{snapshot_id}",
        "visibility_required": "private",
        "immutable": True,
    }
    manifest["files"] = file_manifest(root)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    upload_private_snapshot(
        root,
        repo_id=args.hf_repo_id,
        snapshot_id=snapshot_id,
        token=hf_token,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
