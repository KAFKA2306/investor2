#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import cast

import numpy as np

from src.research.alphazerobeta import EvaluationMetrics, evaluate_weight_path, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate all-asset AlphaZeroBeta rank/score-to-weight mappings.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--weights", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--canonical-comparison", required=True, type=Path)
    parser.add_argument("--topk-summary", required=True, type=Path)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=30.0)
    parser.add_argument("--baseline-tolerance", type=float, default=1e-4)
    return parser.parse_args()


def annualized_sharpe(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=np.float64)
    if values.size < 2:
        return 0.0
    std = float(values.std(ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(math.sqrt(252.0) * values.mean() / std)


def correlation(returns: np.ndarray, benchmark: np.ndarray) -> float:
    values = np.asarray(returns, dtype=np.float64)
    market = np.asarray(benchmark, dtype=np.float64)
    if values.shape != market.shape:
        raise AssertionError("return and benchmark arrays must have identical shape")
    if values.size < 2 or float(values.std(ddof=0)) <= 1e-12 or float(market.std(ddof=0)) <= 1e-12:
        return 0.0
    return float(np.corrcoef(values, market)[0, 1])


def max_drawdown(returns: np.ndarray) -> float:
    equity = np.cumprod(1.0 + np.asarray(returns, dtype=np.float64))
    if equity.size == 0:
        return 0.0
    peaks = np.maximum.accumulate(equity)
    return float((equity / peaks - 1.0).min())


def aggregate(
    returns: list[np.ndarray],
    benchmarks: list[np.ndarray],
    metrics: list[EvaluationMetrics],
) -> dict[str, float | int]:
    net = np.concatenate(returns)
    benchmark = np.concatenate(benchmarks)
    observations = sum(item.observations for item in metrics)
    weighted_turnover = sum(item.mean_turnover * item.observations for item in metrics) / observations
    weighted_gross = sum(item.mean_gross_exposure * item.observations for item in metrics) / observations
    return {
        "observations": int(net.size),
        "annualized_sharpe": annualized_sharpe(net),
        "benchmark_correlation": correlation(net, benchmark),
        "max_drawdown": max_drawdown(net),
        "cumulative_return": float(np.prod(1.0 + net) - 1.0),
        "mean_turnover": float(weighted_turnover),
        "max_abs_net_exposure": float(max(item.max_abs_net_exposure for item in metrics)),
        "mean_gross_exposure": float(weighted_gross),
    }


def normalize_full_gross(values: np.ndarray) -> np.ndarray:
    row = np.asarray(values, dtype=np.float64)
    centered = row - row.mean()
    gross = float(np.abs(centered).sum())
    if gross <= 1e-12:
        raise ValueError("cannot normalize zero-gross row")
    return (centered / gross).astype(np.float32)


def dense_full_gross(scores: np.ndarray) -> np.ndarray:
    return np.stack([normalize_full_gross(row) for row in np.asarray(scores)], axis=0)


def rank_power_weights(scores: np.ndarray, power: float) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("scores must be [T, N]")
    n_assets = values.shape[1]
    center = (n_assets - 1) / 2.0
    rows: list[np.ndarray] = []
    for row in values:
        order = np.argsort(row, kind="stable")
        ranks = np.empty(n_assets, dtype=np.float64)
        ranks[order] = np.arange(n_assets, dtype=np.float64)
        centered_rank = ranks - center
        if power == 0.0:
            signal = np.sign(centered_rank)
        else:
            signal = np.sign(centered_rank) * np.power(np.abs(centered_rank), power)
        rows.append(normalize_full_gross(signal))
    return np.stack(rows, axis=0)


def shrink_weights(sign_weights: np.ndarray, dense_weights: np.ndarray, alpha: float) -> np.ndarray:
    if sign_weights.shape != dense_weights.shape:
        raise ValueError("shrinkage inputs must have identical shape")
    return np.stack(
        [
            normalize_full_gross((1.0 - alpha) * sign_row + alpha * dense_row)
            for sign_row, dense_row in zip(sign_weights, dense_weights, strict=True)
        ],
        axis=0,
    )


def load_artifact(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as artifact:
        required = {"dates", "weights"}
        missing = sorted(required - set(artifact.files))
        if missing:
            raise AssertionError(f"{path} missing arrays: {missing}")
        return artifact["dates"].astype(str), artifact["weights"].astype(np.float32)


def canonical_check(dense: dict[str, float | int], path: Path, tolerance: float) -> dict[str, object]:
    canonical = json.loads(path.read_text(encoding="utf-8"))["primary_lambda_corr_0_5"]
    keys = ["observations", "annualized_sharpe", "benchmark_correlation", "max_drawdown", "cumulative_return"]
    deltas: dict[str, float] = {}
    for key in keys:
        actual = float(dense[key])
        expected = float(canonical[key])
        deltas[key] = actual - expected
        if key == "observations":
            if int(actual) != int(expected):
                raise AssertionError(f"dense observations mismatch: {actual} != {expected}")
        elif abs(actual - expected) > tolerance:
            raise AssertionError(f"dense {key} mismatch: {actual} vs {expected}, tolerance={tolerance}")
    return {"passed": True, "tolerance": tolerance, "delta_actual_minus_canonical": deltas}


def compare_metrics(
    actual: dict[str, float | int],
    expected: dict[str, float | int],
    tolerance: float,
) -> dict[str, object]:
    keys = [
        "observations",
        "annualized_sharpe",
        "benchmark_correlation",
        "max_drawdown",
        "cumulative_return",
        "mean_turnover",
    ]
    deltas: dict[str, float] = {}
    for key in keys:
        delta = float(actual[key]) - float(expected[key])
        deltas[key] = delta
        if key == "observations":
            if int(actual[key]) != int(expected[key]):
                raise AssertionError(f"{key} mismatch: {actual[key]} != {expected[key]}")
        elif abs(delta) > tolerance:
            raise AssertionError(f"{key} mismatch: delta={delta}, tolerance={tolerance}")
    return {"passed": True, "tolerance": tolerance, "delta_actual_minus_expected": deltas}


def main() -> None:
    args = parse_args()
    with np.load(args.dataset, allow_pickle=False) as dataset:
        dataset_dates = dataset["dates"].astype(str)
        all_returns = dataset["returns"].astype(np.float32)
        all_benchmark = dataset["benchmark"].astype(np.float32)
        asset_count = int(dataset["returns"].shape[1])
    if asset_count != 64:
        raise AssertionError(f"expected canonical 64-asset panel, got {asset_count}")
    date_lookup = {date: index for index, date in enumerate(dataset_dates)}

    variant_returns: dict[str, list[np.ndarray]] = {}
    variant_benchmarks: dict[str, list[np.ndarray]] = {}
    variant_metrics: dict[str, list[EvaluationMetrics]] = {}
    observed_dates: set[str] = set()

    for weight_path in args.weights:
        dates, scores = load_artifact(weight_path)
        overlap = observed_dates.intersection(dates.tolist())
        if overlap:
            raise AssertionError(f"OOS folds overlap: {sorted(overlap)[:3]}")
        observed_dates.update(dates.tolist())
        missing = [date for date in dates if date not in date_lookup]
        if missing:
            raise AssertionError(f"weight dates missing from dataset: {missing[:3]}")
        indices = np.asarray([date_lookup[date] for date in dates], dtype=np.int64)
        returns = all_returns[indices]
        benchmark = all_benchmark[indices]

        dense = dense_full_gross(scores)
        sign = rank_power_weights(scores, 0.0)
        variants = {
            "dense_score": dense,
            "rank_power_0_sign": sign,
            "rank_power_0_5": rank_power_weights(scores, 0.5),
            "rank_power_1": rank_power_weights(scores, 1.0),
            "rank_power_2": rank_power_weights(scores, 2.0),
            "shrink_sign_dense_0_25": shrink_weights(sign, dense, 0.25),
            "shrink_sign_dense_0_50": shrink_weights(sign, dense, 0.50),
            "shrink_sign_dense_0_75": shrink_weights(sign, dense, 0.75),
        }
        for name, weights in variants.items():
            metrics, net = evaluate_weight_path(
                weights,
                returns,
                benchmark,
                transaction_cost_bps_per_side=args.transaction_cost_bps,
                borrow_fee_bps_per_year=args.borrow_fee_bps,
            )
            variant_returns.setdefault(name, []).append(net)
            variant_benchmarks.setdefault(name, []).append(benchmark)
            variant_metrics.setdefault(name, []).append(metrics)

    results: dict[str, dict[str, float | int]] = {
        name: aggregate(variant_returns[name], variant_benchmarks[name], variant_metrics[name])
        for name in variant_returns
    }
    dense_result = results["dense_score"]
    baseline_reproduction = canonical_check(dense_result, args.canonical_comparison, args.baseline_tolerance)

    topk = json.loads(args.topk_summary.read_text(encoding="utf-8"))
    topk32 = cast(dict[str, float | int], topk["topk"]["32"])
    sign_reproduction = compare_metrics(results["rank_power_0_sign"], topk32, 1e-10)

    candidates = [name for name in results if name != "dense_score"]
    best_name = max(
        candidates,
        key=lambda name: (
            float(results[name]["annualized_sharpe"]),
            float(results[name]["cumulative_return"]),
        ),
    )
    best = results[best_name]
    improves_both = float(best["annualized_sharpe"]) > float(dense_result["annualized_sharpe"]) and float(
        best["cumulative_return"]
    ) > float(dense_result["cumulative_return"])
    positive_oos = float(best["annualized_sharpe"]) > 0.0 and float(best["cumulative_return"]) > 0.0
    if positive_oos:
        verdict = "MAPPING_FOUND_POSITIVE_OOS"
    elif improves_both:
        verdict = "MAPPING_IMPROVES_BUT_REMAINS_NEGATIVE"
    else:
        verdict = "MAPPING_DOES_NOT_IMPROVE_BOTH"

    deltas: dict[str, float] = {
        "annualized_sharpe": float(best["annualized_sharpe"]) - float(dense_result["annualized_sharpe"]),
        "cumulative_return": float(best["cumulative_return"]) - float(dense_result["cumulative_return"]),
        "benchmark_correlation": float(best["benchmark_correlation"]) - float(dense_result["benchmark_correlation"]),
        "max_drawdown": float(best["max_drawdown"]) - float(dense_result["max_drawdown"]),
        "mean_turnover": float(best["mean_turnover"]) - float(dense_result["mean_turnover"]),
    }
    payload: dict[str, object] = {
        "schema_version": "investor2.alphazerobeta-rank-weight-mapping.v1",
        "hypothesis": "AlphaZeroBeta may contain usable cross-sectional rank/sign information even when its raw score magnitudes are poorly calibrated for portfolio sizing.",
        "asset_count": asset_count,
        "fold_count": len(args.weights),
        "observations": int(dense_result["observations"]),
        "cost_assumptions": {
            "transaction_cost_bps_per_side": args.transaction_cost_bps,
            "borrow_fee_bps_per_year": args.borrow_fee_bps,
        },
        "mapping_contract": {
            "rank_power": "stable cross-sectional rank each day, centered around the 64-asset midpoint, sign(rank)*abs(rank)^p, then exactly dollar-neutral gross-1 normalization",
            "shrinkage": "convex blend of sign-only rank weights and normalized dense score weights, followed by exactly dollar-neutral gross-1 normalization",
            "all_assets_used": True,
        },
        "canonical_dense_reproduction": baseline_reproduction,
        "k32_sign_reproduction": sign_reproduction,
        "results": results,
        "best_mapping_by_sharpe": {"name": best_name, "metrics": best},
        "delta_best_minus_dense": deltas,
        "improves_sharpe_and_return": improves_both,
        "positive_after_cost_oos": positive_oos,
        "verdict": verdict,
        "claim_boundary": "Post-hoc execution-mapping ablation on the frozen J-Quants Free 64-stock surrogate. It tests portfolio construction, not a paper-faithful licensed-data reproduction and not a new model-training result.",
    }
    write_json(args.output, payload)
    print(json.dumps({"output": str(args.output), "best_mapping": best_name, "verdict": verdict}, sort_keys=True))


if __name__ == "__main__":
    main()
