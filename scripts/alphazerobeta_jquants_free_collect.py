#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jquantsapi
import numpy as np
import pandas as pd
import requests

FREE_HISTORY_YEARS = 2
FREE_DELAY_DAYS = 84
REQUEST_INTERVAL_SECONDS = 12.5
FREE_DATASETS = (
    "equities_master",
    "equities_bars_daily",
    "financial_summary",
    "earnings_date",
    "earnings_calendar",
    "trading_calendar",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect J-Quants Free data into ephemeral files without redistributing raw records."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scope", choices=("core", "metadata"), required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_window(start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    today = pd.Timestamp(datetime.now(tz=UTC).date())
    start_ts = pd.Timestamp(start) if start else today - pd.DateOffset(years=FREE_HISTORY_YEARS)
    end_ts = pd.Timestamp(end) if end else today - timedelta(days=FREE_DELAY_DAYS)
    if start_ts > end_ts:
        raise ValueError("start must not be after end")
    return start_ts.normalize(), end_ts.normalize()


def month_chunks(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    chunks: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + pd.offsets.MonthEnd(0), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + pd.Timedelta(days=1)
    return chunks


class FreePlanClient(jquantsapi.ClientV2):
    """ClientV2 with spacing applied to every HTTP page, including pagination."""

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key=api_key)
        self.request_count = 0
        self._last_request_at = 0.0

    def _get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < REQUEST_INTERVAL_SECONDS:
            time.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
        self.request_count += 1
        try:
            response = super()._get(url, params=params)
        finally:
            self._last_request_at = time.monotonic()
        return response


def normalize_prices(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "AdjC": "AdjClose",
        "AdjVo": "Volume",
        "C": "Close",
        "Vo": "RawVolume",
        "Va": "TradingValue",
    }
    out = frame.rename(columns={key: value for key, value in aliases.items() if key in frame.columns}).copy()
    if "Volume" not in out.columns and "RawVolume" in out.columns:
        out["Volume"] = out["RawVolume"]
    required = {"Code", "Date", "AdjClose", "Volume"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise AssertionError(f"daily bars missing columns: {missing}")
    out["Code"] = out["Code"].astype(str)
    out["Date"] = pd.to_datetime(out["Date"], errors="raise").dt.tz_localize(None)
    out["AdjClose"] = pd.to_numeric(out["AdjClose"], errors="coerce")
    out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
    return out[out["AdjClose"].notna() & out["Volume"].notna()].sort_values(["Code", "Date"])


def write_frame(path: Path, frame: pd.DataFrame) -> dict[str, object]:
    frame.to_parquet(path, index=False, compression="zstd")
    return {
        "file": path.name,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "sha256": sha256_file(path),
    }


def collect_daily_range(client: FreePlanClient, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for chunk_start, chunk_end in month_chunks(start, end):
        frame = client.get_eq_bars_daily(
            from_yyyymmdd=str(chunk_start.date()),
            to_yyyymmdd=str(chunk_end.date()),
        )
        if not frame.empty:
            parts.append(normalize_prices(frame))
        print(
            json.dumps(
                {
                    "dataset": "equities_bars_daily",
                    "from": str(chunk_start.date()),
                    "to": str(chunk_end.date()),
                    "rows": int(len(frame)),
                    "http_requests": client.request_count,
                }
            ),
            flush=True,
        )
    if not parts:
        raise AssertionError("J-Quants Free returned no daily bars")
    prices = pd.concat(parts, ignore_index=True).drop_duplicates(["Code", "Date"], keep="last")
    return prices.sort_values(["Code", "Date"]).reset_index(drop=True)


def collect_by_publication_date(
    client: FreePlanClient,
    dates: pd.DatetimeIndex,
    dataset: str,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for index, day in enumerate(dates):
        date_text = str(day.date())
        if dataset == "financial_summary":
            frame = client.get_fin_summary(date_yyyymmdd=date_text)
        elif dataset == "earnings_date":
            frame = client.get_fin_earnings_date(date_yyyymmdd=date_text)
        else:
            raise ValueError(f"unsupported publication-date dataset: {dataset}")
        if not frame.empty:
            parts.append(frame)
        if index % 20 == 0 or index == len(dates) - 1:
            print(
                json.dumps(
                    {
                        "dataset": dataset,
                        "date": date_text,
                        "days_done": index + 1,
                        "days_total": len(dates),
                        "http_requests": client.request_count,
                    }
                ),
                flush=True,
            )
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).drop_duplicates().reset_index(drop=True)


def common_manifest(
    *,
    scope: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    client: FreePlanClient,
    datasets: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "investor2.alphazerobeta-jquants-free-source.v3",
        "source": "J-Quants API v2 Free",
        "scope": scope,
        "plan": {
            "history": "two years excluding the latest 12 weeks",
            "rate_limit": "5 calls/minute",
            "requested_date_start": str(start.date()),
            "requested_date_end": str(end.date()),
        },
        "official_free_datasets": list(FREE_DATASETS),
        "collected_datasets": sorted(datasets),
        "http_requests": client.request_count,
        "retention": "ephemeral raw data; never committed, uploaded, or retained after validation",
        "datasets": datasets,
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }


def collect_core(
    client: FreePlanClient,
    root: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, object]:
    prices = collect_daily_range(client, start, end)
    actual_start = pd.Timestamp(prices["Date"].min()).normalize()
    actual_end = pd.Timestamp(prices["Date"].max()).normalize()

    master = client.get_eq_master(date=str(actual_end.date()))
    if master.empty or "Code" not in master.columns:
        raise AssertionError("listed-issue master is empty")
    master = master.sort_values("Code").reset_index(drop=True)

    trading_calendar = client.get_mkt_calendar(
        from_yyyymmdd=str(start.date()),
        to_yyyymmdd=str(end.date()),
    )
    if trading_calendar.empty:
        raise AssertionError("trading calendar is empty")

    prices["AssetReturn"] = prices.groupby("Code", observed=True)["AdjClose"].transform(
        lambda values: np.log(values).diff()
    )
    market_return = prices.groupby("Date", observed=True)["AssetReturn"].mean().dropna().sort_index()
    benchmark = pd.DataFrame(
        {
            "Date": market_return.index,
            "Close": 100.0 * np.exp(market_return.cumsum()).to_numpy(),
        }
    )

    datasets = {
        "equities_bars_daily": write_frame(root / "prices.parquet", prices),
        "equities_master": write_frame(root / "universe.parquet", master),
        "trading_calendar": write_frame(root / "trading_calendar.parquet", trading_calendar),
        "benchmark": write_frame(root / "benchmark.parquet", benchmark),
    }
    manifest = common_manifest(
        scope="core",
        start=start,
        end=end,
        client=client,
        datasets=datasets,
    )
    manifest.update(
        {
            "actual_date_range": {
                "start": str(actual_start.date()),
                "end": str(actual_end.date()),
            },
            "ticker_count": int(prices["Code"].nunique()),
            "price_rows": int(len(prices)),
            "trading_calendar_rows": int(len(trading_calendar)),
            "benchmark": "equal-weight mean log return of all cached equities; TOPIX is not in Free",
        }
    )
    return manifest


def collect_metadata(
    client: FreePlanClient,
    root: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, object]:
    calendar_dates = pd.date_range(start, end, freq="D")
    financials = collect_by_publication_date(client, calendar_dates, "financial_summary")
    earnings_dates = collect_by_publication_date(client, calendar_dates, "earnings_date")
    earnings_calendar = client.get_eq_earnings_cal()

    datasets = {
        "financial_summary": write_frame(root / "financial_summary.parquet", financials),
        "earnings_date": write_frame(root / "earnings_date.parquet", earnings_dates),
        "earnings_calendar": write_frame(root / "earnings_calendar.parquet", earnings_calendar),
    }
    manifest = common_manifest(
        scope="metadata",
        start=start,
        end=end,
        client=client,
        datasets=datasets,
    )
    manifest.update(
        {
            "calendar_days_scanned": int(len(calendar_dates)),
            "financial_summary_rows": int(len(financials)),
            "earnings_date_rows": int(len(earnings_dates)),
            "earnings_calendar_rows": int(len(earnings_calendar)),
        }
    )
    return manifest


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")

    requested_start, requested_end = resolve_window(args.start, args.end)
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=False)
    client = FreePlanClient(api_key)

    if args.scope == "core":
        manifest = collect_core(client, root, requested_start, requested_end)
    else:
        manifest = collect_metadata(client, root, requested_start, requested_end)

    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
