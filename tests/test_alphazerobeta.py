from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from src.research.alphazerobeta import (
    PolicyValueNet,
    alpha_zero_beta_reward,
    evaluate_weight_path,
    make_walk_forward_folds,
    multiscale_window,
    project_market_neutral,
)


def test_market_neutral_projection_enforces_net_zero_and_gross_cap() -> None:
    result = project_market_neutral(np.array([3.0, -1.0, 2.0, 0.0]))
    assert abs(float(result.sum())) < 1e-6
    assert float(np.abs(result).sum()) <= 1.0 + 1e-6


def test_reward_penalizes_correlation_and_turnover() -> None:
    history = np.array([0.01, -0.01, 0.02, -0.02])
    benchmark = history.copy()
    previous = np.array([0.5, -0.5])
    current = np.array([-0.5, 0.5])
    penalized = alpha_zero_beta_reward(0.01, 0.0, history, benchmark, current, previous)
    unpenalized = alpha_zero_beta_reward(
        0.01,
        0.0,
        history,
        benchmark,
        current,
        previous,
        lambda_corr=0.0,
        lambda_turnover=0.0,
    )
    assert penalized < unpenalized


def test_walk_forward_uses_non_overlapping_test_windows() -> None:
    dates = pd.bdate_range("2019-01-01", "2025-12-31")
    folds = make_walk_forward_folds(dates, test_start="2023-01-01", test_end="2023-12-31")
    assert len(folds) == 2
    assert folds[0].test_indices[1] <= folds[1].test_indices[0]
    assert folds[0].train_indices[1] <= folds[0].validation_indices[0]
    assert folds[0].validation_indices[1] <= folds[0].test_indices[0]


def test_multiscale_model_forward_shape() -> None:
    rng = np.random.default_rng(2306)
    features = rng.normal(size=(140, 4, 3)).astype(np.float32)
    daily, weekly, monthly = multiscale_window(features, 120, agent_window=40)
    model = PolicyValueNet(12, 4, hidden_size=16, head_hidden=16, agent_window=40)
    hidden = torch.zeros(1, 1, 16)
    policy, value, next_hidden = model(
        torch.from_numpy(daily).unsqueeze(0),
        torch.from_numpy(weekly).unsqueeze(0),
        torch.from_numpy(monthly).unsqueeze(0),
        hidden,
    )
    assert policy.shape == (1, 4)
    assert value.shape == (1,)
    assert next_hidden.shape == (1, 1, 16)


def test_evaluation_reprojects_weights_and_applies_costs() -> None:
    weights = np.array([[2.0, -1.0], [1.0, -1.0], [-1.0, 1.0]], dtype=np.float32)
    returns = np.array([[0.01, -0.01], [0.02, -0.01], [-0.01, 0.02]], dtype=np.float32)
    benchmark = np.array([0.005, 0.004, -0.002], dtype=np.float32)
    metrics, net_returns = evaluate_weight_path(weights, returns, benchmark, transaction_cost_bps_per_side=10.0)
    assert metrics.observations == 3
    assert metrics.max_abs_net_exposure < 1e-6
    assert metrics.mean_gross_exposure <= 1.0 + 1e-6
    assert net_returns.shape == (3,)
