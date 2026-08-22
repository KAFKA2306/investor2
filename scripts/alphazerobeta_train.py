#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.optim import Adam

from src.research.alphazerobeta import (
    PAPER_AGENT_WINDOW,
    PAPER_GAE_LAMBDA,
    PAPER_GAMMA,
    PAPER_LEARNING_RATE,
    PAPER_PPO_CLIP,
    PAPER_PPO_EPOCHS,
    AlphaZeroBetaEnvironment,
    PolicyValueNet,
    evaluate_weight_path,
    make_walk_forward_folds,
    metrics_to_dict,
    multiscale_window,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one bounded AlphaZeroBeta recurrent-PPO fold.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test-start", required=True)
    parser.add_argument("--test-end", required=True)
    parser.add_argument("--fold-index", type=int, default=0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--seed", type=int, default=2306)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--hidden-size", type=int, default=512)
    parser.add_argument("--agent-window", type=int, default=PAPER_AGENT_WINDOW)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=100.0)
    parser.add_argument("--lambda-corr", type=float, default=0.5)
    parser.add_argument("--lambda-turnover", type=float, default=0.001)
    return parser.parse_args()


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def tensor_window(
    features: np.ndarray,
    t: int,
    device: torch.device,
    agent_window: int,
) -> tuple[torch.Tensor, ...]:
    windows = multiscale_window(features, t, agent_window=agent_window)
    return tuple(torch.as_tensor(x, dtype=torch.float32, device=device).unsqueeze(0) for x in windows)


def collect_trajectory(
    model: PolicyValueNet,
    env: AlphaZeroBetaEnvironment,
    features: np.ndarray,
    device: torch.device,
    *,
    hidden_size: int,
    agent_window: int,
    horizon: int,
) -> dict[str, object]:
    obs: list[tuple[torch.Tensor, ...]] = []
    actions: list[torch.Tensor] = []
    rewards: list[float] = []
    values: list[torch.Tensor] = []
    log_probs: list[torch.Tensor] = []
    env.reset()
    hidden = torch.zeros(1, 1, hidden_size, device=device)
    for _ in range(horizon):
        inputs = tensor_window(features, env.t, device, agent_window)
        mean, value, hidden = model(*inputs, hidden)
        dist = torch.distributions.Normal(mean, 0.1)
        sample = dist.sample()
        log_prob = dist.log_prob(sample).sum(dim=-1)
        action = torch.tanh(sample).detach().cpu().numpy()[0]
        _, reward, done, _ = env.step(action)
        obs.append(inputs)
        actions.append(sample.squeeze(0))
        rewards.append(reward)
        values.append(value.squeeze(0))
        log_probs.append(log_prob.squeeze(0))
        hidden = hidden.detach()
        if done:
            break
    return {
        "obs": obs,
        "actions": torch.stack(actions),
        "rewards": torch.tensor(rewards, dtype=torch.float32, device=device),
        "values": torch.stack(values).detach(),
        "log_probs": torch.stack(log_probs).detach(),
    }


def gae(rewards: torch.Tensor, values: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    advantages = torch.zeros_like(rewards)
    state = torch.tensor(0.0, device=rewards.device)
    for t in reversed(range(len(rewards))):
        v_next = values[t + 1] if t + 1 < len(values) else torch.tensor(0.0, device=rewards.device)
        delta = rewards[t] + PAPER_GAMMA * v_next - values[t]
        state = delta + PAPER_GAMMA * PAPER_GAE_LAMBDA * state
        advantages[t] = state
    returns = advantages + values
    advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)
    return advantages, returns


def ppo_update(
    model: PolicyValueNet,
    optimizer: Adam,
    rollout: dict[str, object],
    *,
    hidden_size: int,
    device: torch.device,
) -> float:
    rewards = rollout["rewards"]
    values = rollout["values"]
    old_log_probs = rollout["log_probs"]
    actions = rollout["actions"]
    obs = rollout["obs"]
    assert isinstance(rewards, torch.Tensor)
    assert isinstance(values, torch.Tensor)
    assert isinstance(old_log_probs, torch.Tensor)
    assert isinstance(actions, torch.Tensor)
    assert isinstance(obs, list)
    advantages, returns = gae(rewards, values)
    last_loss = 0.0
    for _ in range(PAPER_PPO_EPOCHS):
        hidden = torch.zeros(1, 1, hidden_size, device=device)
        new_log_probs: list[torch.Tensor] = []
        new_values: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []
        for k, inputs in enumerate(obs):
            mean, value, hidden = model(*inputs, hidden)
            dist = torch.distributions.Normal(mean, 0.1)
            new_log_probs.append(dist.log_prob(actions[k]).sum(dim=-1).squeeze())
            new_values.append(value.squeeze(0))
            entropies.append(dist.entropy().sum(dim=-1).squeeze())
        new_log_prob = torch.stack(new_log_probs)
        new_value = torch.stack(new_values)
        entropy = torch.stack(entropies).mean()
        ratio = (new_log_prob - old_log_probs).exp()
        clipped = torch.clamp(ratio, 1 - PAPER_PPO_CLIP, 1 + PAPER_PPO_CLIP)
        policy_loss = -torch.min(ratio * advantages, clipped * advantages).mean()
        value_loss = F.mse_loss(new_value, returns)
        loss = policy_loss + 0.5 * value_loss - 0.01 * entropy
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
        optimizer.step()
        last_loss = float(loss.detach().cpu())
    return last_loss


def deterministic_weights(
    model: PolicyValueNet,
    features: np.ndarray,
    start: int,
    end: int,
    device: torch.device,
    *,
    hidden_size: int,
    agent_window: int,
) -> np.ndarray:
    model.eval()
    hidden = torch.zeros(1, 1, hidden_size, device=device)
    weights: list[np.ndarray] = []
    with torch.no_grad():
        for t in range(start, end):
            inputs = tensor_window(features, t, device, agent_window)
            mean, _, hidden = model(*inputs, hidden)
            weights.append(torch.tanh(mean).squeeze(0).cpu().numpy())
    return np.asarray(weights, dtype=np.float32)


def next_period_bounds(start: int, end: int) -> tuple[int, int, int, int]:
    """Align decisions made at t with realized returns at t+1 inside [start, end)."""
    if end - start < 2:
        raise ValueError("next-period evaluation requires at least two observations")
    return start, end - 1, start + 1, end


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
    losses = []
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
        env = AlphaZeroBetaEnvironment(
            returns,
            benchmark,
            start=segment_start,
            end=segment_end,
            lambda_corr=args.lambda_corr,
            lambda_turnover=args.lambda_turnover,
        )
        rollout = collect_trajectory(
            model,
            env,
            features,
            device,
            hidden_size=args.hidden_size,
            agent_window=args.agent_window,
            horizon=args.horizon,
        )
        losses.append(ppo_update(model, optimizer, rollout, hidden_size=args.hidden_size, device=device))
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
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
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
            "schema_version": "investor2.alphazerobeta-fold-result.v2",
            "hypothesis_id": "alphazerobeta_market_neutral_v1",
            "dataset": str(args.dataset),
            "device": str(device),
            "cuda_device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
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
            },
            "evaluation_cost_assumptions": {
                "transaction_cost_bps_per_side": args.transaction_cost_bps,
                "borrow_fee_bps_per_year": args.borrow_fee_bps,
                "classification": "assumption, not realized execution cost",
            },
            "metrics": metrics_to_dict(metrics),
            "weights_artifact": str(weights_path),
            "claim_boundary": "One bounded fold is a feasibility result, not hypothesis confirmation.",
        },
    )
    print(json.dumps({"result": str(args.output), "metrics": metrics_to_dict(metrics)}))


if __name__ == "__main__":
    main()
