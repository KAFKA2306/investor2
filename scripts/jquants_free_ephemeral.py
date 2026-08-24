#!/usr/bin/env python3
# Raw J-Quants rows must remain on the ephemeral runner unless distribution is separately authorized.
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter

FREE_HISTORY_YEARS = 2
FREE_DELAY_WEEKS = 12
DEFAULT_REQUEST_INTERVAL_SECONDS = 15.0
MIN_REQUEST_INTERVAL_SECONDS = 15.0
RATE_LIMIT_COOLDOWN_SECONDS = 70.0
MAX_HTTP_ATTEMPTS = 6
BENCHMARK_CODE = "13060"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch all-symbol J-Quants Free daily bars into an ephemeral local snapshot for empirical validation."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--as-of", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--request-interval", type=float, default=DEFAULT_REQUEST_INTERVAL_SECONDS)
    return parser.parse_args()


def resolve_window(as_of: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    visible_end = pd.Timestamp(as_of).normalize() - timedelta(weeks=FREE_DELAY_WEEKS)
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
    for path in sorted(root.rglob("*.parquet")):
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
    if out.duplicated(["Code", "Date"]).any():
        raise AssertionError("duplicate J-Quants Code/Date rows")
    return out.sort_values(["Code", "Date"]).reset_index(drop=True)


def benchmark_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    benchmark = prices[prices["Code"] == BENCHMARK_CODE].copy()
    if benchmark.empty:
        raise AssertionError(f"TOPIX ETF proxy {BENCHMARK_CODE} is absent from the J-Quants Free window")
    return benchmark.sort_values("Date").reset_index(drop=True)


def write_price_partitions(prices: pd.DataFrame, root: Path) -> None:
    price_root = root / "prices" / "jp"
    price_root.mkdir(parents=True, exist_ok=True)
    for year, group in prices.groupby(prices["Date"].dt.year, observed=True):
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

        def _get(self, url: str, params: dict[str, Any] | None = None):
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
                                value = exc.response.headers.get("Retry-After", "")
                                if value.isdigit():
                                    retry_after = float(value)
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
    for index, day in enumerate(candidates, start=1):
        frame = client.get_eq_bars_daily(date_yyyymmdd=day.strftime("%Y%m%d"))
        if not frame.empty:
            frames.append(frame)
        if index == 1 or index % 5 == 0 or index == len(candidates):
            print(
                json.dumps(
                    {
                        "event": "month_progress",
                        "candidate_days_done": index,
                        "candidate_days_total": len(candidates),
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


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if args.request_interval < MIN_REQUEST_INTERVAL_SECONDS:
        raise ValueError(f"request interval must be >= {MIN_REQUEST_INTERVAL_SECONDS}s")

    start, end = resolve_window(args.as_of)
    root = args.output_dir
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    staging = root / ".staging"
    staging.mkdir()

    client = make_rate_limited_client(api_key, args.request_interval)
    month_files: list[Path] = []
    for month, month_start, month_end in month_windows(start, end):
        raw = fetch_month(client, month_start, month_end)
        if raw.empty:
            continue
        normalized = normalize_prices(raw)
        path = staging / f"{month}.parquet"
        normalized.to_parquet(path, index=False, compression="zstd")
        month_files.append(path)
        print(
            json.dumps(
                {
                    "event": "ephemeral_month_complete",
                    "month": month,
                    "rows": int(len(normalized)),
                    "http_requests": client.request_count,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    if not month_files:
        raise AssertionError("J-Quants Free returned no daily bars in the visible window")
    prices = pd.concat((pd.read_parquet(path) for path in month_files), ignore_index=True)
    prices = prices.sort_values(["Code", "Date"]).reset_index(drop=True)
    if prices.duplicated(["Code", "Date"]).any():
        raise AssertionError("duplicate J-Quants Code/Date rows across monthly partitions")

    actual_start = pd.Timestamp(prices["Date"].min())
    actual_end = pd.Timestamp(prices["Date"].max())
    write_price_partitions(prices, root)
    benchmark = benchmark_from_prices(prices)
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")
    shutil.rmtree(staging)

    manifest: dict[str, object] = {
        "schema_version": "investor2.jquants-free-ephemeral.v1",
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
        "price_columns": list(prices.columns),
        "benchmark": {
            "code": BENCHMARK_CODE,
            "label": "NEXT FUNDS TOPIX ETF proxy",
            "exact_topix": False,
            "rows": int(len(benchmark)),
        },
        "request_count": int(client.request_count),
        "minimum_request_interval_seconds": float(args.request_interval),
        "rate_limit_cooldown_seconds": RATE_LIMIT_COOLDOWN_SECONDS,
        "acquisition_method": "one all-symbol date query per weekday; full raw rows remain only on the ephemeral runner",
        "raw_scope": "all equity daily-bar rows returned by J-Quants for every visible market date in the Free window",
        "raw_retention": "ephemeral GitHub Actions runner only; always-step deletes working data",
        "external_distribution": "blocked; no raw J-Quants upload, artifact, or repository commit",
    }
    manifest["files"] = file_manifest(root)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
