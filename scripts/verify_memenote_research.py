#!/usr/bin/env python3
"""Reproduce testable memenote ideas on frozen investor2 evidence.

This module deliberately separates three things that the source articles can easily
blur together in casual use: a mathematically useful indicator, a tradable rule,
and an incremental predictive feature.  It reuses checked-in market snapshots and
does not create a second market-data authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]
CATALOG_PATH = ROOT / "data/research/memenote/hypothesis_catalog.json"
PRICE_PATH = ROOT / "docs/research/results/alphazerobeta_2024/raw/prices.csv"
PRICE_MANIFEST_PATH = ROOT / "docs/research/results/alphazerobeta_2024/source_manifest.json"
FUNDING_PATH = (
    ROOT
    / "data/ark-big-ideas/snapshots/bitcoin-derivatives-daily/0c4f7b0dfacea01cf9efd0935f08330fa6839d9d987a4b332a56fad180fda61e.json"
)

CROSS_ASSET_UNIVERSE = ("QQQ", "DIA", "IWM", "GLD", "TLT")
PRIMARY_LOOKBACK = 63
LOOKBACK_SENSITIVITY = (21, 63, 126)
TOP_K = 2
TRADING_COST_BPS = 15.0
VALIDATION_START = "2023-01-01"
VALIDATION_END = "2023-12-31"
TEST_START = "2024-01-01"
TEST_END = "2024-12-31"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def load_prices(path: Path = PRICE_PATH, manifest_path: Path = PRICE_MANIFEST_PATH) -> pd.DataFrame:
    manifest = load_json(manifest_path)
    expected_hash = str(manifest["normalized_prices_sha256"])
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(f"price snapshot hash mismatch: expected {expected_hash}, got {actual_hash}")

    frame = pd.read_csv(path, parse_dates=["Date"])
    required_columns = {"Code", "Date", "Close", "Volume"}
    if set(frame.columns) != required_columns:
        raise ValueError(f"unexpected price columns: {list(frame.columns)}")
    missing = sorted(set(CROSS_ASSET_UNIVERSE) - set(frame["Code"].unique()))
    if missing:
        raise ValueError(f"missing frozen universe members: {missing}")

    selected = frame.loc[frame["Code"].isin(CROSS_ASSET_UNIVERSE), ["Code", "Date", "Close"]]
    prices = selected.pivot(index="Date", columns="Code", values="Close").sort_index()
    prices = prices.loc[:, list(CROSS_ASSET_UNIVERSE)].dropna(how="any")
    if prices.empty or (prices <= 0).any().any():
        raise ValueError("prices must be non-empty and strictly positive")
    return prices


def raw_strength(prices: pd.DataFrame, lookback: int, method: str) -> pd.DataFrame:
    ratio = prices / prices.shift(lookback)
    if method == "log":
        return np.log(ratio)
    if method == "simple":
        return ratio - 1.0
    raise ValueError(f"unsupported strength method: {method}")


def centered_log_strength(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    strength = raw_strength(prices, lookback, "log")
    return strength.sub(strength.mean(axis=1), axis=0)


def month_end_signal_dates(index: pd.DatetimeIndex, first_valid: pd.Timestamp) -> list[pd.Timestamp]:
    eligible = index[index >= first_valid]
    if eligible.empty:
        return []
    grouped = pd.Series(eligible, index=eligible).groupby(eligible.to_period("M")).max()
    return [pd.Timestamp(value) for value in grouped.tolist()]


def target_schedule(
    prices: pd.DataFrame,
    *,
    lookback: int,
    method: str,
    top_k: int = TOP_K,
) -> dict[pd.Timestamp, pd.Series]:
    scores = raw_strength(prices, lookback, method)
    valid = scores.dropna(how="any")
    if valid.empty:
        raise ValueError("no valid signal observations")
    signal_dates = month_end_signal_dates(prices.index, valid.index[0])
    schedule: dict[pd.Timestamp, pd.Series] = {}
    for signal_date in signal_dates:
        position = prices.index.get_loc(signal_date)
        if not isinstance(position, (int, np.integer)) or position + 1 >= len(prices.index):
            continue
        execution_date = prices.index[int(position) + 1]
        row = scores.loc[signal_date].dropna()
        if len(row) < top_k:
            continue
        winners = row.nlargest(top_k).index
        target = pd.Series(0.0, index=prices.columns, dtype=float)
        target.loc[winners] = 1.0 / top_k
        schedule[execution_date] = target
    return schedule


def equal_weight_schedule(prices: pd.DataFrame, *, lookback: int) -> dict[pd.Timestamp, pd.Series]:
    score = raw_strength(prices, lookback, "log").dropna(how="any")
    if score.empty:
        raise ValueError("no valid baseline observations")
    target = pd.Series(1.0 / len(prices.columns), index=prices.columns, dtype=float)
    schedule: dict[pd.Timestamp, pd.Series] = {}
    for signal_date in month_end_signal_dates(prices.index, score.index[0]):
        position = prices.index.get_loc(signal_date)
        if not isinstance(position, (int, np.integer)) or position + 1 >= len(prices.index):
            continue
        schedule[prices.index[int(position) + 1]] = target.copy()
    return schedule


def simulate(
    prices: pd.DataFrame,
    schedule: dict[pd.Timestamp, pd.Series],
    *,
    trading_cost_bps: float,
) -> pd.DataFrame:
    asset_returns = prices.pct_change().fillna(0.0)
    weights = pd.Series(0.0, index=prices.columns, dtype=float)
    rows: list[dict[str, float | pd.Timestamp]] = []
    cost_rate = trading_cost_bps / 10_000.0

    for date, returns in asset_returns.iterrows():
        gross_return = float((weights * returns).sum())
        denominator = 1.0 + gross_return
        if denominator <= 0:
            raise ValueError("portfolio wealth became non-positive")
        drifted = weights * (1.0 + returns) / denominator
        turnover = 0.0
        if date in schedule:
            target = schedule[date]
            turnover = float((target - drifted).abs().sum())
            weights = target.copy()
        else:
            weights = drifted
        cost = turnover * cost_rate
        rows.append(
            {
                "date": date,
                "gross_return": gross_return,
                "net_return": gross_return - cost,
                "turnover": turnover,
                "exposure": float(weights.abs().sum()),
            }
        )

    result = pd.DataFrame(rows).set_index("date")
    return result


def _worst_compounded(returns: pd.Series, window: int) -> float | None:
    if len(returns) < window:
        return None
    values = (1.0 + returns).rolling(window).apply(np.prod, raw=True) - 1.0
    return float(values.min())


def metrics(result: pd.DataFrame, start: str, end: str) -> dict[str, float | int | None | str]:
    window = result.loc[start:end].copy()
    if window.empty:
        raise ValueError(f"empty evaluation window {start}..{end}")
    returns = window["net_return"].astype(float)
    n = len(returns)
    mean = float(returns.mean())
    volatility = float(returns.std(ddof=1))
    annualized_return = mean * 252.0
    annualized_volatility = volatility * math.sqrt(252.0)
    sharpe = annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0
    downside = returns.loc[returns < 0]
    downside_vol = float(downside.std(ddof=1)) * math.sqrt(252.0) if len(downside) > 1 else 0.0
    sortino = annualized_return / downside_vol if downside_vol > 0 else 0.0
    wealth = (1.0 + returns).cumprod()
    cumulative_return = float(wealth.iloc[-1] - 1.0)
    cagr = float(wealth.iloc[-1] ** (252.0 / n) - 1.0)
    drawdown = wealth / wealth.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else None
    return {
        "start": str(window.index[0].date()),
        "end": str(window.index[-1].date()),
        "sessions": n,
        "annualized_arithmetic_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_zero_rf": sharpe,
        "sortino_zero_rf": sortino,
        "cagr": cagr,
        "cumulative_return": cumulative_return,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
        "worst_1d": float(returns.min()),
        "worst_1w": _worst_compounded(returns, 5),
        "worst_1m": _worst_compounded(returns, 21),
        "turnover": float(window["turnover"].sum()),
        "rebalance_count": int((window["turnover"] > 1e-12).sum()),
        "positive_day_fraction": float((returns > 0).mean()),
        "mean_exposure": float(window["exposure"].mean()),
    }


def compare_allocation(prices: pd.DataFrame, lookback: int, method: str) -> dict[str, Any]:
    strategy = simulate(
        prices,
        target_schedule(prices, lookback=lookback, method=method),
        trading_cost_bps=TRADING_COST_BPS,
    )
    baseline = simulate(
        prices,
        equal_weight_schedule(prices, lookback=lookback),
        trading_cost_bps=TRADING_COST_BPS,
    )
    return {
        "validation": {
            "strategy": metrics(strategy, VALIDATION_START, VALIDATION_END),
            "baseline_equal_weight": metrics(baseline, VALIDATION_START, VALIDATION_END),
        },
        "test": {
            "strategy": metrics(strategy, TEST_START, TEST_END),
            "baseline_equal_weight": metrics(baseline, TEST_START, TEST_END),
        },
    }


def allocation_verdict(comparison: dict[str, Any]) -> str:
    validation = comparison["validation"]
    test = comparison["test"]

    def beats(period: dict[str, Any]) -> bool:
        strategy = period["strategy"]
        baseline = period["baseline_equal_weight"]
        return (
            strategy["cumulative_return"] > baseline["cumulative_return"]
            and strategy["sharpe_zero_rf"] > baseline["sharpe_zero_rf"]
        )

    if beats(validation) and beats(test):
        return "USE"
    if beats(validation) or beats(test):
        return "CONDITION"
    return "REJECT"


def ranking_agreement(prices: pd.DataFrame, lookback: int, top_k: int = TOP_K) -> float:
    simple = raw_strength(prices, lookback, "simple")
    log = raw_strength(prices, lookback, "log")
    valid = simple.dropna(how="any")
    agreements: list[bool] = []
    for date in month_end_signal_dates(prices.index, valid.index[0]):
        simple_top = set(simple.loc[date].nlargest(top_k).index)
        log_top = set(log.loc[date].nlargest(top_k).index)
        agreements.append(simple_top == log_top)
    if not agreements:
        raise ValueError("no ranking observations")
    return sum(agreements) / len(agreements)


def parameter_dependence_verdict(sensitivity: dict[str, Any]) -> str:
    test_returns = [
        float(payload["test"]["strategy"]["cumulative_return"])
        for payload in sensitivity.values()
    ]
    spread = max(test_returns) - min(test_returns)
    return "USE" if spread >= 0.03 else "REJECT"


def load_funding_frame(path: Path = FUNDING_PATH) -> pd.DataFrame:
    payload = load_json(path)
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("funding snapshot records must be a list")
    rows = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("symbol") == "BTCUSDT"
        and record.get("contract_type") == "PERPETUAL"
        and record.get("funding_rate_sum") is not None
        and record.get("index_close") is not None
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("funding snapshot has no BTCUSDT perpetual rows")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    if not frame["date"].is_monotonic_increasing:
        raise ValueError("funding dates are not chronological")
    return frame[["date", "index_close", "funding_rate_sum"]].reset_index(drop=True)


def _design_matrix(frame: pd.DataFrame, columns: Iterable[str], stats: dict[str, tuple[float, float]]) -> np.ndarray:
    normalized: list[np.ndarray] = [np.ones(len(frame), dtype=float)]
    for column in columns:
        mean, std = stats[column]
        normalized.append((frame[column].to_numpy(dtype=float) - mean) / std)
    return np.column_stack(normalized)


def _fit_ols(train: pd.DataFrame, columns: tuple[str, ...]) -> tuple[np.ndarray, dict[str, tuple[float, float]]]:
    stats: dict[str, tuple[float, float]] = {}
    for column in columns:
        mean = float(train[column].mean())
        std = float(train[column].std(ddof=1))
        if not math.isfinite(std) or std <= 0:
            raise ValueError(f"feature has no variation: {column}")
        stats[column] = (mean, std)
    matrix = _design_matrix(train, columns, stats)
    target = train["target_next_return"].to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    return coefficients, stats


def _evaluate_ols(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    coefficients: np.ndarray,
    stats: dict[str, tuple[float, float]],
) -> dict[str, float]:
    prediction = _design_matrix(frame, columns, stats) @ coefficients
    target = frame["target_next_return"].to_numpy(dtype=float)
    mse = float(np.mean((target - prediction) ** 2))
    directional_accuracy = float(np.mean(np.sign(prediction) == np.sign(target)))
    return {"mse": mse, "directional_accuracy": directional_accuracy}


def funding_ablation(frame: pd.DataFrame) -> dict[str, Any]:
    data = frame.copy()
    data["price_momentum_1d"] = np.log(data["index_close"] / data["index_close"].shift(1))
    data["target_next_return"] = np.log(data["index_close"].shift(-1) / data["index_close"])
    data = data.dropna().reset_index(drop=True)
    if len(data) < 60:
        return {
            "status": "BLOCKED",
            "reason": f"only {len(data)} aligned daily rows; at least 60 required",
            "source_sha256": sha256_file(FUNDING_PATH),
        }

    train_end = int(len(data) * 0.60)
    validation_end = int(len(data) * 0.80)
    train = data.iloc[:train_end]
    validation = data.iloc[train_end:validation_end]
    test = data.iloc[validation_end:]
    if min(len(train), len(validation), len(test)) < 10:
        return {
            "status": "BLOCKED",
            "reason": "chronological split leaves fewer than 10 observations in a segment",
            "source_sha256": sha256_file(FUNDING_PATH),
        }

    baseline_columns = ("price_momentum_1d",)
    augmented_columns = ("price_momentum_1d", "funding_rate_sum")
    baseline_beta, baseline_stats = _fit_ols(train, baseline_columns)
    augmented_beta, augmented_stats = _fit_ols(train, augmented_columns)
    validation_baseline = _evaluate_ols(validation, baseline_columns, baseline_beta, baseline_stats)
    validation_augmented = _evaluate_ols(validation, augmented_columns, augmented_beta, augmented_stats)
    test_baseline = _evaluate_ols(test, baseline_columns, baseline_beta, baseline_stats)
    test_augmented = _evaluate_ols(test, augmented_columns, augmented_beta, augmented_stats)

    validation_improvement = 1.0 - validation_augmented["mse"] / validation_baseline["mse"]
    test_improvement = 1.0 - test_augmented["mse"] / test_baseline["mse"]
    if validation_improvement >= 0.02 and test_improvement >= 0.02:
        verdict = "USE"
    elif validation_improvement > 0 or test_improvement > 0:
        verdict = "CONDITION"
    else:
        verdict = "REJECT"

    return {
        "status": verdict,
        "feature": "funding_rate_sum",
        "target": "next-day BTCUSDT index log return",
        "point_in_time_contract": "features at day t predict index return from t to t+1",
        "rows": len(data),
        "date_start": str(data["date"].iloc[0].date()),
        "date_end": str(data["date"].iloc[-1].date()),
        "split_rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "validation": {
            "price_only": validation_baseline,
            "price_plus_funding": validation_augmented,
            "mse_improvement_fraction": validation_improvement,
        },
        "test": {
            "price_only": test_baseline,
            "price_plus_funding": test_augmented,
            "mse_improvement_fraction": test_improvement,
        },
        "source_sha256": sha256_file(FUNDING_PATH),
    }


def build_report() -> dict[str, Any]:
    catalog = load_json(CATALOG_PATH)
    prices = load_prices()
    centered = centered_log_strength(prices, PRIMARY_LOOKBACK).dropna(how="any")
    sum_zero_error = float(centered.sum(axis=1).abs().max())
    agreement = ranking_agreement(prices, PRIMARY_LOOKBACK)

    sensitivity = {
        str(lookback): compare_allocation(prices, lookback, "log")
        for lookback in LOOKBACK_SENSITIVITY
    }
    primary = sensitivity[str(PRIMARY_LOOKBACK)]
    allocation_status = allocation_verdict(primary)
    parameter_status = parameter_dependence_verdict(sensitivity)
    funding = funding_ablation(load_funding_frame())

    hypothesis_results = {
        "memenote_log_relative_strength_v1": {
            "status": allocation_status,
            "explanatory_indicator": "USE",
            "incremental_log_transform_edge": "REJECT" if agreement == 1.0 else "CONDITION",
            "regime_classifier": "BLOCKED",
            "timing_signal": "BLOCKED",
            "reason": (
                "sum-zero explanatory representation is reproduced; allocation value is judged only by frozen OOS periods; "
                "the source does not specify deterministic regime or entry/exit rules"
            ),
        },
        "memenote_regime_parameter_dependence_v1": {
            "status": parameter_status,
            "reason": "verdict uses the spread across predeclared 21/63/126-session OOS lookbacks",
        },
        "memenote_btc_funding_incremental_v1": {
            "status": funding["status"],
            "reason": "chronological price-only versus price+funding OLS ablation",
        },
        "memenote_strategy_rule_reproduction_v1": {
            "status": "BLOCKED",
            "reason": "exact article-specific entry/exit rules are not independently available; discretionary details are not invented",
        },
    }

    return {
        "schema_version": "investor2.memenote-research-verification.v1",
        "issue": "https://github.com/KAFKA2306/investor2/issues/421",
        "catalog_sha256": sha256_file(CATALOG_PATH),
        "source_policy": "memenote is hypothesis input, not empirical authority",
        "market_data": {
            "price_snapshot": str(PRICE_PATH.relative_to(ROOT)),
            "price_snapshot_sha256": sha256_file(PRICE_PATH),
            "source_manifest": str(PRICE_MANIFEST_PATH.relative_to(ROOT)),
            "funding_snapshot": str(FUNDING_PATH.relative_to(ROOT)),
            "funding_snapshot_sha256": sha256_file(FUNDING_PATH),
        },
        "relative_strength": {
            "universe": list(CROSS_ASSET_UNIVERSE),
            "asset_roles": {
                "QQQ": "US growth equities",
                "DIA": "US large-cap equities",
                "IWM": "US small-cap equities",
                "GLD": "gold proxy",
                "TLT": "long-duration US Treasury proxy",
            },
            "unavailable_in_frozen_price_snapshot": ["USDJPY", "Japan equities", "BTC spot"],
            "lookback_sessions": PRIMARY_LOOKBACK,
            "top_k": TOP_K,
            "trading_cost_bps_per_traded_notional": TRADING_COST_BPS,
            "signal_execution": "month-end close signal, rebalance after the next session return; no same-bar look-ahead",
            "max_abs_centered_strength_sum": sum_zero_error,
            "simple_vs_log_top_k_rank_agreement": agreement,
            "primary_oos": primary,
            "parameter_sensitivity": sensitivity,
            "allocation_verdict": allocation_status,
            "parameter_dependence_verdict": parameter_status,
        },
        "price_external_feature_ablation": funding,
        "strategy_reproduction_contract": {
            "signal_timestamp": "close(t)",
            "earliest_execution": "after return(t,t+1); target weights become active for subsequent returns",
            "price": "frozen adjusted close when available",
            "position_sizing": "equal weight among top-k for the reproduced allocation test",
            "cost": f"{TRADING_COST_BPS} bps per traded notional",
            "leverage": "none",
            "missing_data": "fail closed",
            "article_specific_stop_take_profit": "UNSPECIFIED/BLOCKED unless source provides exact rules",
        },
        "hypothesis_results": hypothesis_results,
        "catalog_hypothesis_count": len(catalog.get("hypotheses", [])),
        "negative_results_are_preserved": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_report(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.output is None or not args.output.exists():
            raise SystemExit("--check requires an existing --output file")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale memenote research output: regenerate {args.output}")
        return
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
