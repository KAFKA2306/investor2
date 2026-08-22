#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from torch.optim import Adam

from scripts.alphazerobeta_train import (
    collect_trajectory,
    deterministic_weights,
    next_period_bounds,
    ppo_update,
    seed_all,
)
from src.research.alphazerobeta import (
    PAPER_AGENT_WINDOW,
    PAPER_LEARNING_RATE,
    PolicyValueNet,
    evaluate_weight_path,
    make_walk_forward_folds,
    metrics_to_dict,
    write_json,
)
from src.research.alphazerobeta_paper import PaperAlphaZeroBetaEnvironment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one AlphaZeroBeta Appendix-D paper-semantics fold.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--test-end", required=True)
    parser.add_argument("--fold-index", type=int, default=0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--seed", type=int, default=2306)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--hidden-size", type=int, default=512)
    parser.add_argument("--agent-window", type=int, default=PAPER_AGENT_WINDOW)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=30.0)
    parser.add_argument("--lambda-corr", type=float, default=0.5)
    parser.add_argument("--lambda-turnover", type=float, default=0.001)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false")
    seed_all(args.seed)
    data = np.load(args.dataset, allow_pickle=False)
    dates = data["dates"].astype(str)
    features = data["features"].astype(np.float32)
    returns = data["returns"].astype(np.float32)
    benchmark = data["benchmark"].astype(np.float32)
    folds = make_walk_forward_folds(dates, test_start=args.test_start, test_end=args.test_end)
    if not 0 <= args.fold_index < len(folds):
        raise AssertionError(f"fold-index {args.fold_index} outside 0..{len(folds) - 1}")
    fold = folds[args.fold_index]
    train_start, train_end = fold.train_indices
    validation_start, validation_end = fold.validation_indices
    test_start, test_end = fold.test_indices
    device = torch.device(args.device)
    feature_dim = features.shape[1] * features.shape[2]
    model = PolicyValueNet(
        feature_dim,
        features.shape[1],
        hidden_size=args.hidden_size,
        head_hidden=args.hidden_size,
        agent_window=args.agent_window,
    ).to(device)
    optimizer = Adam(model.parameters(), lr=PAPER_LEARNING_RATE)
    losses: list[float] = []
    best_validation_sharpe = float("-inf")
    best_state: dict[str, torch.Tensor] | None = None
    train_span = train_end - train_start - 1
    segment = min(args.horizon, train_span)
    if segment < 2:
        raise AssertionError("training fold is too short")
    max_offset = max(1, train_span - segment + 1)
    validation_decision_start, validation_decision_end, validation_target_start, validation_target_end = (
        next_period_bounds(validation_start, validation_end)
    )

    for iteration in range(args.iterations):
        segment_start = train_start + (iteration * segment) % max_offset
        segment_end = min(segment_start + segment + 1, train_end)
        env = PaperAlphaZeroBetaEnvironment(
            returns,
            benchmark,
            start=segment_start,
            end=segment_end,
            lambda_corr=args.lambda_corr,
            lambda_turnover=args.lambda_turnover,
        )
        rollout = collect_trajectory(
            model,
            env,  # type: ignore[arg-type] -- same step/reset/t/n_assets protocol as bounded environment
            features,
            device,
            hidden_size=args.hidden_size,
            agent_window=args.agent_window,
            horizon=args.horizon,
        )
        losses.append(
            ppo_update(model, optimizer, rollout, hidden_size=args.hidden_size, device=device)
        )
        validation_weights = deterministic_weights(
            model,
            features,
            validation_decision_start,
            validation_decision_end,
            device,
            hidden_size=args.hidden_size,
            agent_window=args.agent_window,
        )
        validation_metrics, _ = evaluate_weight_path(
            validation_weights,
            returns[validation_target_start:validation_target_end],
            benchmark[validation_target_start:validation_target_end],
            transaction_cost_bps_per_side=args.transaction_cost_bps,
            borrow_fee_bps_per_year=args.borrow_fee_bps,
        )
        if validation_metrics.annualized_sharpe > best_validation_sharpe:
            best_validation_sharpe = validation_metrics.annualized_sharpe
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }

    if best_state is None:
        raise AssertionError("no validation checkpoint selected")
    model.load_state_dict(best_state)
    test_decision_start, test_decision_end, test_target_start, test_target_end = next_period_bounds(
        test_start, test_end
    )
    raw_weights = deterministic_weights(
        model,
        features,
        test_decision_start,
        test_decision_end,
        device,
        hidden_size=args.hidden_size,
        agent_window=args.agent_window,
    )
    test_returns = returns[test_target_start:test_target_end]
    test_benchmark = benchmark[test_target_start:test_target_end]
    metrics, net_returns = evaluate_weight_path(
        raw_weights,
        test_returns,
        test_benchmark,
        transaction_cost_bps_per_side=args.transaction_cost_bps,
        borrow_fee_bps_per_year=args.borrow_fee_bps,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    weights_path = args.output.with_suffix(".weights.npz")
    np.savez_compressed(
        weights_path,
        dates=dates[test_target_start:test_target_end],
        weights=raw_weights,
        net_returns=net_returns.astype(np.float32),
        benchmark=test_benchmark,
    )
    write_json(
        args.output,
        {
            "schema_version": "investor2.alphazerobeta-paper-fold-result.v1",
            "paper": "arXiv:2607.18001v1 Appendix D",
            "dataset": str(args.dataset),
            "device": str(device),
            "seed": args.seed,
            "fold": asdict(fold),
            "realized_oos_dates": {
                "start": str(dates[test_target_start]),
                "end": str(dates[test_target_end - 1]),
            },
            "training": {
                "iterations": args.iterations,
                "horizon": args.horizon,
                "hidden_size": args.hidden_size,
                "agent_window": args.agent_window,
                "final_loss": losses[-1] if losses else None,
                "best_validation_sharpe": best_validation_sharpe,
                "lambda_corr": args.lambda_corr,
                "lambda_turnover": args.lambda_turnover,
                "reward_history_semantics": "Appendix D.4.2: previous weights reapplied over [t-W,t)",
            },
            "evaluation_cost_assumptions": {
                "transaction_cost_bps_per_side": args.transaction_cost_bps,
                "borrow_fee_bps_per_year": args.borrow_fee_bps,
                "classification": "public-surrogate execution assumption",
            },
            "metrics": metrics_to_dict(metrics),
            "weights_artifact": str(weights_path),
            "claim_boundary": "Paper-semantics implementation smoke on surrogate inputs; not a Table-4 reproduction.",
        },
    )
    print(
        json.dumps(
            {"result": str(args.output), "metrics": metrics_to_dict(metrics)},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
