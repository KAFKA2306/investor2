#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

from scripts import alphazerobeta_train as trainer
from scripts.alphazerobeta_japan_free_train import japan_free_folds
from src.research.tradability import mask_action_for_tradability, resolve_tradable, tradability_summary


def _argument_path(name: str) -> Path:
    try:
        index = sys.argv.index(name)
    except ValueError as exc:
        raise SystemExit(f"missing required argument {name}") from exc
    if index + 1 >= len(sys.argv):
        raise SystemExit(f"missing value for {name}")
    return Path(sys.argv[index + 1])


DATASET_PATH = _argument_path("--dataset")
OUTPUT_PATH = _argument_path("--output")
with np.load(DATASET_PATH, allow_pickle=False) as dataset:
    shape = dataset["returns"].shape
    TRADABLE = resolve_tradable(dataset, shape)


def collect_trajectory(
    model: trainer.PolicyValueNet,
    env: trainer.AlphaZeroBetaEnvironment | trainer.PaperAlphaZeroBetaEnvironment,
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
        inputs = trainer.tensor_window(features, env.t, device, agent_window)
        mean, value, hidden = model(*inputs, hidden)
        dist = torch.distributions.Normal(mean, 0.1)
        sample = dist.sample()
        log_prob = dist.log_prob(sample).sum(dim=-1)
        raw_action = torch.tanh(sample).detach().cpu().numpy()[0]
        action = mask_action_for_tradability(raw_action, TRADABLE[env.t]).astype(np.float32)
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


def deterministic_weights(
    model: trainer.PolicyValueNet,
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
            inputs = trainer.tensor_window(features, t, device, agent_window)
            mean, _, hidden = model(*inputs, hidden)
            raw = torch.tanh(mean).squeeze(0).cpu().numpy()
            weights.append(mask_action_for_tradability(raw, TRADABLE[t]).astype(np.float32))
    return np.asarray(weights, dtype=np.float32)


def main() -> None:
    trainer.collect_trajectory = collect_trajectory
    trainer.deterministic_weights = deterministic_weights
    trainer.make_walk_forward_folds = japan_free_folds
    trainer.main()

    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    payload["tradability"] = {
        **tradability_summary(TRADABLE),
        "policy_rule": (
            "At each decision date, inactive raw action components are set to the active-action mean before "
            "market-neutral projection; this makes every inactive projected weight exactly zero without using future availability."
        ),
        "walk_forward_adapter": "same bounded J-Quants Free 12m train / 3m validation / 3m test schedule as alphazerobeta_japan_free_train.py",
        "legacy_compatibility": "datasets without a tradable array are treated as fully tradable",
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
