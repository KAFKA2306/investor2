#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

DEFAULT_STORAGE_PREFIX = "central/investor2/private/yahoo-market-cache/jp-v1"
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
    parser = argparse.ArgumentParser(description="Build one immutable Yahoo/yfinance equity snapshot locally.")
    parser.add_argument("--start", default="2004-01-01")
    parser.add_argument("--end", default="2025-01-01", help="Exclusive end date")
    parser.add_argument("--regions", default="jp", help="Comma-separated Yahoo regions or 'all'")
    parser.add_argument("--benchmark", default="1306.T", help="Broad Japan benchmark proxy; default is TOPIX ETF")
    parser.add_argument("--storage-prefix", default=DEFAULT_STORAGE_PREFIX)
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--request-pause", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=Path("cache/alphazerobeta-market-snapshot"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_output(root: Path, *, overwrite: bool) -> None:
    if (root / "manifest.json").exists() and not overwrite:
        raise RuntimeError(f"{root}/manifest.json already exists; refusing to overwrite immutable snapshot")
    if root.exists() and overwrite:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


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
    return (
        universe.drop_duplicates(["Region", "Ticker"], keep="first")
        .sort_values(["Region", "Ticker"])
        .reset_index(drop=True)
    )


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
        frame = frame.rename(
            columns={"Adj Close": "AdjClose", "Stock Splits": "StockSplits", "Capital Gains": "CapitalGains"}
        )
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
    return pd.DataFrame() if raw is None else normalize_download(raw, tickers)


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
                frame.to_parquet(
                    region_dir / f"part-{index // batch_size:05d}.parquet", index=False, compression="zstd"
                )
                rows += len(frame)
            print(
                json.dumps({"region": region, "batch": index // batch_size, "tickers": len(batch), "rows": len(frame)}),
                flush=True,
            )
            time.sleep(pause)
        counts[str(region)] = rows
    return counts


def file_manifest(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def main() -> None:
    args = parse_args()
    regions = (
        list(ALL_REGIONS)
        if args.regions.lower() == "all"
        else [value.strip().lower() for value in args.regions.split(",") if value.strip()]
    )
    unknown = sorted(set(regions) - set(ALL_REGIONS))
    if unknown:
        raise ValueError(f"unsupported Yahoo regions: {unknown}")
    root = args.output_dir
    prepare_output(root, overwrite=args.overwrite)

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
    files = file_manifest(root)

    manifest: dict[str, object] = {
        "schema_version": "investor2.market-snapshot.v2",
        "source": "Yahoo Finance via yfinance",
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "start": args.start,
        "end_exclusive": args.end,
        "regions": regions,
        "ticker_count": int(len(universe)),
        "ticker_count_by_region": {
            str(key): int(value) for key, value in universe.groupby("Region", observed=True)["Ticker"].nunique().items()
        },
        "price_rows_by_region": row_counts,
        "benchmark": args.benchmark,
        "immutable": True,
        "files": files,
        "storage_contract": {
            "writer_repository": "KAFKA2306/semiconductor-earnings-model",
            "bucket": "k4fka/kafka-data-lake",
            "prefix": args.storage_prefix,
            "consumer_repository_authentication": False,
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output_dir": str(root), "ticker_count": manifest["ticker_count"], "files": len(files)}))


if __name__ == "__main__":
    main()
