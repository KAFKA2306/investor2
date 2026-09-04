from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.skfolio_tail_allocation_oos import portfolio_metrics, simulate_fold


def test_simulate_fold_applies_only_rebalance_cost() -> None:
    index = pd.date_range("2026-01-01", periods=2, freq="D")
    columns = [f"A{i:02d}" for i in range(20)]
    values = np.zeros((2, 20), dtype=float)
    values[0, 0] = 0.01
    values[1, 1] = 0.01
    returns = pd.DataFrame(values, index=index, columns=columns)
    target = np.full(20, 0.05)
    previous = target.copy()
    previous[0] = 0.06
    previous[1] = 0.04

    realized, end_weights, turnover, cost = simulate_fold(
        returns,
        target,
        previous,
    )

    assert np.isclose(turnover, 0.01)
    assert np.isclose(cost, 0.00002)
    assert np.isclose(realized.iloc[0], 0.00048)
    assert np.isclose(end_weights.sum(), 1.0)


def test_portfolio_metrics_reward_less_negative_tail() -> None:
    base = pd.Series([0.01, -0.03, 0.02, -0.01, 0.01] * 10, dtype=float)
    improved = pd.Series([0.01, -0.02, 0.02, -0.01, 0.01] * 10, dtype=float)

    base_metrics = portfolio_metrics(base)
    improved_metrics = portfolio_metrics(improved)

    assert improved_metrics["maximum_drawdown"] > base_metrics["maximum_drawdown"]
    assert improved_metrics["expected_shortfall_95_daily"] > base_metrics["expected_shortfall_95_daily"]
