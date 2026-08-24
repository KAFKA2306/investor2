from __future__ import annotations

import numpy as np

from src.research.alphazerobeta import project_market_neutral
from src.research.tradability import mask_action_for_tradability, mask_research_array, ranked_long_short_weights


def test_mask_action_forces_inactive_projected_weight_to_zero() -> None:
    action = np.asarray([0.8, -0.4, 0.2, 0.6], dtype=np.float64)
    tradable = np.asarray([True, True, False, True])
    masked = mask_action_for_tradability(action, tradable)
    projected = project_market_neutral(masked)
    assert projected[2] == 0.0
    np.testing.assert_allclose(projected.sum(), 0.0, atol=1e-7)


def test_mask_action_does_not_change_fully_tradable_action() -> None:
    action = np.asarray([0.2, -0.1, 0.7], dtype=np.float64)
    masked = mask_action_for_tradability(action, np.ones(3, dtype=bool))
    np.testing.assert_allclose(masked, action)


def test_research_mask_excludes_inactive_observation() -> None:
    values = np.arange(6, dtype=np.float64).reshape(2, 3)
    tradable = np.asarray([[True, False, True], [True, True, False]])
    masked = mask_research_array(values, tradable)
    assert np.isnan(masked[0, 1])
    assert np.isnan(masked[1, 2])
    assert masked[0, 0] == 0.0


def test_ranked_weights_never_allocate_to_inactive_assets() -> None:
    scores = np.asarray(
        [
            [-10.0, -5.0, 1.0, 3.0, 8.0, 9.0],
            [-9.0, -4.0, 2.0, 4.0, 7.0, 10.0],
        ]
    )
    tradable = np.asarray(
        [
            [True, True, True, True, False, True],
            [True, False, True, True, True, True],
        ]
    )
    weights = ranked_long_short_weights(
        scores,
        tradable,
        n_long=2,
        n_short=2,
        beta=0.8,
        gamma=0.0,
    )
    assert weights[0, 4] == 0.0
    assert weights[1, 1] == 0.0
    np.testing.assert_allclose(weights.sum(axis=1), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.abs(weights).sum(axis=1), 0.8, atol=1e-12)
