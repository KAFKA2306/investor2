#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from src.research.alphazerobeta import EvaluationMetrics, evaluate_weight_path, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate rank-only Top-K long / Bottom-K short selection from trained AlphaZeroBeta weights."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--weights", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frequency-output", type=Path)
    parser.add_argument("--ks", default="5,10,20,32")
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=30.0)
    parser.add_argument("--canonical-comparison", type=Path)
    parser.add_argument("--baseline-tolerance", type=float, default=1e-8)
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


def equal_weight_top_bottom(scores: np.ndarray, k: int) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("scores must be [T, N]")
    n_assets = values.shape[1]
    if k < 1 or 2 * k > n_assets:
        raise ValueError(f"k={k} invalid for {n_assets} assets")
    selected = np.zeros_like(values, dtype=np.float32)
    for t, row in enumerate(values):
        order = np.argsort(row, kind="stable")
        short_idx = order[:k]
        long_idx = order[-k:]
        if np.intersect1d(short_idx, long_idx).size:
            raise AssertionError("long and short selections overlap")
        selected[t, short_idx] = -0.5 / k
        selected[t, long_idx] = 0.5 / k
    return selected


def load_artifact(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as artifact:
        required = {"dates", "weights"}
        missing = sorted(required - set(artifact.files))
        if missing:
            raise AssertionError(f"{path} missing arrays: {missing}")
        return artifact["dates"].astype(str), artifact["weights"].astype(np.float32)


def frequency_rows(
    codes: np.ndarray,
    dates: np.ndarray,
    scores: np.ndarray,
    k: int,
    fold: int,
) -> list[dict[str, object]]:
    longs: Counter[str] = Counter()
    shorts: Counter[str] = Counter()
    for row in scores:
        order = np.argsort(row, kind="stable")
        for index in order[-k:]:
            longs[str(codes[index])] += 1
        for index in order[:k]:
            shorts[str(codes[index])] += 1
    rows: list[dict[str, object]] = []
    for code in codes.astype(str):
        rows.append(
            {
                "fold": fold,
                "k": k,
                "Code": code,
                "observations": int(len(dates)),
                "long_days": int(longs[code]),
                "short_days": int(shorts[code]),
                "long_rate": float(longs[code] / len(dates)),
                "short_rate": float(shorts[code] / len(dates)),
            }
        )
    return rows


def canonical_check(
    dense: dict[str, float | int],
    path: Path,
    tolerance: float,
) -> dict[str, object]:
    canonical = json.loads(path.read_text(encoding="utf-8"))["primary_lambda_corr_0_5"]
    keys = ["observations", "annualized_sharpe", "benchmark_correlation", "max_drawdown", "cumulative_return"]
    deltas: dict[str, float] = {}
    for key in keys:
        expected = float(canonical[key])
        actual = float(dense[key])
        deltas[key] = actual - expected
        if key == "observations":
            if int(actual) != int(expected):
                raise AssertionError(f"dense baseline observations mismatch: {actual} != {expected}")
        elif abs(actual - expected) > tolerance:
            raise AssertionError(
                f"dense baseline does not reproduce canonical {key}: {actual} vs {expected}, tolerance={tolerance}"
            )
    return {"passed": True, "tolerance": tolerance, "delta_actual_minus_canonical": deltas}


def main() -> None:
    args = parse_args()
    ks = sorted({int(item.strip()) for item in args.ks.split(",") if item.strip()})
    if not ks:
        raise ValueError("at least one K is required")

    with np.load(args.dataset, allow_pickle=False) as dataset:
        dataset_dates = dataset["dates"].astype(str)
        codes = dataset["codes"].astype(str)
        all_returns = dataset["returns"].astype(np.float32)
        all_benchmark = dataset["benchmark"].astype(np.float32)
    date_lookup = {date: i for i, date in enumerate(dataset_dates)}

    observed_dates: set[str] = set()
    dense_returns: list[np.ndarray] = []
    dense_benchmarks: list[np.ndarray] = []
    dense_metrics: list[EvaluationMetrics] = []
    topk_returns: dict[int, list[np.ndarray]] = {k: [] for k in ks}
    topk_benchmarks: dict[int, list[np.ndarray]] = {k: [] for k in ks}
    topk_metrics: dict[int, list[EvaluationMetrics]] = {k: [] for k in ks}
    frequencies: list[dict[str, object]] = []

    for fold, weight_path in enumerate(args.weights):
        dates, scores = load_artifact(weight_path)
        if scores.shape[1] != len(codes):
            raise AssertionError(f"asset count mismatch in {weight_path}: {scores.shape[1]} != {len(codes)}")
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

        metrics, net = evaluate_weight_path(
            scores,
            returns,
            benchmark,
            transaction_cost_bps_per_side=args.transaction_cost_bps,
            borrow_fee_bps_per_year=args.borrow_fee_bps,
        )
        dense_returns.append(net)
        dense_benchmarks.append(benchmark)
        dense_metrics.append(metrics)

        for k in ks:
            sparse = equal_weight_top_bottom(scores, k)
            sparse_metrics, sparse_net = evaluate_weight_path(
                sparse,
                returns,
                benchmark,
                transaction_cost_bps_per_side=args.transaction_cost_bps,
                borrow_fee_bps_per_year=args.borrow_fee_bps,
            )
            topk_returns[k].append(sparse_net)
            topk_benchmarks[k].append(benchmark)
            topk_metrics[k].append(sparse_metrics)
            frequencies.extend(frequency_rows(codes, dates, scores, k, fold))

    dense = aggregate(dense_returns, dense_benchmarks, dense_metrics)
    results: dict[str, dict[str, float | int]] = {
        str(k): aggregate(topk_returns[k], topk_benchmarks[k], topk_metrics[k]) for k in ks
    }
    best_k = max(
        ks,
        key=lambda k: (
            float(results[str(k)]["annualized_sharpe"]),
            float(results[str(k)]["cumulative_return"]),
        ),
    )
    baseline_check = None
    if args.canonical_comparison:
        baseline_check = canonical_check(dense, args.canonical_comparison, args.baseline_tolerance)

    best = results[str(best_k)]
    payload: dict[str, object] = {
        "schema_version": "investor2.alphazerobeta-topk-selection.v1",
        "hypothesis": "AlphaZeroBeta rank information may become more investable when restricted to Top-K longs and Bottom-K shorts.",
        "selection_rule": "Each OOS day rank the 64 raw policy scores; long Top-K and short Bottom-K at equal weight, +0.5 gross long and -0.5 gross short.",
        "sizing": "equal weight within each selected side; selection is isolated from model sizing",
        "fold_count": len(args.weights),
        "asset_count": int(len(codes)),
        "ks": ks,
        "cost_assumptions": {
            "transaction_cost_bps_per_side": args.transaction_cost_bps,
            "borrow_fee_bps_per_year": args.borrow_fee_bps,
        },
        "dense_baseline": dense,
        "canonical_baseline_reproduction": baseline_check,
        "topk": results,
        "best_topk_by_sharpe": {"k": best_k, "metrics": best},
        "delta_best_minus_dense": {
            "annualized_sharpe": float(best["annualized_sharpe"]) - float(dense["annualized_sharpe"]),
            "cumulative_return": float(best["cumulative_return"]) - float(dense["cumulative_return"]),
            "benchmark_correlation": float(best["benchmark_correlation"]) - float(dense["benchmark_correlation"]),
            "max_drawdown": float(best["max_drawdown"]) - float(dense["max_drawdown"]),
            "mean_turnover": float(best["mean_turnover"]) - float(dense["mean_turnover"]),
        },
        "verdict": (
            "TOPK_IMPROVES_SHARPE_AND_RETURN"
            if float(best["annualized_sharpe"]) > float(dense["annualized_sharpe"])
            and float(best["cumulative_return"]) > float(dense["cumulative_return"])
            else "TOPK_DOES_NOT_IMPROVE_BOTH"
        ),
        "claim_boundary": "Post-hoc execution ablation on the frozen J-Quants Free surrogate; not paper-faithful AlphaZeroBeta and not an exact licensed-data reproduction.",
    }
    write_json(args.output, payload)

    if args.frequency_output:
        import pandas as pd

        frame = pd.DataFrame(frequencies).sort_values(["k", "fold", "Code"])
        args.frequency_output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.frequency_output, index=False)

    print(json.dumps({"output": str(args.output), "best_k": best_k, "verdict": payload["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()
