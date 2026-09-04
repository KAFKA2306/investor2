import numpy as np
import pandas as pd

from scripts.skfolio_allocation_oos import (
    min_variance_weights,
    one_way_turnover,
    portfolio_metrics,
)


def test_min_variance_weights_are_long_only_fully_invested_and_capped() -> None:
    covariance = np.diag([0.01, 0.02, 0.03, 0.04])
    weights = min_variance_weights(covariance, max_weight=0.4)

    assert np.isclose(weights.sum(), 1.0)
    assert np.all(weights >= 0)
    assert np.all(weights <= 0.4 + 1e-8)
    assert weights[0] >= weights[1] >= weights[2] >= weights[3]


def test_one_way_turnover_uses_half_l1_distance() -> None:
    previous = np.array([0.5, 0.5, 0.0])
    current = np.array([0.25, 0.5, 0.25])
    assert np.isclose(one_way_turnover(previous, current), 0.25)


def test_portfolio_metrics_report_drawdown_and_expected_shortfall() -> None:
    returns = pd.Series([0.02, -0.10, 0.03, -0.02, 0.01], dtype=float)
    metrics = portfolio_metrics(returns)

    assert metrics["maximum_drawdown"] < 0
    assert metrics["expected_shortfall_95_daily"] == -0.10
    assert metrics["worst_day"] == -0.10
    assert np.isfinite(metrics["annualized_volatility"])
    assert np.isfinite(metrics["cagr"])
