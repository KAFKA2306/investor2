from __future__ import annotations

from decimal import Decimal

import pytest

from src.io.providers.polymarket import GammaMarket, MidpointResponse, PriceHistoryResponse, normalize_market


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
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.64", "0.36"]',
            "clobTokenIds": '["yes-token", "no-token"]',
            "volumeNum": 1000.0,
            "volume24hr": 125.0,
            "liquidityNum": 250.0,
        }
    )


def test_normalize_gamma_market_keeps_identity_and_token_mapping() -> None:
    normalized = normalize_market(_market())

    assert normalized["market_id"] == "123"
    assert normalized["condition_id"] == "0xcondition"
    assert normalized["outcomes"] == ["Yes", "No"]
    assert normalized["token_ids"] == ["yes-token", "no-token"]
    assert normalized["gamma_outcome_prices"] == ["0.64", "0.36"]
    assert normalized["liquidity"] == 250.0


def test_normalize_market_rejects_token_outcome_mismatch() -> None:
    market = _market().model_copy(update={"clob_token_ids": '["yes-token"]'})

    with pytest.raises(ValueError, match="cardinality mismatch"):
        normalize_market(market)


def test_clob_responses_parse_prices_as_decimal() -> None:
    midpoint = MidpointResponse.model_validate({"mid_price": "0.45"})
    history = PriceHistoryResponse.model_validate({"history": [{"t": 1_787_000_000, "p": 0.45}]})

    assert midpoint.mid_price == Decimal("0.45")
    assert history.history[0].p == Decimal("0.45")
