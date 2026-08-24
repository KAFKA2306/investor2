#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import alphazerobeta_prepare as prepare
from src.research.market_snapshot import MarketSnapshot, load_manifest, load_prices

QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute derived EDA statistics for the AlphaZeroBeta J-Quants validation."
    )
    parser.add_argument("--market-snapshot-dir", required=True, type=Path)
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def finite_series(values: object) -> pd.Series:
    series = pd.Series(np.asarray(values).reshape(-1))
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def describe(values: object) -> dict[str, float | int | None]:
    series = finite_series(values)
    total = int(len(series))
    valid = series.dropna()
    n = int(len(valid))
    if n == 0:
        return {"count_total": total, "count_valid": 0, "missing_rate": 1.0 if total else None}
    quantiles = valid.quantile(list(QUANTILES))
    q25 = float(quantiles.loc[0.25])
    q75 = float(quantiles.loc[0.75])
    iqr = q75 - q25
    if iqr == 0:
        iqr_outlier_rate = 0.0
    else:
        lo = q25 - 1.5 * iqr
        hi = q75 + 1.5 * iqr
        iqr_outlier_rate = float(((valid < lo) | (valid > hi)).mean())
    std = float(valid.std(ddof=0))
    mean = float(valid.mean())
    z3_rate = 0.0 if std == 0 else float((np.abs((valid - mean) / std) > 3.0).mean())
    return {
        "count_total": total,
        "count_valid": n,
        "missing_rate": float(1.0 - n / total) if total else None,
        "zero_rate_valid": float((valid == 0).mean()),
        "mean": mean,
        "std": std,
        "min": float(valid.min()),
        "p01": float(quantiles.loc[0.01]),
        "p05": float(quantiles.loc[0.05]),
        "p25": q25,
        "median": float(quantiles.loc[0.50]),
        "p75": q75,
        "p95": float(quantiles.loc[0.95]),
        "p99": float(quantiles.loc[0.99]),
        "max": float(valid.max()),
        "skew": float(valid.skew()) if n >= 3 else None,
        "kurtosis_excess": float(valid.kurt()) if n >= 4 else None,
        "iqr_outlier_rate": iqr_outlier_rate,
        "abs_z_gt_3_rate": z3_rate,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def column_quality(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in frame.columns:
        series = frame[column]
        record: dict[str, object] = {
            "column": str(column),
            "dtype": str(series.dtype),
            "rows": int(len(series)),
            "missing_count": int(series.isna().sum()),
            "missing_rate": float(series.isna().mean()),
        }
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().any():
            record["numeric_valid_count"] = int(numeric.notna().sum())
            record["zero_rate_numeric_valid"] = float((numeric.dropna() == 0).mean())
        rows.append(record)
    return pd.DataFrame(rows).sort_values("column").reset_index(drop=True)


def ticker_stats(prices: pd.DataFrame) -> pd.DataFrame:
    ordered = prices.sort_values(["Code", "Date"]).copy()
    ordered["log_return"] = ordered.groupby("Code", observed=True)["Close"].transform(
        lambda values: np.log(values).diff()
    )
    grouped = ordered.groupby("Code", observed=True)
    base = grouped.agg(
        observations=("Date", "size"),
        date_start=("Date", "min"),
        date_end=("Date", "max"),
        close_mean=("Close", "mean"),
        close_median=("Close", "median"),
        volume_mean=("Volume", "mean"),
        volume_median=("Volume", "median"),
        zero_volume_rate=("Volume", lambda values: float((values == 0).mean())),
        return_observations=("log_return", "count"),
        return_mean=("log_return", "mean"),
        return_std=("log_return", lambda values: float(values.std(ddof=0))),
        return_skew=("log_return", "skew"),
    )
    kurt = (
        grouped["log_return"]
        .apply(lambda values: float(values.kurt()) if values.count() >= 4 else np.nan)
        .rename("return_kurtosis_excess")
    )
    quantiles = grouped["log_return"].quantile([0.01, 0.05, 0.50, 0.95, 0.99]).unstack()
    quantiles.columns = ["return_p01", "return_p05", "return_median", "return_p95", "return_p99"]
    abs10 = (
        grouped["log_return"]
        .apply(lambda values: float((values.dropna().abs() > np.log(1.10)).mean()) if values.notna().any() else np.nan)
        .rename("abs_return_gt_10pct_rate")
    )
    result = base.join(kurt).join(quantiles).join(abs10).reset_index()
    result["date_start"] = pd.to_datetime(result["date_start"]).dt.strftime("%Y-%m-%d")
    result["date_end"] = pd.to_datetime(result["date_end"]).dt.strftime("%Y-%m-%d")
    return result.sort_values("Code").reset_index(drop=True)


def full_market_stats(snapshot_dir: Path) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    snapshot = MarketSnapshot(snapshot_dir)
    manifest = load_manifest(snapshot)
    raw = load_prices(snapshot, regions=["jp"])
    quality = column_quality(raw)
    prices = prepare.normalize_price_frame(raw)
    del raw

    ordered = prices.sort_values(["Code", "Date"]).copy()
    ordered["log_return"] = ordered.groupby("Code", observed=True)["Close"].transform(
        lambda values: np.log(values).diff()
    )
    returns = ordered.dropna(subset=["log_return"])
    grouped_returns = returns.groupby("Date", observed=True)["log_return"]
    daily = grouped_returns.agg(
        cross_section_count="count",
        cross_section_mean="mean",
        cross_section_median="median",
        cross_section_std=lambda values: float(values.std(ddof=0)),
    )
    daily["cross_section_iqr"] = grouped_returns.quantile(0.75) - grouped_returns.quantile(0.25)

    by_ticker = ticker_stats(prices)
    payload: dict[str, object] = {
        "source_manifest": {
            "actual_date_range": manifest.get("actual_date_range"),
            "price_rows": manifest.get("price_rows"),
            "ticker_count": manifest.get("ticker_count"),
            "observed_market_days": manifest.get("observed_market_days"),
            "request_count": manifest.get("request_count"),
            "cache": manifest.get("cache"),
        },
        "normalized_market": {
            "rows": int(len(prices)),
            "tickers": int(prices["Code"].nunique()),
            "market_days": int(prices["Date"].nunique()),
            "date_start": str(prices["Date"].min().date()),
            "date_end": str(prices["Date"].max().date()),
        },
        "close": describe(prices["Close"]),
        "volume": describe(prices["Volume"]),
        "log_return": {
            **describe(returns["log_return"]),
            "abs_gt_5pct_rate": float((returns["log_return"].abs() > np.log(1.05)).mean()),
            "abs_gt_10pct_rate": float((returns["log_return"].abs() > np.log(1.10)).mean()),
            "abs_gt_20pct_rate": float((returns["log_return"].abs() > np.log(1.20)).mean()),
        },
        "observations_per_ticker": describe(by_ticker["observations"]),
        "cross_sectional_daily_return_dispersion": {
            "std": describe(daily["cross_section_std"]),
            "iqr": describe(daily["cross_section_iqr"]),
            "count": describe(daily["cross_section_count"]),
        },
    }
    return payload, quality, by_ticker


def panel_stats(panel_path: Path) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    with np.load(panel_path, allow_pickle=False) as data:
        dates = data["dates"].astype(str)
        codes = data["codes"].astype(str)
        feature_names = data["feature_names"].astype(str)
        features = data["features"].astype(np.float64)
        returns = data["returns"].astype(np.float64)
        benchmark = data["benchmark"].astype(np.float64)

    feature_rows: list[dict[str, object]] = []
    for index, name in enumerate(feature_names):
        values = features[:, :, index]
        record: dict[str, object] = {"feature": str(name), **describe(values)}
        daily_mean = np.nanmean(values, axis=1)
        daily_std = np.nanstd(values, axis=1)
        record["daily_cross_section_mean_abs_mean"] = float(np.nanmean(np.abs(daily_mean)))
        record["daily_cross_section_std_mean"] = float(np.nanmean(daily_std))
        record["daily_cross_section_std_std"] = float(np.nanstd(daily_std))
        record["abs_value_gt_3_rate"] = float(np.nanmean(np.abs(values) > 3.0))
        feature_rows.append(record)
    feature_stats = pd.DataFrame(feature_rows)

    asset_rows: list[dict[str, object]] = []
    for index, code in enumerate(codes):
        record: dict[str, object] = {"Code": str(code), **describe(returns[:, index])}
        record["annualized_volatility"] = float(np.nanstd(returns[:, index], ddof=0) * np.sqrt(252.0))
        asset_rows.append(record)
    asset_stats = pd.DataFrame(asset_rows).sort_values("Code").reset_index(drop=True)

    daily_dispersion = np.nanstd(returns, axis=1)
    payload: dict[str, object] = {
        "shape": {"T": int(features.shape[0]), "N": int(features.shape[1]), "F": int(features.shape[2])},
        "date_start": str(dates[0]),
        "date_end": str(dates[-1]),
        "feature_count": int(len(feature_names)),
        "feature_missing_total": int(np.isnan(features).sum()),
        "return_missing_total": int(np.isnan(returns).sum()),
        "benchmark_missing_total": int(np.isnan(benchmark).sum()),
        "asset_return": {
            **describe(returns),
            "abs_gt_5pct_rate": float(np.nanmean(np.abs(returns) > np.log(1.05))),
            "abs_gt_10pct_rate": float(np.nanmean(np.abs(returns) > np.log(1.10))),
            "abs_gt_20pct_rate": float(np.nanmean(np.abs(returns) > np.log(1.20))),
        },
        "benchmark_return": describe(benchmark),
        "daily_cross_section_return_std": describe(daily_dispersion),
        "feature_daily_cross_section_sanity": {
            "mean_abs_cross_section_mean_across_features": float(
                feature_stats["daily_cross_section_mean_abs_mean"].mean()
            ),
            "mean_cross_section_std_across_features": float(feature_stats["daily_cross_section_std_mean"].mean()),
        },
    }
    return payload, feature_stats, asset_stats


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    market, raw_quality, per_ticker = full_market_stats(args.market_snapshot_dir)
    panel, feature_stats, panel_asset_stats = panel_stats(args.panel)

    raw_quality.to_csv(args.output_dir / "raw_column_quality.csv", index=False)
    per_ticker.to_csv(args.output_dir / "per_ticker_stats.csv", index=False)
    feature_stats.to_csv(args.output_dir / "panel_feature_stats.csv", index=False)
    panel_asset_stats.to_csv(args.output_dir / "panel_asset_return_stats.csv", index=False)

    payload = {
        "schema_version": "investor2.alphazerobeta-eda.v1",
        "claim_boundary": (
            "Derived descriptive statistics from the frozen J-Quants Free surrogate validation window; "
            "no raw J-Quants rows are published."
        ),
        "full_market": market,
        "prepared_panel": panel,
        "files": {
            "raw_column_quality": "raw_column_quality.csv",
            "per_ticker_stats": "per_ticker_stats.csv",
            "panel_feature_stats": "panel_feature_stats.csv",
            "panel_asset_return_stats": "panel_asset_return_stats.csv",
        },
    }
    write_json(args.output_dir / "summary.json", payload)
    print(
        json.dumps(
            {
                "status": "completed",
                "market_rows": market["normalized_market"]["rows"],
                "market_tickers": market["normalized_market"]["tickers"],
                "panel_shape": panel["shape"],
                "output_dir": str(args.output_dir),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
