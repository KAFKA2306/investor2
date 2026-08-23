#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import jquantsapi

FREE_HISTORY_YEARS = 2
FREE_DELAY_DAYS = 84
REQUEST_INTERVAL_SECONDS = 12.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect the J-Quants Free visible Japan window into ephemeral files.")
    parser.add_argument("--output-dir", type=Path, required=True)
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


def normalize_prices(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"AdjC": "AdjClose", "AdjVo": "Volume", "C": "Close", "Vo": "RawVolume", "Va": "TradingValue"}
    out = frame.rename(columns={key: value for key, value in aliases.items() if key in frame.columns}).copy()
    if "Volume" not in out.columns and "RawVolume" in out.columns:
        out["Volume"] = out["RawVolume"]
    required = {"Code", "Date", "AdjClose", "Volume"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise AssertionError(f"daily bars missing columns: {missing}")
    out["Code"] = out["Code"].astype(str)
    out["Date"] = pd.to_datetime(out["Date"], errors="raise")
    out["AdjClose"] = pd.to_numeric(out["AdjClose"], errors="coerce")
    out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
    out = out[out["AdjClose"].notna() & out["Volume"].notna()]
    return out.sort_values(["Code", "Date"]).reset_index(drop=True)


def call_with_spacing(last_call: float, fn, /, *args, **kwargs):
    elapsed = time.monotonic() - last_call
    if elapsed < REQUEST_INTERVAL_SECONDS:
        time.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
    for attempt in range(4):
        try:
            value = fn(*args, **kwargs)
            return value, time.monotonic()
        except Exception as exc:
            if "429" not in str(exc) or attempt == 3:
                raise
            time.sleep(65)
    raise AssertionError("unreachable")


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    start, end = resolve_window(args.start, args.end)
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=False)
    client = jquantsapi.ClientV2(api_key=api_key)
    last_call = 0.0
    api_calls = 0

    master, last_call = call_with_spacing(last_call, client.get_eq_master, date=end.date().isoformat())
    api_calls += 1
    if master.empty or "Code" not in master.columns:
        raise AssertionError("listed-issue master is empty")
    master = master.sort_values("Code").reset_index(drop=True)
    master.to_parquet(root / "universe.parquet", index=False, compression="zstd")

    price_parts: list[pd.DataFrame] = []
    fin_parts: list[pd.DataFrame] = []
    for day in pd.date_range(start, end, freq="B"):
        date_text = day.date().isoformat()
        bars, last_call = call_with_spacing(last_call, client.get_eq_bars_daily, date_yyyymmdd=date_text)
        api_calls += 1
        if not bars.empty:
            price_parts.append(normalize_prices(bars))

        cursor = ""
        while True:
            result, last_call = call_with_spacing(
                last_call,
                client.get_fin_summary_cursor,
                date_yyyymmdd=date_text,
                cursor=cursor,
            )
            api_calls += 1
            financials, next_cursor = result
            if not financials.empty:
                fin_parts.append(financials)
            if not next_cursor:
                break
            cursor = str(next_cursor)

        print(json.dumps({"date": date_text, "bars": int(len(bars)), "api_calls": api_calls}), flush=True)

    if not price_parts:
        raise AssertionError("J-Quants Free returned no daily bars")
    prices = pd.concat(price_parts, ignore_index=True).drop_duplicates(["Code", "Date"], keep="last")
    prices = prices.sort_values(["Code", "Date"]).reset_index(drop=True)
    prices.to_csv(root / "prices.csv", index=False)

    prices["AssetReturn"] = prices.groupby("Code", observed=True)["AdjClose"].transform(lambda x: np.log(x).diff())
    market_return = prices.groupby("Date", observed=True)["AssetReturn"].mean().dropna().sort_index()
    benchmark = pd.DataFrame({"Date": market_return.index, "Close": 100.0 * np.exp(market_return.cumsum()).to_numpy()})
    benchmark.to_csv(root / "benchmark.csv", index=False)

    financials = pd.concat(fin_parts, ignore_index=True) if fin_parts else pd.DataFrame()
    financials.to_parquet(root / "financial_summary.parquet", index=False, compression="zstd")

    files = [root / "prices.csv", root / "benchmark.csv", root / "universe.parquet", root / "financial_summary.parquet"]
    manifest = {
        "schema_version": "investor2.alphazerobeta-jquants-free-source.v1",
        "source": "J-Quants API v2 Free",
        "date_start": str(start.date()),
        "date_end": str(end.date()),
        "ticker_count": int(prices["Code"].nunique()),
        "price_rows": int(len(prices)),
        "financial_summary_rows": int(len(financials)),
        "api_calls": api_calls,
        "benchmark": "equal-weight mean log return of all cached equities; TOPIX is unavailable on Free",
        "retention": "ephemeral raw data; deleted after validation and never committed/uploaded",
        "files": {path.name: sha256_file(path) for path in files},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
