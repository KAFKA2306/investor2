#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.research.alphazerobeta import write_json
from src.research.alphazerobeta_paper import (
    PAPER_HYPERPARAMETERS,
    exact_paper_readiness,
    public_surrogate_deviations,
)

DEFAULT_DATASET = Path("docs/research/results/alphazerobeta_2024/etf_panel.npz")
DEFAULT_OUTPUT = Path("docs/research/results/alphazerobeta_paper_reproduction")
PUBLIC_SEED = 2306
PUBLIC_ITERATIONS = 10
PUBLIC_HORIZON = 200
PUBLIC_TRANSACTION_COST_BPS = 15.0
PUBLIC_BORROW_BPS = 30.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute the disclosed AlphaZeroBeta paper reproduction contract.")
    parser.add_argument("--mode", choices=["exact-paper", "public-surrogate"], required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def run(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=env)


def exact_paper_mode(args: argparse.Namespace) -> int:
    manifest = read_json(args.manifest) if args.manifest else None
    readiness = exact_paper_readiness(manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "exact_paper_readiness.json", readiness)
    if not bool(readiness["ready"]):
        print(json.dumps(readiness, sort_keys=True))
        return 2
    raise RuntimeError(
        "exact-paper inputs passed the declared manifest gates, but the licensed dataset itself must be independently "
        "audited before a 22-fold x 9-restart Table-4 reproduction is allowed to run"
    )


def train_fold(dataset: Path, output: Path, fold_index: int, lambda_corr: float) -> Path:
    run(
        [
            sys.executable,
            "scripts/alphazerobeta_paper_train.py",
            "--dataset",
            str(dataset),
            "--output",
            str(output),
            "--test-start",
            "2024-01-01",
            "--test-end",
            "2024-12-31",
            "--fold-index",
            str(fold_index),
            "--device",
            "cpu",
            "--seed",
            str(PUBLIC_SEED),
            "--iterations",
            str(PUBLIC_ITERATIONS),
            "--horizon",
            str(PUBLIC_HORIZON),
            "--hidden-size",
            str(PAPER_HYPERPARAMETERS.hidden_size),
            "--agent-window",
            str(PAPER_HYPERPARAMETERS.agent_window),
            "--transaction-cost-bps",
            str(PUBLIC_TRANSACTION_COST_BPS),
            "--borrow-fee-bps",
            str(PUBLIC_BORROW_BPS),
            "--lambda-corr",
            str(lambda_corr),
            "--lambda-turnover",
            str(PAPER_HYPERPARAMETERS.lambda_turnover),
        ]
    )
    return output.with_suffix(".weights.npz")


def public_surrogate_mode(args: argparse.Namespace) -> int:
    if not args.dataset.exists():
        raise FileNotFoundError(args.dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    readiness = exact_paper_readiness(None)
    write_json(args.output_dir / "exact_paper_readiness.json", readiness)

    primary_weights: list[Path] = []
    ablation_weights: list[Path] = []
    for fold_index in (0, 1):
        primary_weights.append(
            train_fold(args.dataset, args.output_dir / f"primary_fold{fold_index}.json", fold_index, 0.5)
        )
        ablation_weights.append(
            train_fold(args.dataset, args.output_dir / f"ablation_fold{fold_index}.json", fold_index, 0.0)
        )

    comparison = args.output_dir / "comparison.json"
    run(
        [
            sys.executable,
            "scripts/alphazerobeta_compare.py",
            "--dataset",
            str(args.dataset),
            "--primary-weights",
            *map(str, primary_weights),
            "--ablation-weights",
            *map(str, ablation_weights),
            "--output",
            str(comparison),
            "--transaction-cost-bps",
            str(PUBLIC_TRANSACTION_COST_BPS),
            "--borrow-fee-bps",
            str(PUBLIC_BORROW_BPS),
        ]
    )
    metrics = read_json(comparison)
    manifest = {
        "schema_version": "investor2.alphazerobeta-paper-reproduction.v1",
        "mode": "public-surrogate",
        "paper": "AlphaZeroBeta: Deep Reinforcement Learning for Market-Neutral Portfolios, arXiv:2607.18001v1",
        "execution_status": "completed",
        "exact_paper_result_reproduction": False,
        "dataset": str(args.dataset),
        "architecture": {
            "cnn_filters": [32, 64, 64],
            "cnn_kernels": [8, 4, 3],
            "cnn_strides": [4, 2, 1],
            "gru_hidden": PAPER_HYPERPARAMETERS.hidden_size,
            "head_hidden": PAPER_HYPERPARAMETERS.head_hidden,
            "agent_window": PAPER_HYPERPARAMETERS.agent_window,
        },
        "reward_state": {
            "sigma_corr_window": PAPER_HYPERPARAMETERS.vol_corr_window,
            "semantics": "Appendix D.4.2: previous weights reapplied to asset returns over [t-W,t)",
            "lambda_corr": PAPER_HYPERPARAMETERS.lambda_corr,
            "lambda_turnover": PAPER_HYPERPARAMETERS.lambda_turnover,
        },
        "ppo": {
            "gamma": PAPER_HYPERPARAMETERS.gamma,
            "gae_lambda": PAPER_HYPERPARAMETERS.gae_lambda,
            "clip": PAPER_HYPERPARAMETERS.ppo_clip,
            "learning_rate": PAPER_HYPERPARAMETERS.learning_rate,
            "ppo_epochs": PAPER_HYPERPARAMETERS.ppo_epochs,
            "entropy_coefficient": PAPER_HYPERPARAMETERS.entropy_coefficient,
            "value_loss_coefficient": PAPER_HYPERPARAMETERS.value_loss_coefficient,
        },
        "execution_smoke": {
            "folds": 2,
            "seed": PUBLIC_SEED,
            "iterations_per_fold": PUBLIC_ITERATIONS,
            "horizon": PUBLIC_HORIZON,
            "transaction_cost_bps_per_side": PUBLIC_TRANSACTION_COST_BPS,
            "borrow_fee_bps_per_year": PUBLIC_BORROW_BPS,
        },
        "deviations_from_table4_replication": public_surrogate_deviations(),
        "comparison": metrics,
    }
    write_json(args.output_dir / "manifest.json", manifest)

    primary = metrics["primary_lambda_corr_0_5"]
    ablation = metrics["ablation_lambda_corr_0"]
    markdown = f"""# AlphaZeroBeta paper-reproduction execution\n\n- Mode: **public-surrogate**\n- Execution: **completed**\n- Exact Table-4 reproduction: **no** — licensed paper inputs are absent and exact mode fails closed.\n- Architecture smoke: CNN 32/64/64, kernels 8/4/3, strides 4/2/1, GRU/head 512, 100-step window.\n- Reward state: Appendix D.4.2 previous-weight rolling 60-day sigma/correlation semantics.\n- PPO smoke: 10 epochs, gamma 0.99, GAE 0.95, clip 0.20, learning rate 3e-4.\n- OOS: two frozen 2024 folds, one seed, Appendix-D-style 10 iterations/fold and horizon 200.\n- Costs: 15 bps/side + 30 bps/year borrow for this public surrogate.\n\n## Primary lambda_corr=0.5\n\n- Cumulative after-cost return: {float(primary['cumulative_return']):.4%}\n- Annualized Sharpe: {float(primary['annualized_sharpe']):.4f}\n- Benchmark correlation: {float(primary['benchmark_correlation']):.4f}\n- Maximum drawdown: {float(primary['max_drawdown']):.4%}\n\n## Lambda_corr=0 ablation\n\n- Cumulative after-cost return: {float(ablation['cumulative_return']):.4%}\n- Annualized Sharpe: {float(ablation['annualized_sharpe']):.4f}\n- Benchmark correlation: {float(ablation['benchmark_correlation']):.4f}\n- Maximum drawdown: {float(ablation['max_drawdown']):.4%}\n\n## Claim boundary\n\nThis run verifies the disclosed 512-wide architecture and Appendix-D reward-state semantics end-to-end on the frozen public panel. It is not a reproduction of the paper's reported Table 4 because the licensed historical constituent and feature data are unavailable. See `manifest.json` and `exact_paper_readiness.json`.\n"""
    (args.output_dir / "SUMMARY.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"comparison": str(comparison), "manifest": str(args.output_dir / "manifest.json")}, sort_keys=True))
    return 0


def main() -> None:
    args = parse_args()
    code = exact_paper_mode(args) if args.mode == "exact-paper" else public_surrogate_mode(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
