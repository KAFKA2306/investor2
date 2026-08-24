#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.alphacrafter_frontier import (
    as_dict,
    composite_scores,
    evaluate_weights,
    factor_metrics,
    make_weight_path,
    orient_factor_on_train,
    paper_strategy_gate,
    screen_factors,
)


@dataclass(frozen=True)
class WalkForwardFold:
    index: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_indices: tuple[int, int]
    validation_indices: tuple[int, int]
    test_indices: tuple[int, int]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _index_bounds(
    dates: pd.DatetimeIndex, start: pd.Timestamp, end_exclusive: pd.Timestamp
) -> tuple[int, int]:
    left = int(dates.searchsorted(start, side="left"))
    right = int(dates.searchsorted(end_exclusive, side="left"))
    if right <= left:
        raise ValueError(f"empty interval: {start.date()} to {end_exclusive.date()}")
    return left, right


def make_walk_forward_folds(
    dates: np.ndarray,
    *,
    test_start: str,
    test_end: str,
    train_months: int,
    validation_months: int,
    test_months: int,
) -> list[WalkForwardFold]:
    idx = pd.DatetimeIndex(pd.to_datetime(dates.tolist())).sort_values()
    test_cursor = pd.Timestamp(test_start)
    final_exclusive = pd.Timestamp(test_end) + pd.Timedelta(days=1)
    folds: list[WalkForwardFold] = []
    fold_index = 0
    while test_cursor < final_exclusive:
        test_exclusive = min(test_cursor + pd.DateOffset(months=test_months), final_exclusive)
        validation_start = test_cursor - pd.DateOffset(months=validation_months)
        train_start = validation_start - pd.DateOffset(months=train_months)
        if train_start < idx[0]:
            raise ValueError(
                f"insufficient history for fold {fold_index}: need {train_start.date()}, have {idx[0].date()}"
            )
        train = _index_bounds(idx, train_start, validation_start)
        validation = _index_bounds(idx, validation_start, test_cursor)
        test = _index_bounds(idx, test_cursor, test_exclusive)
        folds.append(
            WalkForwardFold(
                index=fold_index,
                train_start=str(idx[train[0]].date()),
                train_end=str(idx[train[1] - 1].date()),
                validation_start=str(idx[validation[0]].date()),
                validation_end=str(idx[validation[1] - 1].date()),
                test_start=str(idx[test[0]].date()),
                test_end=str(idx[test[1] - 1].date()),
                train_indices=train,
                validation_indices=validation,
                test_indices=test,
            )
        )
        fold_index += 1
        test_cursor = test_exclusive
    return folds


UPSTREAM_COMMIT = "c6dbc1ba4e0a4ecbc3ea1454c5290dbea4b36b0d"
PAPER_URL = "https://arxiv.org/abs/2605.05580v2"
TRADER_TRIALS = (
    {"name": "balanced_16x16", "n_long": 16, "n_short": 16, "beta": 0.8, "gamma": 0.0},
    {"name": "long_tilt_24x8", "n_long": 24, "n_short": 8, "beta": 0.8, "gamma": 0.5},
    {"name": "short_tilt_8x24", "n_long": 8, "n_short": 24, "beta": 0.8, "gamma": -0.5},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen AlphaCrafter representative on a prepared J-Quants panel.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--dataset-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--test-end", required=True)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with np.load(args.dataset, allow_pickle=False) as data:
        dates = data["dates"].astype(str)
        feature_names = data["feature_names"].astype(str).tolist()
        features = data["features"].astype(np.float64)
        returns = data["returns"].astype(np.float64)
        benchmark = data["benchmark"].astype(np.float64)

    if features.shape[:2] != returns.shape:
        raise AssertionError("features and returns shapes are inconsistent")
    if features.shape[2] != len(feature_names):
        raise AssertionError("feature_names do not match feature tensor")
    if features.shape[1] != 256:
        raise AssertionError(f"frontier contract requires exactly 256 assets, got {features.shape[1]}")

    manifest = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
    generated_folds = make_walk_forward_folds(
        dates,
        test_start=args.test_start,
        test_end=args.test_end,
        train_months=12,
        validation_months=3,
        test_months=3,
    )
    if len(generated_folds) < 2:
        raise AssertionError(f"frontier contract requires at least two OOS folds, got {len(generated_folds)}")
    folds = generated_folds[:2]

    global_test_weights = np.zeros_like(returns, dtype=np.float64)
    fold_payloads: list[dict[str, object]] = []

    for fold in folds:
        train_start, train_end = fold.train_indices
        validation_start, validation_end = fold.validation_indices
        test_start, test_end = fold.test_indices

        oriented_factors: dict[str, np.ndarray] = {}
        validation_details: dict[str, object] = {}
        for feature_index, feature_name in enumerate(feature_names):
            raw_factor = features[:, :, feature_index]
            oriented, train_direction = orient_factor_on_train(raw_factor, returns, train_start, train_end)
            one_day = factor_metrics(oriented, returns, validation_start, validation_end, horizon=1)
            five_day = factor_metrics(oriented, returns, validation_start, validation_end, horizon=5)
            validation_details[feature_name] = {
                "train_orientation": train_direction,
                "one_day": as_dict(one_day),
                "five_day": as_dict(five_day),
                "miner_pass": bool(one_day.passed and five_day.passed),
            }
            if one_day.passed and five_day.passed:
                oriented_factors[feature_name] = oriented

        selected = (
            screen_factors(oriented_factors, returns, validation_start, validation_end) if oriented_factors else []
        )
        scores = composite_scores(oriented_factors, selected) if selected else np.zeros_like(returns, dtype=np.float64)

        trial_results: list[dict[str, object]] = []
        viable_trials: list[tuple[float, dict[str, object], np.ndarray]] = []
        for policy in TRADER_TRIALS:
            weights = make_weight_path(
                scores,
                n_long=int(policy["n_long"]),
                n_short=int(policy["n_short"]),
                beta=float(policy["beta"]),
                gamma=float(policy["gamma"]),
            )
            validation_metrics, _ = evaluate_weights(
                weights,
                returns,
                benchmark,
                validation_start,
                validation_end,
                transaction_cost_bps_per_side=args.transaction_cost_bps,
                borrow_fee_bps_per_year=args.borrow_fee_bps,
            )
            passed = bool(selected) and paper_strategy_gate(validation_metrics)
            trial = {
                **policy,
                "validation_metrics": as_dict(validation_metrics),
                "paper_strategy_gate": passed,
            }
            trial_results.append(trial)
            if passed:
                viable_trials.append((validation_metrics.annualized_sharpe, trial, weights))

        if viable_trials:
            _, selected_trial, selected_weights = max(viable_trials, key=lambda item: item[0])
            global_test_weights[test_start:test_end] = selected_weights[test_start:test_end]
            test_metrics, _ = evaluate_weights(
                selected_weights,
                returns,
                benchmark,
                test_start,
                test_end,
                transaction_cost_bps_per_side=args.transaction_cost_bps,
                borrow_fee_bps_per_year=args.borrow_fee_bps,
            )
            execution_state = "EXECUTED"
        else:
            selected_trial = None
            zero_weights = np.zeros_like(returns, dtype=np.float64)
            test_metrics, _ = evaluate_weights(
                zero_weights,
                returns,
                benchmark,
                test_start,
                test_end,
                transaction_cost_bps_per_side=args.transaction_cost_bps,
                borrow_fee_bps_per_year=args.borrow_fee_bps,
            )
            execution_state = "NO_VIABLE_STRATEGY"

        fold_payloads.append(
            {
                "fold": {
                    "index": fold.index,
                    "train_start": fold.train_start,
                    "train_end": fold.train_end,
                    "validation_start": fold.validation_start,
                    "validation_end": fold.validation_end,
                    "test_start": fold.test_start,
                    "test_end": fold.test_end,
                },
                "miner": {
                    "candidate_count": len(feature_names),
                    "passed_count": len(oriented_factors),
                    "validation": validation_details,
                },
                "screener": {"selected_factors": selected},
                "trader": {
                    "trials": trial_results,
                    "selected_trial": selected_trial,
                    "execution_state": execution_state,
                },
                "oos_metrics": as_dict(test_metrics),
            }
        )

    aggregate_start = folds[0].test_indices[0]
    aggregate_end = folds[-1].test_indices[1]
    aggregate_metrics, _ = evaluate_weights(
        global_test_weights,
        returns,
        benchmark,
        aggregate_start,
        aggregate_end,
        transaction_cost_bps_per_side=args.transaction_cost_bps,
        borrow_fee_bps_per_year=args.borrow_fee_bps,
    )
    economic_gate = aggregate_metrics.cumulative_return > 0.0 and aggregate_metrics.annualized_sharpe > 0.0
    payload = {
        "schema_version": "investor2.alphacrafter-jquants-frontier.v1",
        "research_date": "2026-08-24",
        "execution_status": "completed",
        "family": "AlphaCrafter",
        "paper": {
            "title": "AlphaCrafter: Harnessing Multi-Agent Workflows for Cross-Sectional Quantitative Trading",
            "url": PAPER_URL,
            "version": "arXiv v2",
            "upstream_repository": "https://github.com/NJU-LINK/AlphaCrafter",
            "upstream_commit": UPSTREAM_COMMIT,
        },
        "reproduction_state": "PARTIAL",
        "representative": "deterministic public-policy representative",
        "claim_boundary": (
            "Reproduces the public quantitative Miner/Screener/Trader gates on the shared J-Quants PIT panel. "
            "It does not reproduce AlphaCrafter's LLM factor generation, LLM semantic similarity, or LLM regime diagnosis."
        ),
        "substitutions": [
            "Prepared J-Quants price/volume feature library substitutes for LLM-generated factor scripts.",
            "Coarse feature-name semantic groups substitute for LLM semantic-similarity filtering.",
            "Three preregistered long/short policies substitute for regime-conditioned LLM hyperparameter proposals.",
            "Factor ensemble is frozen before untouched OOS; no OOS re-mining or re-screening is allowed.",
            "Only generated fold indices 0 and 1 are evaluated to match the repository's existing AlphaZeroBeta two-fold execution; any calendar-split tail is reported but not silently added.",
            "Rank turnover is computed on percentile ranks to make the upstream <0.4 threshold dimensionally interpretable.",
        ],
        "shared_contract": {
            "dataset_sha256": sha256_file(args.dataset),
            "dataset_manifest_sha256": sha256_file(args.dataset_manifest),
            "asset_count": int(features.shape[1]),
            "feature_count": int(features.shape[2]),
            "date_start": str(pd.Timestamp(str(dates[0])).date()),
            "date_end": str(pd.Timestamp(str(dates[-1])).date()),
            "universe_cutoff": manifest.get("universe_cutoff"),
            "selected_codes": manifest.get("selected_codes"),
            "walk_forward": {
                "train_months": 12,
                "validation_months": 3,
                "test_months": 3,
                "generated_fold_count": len(generated_folds),
                "used_fold_indices": [0, 1],
                "effective_test_end": folds[-1].test_end,
                "source_window_test_end": args.test_end,
            },
            "benchmark": "13060 NEXT FUNDS TOPIX ETF proxy",
            "transaction_cost_bps_per_side": args.transaction_cost_bps,
            "borrow_fee_bps_per_year": args.borrow_fee_bps,
        },
        "paper_policy": {
            "factor_horizons_days": [1, 5],
            "screener_recent_rank_ic_days": 10,
            "screener_min_abs_rank_ic": 0.02,
            "max_trader_trials": 3,
            "strategy_gate": {"return_gt": 0.08, "sharpe_gt": 0.6, "max_drawdown_gt": -0.08},
            "trials": list(TRADER_TRIALS),
        },
        "folds": fold_payloads,
        "aggregate_oos_metrics": as_dict(aggregate_metrics),
        "hard_gates": {
            "pit_contract": True,
            "explicit_costs": True,
            "positive_after_cost_return_and_sharpe": economic_gate,
            "full_upstream_method_reproduced": False,
            "matched_aaarts_256_result_available": False,
        },
        "frontier_verdict": "BLOCKED",
        "blockers": [
            "Full AlphaCrafter LLM Miner/Screener/regime pipeline is not reproduced by this deterministic representative.",
            "A matched AAARTS 256-asset result under the same frozen contract is not yet persisted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "reproduction_state": payload["reproduction_state"],
                "frontier_verdict": payload["frontier_verdict"],
                "aggregate_oos_metrics": payload["aggregate_oos_metrics"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
