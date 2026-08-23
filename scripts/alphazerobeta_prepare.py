#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.market_snapshot import MarketSnapshot, load_benchmark, load_manifest, load_prices

ROLLING_WINDOWS = (5, 20, 60)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a PIT-safe AlphaZeroBeta panel from local files or a materialized central market cache."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prices-csv", type=Path)
    source.add_argument("--market-snapshot-dir", type=Path, help="Materialized central HF Storage Bucket snapshot")
    parser.add_argument("--benchmark-csv", type=Path, help="Required with --prices-csv")
    parser.add_argument("--market-regions", default="us", help="Comma-separated cached price regions")
    parser.add_argument("--output", required=True, type=Path, help="Output .npz path")
    parser.add_argument("--manifest", type=Path, help="Defaults to <output>.manifest.json")
    parser.add_argument("--max-assets", type=int, default=64)
    parser.add_argument(
        "--universe-cutoff", required=True, help="Only data on/before this date chooses the liquid universe"
    )
    parser.add_argument("--start", help="Optional inclusive panel start date")
    parser.add_argument("--end", help="Optional inclusive panel end date")
    return parser.parse_args()


def normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "AdjustmentClose": "Close",
        "AdjustmentVolume": "Volume",
        "Ticker": "Code",
        "code": "Code",
        "date": "Date",
    }
    normalized = frame.rename(
        columns={key: value for key, value in aliases.items() if key in frame.columns and value not in frame.columns}
    ).copy()
    if "AdjClose" in normalized.columns:
        adjusted = pd.to_numeric(normalized["AdjClose"], errors="coerce")
        if "Close" in normalized.columns:
            normalized["Close"] = adjusted.fillna(pd.to_numeric(normalized["Close"], errors="coerce"))
        else:
            normalized["Close"] = adjusted
    required = {"Code", "Date", "Close", "Volume"}
    missing = sorted(required - set(normalized.columns))
    if missing:
        raise AssertionError(f"prices input missing columns: {missing}")
    out = normalized[["Code", "Date", "Close", "Volume"]].copy()
    out["Code"] = out["Code"].astype(str)
    out["Date"] = pd.to_datetime(out["Date"], errors="raise").dt.tz_localize(None)
    out["Close"] = pd.to_numeric(out["Close"], errors="raise")
    out["Volume"] = pd.to_numeric(out["Volume"], errors="raise")
    out = out[(out["Close"] > 0) & (out["Volume"] >= 0)].sort_values(["Code", "Date"])
    if out.duplicated(["Code", "Date"]).any():
        raise AssertionError("duplicate Code/Date rows")
    return out


def normalize_prices(path: Path) -> pd.DataFrame:
    return normalize_price_frame(pd.read_csv(path))


def normalize_benchmark_frame(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {"AdjustmentClose": "Close", "date": "Date"}
    normalized = frame.rename(
        columns={key: value for key, value in aliases.items() if key in frame.columns and value not in frame.columns}
    ).copy()
    if "AdjClose" in normalized.columns:
        adjusted = pd.to_numeric(normalized["AdjClose"], errors="coerce")
        if "Close" in normalized.columns:
            normalized["Close"] = adjusted.fillna(pd.to_numeric(normalized["Close"], errors="coerce"))
        else:
            normalized["Close"] = adjusted
    required = {"Date", "Close"}
    missing = sorted(required - set(normalized.columns))
    if missing:
        raise AssertionError(f"benchmark input missing columns: {missing}")
    out = normalized[["Date", "Close"]].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="raise").dt.tz_localize(None)
    out["Close"] = pd.to_numeric(out["Close"], errors="raise")
    out = out[out["Close"] > 0].sort_values("Date")
    if out["Date"].duplicated().any():
        raise AssertionError("duplicate benchmark dates")
    out["BenchmarkReturn"] = np.log(out["Close"]).diff()
    return out


def normalize_benchmark(path: Path) -> pd.DataFrame:
    return normalize_benchmark_frame(pd.read_csv(path))


def load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if args.market_snapshot_dir:
        regions = [value.strip().lower() for value in args.market_regions.split(",") if value.strip()]
        snapshot = MarketSnapshot(args.market_snapshot_dir)
        snapshot_manifest = load_manifest(snapshot)
        return (
            normalize_price_frame(load_prices(snapshot, regions=regions)),
            normalize_benchmark_frame(load_benchmark(snapshot)),
            {
                "source": "central-hf-storage-bucket-materialization",
                "market_snapshot_dir": str(args.market_snapshot_dir),
                "market_regions": regions,
                "snapshot_fetched_at_utc": snapshot_manifest.get("fetched_at_utc"),
                "snapshot_ticker_count": snapshot_manifest.get("ticker_count"),
                "storage_contract": snapshot_manifest.get("storage_contract"),
            },
        )
    if args.prices_csv is None or args.benchmark_csv is None:
        raise ValueError("--benchmark-csv is required with --prices-csv")
    return (
        normalize_prices(args.prices_csv),
        normalize_benchmark(args.benchmark_csv),
        {
            "source": "local-csv",
            "prices_csv": str(args.prices_csv),
            "prices_sha256": sha256_file(args.prices_csv),
            "benchmark_csv": str(args.benchmark_csv),
            "benchmark_sha256": sha256_file(args.benchmark_csv),
        },
    )


def choose_universe(prices: pd.DataFrame, cutoff: pd.Timestamp, max_assets: int) -> list[str]:
    if max_assets < 2:
        raise AssertionError("max-assets must be at least 2")
    pre = prices[prices["Date"] <= cutoff].copy()
    if pre.empty:
        raise AssertionError("no price rows on/before universe cutoff")
    pre["DollarVolume"] = pre["Close"] * pre["Volume"]
    stats = pre.groupby("Code", observed=True).agg(days=("Date", "nunique"), adv=("DollarVolume", "mean"))
    min_days = min(60, int(stats["days"].max()))
    eligible = stats[stats["days"] >= min_days].sort_values(["adv", "days"], ascending=False)
    codes = eligible.head(max_assets).index.astype(str).tolist()
    if len(codes) < 2:
        raise AssertionError("fewer than two eligible assets")
    return codes


def build_asset_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("Date").set_index("Date")
    ret = np.log(g["Close"]).diff()
    log_volume = np.log1p(g["Volume"])
    features = {"log_return": ret, "log_volume": log_volume}
    for window in ROLLING_WINDOWS:
        features[f"ret_mean_{window}"] = ret.rolling(window).mean()
        features[f"ret_std_{window}"] = ret.rolling(window).std(ddof=0)
        features[f"momentum_{window}"] = np.log(g["Close"] / g["Close"].shift(window))
        features[f"vol_mean_{window}"] = log_volume.rolling(window).mean()
        features[f"vol_std_{window}"] = log_volume.rolling(window).std(ddof=0)
    frame = pd.DataFrame(features)
    frame["asset_return"] = ret
    return frame.replace([np.inf, -np.inf], np.nan)


def cross_sectional_zscore(panel: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    result = panel.copy()
    for column in feature_columns:
        grouped = result.groupby("Date", observed=True)[column]
        mean = grouped.transform("mean")
        std = grouped.transform(lambda values: values.std(ddof=0)).replace(0.0, np.nan)
        result[column] = ((result[column] - mean) / std).fillna(0.0)
    return result


def main() -> None:
    args = parse_args()
    prices, benchmark, source_metadata = load_inputs(args)
    cutoff = pd.Timestamp(args.universe_cutoff)
    codes = choose_universe(prices, cutoff, args.max_assets)
    selected = prices[prices["Code"].isin(codes)].copy()
    pieces = []
    for code, group in selected.groupby("Code", observed=True):
        feature_frame = build_asset_features(group).reset_index()
        feature_frame["Code"] = str(code)
        pieces.append(feature_frame)
    panel = pd.concat(pieces, ignore_index=True)
    if args.start:
        panel = panel[panel["Date"] >= pd.Timestamp(args.start)]
    if args.end:
        panel = panel[panel["Date"] <= pd.Timestamp(args.end)]
    feature_columns = [column for column in panel.columns if column not in {"Date", "Code", "asset_return"}]
    panel = cross_sectional_zscore(panel, feature_columns)
    counts = panel.groupby("Date", observed=True)["Code"].nunique()
    common_dates = counts[counts == len(codes)].index.sort_values()
    panel = panel[panel["Date"].isin(common_dates)].dropna(subset=feature_columns + ["asset_return"])
    counts = panel.groupby("Date", observed=True)["Code"].nunique()
    common_dates = counts[counts == len(codes)].index.sort_values()
    panel = panel[panel["Date"].isin(common_dates)]
    bench = benchmark.set_index("Date").reindex(common_dates)
    valid_dates = bench["BenchmarkReturn"].dropna().index
    panel = panel[panel["Date"].isin(valid_dates)]
    common_dates = pd.DatetimeIndex(valid_dates)
    if len(common_dates) < 252:
        raise AssertionError(f"only {len(common_dates)} aligned trading days; need at least 252")
    code_order = sorted(codes)
    panel = panel.set_index(["Date", "Code"]).sort_index()
    features = np.stack(
        [panel.loc[(common_dates, code), feature_columns].to_numpy(dtype=np.float32) for code in code_order], axis=1
    )
    returns = np.stack(
        [panel.loc[(common_dates, code), "asset_return"].to_numpy(dtype=np.float32) for code in code_order], axis=1
    )
    benchmark_returns = benchmark.set_index("Date").loc[common_dates, "BenchmarkReturn"].to_numpy(dtype=np.float32)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        dates=np.asarray(common_dates.strftime("%Y-%m-%d"), dtype="U10"),
        codes=np.asarray(code_order, dtype="U32"),
        feature_names=np.asarray(feature_columns, dtype="U64"),
        features=features,
        returns=returns,
        benchmark=benchmark_returns,
    )
    manifest = args.manifest or args.output.with_suffix(args.output.suffix + ".manifest.json")
    write_json(
        manifest,
        {
            "schema_version": "investor2.alphazerobeta-prepared-dataset.v2",
            **source_metadata,
            "universe_cutoff": str(cutoff.date()),
            "selection_rule": "top mean price*volume on/before cutoff, minimum available-history gate",
            "selected_codes": code_order,
            "date_start": str(common_dates[0].date()),
            "date_end": str(common_dates[-1].date()),
            "trading_days": len(common_dates),
            "feature_names": feature_columns,
            "shape": {"T": int(features.shape[0]), "N": int(features.shape[1]), "F": int(features.shape[2])},
            "dataset_sha256": sha256_file(args.output),
            "notes": [
                "Universe selection uses only data at or before universe_cutoff.",
                "Features use backward-looking rolling windows and same-day cross-sectional normalization only.",
                "No backward fill is used.",
                "Materialized central cache inputs do not access Yahoo during panel preparation.",
            ],
        },
    )
    print(json.dumps({"dataset": str(args.output), "manifest": str(manifest), "shape": list(features.shape)}))


if __name__ == "__main__":
    main()
