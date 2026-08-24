#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.session_state_baseline import select_prices, validate_snapshot_coverage
from src.research.market_snapshot import MarketSnapshot, load_manifest, load_prices_from_snapshots
from src.research.session_state import add_session_tilt, decompose_daily_sessions


def _csv(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("at least one value is required")
    return values


def _costs(raw: str) -> list[float]:
    values = [float(value) for value in _csv(raw)]
    if any(value < 0 for value in values):
        raise ValueError("costs must be non-negative")
    if len(values) != len(set(values)):
        raise ValueError("duplicate costs are not allowed")
    return values


def _corr(left: pd.Series, right: pd.Series) -> float | None:
    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].std(ddof=1) == 0 or pair.iloc[:, 1].std(ddof=1) == 0:
        return None
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))


def _fit_ols(feature: pd.Series, target: pd.Series) -> tuple[float, float]:
    frame = pd.DataFrame({"x": feature, "y": target}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 20:
        raise AssertionError("at least 20 training observations are required")
    design = np.column_stack([np.ones(len(frame)), frame["x"].to_numpy(dtype=float)])
    coeff, *_ = np.linalg.lstsq(design, frame["y"].to_numpy(dtype=float), rcond=None)
    return float(coeff[0]), float(coeff[1])


def _mse(actual: pd.Series, predicted: pd.Series | np.ndarray) -> float:
    left = actual.to_numpy(dtype=float)
    right = np.asarray(predicted, dtype=float)
    return float(np.mean(np.square(left - right)))


def _performance(returns: pd.Series, benchmark: pd.Series, *, trading_days: int) -> dict[str, Any]:
    data = pd.DataFrame({"strategy": returns, "benchmark": benchmark}).dropna(subset=["strategy"])
    if data.empty:
        raise AssertionError("strategy has no OOS observations")
    strategy = data["strategy"].astype(float)
    equity = (1.0 + strategy).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    std = strategy.std(ddof=1)
    sharpe = None if len(strategy) < 2 or std == 0 else float(np.sqrt(trading_days) * strategy.mean() / std)
    benchmark_pair = data.dropna(subset=["benchmark"])
    beta = None
    corr = None
    if len(benchmark_pair) >= 3 and benchmark_pair["benchmark"].var(ddof=1) > 0:
        beta = float(
            benchmark_pair[["strategy", "benchmark"]].cov(ddof=1).loc["strategy", "benchmark"]
            / benchmark_pair["benchmark"].var(ddof=1)
        )
        corr = _corr(benchmark_pair["strategy"], benchmark_pair["benchmark"])
    return {
        "observations": int(len(strategy)),
        "total_return": float(equity.iloc[-1] - 1.0),
        "annualized_arithmetic_return": float(strategy.mean() * trading_days),
        "annualized_compound_return": float(equity.iloc[-1] ** (trading_days / len(strategy)) - 1.0),
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "beta_to_benchmark_close_to_close": beta,
        "correlation_to_benchmark_close_to_close": corr,
    }


def prepare_rows(
    prices: pd.DataFrame,
    *,
    tickers: list[str],
    start: str,
    end: str,
    adjustment: str,
    half_life: int,
    min_periods: int,
) -> pd.DataFrame:
    selected = select_prices(prices, tickers=tickers, start=start, end=end, adjustment=adjustment)
    returns = decompose_daily_sessions(selected, adjustment=adjustment)
    featured = add_session_tilt(returns, half_life=half_life, min_periods=min_periods)
    tilt = f"session_tilt_{half_life}"
    pieces: list[pd.DataFrame] = []
    for _, group in featured.groupby("Ticker", observed=True, sort=False):
        item = group.sort_values("Date").copy()
        item["target_date"] = item["Date"].shift(-1)
        item["target_session_spread"] = item["session_spread"].shift(-1)
        item["target_close_to_close"] = item["r_close_to_close"].shift(-1)
        item["feature_session_tilt"] = item[tilt]
        item["feature_lag_session_spread"] = item["session_spread"]
        pieces.append(item)
    return pd.concat(pieces, ignore_index=True)


def evaluate(
    prices: pd.DataFrame,
    *,
    tickers: list[str],
    benchmark_ticker: str,
    start: str,
    end: str,
    train_start: str,
    test_start: str,
    adjustment: str,
    half_life: int,
    min_periods: int,
    trading_days: int,
    costs_bps_per_side: list[float],
    primary_cost_bps_per_side: float,
    stress_cost_bps_per_side: float,
    one_way_turnover_per_asset_day: float,
    minimum_ic: float,
    minimum_mse_improvement: float,
    minimum_positive_ic_tickers: int,
    minimum_primary_ann_return: float,
    minimum_primary_sharpe: float,
    minimum_stress_ann_return: float,
    minimum_stress_sharpe: float,
) -> dict[str, Any]:
    if benchmark_ticker not in tickers:
        raise ValueError("benchmark_ticker must be included in tickers")
    if primary_cost_bps_per_side not in costs_bps_per_side:
        raise ValueError("primary cost must be included in cost sensitivity list")
    if stress_cost_bps_per_side not in costs_bps_per_side:
        raise ValueError("stress cost must be included in cost sensitivity list")
    if one_way_turnover_per_asset_day < 0:
        raise ValueError("one_way_turnover_per_asset_day must be non-negative")
    if minimum_positive_ic_tickers < 0 or minimum_positive_ic_tickers > len(tickers):
        raise ValueError("minimum_positive_ic_tickers must be within the ticker universe size")

    rows = prepare_rows(
        prices,
        tickers=tickers,
        start=start,
        end=end,
        adjustment=adjustment,
        half_life=half_life,
        min_periods=min_periods,
    )
    required = [
        "target_date",
        "target_session_spread",
        "feature_session_tilt",
        "feature_lag_session_spread",
    ]
    usable = rows.dropna(subset=required).replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    train = usable[
        (usable["target_date"] >= pd.Timestamp(train_start)) & (usable["target_date"] < pd.Timestamp(test_start))
    ].copy()
    test = usable[
        (usable["target_date"] >= pd.Timestamp(test_start)) & (usable["target_date"] <= pd.Timestamp(end))
    ].copy()
    if len(train) < 100 or len(test) < 100:
        raise AssertionError(f"insufficient train/test rows: train={len(train)} test={len(test)}")

    train_mean = float(train["target_session_spread"].mean())
    tilt_intercept, tilt_beta = _fit_ols(train["feature_session_tilt"], train["target_session_spread"])
    lag_intercept, lag_beta = _fit_ols(train["feature_lag_session_spread"], train["target_session_spread"])
    pred_intercept = np.full(len(test), train_mean)
    pred_tilt = tilt_intercept + tilt_beta * test["feature_session_tilt"].to_numpy(dtype=float)
    pred_lag = lag_intercept + lag_beta * test["feature_lag_session_spread"].to_numpy(dtype=float)
    mse_intercept = _mse(test["target_session_spread"], pred_intercept)
    mse_tilt = _mse(test["target_session_spread"], pred_tilt)
    mse_lag = _mse(test["target_session_spread"], pred_lag)
    improvement_intercept = 1.0 - mse_tilt / mse_intercept
    improvement_lag = 1.0 - mse_tilt / mse_lag
    ic = _corr(test["feature_session_tilt"], test["target_session_spread"])

    per_ticker: list[dict[str, Any]] = []
    for ticker, group in test.groupby("Ticker", observed=True):
        ticker_ic = _corr(group["feature_session_tilt"], group["target_session_spread"])
        per_ticker.append(
            {
                "ticker": str(ticker),
                "observations": int(len(group)),
                "information_coefficient": ticker_ic,
                "gross_sign_strategy_ann_arithmetic": float(
                    (np.sign(group["feature_session_tilt"]) * group["target_session_spread"]).mean() * trading_days
                ),
            }
        )

    benchmark = test.loc[
        test["Ticker"] == benchmark_ticker,
        ["target_date", "target_close_to_close"],
    ].drop_duplicates("target_date")
    if benchmark.empty:
        raise AssertionError(f"benchmark ticker absent from OOS rows: {benchmark_ticker}")

    strategies: list[dict[str, Any]] = []
    for cost_bps in costs_bps_per_side:
        cost = one_way_turnover_per_asset_day * cost_bps / 10_000.0
        work = test.copy()
        signal = np.sign(work["feature_session_tilt"].to_numpy(dtype=float))
        lag_signal = np.sign(work["feature_lag_session_spread"].to_numpy(dtype=float))
        work["session_tilt_net"] = signal * work["target_session_spread"] - np.abs(signal) * cost
        work["lag_spread_net"] = lag_signal * work["target_session_spread"] - np.abs(lag_signal) * cost
        portfolio = (
            work.groupby("target_date", observed=True)[["session_tilt_net", "lag_spread_net"]].mean().reset_index()
        )
        portfolio = portfolio.merge(benchmark, on="target_date", how="left", validate="one_to_one")
        strategies.append(
            {
                "cost_bps_per_side": cost_bps,
                "cost_model": "fixed one-way turnover per active asset-day",
                "session_tilt": _performance(
                    portfolio["session_tilt_net"], portfolio["target_close_to_close"], trading_days=trading_days
                ),
                "lag_session_spread_baseline": _performance(
                    portfolio["lag_spread_net"], portfolio["target_close_to_close"], trading_days=trading_days
                ),
                "one_way_turnover_per_asset_day": one_way_turnover_per_asset_day,
            }
        )

    positive_ic_tickers = sum(
        1
        for row in per_ticker
        if row["information_coefficient"] is not None and row["information_coefficient"] > minimum_ic
    )
    primary = next(row for row in strategies if row["cost_bps_per_side"] == primary_cost_bps_per_side)
    stress = next(row for row in strategies if row["cost_bps_per_side"] == stress_cost_bps_per_side)
    predictive_pass = bool(
        ic is not None
        and ic > minimum_ic
        and improvement_intercept > minimum_mse_improvement
        and improvement_lag > minimum_mse_improvement
    )
    breadth_pass = positive_ic_tickers >= minimum_positive_ic_tickers
    primary_perf = primary["session_tilt"]
    primary_economic_pass = bool(
        primary_perf["annualized_arithmetic_return"] > minimum_primary_ann_return
        and primary_perf["sharpe"] is not None
        and primary_perf["sharpe"] > minimum_primary_sharpe
    )
    stress_perf = stress["session_tilt"]
    stress_economic_pass = bool(
        stress_perf["annualized_arithmetic_return"] > minimum_stress_ann_return
        and stress_perf["sharpe"] is not None
        and stress_perf["sharpe"] > minimum_stress_sharpe
    )
    if predictive_pass and breadth_pass and primary_economic_pass and stress_economic_pass:
        decision = "USE"
    elif predictive_pass or (ic is not None and ic > minimum_ic and primary_economic_pass):
        decision = "CONDITION"
    else:
        decision = "REJECT"

    return {
        "schema_version": "investor2.session-state-oos.v2",
        "decision": decision,
        "decision_scope": "daily-bar SessionTilt under the supplied historical contract",
        "specification": {
            "tickers": tickers,
            "benchmark_ticker": benchmark_ticker,
            "start": start,
            "end": end,
            "train_start": train_start,
            "test_start": test_start,
            "test_end": end,
            "adjustment": adjustment,
            "half_life": half_life,
            "min_periods": min_periods,
            "trading_days": trading_days,
            "costs_bps_per_side": costs_bps_per_side,
            "primary_cost_bps_per_side": primary_cost_bps_per_side,
            "stress_cost_bps_per_side": stress_cost_bps_per_side,
            "one_way_turnover_per_asset_day": one_way_turnover_per_asset_day,
            "minimum_ic": minimum_ic,
            "minimum_mse_improvement": minimum_mse_improvement,
            "minimum_positive_ic_tickers": minimum_positive_ic_tickers,
            "minimum_primary_ann_return": minimum_primary_ann_return,
            "minimum_primary_sharpe": minimum_primary_sharpe,
            "minimum_stress_ann_return": minimum_stress_ann_return,
            "minimum_stress_sharpe": minimum_stress_sharpe,
            "forecast_target": "next trading day's r_overnight - r_intraday",
            "feature_availability": "SessionTilt through close(t) predicts sessions on t+1",
            "capacity_status": "NOT_TESTED_DAILY_BARS",
        },
        "sample": {"train_rows": int(len(train)), "test_rows": int(len(test))},
        "predictive": {
            "information_coefficient": ic,
            "ols_session_tilt": {"intercept": tilt_intercept, "beta": tilt_beta},
            "ols_lag_session_spread": {"intercept": lag_intercept, "beta": lag_beta},
            "mse_intercept": mse_intercept,
            "mse_session_tilt": mse_tilt,
            "mse_lag_session_spread": mse_lag,
            "mse_improvement_vs_intercept": improvement_intercept,
            "mse_improvement_vs_lag_session_spread": improvement_lag,
            "positive_ic_tickers": positive_ic_tickers,
            "ticker_count": len(per_ticker),
        },
        "per_ticker": per_ticker,
        "strategies": strategies,
        "decision_tests": {
            "predictive_pass": predictive_pass,
            "breadth_pass": breadth_pass,
            "primary_cost_economic_pass": primary_economic_pass,
            "stress_cost_economic_pass": stress_economic_pass,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate SessionTilt under an explicit historical OOS contract.")
    parser.add_argument("--market-snapshot-dir", required=True, type=Path, action="append")
    parser.add_argument("--market-regions", required=True)
    parser.add_argument("--tickers", required=True)
    parser.add_argument("--benchmark-ticker", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--train-start", required=True)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--adjustment", required=True, choices=["adjusted", "raw"])
    parser.add_argument("--half-life", required=True, type=int)
    parser.add_argument("--min-periods", required=True, type=int)
    parser.add_argument("--trading-days", required=True, type=int)
    parser.add_argument("--costs-bps-per-side", required=True)
    parser.add_argument("--primary-cost-bps-per-side", required=True, type=float)
    parser.add_argument("--stress-cost-bps-per-side", required=True, type=float)
    parser.add_argument("--one-way-turnover-per-asset-day", required=True, type=float)
    parser.add_argument("--minimum-ic", required=True, type=float)
    parser.add_argument("--minimum-mse-improvement", required=True, type=float)
    parser.add_argument("--minimum-positive-ic-tickers", required=True, type=int)
    parser.add_argument("--minimum-primary-ann-return", required=True, type=float)
    parser.add_argument("--minimum-primary-sharpe", required=True, type=float)
    parser.add_argument("--minimum-stress-ann-return", required=True, type=float)
    parser.add_argument("--minimum-stress-sharpe", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = _csv(args.tickers)
    regions = _csv(args.market_regions)
    snapshots = [MarketSnapshot(path) for path in args.market_snapshot_dir]
    manifests = [load_manifest(snapshot) for snapshot in snapshots]
    validate_snapshot_coverage(manifests, start=args.start, end=args.end)
    prices = load_prices_from_snapshots(snapshots, regions=regions)
    payload = evaluate(
        prices,
        tickers=tickers,
        benchmark_ticker=args.benchmark_ticker,
        start=args.start,
        end=args.end,
        train_start=args.train_start,
        test_start=args.test_start,
        adjustment=args.adjustment,
        half_life=args.half_life,
        min_periods=args.min_periods,
        trading_days=args.trading_days,
        costs_bps_per_side=_costs(args.costs_bps_per_side),
        primary_cost_bps_per_side=args.primary_cost_bps_per_side,
        stress_cost_bps_per_side=args.stress_cost_bps_per_side,
        one_way_turnover_per_asset_day=args.one_way_turnover_per_asset_day,
        minimum_ic=args.minimum_ic,
        minimum_mse_improvement=args.minimum_mse_improvement,
        minimum_positive_ic_tickers=args.minimum_positive_ic_tickers,
        minimum_primary_ann_return=args.minimum_primary_ann_return,
        minimum_primary_sharpe=args.minimum_primary_sharpe,
        minimum_stress_ann_return=args.minimum_stress_ann_return,
        minimum_stress_sharpe=args.minimum_stress_sharpe,
    )
    payload["source_snapshots"] = manifests
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "decision": payload["decision"], **payload["predictive"]}))


if __name__ == "__main__":
    main()
