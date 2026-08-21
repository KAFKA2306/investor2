from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal

import requests
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"
REQUEST_TIMEOUT_SECONDS = 30
PriceInterval = Literal["max", "all", "1m", "1w", "1d", "6h", "1h"]


class GammaMarket(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    question: str
    condition_id: str = Field(alias="conditionId")
    slug: str
    resolution_source: str | None = Field(default=None, alias="resolutionSource")
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    active: bool
    closed: bool
    enable_order_book: bool = Field(default=False, alias="enableOrderBook")
    accepting_orders: bool = Field(default=False, alias="acceptingOrders")
    outcomes: str | list[str] | None = None
    outcome_prices: str | list[str] | None = Field(default=None, alias="outcomePrices")
    clob_token_ids: str | list[str] | None = Field(default=None, alias="clobTokenIds")
    volume_num: float | None = Field(default=None, alias="volumeNum")
    liquidity_num: float | None = Field(default=None, alias="liquidityNum")
    volume_24h: float | None = Field(default=None, alias="volume24hr")


class GammaMarketPage(BaseModel):
    markets: list[GammaMarket]
    next_cursor: str | None = None


class MidpointResponse(BaseModel):
    mid_price: Decimal


class SpreadResponse(BaseModel):
    spread: Decimal


class PricePoint(BaseModel):
    t: int
    p: Decimal


class PriceHistoryResponse(BaseModel):
    history: list[PricePoint]


_GAMMA_MARKETS = TypeAdapter(list[GammaMarket])


def _decode_string_list(value: str | list[str] | None, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    decoded = json.loads(value)
    if not isinstance(decoded, list):
        raise ValueError(f"{field_name} must decode to a list")
    return [str(item) for item in decoded]


def normalize_market(market: GammaMarket) -> dict[str, Any]:
    outcomes = _decode_string_list(market.outcomes, field_name="outcomes")
    token_ids = _decode_string_list(market.clob_token_ids, field_name="clobTokenIds")
    outcome_prices = _decode_string_list(market.outcome_prices, field_name="outcomePrices")
    if token_ids and outcomes and len(token_ids) != len(outcomes):
        raise ValueError("Polymarket token/outcome cardinality mismatch")
    if outcome_prices and outcomes and len(outcome_prices) != len(outcomes):
        raise ValueError("Polymarket price/outcome cardinality mismatch")

    return {
        "market_id": market.id,
        "condition_id": market.condition_id,
        "slug": market.slug,
        "question": market.question,
        "resolution_source": market.resolution_source,
        "start_date": market.start_date,
        "end_date": market.end_date,
        "active": market.active,
        "closed": market.closed,
        "enable_order_book": market.enable_order_book,
        "accepting_orders": market.accepting_orders,
        "outcomes": outcomes,
        "token_ids": token_ids,
        "gamma_outcome_prices": [str(Decimal(value)) for value in outcome_prices],
        "volume": market.volume_num,
        "volume_24h": market.volume_24h,
        "liquidity": market.liquidity_num,
    }


def fetch_markets(
    *,
    limit: int = 100,
    offset: int = 0,
    closed: bool = False,
    order: str | None = None,
    ascending: bool | None = None,
    liquidity_num_min: float | None = None,
    volume_num_min: float | None = None,
    session: requests.Session | None = None,
) -> list[GammaMarket]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    params: dict[str, Any] = {"limit": limit, "offset": offset, "closed": closed}
    if order:
        params["order"] = order
    if ascending is not None:
        params["ascending"] = ascending
    if liquidity_num_min is not None:
        params["liquidity_num_min"] = liquidity_num_min
    if volume_num_min is not None:
        params["volume_num_min"] = volume_num_min
    client = session or requests.Session()
    response = client.get(f"{GAMMA_BASE_URL}/markets", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return _GAMMA_MARKETS.validate_python(response.json())


def fetch_markets_page(
    *,
    limit: int = 100,
    after_cursor: str | None = None,
    closed: bool = False,
    order: str | None = None,
    ascending: bool | None = None,
    liquidity_num_min: float | None = None,
    volume_num_min: float | None = None,
    session: requests.Session | None = None,
) -> GammaMarketPage:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    params: dict[str, Any] = {"limit": limit, "closed": closed}
    if after_cursor:
        params["after_cursor"] = after_cursor
    if order:
        params["order"] = order
    if ascending is not None:
        params["ascending"] = ascending
    if liquidity_num_min is not None:
        params["liquidity_num_min"] = liquidity_num_min
    if volume_num_min is not None:
        params["volume_num_min"] = volume_num_min
    client = session or requests.Session()
    response = client.get(f"{GAMMA_BASE_URL}/markets/keyset", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return GammaMarketPage.model_validate(response.json())


def fetch_midpoint(token_id: str, *, session: requests.Session | None = None) -> Decimal:
    client = session or requests.Session()
    response = client.get(
        f"{CLOB_BASE_URL}/midpoint",
        params={"token_id": token_id},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return MidpointResponse.model_validate(response.json()).mid_price


def fetch_spread(token_id: str, *, session: requests.Session | None = None) -> Decimal:
    client = session or requests.Session()
    response = client.get(
        f"{CLOB_BASE_URL}/spread",
        params={"token_id": token_id},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return SpreadResponse.model_validate(response.json()).spread


def fetch_price_history(
    token_id: str,
    *,
    interval: PriceInterval = "1d",
    fidelity: int = 60,
    start_ts: int | None = None,
    end_ts: int | None = None,
    session: requests.Session | None = None,
) -> list[PricePoint]:
    if fidelity <= 0:
        raise ValueError("fidelity must be positive")
    params: dict[str, Any] = {"market": token_id, "interval": interval, "fidelity": fidelity}
    if start_ts is not None:
        params["startTs"] = start_ts
    if end_ts is not None:
        params["endTs"] = end_ts
    client = session or requests.Session()
    response = client.get(f"{CLOB_BASE_URL}/prices-history", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return PriceHistoryResponse.model_validate(response.json()).history
