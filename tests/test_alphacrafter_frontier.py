from __future__ import annotations

import numpy as np

from src.research.alphacrafter_frontier import (
    evaluate_weights,
    factor_metrics,
    make_weight_path,
    orient_factor_on_train,
    paper_strategy_gate,
    screen_factors,
)


def synthetic_signal(seed: int = 2306) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    factor = rng.normal(size=(420, 64))
    returns = rng.normal(scale=0.01, size=(420, 64))
    returns[1:] += 0.003 * factor[:-1]
    return factor, returns


def test_factor_gate_accepts_forward_signal() -> None:
    factor, returns = synthetic_signal()
    oriented, direction = orient_factor_on_train(factor, returns, 0, 250)
    assert direction == 1
    one_day = factor_metrics(oriented, returns, 250, 350, horizon=1)
    five_day = factor_metrics(oriented, returns, 250, 350, horizon=5)
    assert one_day.passed
    assert five_day.passed
    assert one_day.coverage == 1.0
    assert one_day.turnover < 0.4


def test_screener_and_trader_are_deterministic() -> None:
    factor, returns = synthetic_signal()
    oriented, _ = orient_factor_on_train(factor, returns, 0, 250)
    factors = {"momentum_20": oriented}
    first = screen_factors(factors, returns, 250, 350)
    second = screen_factors(factors, returns, 250, 350)
    assert first == second
    assert len(first) == 1
    weights = make_weight_path(oriented, n_long=8, n_short=8, beta=0.8, gamma=0.0)
    np.testing.assert_allclose(weights.sum(axis=1), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.abs(weights).sum(axis=1), 0.8, atol=1e-12)


def test_after_cost_evaluation_charges_turnover_and_borrow() -> None:
    factor, returns = synthetic_signal()
    weights = make_weight_path(factor, n_long=8, n_short=8, beta=0.8, gamma=0.0)
    benchmark = returns.mean(axis=1)
    free, _ = evaluate_weights(
        weights,
        returns,
        benchmark,
        300,
        390,
        transaction_cost_bps_per_side=0.0,
        borrow_fee_bps_per_year=0.0,
    )
    costly, _ = evaluate_weights(
        weights,
        returns,
        benchmark,
        300,
        390,
        transaction_cost_bps_per_side=15.0,
        borrow_fee_bps_per_year=30.0,
    )
    assert costly.cumulative_return < free.cumulative_return
    assert costly.mean_turnover > 0
    assert costly.mean_gross_exposure > 0


def test_evaluation_respects_exclusive_fold_end() -> None:
    weights = np.ones((8, 2), dtype=np.float64) * 0.25
    returns = np.zeros((8, 2), dtype=np.float64)
    benchmark = np.zeros(8, dtype=np.float64)
    returns[5] = 100.0
    metrics, realized = evaluate_weights(
        weights,
        returns,
        benchmark,
        1,
        5,
        transaction_cost_bps_per_side=0.0,
        borrow_fee_bps_per_year=0.0,
    )
    assert metrics.observations == 3
    assert realized.shape == (3,)
    np.testing.assert_allclose(realized, 0.0)


def test_paper_strategy_gate_is_strict() -> None:
    factor, returns = synthetic_signal()
    weights = make_weight_path(factor, n_long=8, n_short=8, beta=0.8, gamma=0.0)
    benchmark = returns.mean(axis=1)
    metrics, _ = evaluate_weights(
        weights,
        returns,
        benchmark,
        300,
        390,
        transaction_cost_bps_per_side=0.0,
        borrow_fee_bps_per_year=0.0,
    )
    assert isinstance(paper_strategy_gate(metrics), bool)
