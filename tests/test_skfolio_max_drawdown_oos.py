from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.skfolio_max_drawdown_oos import portfolio_metrics, simulate_fold


def test_simulate_fold_charges_initial_rebalance_cost() -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D")
    returns = pd.DataFrame(
        [[0.01, 0.00], [0.00, 0.01]],
        index=index,
        columns=["A", "B"],
    )
    target = np.array([0.5, 0.5])
    previous = np.array([0.6, 0.4])

    realized, end_weights, turnover, cost = simulate_fold(
        returns,
        target,
        previous,
    )

    assert np.isclose(turnover, 0.1)
    assert np.isclose(cost, 0.0002)
    assert np.isclose(realized.iloc[0], 0.0048)
    assert np.isclose(end_weights.sum(), 1.0)


def test_portfolio_metrics_reward_smaller_drawdown_and_tail_loss() -> None:
    base = pd.Series([0.01, -0.03, 0.02, -0.01, 0.01] * 10, dtype=float)
    improved = pd.Series([0.01, -0.02, 0.02, -0.01, 0.01] * 10, dtype=float)

    base_metrics = portfolio_metrics(base)
    improved_metrics = portfolio_metrics(improved)

    assert improved_metrics["maximum_drawdown"] > base_metrics["maximum_drawdown"]
    assert (
        improved_metrics["expected_shortfall_95_daily"]
        > base_metrics["expected_shortfall_95_daily"]
    )
