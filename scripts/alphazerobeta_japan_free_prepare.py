#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

from scripts import alphazerobeta_prepare as prepare
from src.research.market_snapshot import (
    MarketSnapshot,
    load_benchmark,
    load_manifest,
    load_prices,
    load_universe,
)

COMMON_STOCK_MARKETS = {"0111", "0112", "0113"}
BENCHMARK_CODE = "13060"
ORIGINAL_LOAD_INPUTS = prepare.load_inputs


def load_japan_inputs(args):
    if not args.market_snapshot_dir:
        return ORIGINAL_LOAD_INPUTS(args)

    regions = [value.strip().lower() for value in args.market_regions.split(",") if value.strip()]
    snapshot = MarketSnapshot(args.market_snapshot_dir)
    manifest = load_manifest(snapshot)
    master = load_universe(snapshot).copy()
    if "Code" not in master.columns or "Mkt" not in master.columns:
        raise AssertionError("PIT J-Quants master must contain Code and Mkt")

    master["Code"] = master["Code"].astype(str)
    market_codes = master["Mkt"].astype(str).str.zfill(4)
    allowed = set(master.loc[market_codes.isin(COMMON_STOCK_MARKETS), "Code"].astype(str))
    allowed.discard(BENCHMARK_CODE)
    if len(allowed) < args.max_assets:
        raise AssertionError(
            f"only {len(allowed)} Prime/Standard/Growth issues in PIT master; need at least {args.max_assets}"
        )

    prices = prepare.normalize_price_frame(load_prices(snapshot, regions=regions))
    prices = prices[prices["Code"].isin(allowed)].copy()
    benchmark = prepare.normalize_benchmark_frame(load_benchmark(snapshot))
    master_dates: list[str] = []
    if "Date" in master.columns:
        parsed = pd.to_datetime(master["Date"], errors="coerce").dropna()
        master_dates = sorted({str(pd.Timestamp(value).date()) for value in parsed})

    return (
        prices,
        benchmark,
        {
            "source": "encrypted-private-hf-jquants-free-cache",
            "market_snapshot_dir": str(args.market_snapshot_dir),
            "market_regions": regions,
            "snapshot_fetched_at_utc": manifest.get("fetched_at_utc"),
            "snapshot_ticker_count": manifest.get("ticker_count"),
            "universe_filter": (
                "J-Quants PIT master Mkt in 0111/0112/0113; benchmark ETF 13060 excluded"
            ),
            "universe_master_dates": master_dates,
            "universe_master_rows": int(len(master)),
            "allowed_common_stock_codes": int(len(allowed)),
        },
    )


def main() -> None:
    prepare.load_inputs = load_japan_inputs
    prepare.main()


if __name__ == "__main__":
    main()
