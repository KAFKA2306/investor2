#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from huggingface_hub import HfApi
from yfinance import EquityQuery

ALL_REGIONS = (
    "ae",
    "ar",
    "at",
    "au",
    "be",
    "br",
    "ca",
    "ch",
    "cl",
    "cn",
    "co",
    "cz",
    "de",
    "dk",
    "ee",
    "eg",
    "es",
    "fi",
    "fr",
    "gb",
    "gr",
    "hk",
    "hu",
    "id",
    "ie",
    "il",
    "in",
    "is",
    "it",
    "jp",
    "kr",
    "kw",
    "lk",
    "lt",
    "lv",
    "mx",
    "my",
    "nl",
    "no",
    "nz",
    "pe",
    "ph",
    "pk",
    "pl",
    "pt",
    "qa",
    "ro",
    "ru",
    "sa",
    "se",
    "sg",
    "sr",
    "th",
    "tr",
    "tw",
    "us",
    "ve",
    "vn",
    "za",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one immutable Yahoo/yfinance equity snapshot and upload to HF.")
    parser.add_argument("--repo-id", required=True, help="Private Hugging Face dataset repo, e.g. user/alphazerobeta-market-cache")
    parser.add_argument("--start", default="2004-01-01")
    parser.add_argument("--end", default="2025-01-01", help="Exclusive end date")
    parser.add_argument("--regions", default="all", help="Comma-separated Yahoo regions or 'all'")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--request-pause", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=Path("cache/alphazerobeta-market-snapshot"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--public", action="store_true", help="Not recommended for raw Yahoo data; private is default")
    return parser.parse_args()


def _quotes(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw = response.get("quotes", [])
    if not isinstance(raw, list):
        raise AssertionError("yfinance screener response quotes must be a list")
    return [row for row in raw if isinstance(row, dict)]


def discover_region(region: str, *, page_size: int, pause: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    offset = 0
    query = EquityQuery("eq", ["region", region])
    while True:
        response = yf.screen(query, offset=offset, size=page_size, sortField="ticker", sortAsc=True)
        if not isinstance(response, dict):
            raise AssertionError(f"unexpected yfinance screen response for region={region}")
        page = _quotes(response)
        new_count = 0
        for quote in page:
            symbol = str(quote.get("symbol", "")).strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            new_count += 1
            rows.append(
                {
                    "Ticker": symbol,
                    "Region": region,
                    "Exchange": str(quote.get("exchange", "")),
                    "QuoteType": str(quote.get("quoteType", "EQUITY")),
                    "ShortName": str(quote.get("shortName", "")),
                    "LongName": str(quote.get("longName", "")),
                    "Currency": str(quote.get("currency", "")),
                }
            )
        total = response.get("total")
        offset += len(page)
        if not page or new_count == 0 or len(page) < page_size or (isinstance(total, int) and offset >= total):
            break
        time.sleep(pause)
    return pd.DataFrame(rows)


def discover_universe(regions: list[str], *, page_size: int, pause: float) -> pd.DataFrame:
    frames = []
    for region in regions:
        frame = discover_region(region, page_size=page_size, pause=pause)
        print(json.dumps({"region": region, "tickers": len(frame)}), flush=True)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        raise AssertionError("yfinance discovery returned no equities")
    universe = pd.concat(frames, ignore_index=True)
    return universe.drop_duplicates(["Ticker"], keep="first").sort_values(["Region", "Ticker"]).reset_index(drop=True)


def normalize_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    if not isinstance(raw.columns, pd.MultiIndex):
        if len(tickers) != 1:
            raise AssertionError("expected MultiIndex columns for multi-ticker download")
        raw = raw.copy()
        raw.columns = pd.MultiIndex.from_product([tickers, raw.columns])
    available = set(map(str, raw.columns.get_level_values(0)))
    parts = []
    for ticker in tickers:
        if ticker not in available:
            continue
        frame = raw[ticker].reset_index()
        rename = {
            "Adj Close": "AdjClose",
            "Stock Splits": "StockSplits",
            "Capital Gains": "CapitalGains",
        }
        frame = frame.rename(columns=rename)
        frame.insert(0, "Ticker", ticker)
        parts.append(frame)
    if not parts:
        return pd.DataFrame()
    result = pd.concat(parts, ignore_index=True)
    date_column = "Date" if "Date" in result.columns else "Datetime"
    if date_column not in result.columns:
        raise AssertionError("downloaded price frame has no Date/Datetime column")
    result = result.rename(columns={date_column: "Date"})
    result["Date"] = pd.to_datetime(result["Date"], utc=True).dt.tz_convert(None)
    return result.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def download_prices(tickers: list[str], *, start: str, end: str) -> pd.DataFrame:
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        actions=True,
        repair=True,
        keepna=False,
        group_by="ticker",
        threads=True,
        progress=False,
        timeout=30,
    )
    if raw is None:
        return pd.DataFrame()
    return normalize_download(raw, tickers)


def ensure_empty_repo(api: HfApi, repo_id: str, *, private: bool, overwrite: bool) -> None:
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    files = set(api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
    if "manifest.json" in files and not overwrite:
        raise RuntimeError(f"{repo_id} already contains manifest.json; refusing to overwrite immutable snapshot")


def write_region_prices(
    universe: pd.DataFrame,
    root: Path,
    *,
    start: str,
    end: str,
    batch_size: int,
    pause: float,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for region, group in universe.groupby("Region", observed=True):
        tickers = group["Ticker"].astype(str).tolist()
        region_dir = root / "prices" / str(region)
        region_dir.mkdir(parents=True, exist_ok=True)
        rows = 0
        for index in range(0, len(tickers), batch_size):
            batch = tickers[index : index + batch_size]
            frame = download_prices(batch, start=start, end=end)
            if not frame.empty:
                frame.to_parquet(region_dir / f"part-{index // batch_size:05d}.parquet", index=False, compression="zstd")
                rows += len(frame)
            print(
                json.dumps({"region": region, "batch": index // batch_size, "tickers": len(batch), "rows": len(frame)}),
                flush=True,
            )
            time.sleep(pause)
        counts[str(region)] = rows
    return counts


def main() -> None:
    args = parse_args()
    regions = list(ALL_REGIONS) if args.regions.lower() == "all" else [x.strip().lower() for x in args.regions.split(",") if x.strip()]
    unknown = sorted(set(regions) - set(ALL_REGIONS))
    if unknown:
        raise ValueError(f"unsupported Yahoo regions: {unknown}")
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    ensure_empty_repo(api, args.repo_id, private=not args.public, overwrite=args.overwrite)

    universe = discover_universe(regions, page_size=args.page_size, pause=args.request_pause)
    universe.to_parquet(root / "universe.parquet", index=False, compression="zstd")
    row_counts = write_region_prices(
        universe,
        root,
        start=args.start,
        end=args.end,
        batch_size=args.batch_size,
        pause=args.request_pause,
    )
    benchmark = download_prices([args.benchmark], start=args.start, end=args.end)
    if benchmark.empty:
        raise AssertionError(f"benchmark download failed: {args.benchmark}")
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")

    manifest: dict[str, object] = {
        "schema_version": "investor2.market-snapshot.v1",
        "source": "Yahoo Finance via yfinance",
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "start": args.start,
        "end_exclusive": args.end,
        "regions": regions,
        "ticker_count": int(universe["Ticker"].nunique()),
        "ticker_count_by_region": {str(k): int(v) for k, v in universe.groupby("Region", observed=True)["Ticker"].nunique().items()},
        "price_rows_by_region": row_counts,
        "benchmark": args.benchmark,
        "immutable": True,
        "usage_note": "One-shot private research cache. Normal experiments must read this snapshot rather than Yahoo directly.",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    commit = api.upload_folder(
        repo_id=args.repo_id,
        repo_type="dataset",
        folder_path=root,
        commit_message=f"snapshot: Yahoo equities {args.start}..{args.end}",
    )
    print(json.dumps({"repo_id": args.repo_id, "commit": str(commit), "ticker_count": manifest["ticker_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
