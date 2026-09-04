#!/usr/bin/env python3
"""Evaluate Maximum Drawdown RiskBudgeting on the frozen J-Quants OOS window."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from skfolio import RiskMeasure
from skfolio.optimization import MeanRisk, RiskBudgeting

from scripts.jquants_japan_panel import choose_japan_universe, load_japan_inputs
from scripts.skfolio_jquants_oos import build_walk_forward_folds, returns_frame_from_panel
from src.research.skfolio_characteristics import asset_panel_from_prices

ANNUALIZATION_FACTOR = 252.0
MAX_WEIGHT = 0.05
ONE_WAY_TURNOVER_COST = 0.002
STRATEGIES = (
    "equal_weight",
    "empirical_min_variance",
    "max_drawdown_risk_budgeting",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-snapshot-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--market-regions", default="jp")
    parser.add_argument("--max-assets", type=int, default=64)
    parser.add_argument("--universe-cutoff", required=True)
    parser.add_argument("--evaluation-start", required=True)
    parser.add_argument("--evaluation-end", required=True)
    parser.add_argument("--train-months", type=int, default=12)
    parser.add_argument("--fold-months", type=int, default=3)
    return parser.parse_args()


def portfolio_metrics(returns: pd.Series) -> dict[str, float]:
    values = returns.to_numpy(dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise AssertionError("portfolio returns must be finite and non-empty")
    if np.any(values <= -1.0):
        raise AssertionError("portfolio return <= -100% invalidates wealth path")

    wealth = np.cumprod(1.0 + values)
    path = np.concatenate(([1.0], wealth))
    running_peak = np.maximum.accumulate(path)
    drawdown = path / running_peak - 1.0
    q05 = float(np.quantile(values, 0.05))
    tail = values[values <= q05]
    daily_vol = float(np.std(values, ddof=1))
    daily_mean = float(np.mean(values))
    return {
        "cagr": float(wealth[-1] ** (ANNUALIZATION_FACTOR / values.size) - 1.0),
        "annualized_volatility": daily_vol * np.sqrt(ANNUALIZATION_FACTOR),
        "sharpe_ratio": (
            0.0
            if daily_vol == 0.0
            else daily_mean / daily_vol * np.sqrt(ANNUALIZATION_FACTOR)
        ),
        "maximum_drawdown": float(drawdown.min()),
        "expected_shortfall_95_daily": float(tail.mean()),
        "worst_day": float(values.min()),
        "cumulative_return": float(wealth[-1] - 1.0),
    }


def simulate_fold(
    test_returns: pd.DataFrame,
    target_weights: np.ndarray,
    previous_end_weights: np.ndarray,
) -> tuple[pd.Series, np.ndarray, float, float]:
    weights = np.asarray(target_weights, dtype=float).copy()
    previous = np.asarray(previous_end_weights, dtype=float)
    if (
        weights.ndim != 1
        or weights.shape[0] != test_returns.shape[1]
        or previous.shape != weights.shape
    ):
        raise AssertionError("weights do not match test assets")
    if not np.isfinite(weights).all() or np.any(weights < -1e-10):
        raise AssertionError("target weights must be finite and long-only")
    if not np.isclose(weights.sum(), 1.0, atol=1e-6):
        raise AssertionError("target weights must sum to one")
    if float(weights.max()) > MAX_WEIGHT + 1e-6:
        raise AssertionError("target weights exceed the fixed 5% cap")

    turnover = float(0.5 * np.abs(weights - previous).sum())
    cost = turnover * ONE_WAY_TURNOVER_COST
    realized: list[float] = []
    for i, row in enumerate(test_returns.to_numpy(dtype=float)):
        gross = float(weights @ row)
        realized.append(gross - cost if i == 0 else gross)
        denominator = 1.0 + gross
        if denominator <= 0.0:
            raise AssertionError("portfolio wealth became non-positive")
        weights = weights * (1.0 + row) / denominator

    return (
        pd.Series(realized, index=test_returns.index, dtype=float),
        weights,
        turnover,
        cost,
    )


def target_weights(train_returns: pd.DataFrame) -> dict[str, np.ndarray]:
    n_assets = train_returns.shape[1]
    equal = np.full(n_assets, 1.0 / n_assets)
    models = {
        "empirical_min_variance": MeanRisk(
            risk_measure=RiskMeasure.VARIANCE,
            min_weights=0.0,
            max_weights=MAX_WEIGHT,
        ),
        "max_drawdown_risk_budgeting": RiskBudgeting(
            risk_measure=RiskMeasure.MAX_DRAWDOWN,
            min_weights=0.0,
            max_weights=MAX_WEIGHT,
        ),
    }
    output = {"equal_weight": equal}
    for name, model in models.items():
        model.fit(train_returns)
        weights = np.asarray(model.weights_, dtype=float)
        if weights.shape != (n_assets,) or not np.isfinite(weights).all():
            raise AssertionError(f"{name} produced invalid weights")
        output[name] = weights
    return output


def main() -> None:
    args = parse_args()
    evaluation_start = pd.Timestamp(args.evaluation_start)
    evaluation_end = pd.Timestamp(args.evaluation_end)
    cutoff = pd.Timestamp(args.universe_cutoff)
    folds = build_walk_forward_folds(
        evaluation_start,
        evaluation_end,
        train_months=args.train_months,
        fold_months=args.fold_months,
    )
    if len(folds) != 2:
        raise AssertionError("study is preregistered for exactly two OOS folds")

    load_args = argparse.Namespace(
        market_snapshot_dir=args.market_snapshot_dir,
        market_regions=args.market_regions,
        max_assets=args.max_assets,
    )
    prices_long, _, source_metadata = load_japan_inputs(load_args)
    selected_codes = sorted(
        choose_japan_universe(prices_long, cutoff, args.max_assets)
    )
    if len(selected_codes) != args.max_assets:
        raise AssertionError("selected universe size differs from the fixed asset count")

    selected = prices_long[prices_long["Code"].isin(selected_codes)].copy()
    price_matrix = (
        selected.pivot(index="Date", columns="Code", values="Close")
        .sort_index()
        .reindex(columns=selected_codes)
    )
    earliest_required = min(fold.train_start for fold in folds)
    working_prices = price_matrix.loc[
        (price_matrix.index >= earliest_required)
        & (price_matrix.index <= evaluation_end)
    ]
    complete_prices = working_prices.dropna(axis=0, how="any")
    if complete_prices.empty:
        raise AssertionError("no complete selected-universe price observations")

    full_mask = pd.DataFrame(
        True,
        index=complete_prices.index,
        columns=complete_prices.columns,
    )
    all_returns = returns_frame_from_panel(
        asset_panel_from_prices(
            complete_prices,
            active_mask=full_mask,
            estimation_mask=full_mask,
        )
    )

    series: dict[str, list[pd.Series]] = {name: [] for name in STRATEGIES}
    equal_start = np.full(len(selected_codes), 1.0 / len(selected_codes))
    previous_weights = {name: equal_start.copy() for name in STRATEGIES}
    total_turnover = {name: 0.0 for name in STRATEGIES}
    total_cost = {name: 0.0 for name in STRATEGIES}
    fold_records: list[dict[str, Any]] = []

    for fold in folds:
        train_returns = all_returns.loc[
            (all_returns.index >= fold.train_start)
            & (all_returns.index <= fold.train_end)
        ]
        test_returns = all_returns.loc[
            (all_returns.index >= fold.test_start)
            & (all_returns.index <= fold.test_end)
        ]
        if len(train_returns) < 180 or len(test_returns) < 30:
            raise AssertionError("fold lacks preregistered minimum observations")

        targets = target_weights(train_returns)
        record: dict[str, Any] = {
            "fold": fold.index,
            "train_start": str(fold.train_start.date()),
            "train_end": str(fold.train_end.date()),
            "test_start": str(fold.test_start.date()),
            "test_end": str(fold.test_end.date()),
            "train_returns": int(len(train_returns)),
            "test_returns": int(len(test_returns)),
            "strategies": {},
        }
        for name in STRATEGIES:
            fold_series, end_weights, turnover, cost = simulate_fold(
                test_returns,
                targets[name],
                previous_weights[name],
            )
            series[name].append(fold_series)
            previous_weights[name] = end_weights
            total_turnover[name] += turnover
            total_cost[name] += cost
            record["strategies"][name] = {
                "target_max_weight": float(np.max(targets[name])),
                "target_effective_assets": float(
                    1.0 / np.sum(np.square(targets[name]))
                ),
                "one_way_turnover": turnover,
                "transaction_cost_fraction": cost,
            }
        fold_records.append(record)

    metrics: dict[str, dict[str, float]] = {}
    for name in STRATEGIES:
        combined = pd.concat(series[name]).sort_index()
        if combined.index.duplicated().any():
            raise AssertionError("OOS fold returns overlap")
        metrics[name] = {
            **portfolio_metrics(combined),
            "total_one_way_turnover": total_turnover[name],
            "total_transaction_cost_fraction": total_cost[name],
            "oos_observations": float(len(combined)),
        }

    baseline = metrics["empirical_min_variance"]
    candidate = metrics["max_drawdown_risk_budgeting"]
    wins = {
        "maximum_drawdown": bool(
            candidate["maximum_drawdown"] > baseline["maximum_drawdown"]
        ),
        "expected_shortfall_95_daily": bool(
            candidate["expected_shortfall_95_daily"]
            > baseline["expected_shortfall_95_daily"]
        ),
        "annualized_volatility_within_105pct": bool(
            candidate["annualized_volatility"]
            <= baseline["annualized_volatility"] * 1.05
        ),
        "sharpe_ratio": bool(candidate["sharpe_ratio"] >= baseline["sharpe_ratio"]),
    }
    verdict = "USE" if all(wins.values()) else "REJECT"

    output = {
        "schema_version": "investor2.skfolio-max-drawdown-allocation-oos.v1",
        "hypothesis_issue": 261,
        "source": source_metadata,
        "universe": {
            "asset_count": len(selected_codes),
            "codes": selected_codes,
            "universe_cutoff": str(cutoff.date()),
        },
        "evaluation": {
            "start": str(evaluation_start.date()),
            "end": str(evaluation_end.date()),
            "train_months": args.train_months,
            "fold_months": args.fold_months,
            "transaction_cost_per_one_way_turnover": ONE_WAY_TURNOVER_COST,
            "initial_previous_weights": "equal_weight",
            "max_asset_weight": MAX_WEIGHT,
        },
        "folds": fold_records,
        "metrics": metrics,
        "candidate_wins_vs_empirical_min_variance": wins,
        "verdict": verdict,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"verdict": verdict, "wins": wins}, sort_keys=True))


if __name__ == "__main__":
    main()
