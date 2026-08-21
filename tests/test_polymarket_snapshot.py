from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from scripts import polymarket_snapshot
from src.io.providers.polymarket import GammaMarket, GammaMarketPage


def _market() -> GammaMarket:
    return GammaMarket.model_validate(
        {
            "id": "123",
            "question": "Will example happen?",
            "conditionId": "0xcondition",
            "slug": "will-example-happen",
            "resolutionSource": "https://example.com/resolution",
            "startDate": "2026-08-01T00:00:00Z",
            "endDate": "2026-12-31T00:00:00Z",
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "acceptingOrders": True,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.64", "0.36"]',
            "clobTokenIds": '["yes-token", "no-token"]',
            "volumeNum": 1000.0,
            "volume24hr": 125.0,
            "liquidityNum": 2500.0,
        }
    )


def test_collect_snapshot_preserves_point_in_time_market_and_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        polymarket_snapshot,
        "fetch_markets_page",
        lambda **_: GammaMarketPage(markets=[_market()], next_cursor=None),
    )
    monkeypatch.setattr(
        polymarket_snapshot,
        "fetch_midpoint",
        lambda token_id, **_: Decimal("0.64") if token_id == "yes-token" else Decimal("0.36"),
    )
    monkeypatch.setattr(polymarket_snapshot, "fetch_spread", lambda _token_id, **_: Decimal("0.02"))

    snapshot = polymarket_snapshot.collect_snapshot(max_markets=1, min_liquidity=1000.0)

    assert snapshot["schema_version"] == "investor2.polymarket-market-snapshot.v1"
    assert snapshot["source"] == "polymarket_market_data"
    assert snapshot["provenance"]["storage_visibility"] == "private-only"
    assert snapshot["records"][0]["condition_id"] == "0xcondition"
    assert snapshot["records"][0]["quotes"][0] == {
        "outcome": "Yes",
        "token_id": "yes-token",
        "midpoint": "0.64",
        "spread": "0.02",
    }


def test_collect_snapshot_skips_markets_without_live_order_book(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled = _market().model_copy(update={"accepting_orders": False})
    monkeypatch.setattr(
        polymarket_snapshot,
        "fetch_markets_page",
        lambda **_: GammaMarketPage(markets=[disabled, _market()], next_cursor=None),
    )
    monkeypatch.setattr(polymarket_snapshot, "fetch_midpoint", lambda _token_id, **_: Decimal("0.5"))
    monkeypatch.setattr(polymarket_snapshot, "fetch_spread", lambda _token_id, **_: Decimal("0.02"))

    snapshot = polymarket_snapshot.collect_snapshot(max_markets=1, min_liquidity=1000.0)

    assert len(snapshot["records"]) == 1
    assert snapshot["records"][0]["accepting_orders"] is True


def test_write_snapshot_is_deterministic_for_same_payload(tmp_path: Path) -> None:
    snapshot: dict[str, Any] = {
        "schema_version": "investor2.polymarket-market-snapshot.v1",
        "observed_at": "2026-08-21T12:00:00Z",
        "source": "polymarket_market_data",
        "provenance": {},
        "records": [],
    }
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    digest_a = polymarket_snapshot.write_snapshot(snapshot, first)
    digest_b = polymarket_snapshot.write_snapshot(snapshot, second)

    assert digest_a == digest_b
    assert json.loads(first.read_text(encoding="utf-8")) == snapshot
