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
import requests
from huggingface_hub import HfApi

BASE_URL = "https://api.jquants.com/v2"
FREE_DELAY_DAYS = 84
FREE_HISTORY_YEARS = 2
MIN_REQUEST_INTERVAL_SECONDS = 12.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cache the complete J-Quants Free-plan dataset needed for the Japan AlphaZeroBeta surrogate."
    )
    parser.add_argument("--repo-id", default="k4fka/alphazerobeta-jquants-free-cache")
    parser.add_argument("--output-dir", type=Path, default=Path("cache/alphazerobeta-jquants-free"))
    parser.add_argument("--end", help="Inclusive end date; defaults to today minus the Free-plan 12-week delay")
    parser.add_argument("--start", help="Inclusive start date; defaults to two years before --end")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class JQuantsFreeClient:
    def __init__(self, api_key: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.last_request = 0.0
        self.calls = 0

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        elapsed = time.monotonic() - self.last_request
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        response = self.session.get(f"{BASE_URL}{path}", params=params or {}, timeout=60)
        self.last_request = time.monotonic()
        self.calls += 1
        if response.status_code == 429:
            time.sleep(65)
            return self._get(path, params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise AssertionError(f"J-Quants response for {path} is not an object")
        return payload

    def fetch_all(self, path: str, params: dict[str, str] | None = None) -> list[dict[str, object]]:
        query = dict(params or {})
        rows: list[dict[str, object]] = []
        while True:
            payload = self._get(path, query)
            data = payload.get("data", [])
            if not isinstance(data, list):
                raise AssertionError(f"J-Quants response data for {path} is not a list")
            rows.extend(row for row in data if isinstance(row, dict))
            pagination_key = payload.get("pagination_key")
            if not pagination_key:
                return rows
            query["pagination_key"] = str(pagination_key)


def free_window(start: str | None, end: str | None) -> tuple[pd.Timestamp, pd.Timestamp]:
    default_end = pd.Timestamp(datetime.now(tz=UTC).date() - timedelta(days=FREE_DELAY_DAYS))
    end_ts = pd.Timestamp(end) if end else default_end
    start_ts = pd.Timestamp(start) if start else end_ts - pd.DateOffset(years=FREE_HISTORY_YEARS) + pd.Timedelta(days=1)
    if start_ts > end_ts:
        raise ValueError("start must be on or before end")
    return start_ts.normalize(), end_ts.normalize()


def write_frame(frame: pd.DataFrame, path: Path) -> int:
    if frame.empty:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")
    return len(frame)


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
        raise AssertionError(f"J-Quants daily bars missing required columns: {missing}")
    out["Code"] = out["Code"].astype(str)
    out["Date"] = pd.to_datetime(out["Date"], errors="raise")
    out["AdjClose"] = pd.to_numeric(out["AdjClose"], errors="coerce")
    out["Volume"] = pd.to_numeric(out["Volume"], errors="coerce")
    return out.sort_values(["Code", "Date"]).reset_index(drop=True)


def build_equal_weight_benchmark(price_files: list[Path]) -> pd.DataFrame:
    prices = pd.concat(
        (pd.read_parquet(path, columns=["Code", "Date", "AdjClose"]) for path in price_files),
        ignore_index=True,
    )
    prices = prices.sort_values(["Code", "Date"])
    prices["AssetReturn"] = prices.groupby("Code", observed=True)["AdjClose"].transform(lambda x: np.log(x).diff())
    market = prices.groupby("Date", observed=True)["AssetReturn"].mean().dropna().sort_index()
    close = np.exp(market.cumsum()) * 100.0
    return pd.DataFrame({"Date": market.index, "Close": close.to_numpy()})


def ensure_private_repo(api: HfApi, repo_id: str, *, overwrite: bool) -> None:
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
    existing = set(api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    if "manifest.json" in existing and not overwrite:
        raise RuntimeError(f"{repo_id} already contains manifest.json; refusing to overwrite immutable cache")


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required")

    start, end = free_window(args.start, args.end)
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)
    client = JQuantsFreeClient(api_key)

    master_rows = client.fetch_all("/equities/master", {})
    universe = pd.DataFrame(master_rows)
    if universe.empty or "Code" not in universe.columns:
        raise AssertionError("J-Quants Free listed-issue master is empty")
    universe["Code"] = universe["Code"].astype(str)
    write_frame(universe, root / "universe.parquet")

    price_rows_total = 0
    financial_rows_total = 0
    price_files: list[Path] = []
    current_month: str | None = None
    month_prices: list[pd.DataFrame] = []
    month_fins: list[pd.DataFrame] = []

    def flush_month(month: str | None) -> None:
        nonlocal price_rows_total, financial_rows_total
        if month is None:
            return
        if month_prices:
            price_frame = normalize_prices(pd.concat(month_prices, ignore_index=True))
            path = root / "prices" / "jp" / f"{month}.parquet"
            price_rows_total += write_frame(price_frame, path)
            price_files.append(path)
            month_prices.clear()
        if month_fins:
            fin_frame = pd.concat(month_fins, ignore_index=True)
            financial_rows_total += write_frame(fin_frame, root / "financial_summary" / f"{month}.parquet")
            month_fins.clear()

    for day in pd.date_range(start, end, freq="B"):
        month = day.strftime("%Y-%m")
        if current_month is None:
            current_month = month
        elif month != current_month:
            flush_month(current_month)
            current_month = month
        date_value = day.strftime("%Y-%m-%d")
        bars = client.fetch_all("/equities/bars/daily", {"date": date_value})
        if bars:
            month_prices.append(pd.DataFrame(bars))
        fins = client.fetch_all("/fins/summary", {"date": date_value})
        if fins:
            month_fins.append(pd.DataFrame(fins))
        print(json.dumps({"date": date_value, "bars": len(bars), "financial_summary": len(fins), "calls": client.calls}), flush=True)

    flush_month(current_month)
    if not price_files:
        raise AssertionError("J-Quants Free daily bars returned no rows")
    benchmark = build_equal_weight_benchmark(price_files)
    write_frame(benchmark, root / "benchmark.parquet")

    files = sorted(path for path in root.rglob("*") if path.is_file())
    manifest = {
        "schema_version": "investor2.jquants-free-market-snapshot.v1",
        "source": "J-Quants API V2 Free plan",
        "source_region": "Japan",
        "fetched_at_utc": datetime.now(tz=UTC).isoformat(),
        "free_plan_contract": {
            "history_years": FREE_HISTORY_YEARS,
            "reporting_delay_days": FREE_DELAY_DAYS,
            "rate_limit_calls_per_minute": 5,
            "datasets_cached": ["listed issue master", "daily stock OHLC", "financial summary"],
        },
        "date_start": str(start.date()),
        "date_end": str(end.date()),
        "ticker_count": int(universe["Code"].nunique()),
        "price_rows": int(price_rows_total),
        "financial_summary_rows": int(financial_rows_total),
        "api_calls": client.calls,
        "benchmark": "equal-weight mean log return of all cached Japanese equities; TOPIX is not available on Free",
        "redistribution": "private personal-use cache only; raw J-Quants data must not be redistributed or exposed publicly",
        "files": {str(path.relative_to(root)): sha256_file(path) for path in files},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    api = HfApi(token=hf_token)
    ensure_private_repo(api, args.repo_id, overwrite=args.overwrite)
    api.upload_folder(
        repo_id=args.repo_id,
        repo_type="dataset",
        folder_path=str(root),
        path_in_repo="",
        commit_message=f"cache J-Quants Free snapshot through {end.date()}",
    )
    print(json.dumps({"repo_id": args.repo_id, **manifest}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
