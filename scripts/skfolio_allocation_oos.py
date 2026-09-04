#!/usr/bin/env python3
"""Evaluate frozen covariance forecasts through constrained OOS minimum-variance allocation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import cvxpy as cp
import numpy as np
import pandas as pd

from scripts.jquants_japan_panel import load_japan_inputs
from scripts.skfolio_jquants_oos import returns_frame_from_panel
from src.research.skfolio_characteristics import asset_panel_from_prices

ANNUALIZATION_FACTOR = 252.0
MAX_ASSET_WEIGHT = 0.05
TRANSACTION_COST_BPS = 20.0
STRATEGY_KEYS = (
    "equal_weight",
    "empirical_covariance_min_variance",
    "price_only_min_variance",
    "true_mktcap_size_beta_min_variance",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use frozen J-Quants OOS covariance artifacts to compare constrained minimum-variance allocations."
        )
    )
    parser.add_argument("--market-snapshot-dir", required=True, type=Path)
    parser.add_argument("--covariance-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--market-regions", default="jp")
    return parser.parse_args()


def min_variance_weights(covariance: np.ndarray, *, max_weight: float = MAX_ASSET_WEIGHT) -> np.ndarray:
    covariance = np.asarray(covariance, dtype=float)
    if covariance.ndim != 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("covariance must be square")
    if not np.isfinite(covariance).all():
        raise ValueError("covariance must be finite")
    n_assets = covariance.shape[0]
    if n_assets * max_weight < 1 - 1e-12:
        raise ValueError("max_weight makes the fully invested portfolio infeasible")

    weights = cp.Variable(n_assets)
    problem = cp.Problem(
        cp.Minimize(cp.quad_form(weights, cp.psd_wrap(covariance))),
        [cp.sum(weights) == 1, weights >= 0, weights <= max_weight],
    )
    problem.solve(solver="CLARABEL")
    if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} or weights.value is None:
        raise RuntimeError(f"minimum-variance optimization failed: {problem.status}")

    solved = np.asarray(weights.value, dtype=float).reshape(-1)
    solved[np.abs(solved) < 1e-10] = 0.0
    if not np.isfinite(solved).all() or solved.min() < -1e-7 or solved.max() > max_weight + 1e-7:
        raise RuntimeError("minimum-variance solution violates weight bounds")
    if abs(float(solved.sum()) - 1.0) > 1e-6:
        raise RuntimeError("minimum-variance solution is not fully invested")
    solved = np.clip(solved, 0.0, max_weight)
    return solved / solved.sum()


def one_way_turnover(previous: np.ndarray, current: np.ndarray) -> float:
    if previous.shape != current.shape:
        raise ValueError("turnover weights must share a shape")
    return float(0.5 * np.abs(current - previous).sum())


def portfolio_metrics(returns: pd.Series) -> dict[str, float]:
    values = returns.to_numpy(dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError("portfolio returns must be finite and non-empty")
    if np.any(values <= -1):
        raise ValueError("portfolio return <= -100% invalidates wealth path")

    wealth = np.cumprod(1 + values)
    running_peak = np.maximum.accumulate(np.concatenate(([1.0], wealth)))
    path = np.concatenate(([1.0], wealth))
    drawdowns = path / running_peak - 1
    daily_mean = float(values.mean())
    daily_vol = float(values.std(ddof=1)) if values.size > 1 else 0.0
    tail_count = max(1, int(np.ceil(values.size * 0.05)))
    expected_shortfall = float(np.sort(values)[:tail_count].mean())
    total_return = float(wealth[-1] - 1)
    cagr = float(wealth[-1] ** (ANNUALIZATION_FACTOR / values.size) - 1)
    return {
        "total_return": total_return,
        "cagr": cagr,
        "annualized_volatility": daily_vol * np.sqrt(ANNUALIZATION_FACTOR),
        "sharpe_zero_risk_free": (0.0 if daily_vol == 0 else daily_mean / daily_vol * np.sqrt(ANNUALIZATION_FACTOR)),
        "maximum_drawdown": float(drawdowns.min()),
        "expected_shortfall_95_daily": expected_shortfall,
        "worst_day": float(values.min()),
    }


def load_selected_returns(
    snapshot_dir: Path,
    *,
    regions: str,
    selected_codes: list[str],
) -> pd.DataFrame:
    load_args = argparse.Namespace(
        market_snapshot_dir=snapshot_dir,
        market_regions=regions,
        max_assets=len(selected_codes),
    )
    prices_long, _, _ = load_japan_inputs(load_args)
    selected = prices_long[prices_long["Code"].isin(selected_codes)].copy()
    prices = selected.pivot(index="Date", columns="Code", values="Close").sort_index().reindex(columns=selected_codes)
    prices = prices.dropna(axis=0, how="any")
    if prices.empty or list(prices.columns) != selected_codes:
        raise AssertionError("selected price panel could not be reconstructed from canonical snapshot")
    mask = pd.DataFrame(True, index=prices.index, columns=prices.columns)
    return returns_frame_from_panel(asset_panel_from_prices(prices, active_mask=mask, estimation_mask=mask))


def evaluate(
    *,
    covariance_dir: Path,
    all_returns: pd.DataFrame,
    transaction_cost_bps: float = TRANSACTION_COST_BPS,
) -> dict[str, object]:
    summary = json.loads((covariance_dir / "summary.json").read_text(encoding="utf-8"))
    folds = cast(list[dict[str, object]], summary["folds"])
    selected_codes = [str(code) for code in cast(dict[str, object], summary["input_contract"])["selected_codes"]]
    if list(all_returns.columns) != selected_codes:
        raise AssertionError("reconstructed return columns differ from frozen investment universe")

    previous_weights = {
        key: np.full(len(selected_codes), 1.0 / len(selected_codes), dtype=float) for key in STRATEGY_KEYS
    }
    strategy_returns: dict[str, list[pd.Series]] = {key: [] for key in STRATEGY_KEYS}
    turnover: dict[str, float] = {key: 0.0 for key in STRATEGY_KEYS}
    fold_details: list[dict[str, object]] = []

    for fold_record in folds:
        fold = cast(dict[str, object], fold_record["fold"])
        fold_index = int(fold["index"])
        test_start = pd.Timestamp(cast(str, fold["test_start"]))
        test_end = pd.Timestamp(cast(str, fold["test_end"]))
        test_returns = all_returns.loc[(all_returns.index >= test_start) & (all_returns.index <= test_end)]
        if test_returns.empty:
            raise AssertionError(f"fold {fold_index} has no reconstructed OOS returns")

        artifact = np.load(covariance_dir / f"fold{fold_index}.npz")
        required = {
            "baseline_covariance",
            "current_skfolio_covariance",
            "candidate_covariance",
        }
        if not required.issubset(artifact.files):
            raise AssertionError(f"fold {fold_index} lacks required covariance arrays")

        weights_by_strategy = {
            "equal_weight": np.full(len(selected_codes), 1.0 / len(selected_codes), dtype=float),
            "empirical_covariance_min_variance": min_variance_weights(artifact["baseline_covariance"]),
            "price_only_min_variance": min_variance_weights(artifact["current_skfolio_covariance"]),
            "true_mktcap_size_beta_min_variance": min_variance_weights(artifact["candidate_covariance"]),
        }
        fold_summary: dict[str, object] = {"fold": fold, "strategies": {}}
        for key, weights in weights_by_strategy.items():
            period = pd.Series(
                test_returns.to_numpy(dtype=float) @ weights,
                index=test_returns.index,
                dtype=float,
            )
            fold_turnover = one_way_turnover(previous_weights[key], weights)
            cost = fold_turnover * transaction_cost_bps / 10_000.0
            if cost:
                period.iloc[0] -= cost
            strategy_returns[key].append(period)
            turnover[key] += fold_turnover
            previous_weights[key] = weights
            cast(dict[str, object], fold_summary["strategies"])[key] = {
                "one_way_turnover": fold_turnover,
                "transaction_cost_return": cost,
                "maximum_weight": float(weights.max()),
                "effective_number_of_assets": float(1.0 / np.square(weights).sum()),
                "metrics_after_cost": portfolio_metrics(period),
            }
        fold_details.append(fold_summary)

    aggregate: dict[str, object] = {}
    for key in STRATEGY_KEYS:
        combined = pd.concat(strategy_returns[key]).sort_index()
        if combined.index.has_duplicates:
            raise AssertionError(f"{key} OOS folds overlap")
        aggregate[key] = {
            "cumulative_one_way_turnover": turnover[key],
            "estimated_transaction_cost_return": (turnover[key] * transaction_cost_bps / 10_000.0),
            "metrics_after_cost": portfolio_metrics(combined),
        }

    empirical = cast(dict[str, object], aggregate["empirical_covariance_min_variance"])
    candidate = cast(dict[str, object], aggregate["true_mktcap_size_beta_min_variance"])
    empirical_metrics = cast(dict[str, float], empirical["metrics_after_cost"])
    candidate_metrics = cast(dict[str, float], candidate["metrics_after_cost"])
    wins = {
        "annualized_volatility": (
            candidate_metrics["annualized_volatility"] < empirical_metrics["annualized_volatility"]
        ),
        "maximum_drawdown": (candidate_metrics["maximum_drawdown"] > empirical_metrics["maximum_drawdown"]),
    }
    verdict = "USE" if all(wins.values()) else "REJECT"
    return {
        "schema_version": "investor2.skfolio-allocation-oos.v1",
        "status": "EVALUATED",
        "verdict": verdict,
        "hypothesis": (
            "true-MktCap Size/Beta covariance improves constrained long-only minimum-variance OOS risk "
            "versus empirical covariance"
        ),
        "acceptance_rule": (
            "USE only if true-MktCap Size/Beta minimum-variance allocation has both lower after-cost "
            "annualized OOS volatility and a smaller-magnitude OOS maximum drawdown than empirical-covariance "
            "minimum-variance allocation; otherwise REJECT"
        ),
        "allocation_contract": {
            "objective": "minimum variance",
            "long_only": True,
            "fully_invested": True,
            "maximum_asset_weight": MAX_ASSET_WEIGHT,
            "transaction_cost_bps_per_one_way_turnover": transaction_cost_bps,
            "transaction_cost_note": "research stress assumption, not a broker fee claim",
            "initial_previous_weights": "equal weight",
        },
        "primary_metric_wins_vs_empirical": wins,
        "aggregate": aggregate,
        "folds": fold_details,
        "source_covariance_schema": summary["schema_version"],
        "source_covariance_verdict": cast(dict[str, object], summary["aggregate"])["true_mktcap_size_beta_candidate"],
        "claim_boundary": (
            "This evaluates risk allocation over the frozen OOS window only; it does not establish alpha or "
            "expected-return improvement."
        ),
    }


def main() -> None:
    args = parse_args()
    source_summary = json.loads((args.covariance_dir / "summary.json").read_text(encoding="utf-8"))
    selected_codes = [str(code) for code in cast(dict[str, object], source_summary["input_contract"])["selected_codes"]]
    all_returns = load_selected_returns(
        args.market_snapshot_dir,
        regions=args.market_regions,
        selected_codes=selected_codes,
    )
    result = evaluate(covariance_dir=args.covariance_dir, all_returns=all_returns)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "wins": result["primary_metric_wins_vs_empirical"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()