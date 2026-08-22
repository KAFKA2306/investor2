#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from src.research.alphazerobeta import evaluate_weight_path, write_json

CORRELATION_GATE = 0.15
NEUTRALITY_TOLERANCE = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare confirmatory AlphaZeroBeta folds with the lambda_corr=0 ablation."
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--primary-weights", required=True, nargs="+", type=Path)
    parser.add_argument("--ablation-weights", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=100.0)
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
        raise AssertionError("return and benchmark arrays must have the same shape")
    if values.size < 2 or float(values.std(ddof=0)) <= 1e-12 or float(market.std(ddof=0)) <= 1e-12:
        return 0.0
    return float(np.corrcoef(values, market)[0, 1])


def max_drawdown(returns: np.ndarray) -> float:
    equity = np.cumprod(1.0 + np.asarray(returns, dtype=np.float64))
    if equity.size == 0:
        return 0.0
    peaks = np.maximum.accumulate(equity)
    return float((equity / peaks - 1.0).min())


def load_weight_artifact(path: Path) -> tuple[np.ndarray, np.ndarray]:
    artifact = np.load(path, allow_pickle=False)
    required = {"dates", "weights"}
    missing = sorted(required - set(artifact.files))
    if missing:
        raise AssertionError(f"{path} missing arrays: {missing}")
    return artifact["dates"].astype(str), artifact["weights"].astype(np.float32)


def evaluate_fold(
    dataset: np.lib.npyio.NpzFile,
    date_lookup: dict[str, int],
    dates: np.ndarray,
    weights: np.ndarray,
    *,
    transaction_cost_bps: float,
    borrow_fee_bps: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    missing = [date for date in dates if date not in date_lookup]
    if missing:
        raise AssertionError(f"weight dates missing from frozen dataset: {missing[:3]}")
    indices = np.asarray([date_lookup[date] for date in dates], dtype=np.int64)
    returns = dataset["returns"][indices].astype(np.float32)
    benchmark = dataset["benchmark"][indices].astype(np.float32)
    metrics, net_returns = evaluate_weight_path(
        weights,
        returns,
        benchmark,
        transaction_cost_bps_per_side=transaction_cost_bps,
        borrow_fee_bps_per_year=borrow_fee_bps,
    )
    neutral = {
        "max_abs_net_exposure": metrics.max_abs_net_exposure,
        "mean_gross_exposure": metrics.mean_gross_exposure,
    }
    return net_returns, benchmark, neutral


def summarize(returns: np.ndarray, benchmark: np.ndarray) -> dict[str, float | int]:
    return {
        "observations": int(returns.size),
        "annualized_sharpe": annualized_sharpe(returns),
        "benchmark_correlation": correlation(returns, benchmark),
        "max_drawdown": max_drawdown(returns),
        "cumulative_return": float(np.prod(1.0 + returns) - 1.0),
    }


def main() -> None:
    args = parse_args()
    if len(args.primary_weights) != len(args.ablation_weights):
        raise AssertionError("primary and ablation artifact counts must match")
    if not args.primary_weights:
        raise AssertionError("at least one fold pair is required")

    dataset = np.load(args.dataset, allow_pickle=False)
    dataset_dates = dataset["dates"].astype(str)
    date_lookup = {date: i for i, date in enumerate(dataset_dates)}
    observed_dates: set[str] = set()
    primary_returns: list[np.ndarray] = []
    ablation_returns: list[np.ndarray] = []
    benchmarks: list[np.ndarray] = []
    primary_neutrality: list[dict[str, float]] = []

    for primary_path, ablation_path in zip(args.primary_weights, args.ablation_weights, strict=True):
        primary_dates, primary_weights = load_weight_artifact(primary_path)
        ablation_dates, ablation_weights = load_weight_artifact(ablation_path)
        if not np.array_equal(primary_dates, ablation_dates):
            raise AssertionError(f"fold dates differ: {primary_path} vs {ablation_path}")
        overlap = observed_dates.intersection(primary_dates.tolist())
        if overlap:
            raise AssertionError(f"test folds overlap: {sorted(overlap)[:3]}")
        observed_dates.update(primary_dates.tolist())
        p_returns, benchmark, neutral = evaluate_fold(
            dataset,
            date_lookup,
            primary_dates,
            primary_weights,
            transaction_cost_bps=args.transaction_cost_bps,
            borrow_fee_bps=args.borrow_fee_bps,
        )
        a_returns, ablation_benchmark, _ = evaluate_fold(
            dataset,
            date_lookup,
            ablation_dates,
            ablation_weights,
            transaction_cost_bps=args.transaction_cost_bps,
            borrow_fee_bps=args.borrow_fee_bps,
        )
        if not np.array_equal(benchmark, ablation_benchmark):
            raise AssertionError("primary and ablation benchmark observations differ")
        primary_returns.append(p_returns)
        ablation_returns.append(a_returns)
        benchmarks.append(benchmark)
        primary_neutrality.append(neutral)

    primary = summarize(np.concatenate(primary_returns), np.concatenate(benchmarks))
    ablation = summarize(np.concatenate(ablation_returns), np.concatenate(benchmarks))
    fold_count = len(primary_returns)
    max_abs_net = max(item["max_abs_net_exposure"] for item in primary_neutrality)
    max_mean_gross = max(item["mean_gross_exposure"] for item in primary_neutrality)
    gates = {
        "minimum_confirmatory_folds": fold_count >= 2,
        "absolute_correlation_lte_0_15": abs(float(primary["benchmark_correlation"])) <= CORRELATION_GATE,
        "sharpe_gt_lambda_corr_zero": float(primary["annualized_sharpe"]) > float(ablation["annualized_sharpe"]),
        "absolute_correlation_lt_lambda_corr_zero": abs(float(primary["benchmark_correlation"]))
        < abs(float(ablation["benchmark_correlation"])),
        "dollar_neutrality": max_abs_net <= NEUTRALITY_TOLERANCE and max_mean_gross <= 1.0 + NEUTRALITY_TOLERANCE,
    }
    verdict = "confirm" if all(gates.values()) else "reject"
    if fold_count < 2:
        verdict = "feasibility_only"

    write_json(
        args.output,
        {
            "schema_version": "investor2.alphazerobeta-comparison.v1",
            "hypothesis_id": "alphazerobeta_market_neutral_v1",
            "dataset": str(args.dataset),
            "fold_count": fold_count,
            "cost_assumptions": {
                "transaction_cost_bps_per_side": args.transaction_cost_bps,
                "borrow_fee_bps_per_year": args.borrow_fee_bps,
                "classification": "pre-registered sensitivity assumption, not realized execution cost",
            },
            "primary_lambda_corr_0_5": primary,
            "ablation_lambda_corr_0": ablation,
            "neutrality": {
                "max_abs_net_exposure_across_folds": max_abs_net,
                "max_fold_mean_gross_exposure": max_mean_gross,
            },
            "gates": gates,
            "verdict": verdict,
            "claim_boundary": (
                "confirm is an independent mechanism-validation verdict, not exact reproduction of the paper's "
                "licensed-data results."
            ),
        },
    )
    print(json.dumps({"output": str(args.output), "verdict": verdict, "gates": gates}, sort_keys=True))


if __name__ == "__main__":
    main()
