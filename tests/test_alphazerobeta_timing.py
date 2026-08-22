from __future__ import annotations

import pytest

from scripts.alphazerobeta_train import next_period_bounds


def test_next_period_bounds_never_use_same_day_return() -> None:
    decision_start, decision_end, target_start, target_end = next_period_bounds(10, 15)
    assert (decision_start, decision_end) == (10, 14)
    assert (target_start, target_end) == (11, 15)
    assert decision_end - decision_start == target_end - target_start


def test_next_period_bounds_require_two_observations() -> None:
    with pytest.raises(ValueError, match="at least two observations"):
        next_period_bounds(10, 11)
