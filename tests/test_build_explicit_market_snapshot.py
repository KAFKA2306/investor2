from __future__ import annotations

import pytest

from scripts.build_explicit_market_snapshot import explicit_universe, parse_tickers


def test_parse_tickers_normalizes_and_rejects_duplicates() -> None:
    assert parse_tickers("spy, qqq, MU") == ["SPY", "QQQ", "MU"]
    with pytest.raises(ValueError, match="duplicate"):
        parse_tickers("SPY,spy")


def test_explicit_universe_preserves_requested_order() -> None:
    frame = explicit_universe(region="US", tickers=["SPY", "MU", "COST"])
    assert frame["Ticker"].tolist() == ["SPY", "MU", "COST"]
    assert frame["Region"].tolist() == ["us", "us", "us"]
    assert frame["UniverseSource"].tolist() == ["explicit", "explicit", "explicit"]
