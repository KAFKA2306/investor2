#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from scripts.alphazerobeta_build_market_snapshot import (
    download_prices,
    file_manifest,
    log_event,
    prepare_output,
    require_repair_runtime,
    write_region_prices,
)


def parse_tickers(raw: str) -> list[str]:
    tickers = [value.strip().upper() for value in raw.split(",") if value.strip()]
    if not tickers:
        raise ValueError("at least one ticker is required")
    if len(tickers) != len(set(tickers)):
        raise ValueError("duplicate tickers are not allowed")
    return tickers


def explicit_universe(*, region: str, tickers: list[str]) -> pd.DataFrame:
    region = region.strip().lower()
    if not region:
        raise ValueError("region is required")
    return pd.DataFrame(
        {
            "Ticker": tickers,
            "Region": [region] * len(tickers),
            "UniverseSource": ["explicit"] * len(tickers),
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an immutable Yahoo snapshot for an explicit ticker universe.")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="Exclusive end date")
    parser.add_argument("--region", required=True)
    parser.add_argument("--tickers", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--storage-prefix", required=True)
    parser.add_argument("--storage-bucket", required=True)
    parser.add_argument("--writer-repository", required=True)
    parser.add_argument("--batch-size", required=True, type=int)
    parser.add_argument("--request-pause", required=True, type=float)
    parser.add_argument("--download-timeout", required=True, type=float)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = parse_tickers(args.tickers)
    universe = explicit_universe(region=args.region, tickers=tickers)
    root = args.output_dir

    require_repair_runtime()
    prepare_output(root, overwrite=args.overwrite)
    universe.to_parquet(root / "universe.parquet", index=False, compression="zstd")

    row_counts = write_region_prices(
        universe,
        root,
        start=args.start,
        end=args.end,
        batch_size=args.batch_size,
        pause=args.request_pause,
        timeout=args.download_timeout,
    )
    returned = set()
    for path in (root / "prices" / args.region.lower()).glob("*.parquet"):
        returned.update(pd.read_parquet(path, columns=["Ticker"])["Ticker"].astype(str).unique())
    missing = sorted(set(tickers) - returned)
    if missing:
        raise AssertionError(f"explicit ticker snapshot missing downloaded symbols: {missing}")

    benchmark = download_prices(
        [args.benchmark],
        start=args.start,
        end=args.end,
        context="benchmark",
        timeout=args.download_timeout,
    )
    if benchmark.empty:
        raise AssertionError(f"benchmark download failed: {args.benchmark}")
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")

    files = file_manifest(root)
    manifest = {
        "schema_version": "investor2.market-snapshot.v2",
        "source": "Yahoo Finance via yfinance",
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "start": args.start,
        "end_exclusive": args.end,
        "regions": [args.region.lower()],
        "ticker_count": len(tickers),
        "ticker_count_by_region": {args.region.lower(): len(tickers)},
        "price_rows_by_region": row_counts,
        "benchmark": args.benchmark,
        "universe_contract": {
            "mode": "explicit_tickers",
            "tickers": tickers,
        },
        "collection_contract": {
            "batch_size": args.batch_size,
            "request_pause_seconds": args.request_pause,
            "download_timeout_seconds": args.download_timeout,
            "interval": "1d",
            "auto_adjust": False,
            "actions": True,
            "repair": True,
        },
        "immutable": True,
        "files": files,
        "storage_contract": {
            "writer_repository": args.writer_repository,
            "bucket": args.storage_bucket,
            "prefix": args.storage_prefix,
            "consumer_repository_authentication": False,
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    log_event(
        "explicit_snapshot_complete",
        output_dir=str(root),
        region=args.region.lower(),
        ticker_count=len(tickers),
        price_rows_by_region=row_counts,
        files=len(files),
    )


if __name__ == "__main__":
    main()
