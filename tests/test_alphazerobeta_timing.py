from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.alphazerobeta_empirical_run import MARKET_DATA_PROVIDER
from scripts.alphazerobeta_train import next_period_bounds

ROOT = Path(__file__).resolve().parents[1]


def test_next_period_bounds_never_use_same_day_return() -> None:
    decision_start, decision_end, target_start, target_end = next_period_bounds(10, 15)
    assert (decision_start, decision_end) == (10, 14)
    assert (target_start, target_end) == (11, 15)
    assert decision_end - decision_start == target_end - target_start


def test_next_period_bounds_require_two_observations() -> None:
    with pytest.raises(ValueError, match="at least two observations"):
        next_period_bounds(10, 11)


def test_empirical_market_provider_is_pinned_to_frozen_snapshot() -> None:
    script = (ROOT / "scripts" / "alphazerobeta_empirical_run.py").read_text(encoding="utf-8")
    assert MARKET_DATA_PROVIDER == "yahoo_chart"
    assert "stooq_daily" not in script
    assert "for loader in" not in script

    manifest = json.loads(
        (ROOT / "docs" / "research" / "results" / "alphazerobeta_2024" / "source_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert {record["provider"] for record in manifest["records"]} == {MARKET_DATA_PROVIDER}