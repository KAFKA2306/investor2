#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.research.market_snapshot import MarketSnapshot, load_manifest, load_prices_from_snapshots
from src.research.session_state import (
    ADJUSTMENT_MODES,
    add_session_tilt,
    annualized_session_summary,
    decompose_daily_sessions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a session-state baseline from explicitly supplied research parameters."
    )
    parser.add_argument(
        "--market-snapshot-dir",
        required=True,
        type=Path,
        action="append",
        help="Materialized immutable snapshot root. Repeat to compose shards.",
    )
    parser.add_argument("--market-regions", required=True, help="Comma-separated snapshot regions to load")
    parser.add_argument("--tickers", required=True, help="Comma-separated symbols to evaluate")
    parser.add_argument("--start", required=True, help="Inclusive analysis start date")
    parser.add_argument("--end", required=True, help="Inclusive analysis end date")
    parser.add_argument("--half-life", required=True, type=int)
    parser.add_argument("--min-periods", required=True, type=int)
    parser.add_argument("--trading-days", required=True, type=int)
    parser.add_argument("--adjustment", required=True, choices=sorted(ADJUSTMENT_MODES))
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def _string_list(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("at least one value is required")
    return values


def validate_snapshot_coverage(manifests: list[dict[str, Any]], *, start: str, end: str) -> None:
    if not manifests:
        raise ValueError("at least one market snapshot manifest is required")
    requested_start = pd.Timestamp(start)
    requested_end_exclusive = pd.Timestamp(end) + pd.Timedelta(days=1)
    if requested_start >= requested_end_exclusive:
        raise ValueError("requested start must not be after end")

    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for manifest in manifests:
        source_start_raw = manifest.get("start")
        source_end_raw = manifest.get("end_exclusive")
        if not isinstance(source_start_raw, str) or not isinstance(source_end_raw, str):
            raise AssertionError("market snapshot manifest must declare start and end_exclusive")
        source_start = pd.Timestamp(source_start_raw)
        source_end_exclusive = pd.Timestamp(source_end_raw)
        if source_start >= source_end_exclusive:
            raise AssertionError("market snapshot manifest has an invalid date interval")
        intervals.append((source_start, source_end_exclusive))

    cursor = requested_start
    for source_start, source_end_exclusive in sorted(intervals):
        if source_end_exclusive <= cursor:
            continue
        if source_start > cursor:
            raise AssertionError(
                "requested window contains an uncovered market snapshot gap: "
                f"gap_starts={cursor.date()} next_snapshot_starts={source_start.date()}"
            )
        cursor = max(cursor, source_end_exclusive)
        if cursor >= requested_end_exclusive:
            return
    raise AssertionError(
        "requested window is not fully covered by immutable snapshots: "
        f"covered_until_exclusive={cursor.date()} requested_until_exclusive={requested_end_exclusive.date()}"
    )


def select_prices(
    frame: pd.DataFrame,
    *,
    tickers: list[str],
    start: str,
    end: str,
    adjustment: str,
) -> pd.DataFrame:
    required = {"Ticker", "Date", "Open", "Close"}
    if adjustment == "adjusted":
        required.add("AdjClose")
    missing = sorted(required - set(frame.columns))
    if missing:
        raise AssertionError(f"materialized market snapshot missing session-state columns: {missing}")
    data = frame.copy()
    data["Ticker"] = data["Ticker"].astype(str)
    data["Date"] = pd.to_datetime(data["Date"], errors="raise").dt.tz_localize(None)
    selected = data[
        data["Ticker"].isin(tickers) & (data["Date"] >= pd.Timestamp(start)) & (data["Date"] <= pd.Timestamp(end))
    ].copy()
    present = set(selected["Ticker"].unique())
    absent = [ticker for ticker in tickers if ticker not in present]
    if absent:
        raise AssertionError(f"requested tickers absent from materialized snapshot/date range: {absent}")
    return selected.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def build_baseline(
    frame: pd.DataFrame,
    *,
    tickers: list[str],
    start: str,
    end: str,
    half_life: int,
    min_periods: int,
    trading_days: int,
    adjustment: str,
) -> dict[str, Any]:
    selected = select_prices(
        frame,
        tickers=tickers,
        start=start,
        end=end,
        adjustment=adjustment,
    )
    returns = decompose_daily_sessions(selected, adjustment=adjustment)
    featured = add_session_tilt(returns, half_life=half_life, min_periods=min_periods)
    summary = annualized_session_summary(returns, trading_days=trading_days)

    results: list[dict[str, Any]] = []
    tilt_column = f"session_tilt_{half_life}"
    for row in summary.to_dict(orient="records"):
        ticker = str(row["Ticker"])
        ticker_feature = featured[(featured["Ticker"] == ticker) & featured[tilt_column].notna()]
        latest = ticker_feature.iloc[-1] if not ticker_feature.empty else None
        results.append(
            {
                **row,
                "first_date": str(selected.loc[selected["Ticker"] == ticker, "Date"].min().date()),
                "last_date": str(selected.loc[selected["Ticker"] == ticker, "Date"].max().date()),
                "latest_session_tilt_date": None if latest is None else str(latest["Date"].date()),
                "latest_session_tilt": None if latest is None else float(latest[tilt_column]),
            }
        )

    return {
        "schema_version": "investor2.session-state-baseline.v3",
        "specification": {
            "tickers": tickers,
            "start": start,
            "end": end,
            "trading_days_per_year": trading_days,
            "session_tilt_half_life": half_life,
            "session_tilt_min_periods": min_periods,
            "adjustment": adjustment,
            "adjustment_formula": (
                "AdjustedOpen = Open * (AdjClose / Close); AdjustedClose = AdjClose"
                if adjustment == "adjusted"
                else "AdjustedOpen = Open; AdjustedClose = Close"
            ),
            "annualization_primary": "arithmetic mean daily component * trading_days_per_year",
            "annualization_sensitivity": "exp(mean log component * trading_days_per_year) - 1",
        },
        "results": results,
    }


def main() -> None:
    args = parse_args()
    regions = _string_list(args.market_regions)
    tickers = _string_list(args.tickers)
    snapshots = [MarketSnapshot(root) for root in args.market_snapshot_dir]
    manifests = [load_manifest(snapshot) for snapshot in snapshots]
    validate_snapshot_coverage(manifests, start=args.start, end=args.end)
    prices = load_prices_from_snapshots(snapshots, regions=regions)
    payload = build_baseline(
        prices,
        tickers=tickers,
        start=args.start,
        end=args.end,
        half_life=args.half_life,
        min_periods=args.min_periods,
        trading_days=args.trading_days,
        adjustment=args.adjustment,
    )
    payload["source_snapshots"] = [
        {
            "schema_version": manifest.get("schema_version"),
            "source": manifest.get("source"),
            "fetched_at_utc": manifest.get("fetched_at_utc"),
            "start": manifest.get("start"),
            "end_exclusive": manifest.get("end_exclusive"),
            "storage_contract": manifest.get("storage_contract"),
            "market_regions": regions,
        }
        for manifest in manifests
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "tickers": tickers,
                "results": len(payload["results"]),
                "snapshot_count": len(snapshots),
            }
        )
    )


if __name__ == "__main__":
    main()
