from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from src.research.alphazerobeta import PolicyValueNet
from src.research.alphazerobeta_paper import (
    PAPER_COSTS,
    PAPER_HYPERPARAMETERS,
    REQUIRED_FEATURE_GROUPS,
    TIME_VARYING_INDICES,
    PaperAlphaZeroBetaEnvironment,
    exact_paper_readiness,
    paper_fold_contract,
)


def test_paper_hyperparameters_match_appendix_d5() -> None:
    hp = PAPER_HYPERPARAMETERS
    assert hp.hidden_size == 512
    assert hp.head_hidden == 512
    assert hp.agent_window == 100
    assert hp.vol_corr_window == 60
    assert hp.gamma == 0.99
    assert hp.gae_lambda == 0.95
    assert hp.ppo_clip == 0.20
    assert hp.learning_rate == 3e-4
    assert hp.entropy_coefficient == 0.01
    assert hp.value_loss_coefficient == 0.5
    assert hp.ppo_epochs == 10
    assert hp.minibatch_trajectories == 256
    assert hp.lambda_corr == 0.5
    assert hp.lambda_turnover == 0.001
    assert hp.walk_forward_splits == 22
    assert hp.restarts_per_fold == 9


def test_policy_network_matches_disclosed_cnn_gru_head_widths() -> None:
    model = PolicyValueNet(feature_dim=16, num_assets=30)
    convs = [layer for layer in model.encoder.conv if isinstance(layer, torch.nn.Conv1d)]
    assert [layer.out_channels for layer in convs] == [32, 64, 64]
    assert [layer.kernel_size[0] for layer in convs] == [8, 4, 3]
    assert [layer.stride[0] for layer in convs] == [4, 2, 1]
    assert model.encoder.gru.hidden_size == 512
    assert model.policy_head[0].out_features == 512
    assert model.value_head[0].out_features == 512
    assert model.policy_head[-1].__class__ is torch.nn.Tanh


def test_paper_reward_state_reapplies_previous_weights_over_rolling_returns() -> None:
    returns = np.array(
        [
            [0.01, -0.01],
            [0.02, 0.00],
            [-0.01, 0.03],
            [0.04, -0.02],
            [0.01, 0.01],
            [0.00, -0.01],
        ],
        dtype=np.float32,
    )
    benchmark = np.array([0.005, 0.004, -0.002, 0.006, 0.001, -0.003], dtype=np.float32)
    env = PaperAlphaZeroBetaEnvironment(returns, benchmark, start=1, end=5, vol_window=60)
    env.t = 3
    env.previous_weights = np.array([0.5, -0.5], dtype=np.float32)

    sigma, corr = env.rolling_state()
    expected_portfolio = returns[1:3] @ env.previous_weights
    expected_benchmark = benchmark[1:3]
    assert np.isclose(sigma, expected_portfolio.std(ddof=0))
    assert np.isclose(corr, np.corrcoef(expected_portfolio, expected_benchmark)[0, 1])


def test_paper_walk_forward_contract_has_22_nonoverlapping_folds() -> None:
    dates = pd.bdate_range("2010-07-01", "2024-12-31")
    folds = paper_fold_contract(dates)
    assert len(folds) == 22
    assert folds[0].test_start >= "2014-01-01"
    assert folds[-1].test_end == "2024-12-31"
    for left, right in zip(folds[:-1], folds[1:], strict=True):
        assert left.test_indices[1] <= right.test_indices[0]


def test_paper_us_cost_schedule_matches_appendix_d4() -> None:
    us = PAPER_COSTS["us_large_cap"]
    assert us.top_decile_bps_per_side == 5.0
    assert us.other_bps_per_side == 15.0
    assert us.borrow_bps_per_year == 30.0


def test_exact_mode_fails_closed_without_licensed_input_manifest() -> None:
    readiness = exact_paper_readiness(None)
    assert readiness["ready"] is False
    assert readiness["blockers"]


def test_exact_mode_accepts_declared_paper_data_contract() -> None:
    readiness = exact_paper_readiness(
        {
            "source_start": "2004-01-01",
            "source_end": "2024-12-31",
            "feature_groups": list(REQUIRED_FEATURE_GROUPS),
            "index_membership": {index: "time-varying" for index in TIME_VARYING_INDICES},
            "providers": ["Bloomberg"],
        }
    )
    assert readiness["ready"] is True
    assert readiness["blockers"] == []
