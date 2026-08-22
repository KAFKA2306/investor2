from __future__ import annotations

import pytest

from scripts.alphazerobeta_train import next_period_slices


def test_next_period_slices_never_use_same_day_return() -> None:
    decision_slice, target_slice = next_period_slices(10, 15)
    assert decision_slice == slice(10, 14)
    assert target_slice == slice(11, 15)
    assert decision_slice.stop - decision_slice.start == target_slice.stop - target_slice.start


def test_next_period_slices_require_two_observations() -> None:
    with pytest.raises(ValueError, match="at least two observations"):
        next_period_slices(10, 11)
