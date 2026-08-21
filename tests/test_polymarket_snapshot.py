from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from scripts import polymarket_snapshot
from src.io.providers.polymarket import GammaMarket


def _market(*, market_id: str = "123") -> GammaMarket:
    return GammaMarket.model_validate(
        {
            "id": market_id,
            "question": "Will example happen?",
            "conditionId": f"0xcondition-{market_id}",
            "slug": f"will-example-happen-{market_id}",
            "resolutionSource": "https://example.com/resolution",
            "startDate": "2026-08-01T00:00:00Z",
            "endDate": "2026-12-31T00:00:00Z",
            "active": True,
            "closed": False,
            "enableOrderBook": True,
            "acceptingOrders": True,
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.64", "0.36"]',
            "clobTokenIds": f'["yes-token-{market_id}", "no-token-{market_id}"]',
            "volumeNum": 1000.0,
            "volume24hr": 125.0,
            "liquidityNum": 2500.0,
        }
    )


def test_collect_snapshot_preserves_point_in_time_market_and_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(polymarket_snapshot, "fetch_markets", lambda **_: [_market()])
    monkeypatch.setattr(
        polymarket_snapshot,
        "fetch_midpoint_if_available",
        lambda token_id, **_: Decimal("0.64") if token_id.startswith("yes-token") else Decimal("0.36"),
    )
    monkeypatch.setattr(polymarket_snapshot, "fetch_spread_if_available", lambda _token_id, **_: Decimal("0.02"))

    snapshot = polymarket_snapshot.collect_snapshot(max_markets=1, min_liquidity=1000.0)

    assert snapshot["schema_version"] == "investor2.polymarket-market-snapshot.v1"
    assert snapshot["source"] == "polymarket_market_data"
    assert snapshot["provenance"]["storage_visibility"] == "private-only"
    assert snapshot["records"][0]["condition_id"] == "0xcondition-123"
    assert snapshot["records"][0]["quotes"][0] == {
        "outcome": "Yes",
        "token_id": "yes-token-123",
        "midpoint": "0.64",
        "spread": "0.02",
    }


def test_discover_live_markets_skips_markets_without_live_order_book(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled = _market().model_copy(update={"accepting_orders": False})
    monkeypatch.setattr(polymarket_snapshot, "fetch_markets", lambda **_: [disabled, _market()])

    markets = polymarket_snapshot.discover_live_markets(
        min_liquidity=1000.0,
        session=polymarket_snapshot.requests.Session(),
    )

    assert len(markets) == 1
    assert markets[0].accepting_orders is True


def test_collect_snapshot_skips_market_without_complete_clob_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(polymarket_snapshot, "fetch_markets", lambda **_: [_market(market_id="sparse"), _market(market_id="quoted")])
    monkeypatch.setattr(
        polymarket_snapshot,
        "fetch_midpoint_if_available",
        lambda token_id, **_: None if token_id == "yes-token-sparse" else Decimal("0.5"),
    )
    monkeypatch.setattr(polymarket_snapshot, "fetch_spread_if_available", lambda _token_id, **_: Decimal("0.02"))

    snapshot = polymarket_snapshot.collect_snapshot(max_markets=1, min_liquidity=1000.0)

    assert snapshot["records"][0]["market_id"] == "quoted"


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
