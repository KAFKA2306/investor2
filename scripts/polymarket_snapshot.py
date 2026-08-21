#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io.providers.polymarket import (  # noqa: E402
    CLOB_BASE_URL,
    GAMMA_BASE_URL,
    GammaMarket,
    fetch_markets,
    fetch_midpoint_if_available,
    fetch_spread_if_available,
    normalize_market,
)

SCHEMA_VERSION = "investor2.polymarket-market-snapshot.v1"
HEALTH_SCHEMA_VERSION = "investor2.polymarket-source-health.v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_quote(midpoint: Decimal, spread: Decimal) -> None:
    if not Decimal("0") <= midpoint <= Decimal("1"):
        raise ValueError("Polymarket midpoint is outside [0, 1]")
    if not Decimal("0") <= spread <= Decimal("1"):
        raise ValueError("Polymarket spread is outside [0, 1]")


def discover_live_markets(*, min_liquidity: float, session: requests.Session) -> list[GammaMarket]:
    if min_liquidity < 0:
        raise ValueError("min_liquidity must be non-negative")
    markets = fetch_markets(limit=100, offset=0, session=session)
    live = [
        market
        for market in markets
        if market.active is True
        and market.closed is False
        and market.enable_order_book is True
        and market.accepting_orders is True
        and market.id
        and market.condition_id
        and market.slug
        and market.question
        and market.clob_token_ids
        and (market.liquidity_num or 0) >= min_liquidity
    ]
    live.sort(key=lambda market: market.liquidity_num or 0, reverse=True)
    if not live:
        raise AssertionError("Polymarket returned no active order-book markets matching the collection scope")
    return live


def _quote_market(market: GammaMarket, *, session: requests.Session) -> dict[str, Any] | None:
    normalized = normalize_market(market)
    outcomes = normalized["outcomes"]
    token_ids = normalized["token_ids"]
    if not outcomes or not token_ids:
        return None
    if len(outcomes) != len(token_ids):
        raise ValueError("Polymarket normalized outcome/token mapping is invalid")

    quotes: list[dict[str, str]] = []
    for outcome, token_id in zip(outcomes, token_ids, strict=True):
        midpoint = fetch_midpoint_if_available(token_id, session=session)
        if midpoint is None:
            return None
        spread = fetch_spread_if_available(token_id, session=session)
        if spread is None:
            return None
        _validate_quote(midpoint, spread)
        quotes.append(
            {
                "outcome": outcome,
                "token_id": token_id,
                "midpoint": str(midpoint),
                "spread": str(spread),
            }
        )
    return {**normalized, "quotes": quotes}


def collect_snapshot(*, max_markets: int, min_liquidity: float) -> dict[str, Any]:
    if max_markets <= 0:
        raise ValueError("max_markets must be positive")

    session = requests.Session()
    markets = discover_live_markets(min_liquidity=min_liquidity, session=session)

    records: list[dict[str, Any]] = []
    for market in markets:
        quoted = _quote_market(market, session=session)
        if quoted is None:
            continue
        records.append(quoted)
        if len(records) >= max_markets:
            break

    if not records:
        raise AssertionError("Polymarket live markets did not expose a complete quoted order book")

    observed_at = utc_now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "source": "polymarket_market_data",
        "provenance": {
            "endpoints": [
                f"{GAMMA_BASE_URL}/markets",
                f"{CLOB_BASE_URL}/midpoint",
                f"{CLOB_BASE_URL}/spread",
            ],
            "query_or_scope": {
                "active": True,
                "closed": False,
                "enable_order_book": True,
                "accepting_orders": True,
                "complete_clob_quote": True,
                "client_order": "liquidity_num desc",
                "liquidity_num_min": min_liquidity,
                "max_markets": max_markets,
            },
            "retrieved_at": observed_at,
            "source_urls": [
                "https://docs.polymarket.com/api-reference/markets/list-markets",
                "https://docs.polymarket.com/api-reference/data/get-midpoint-price",
                "https://docs.polymarket.com/api-reference/market-data/get-spread",
            ],
            "storage_visibility": "private-only",
        },
        "records": records,
    }


def write_snapshot(snapshot: dict[str, Any], output: Path) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect read-only Polymarket market observations.")
    parser.add_argument(
        "--health-gamma",
        action="store_true",
        help="Validate live Gamma discovery without persisting data.",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Validate live Gamma/CLOB access without persisting data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Private output path for a normalized snapshot.",
    )
    parser.add_argument("--max-markets", type=int, default=20)
    parser.add_argument("--min-liquidity", type=float, default=1000.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    health_mode = args.health_gamma or args.health_only
    if not health_mode and args.output is None:
        raise SystemExit("--output is required unless a health mode is used")

    if args.health_gamma:
        discover_live_markets(min_liquidity=args.min_liquidity, session=requests.Session())
        print(json.dumps({"schema_version": HEALTH_SCHEMA_VERSION, "stage": "gamma", "status": "PASS"}, sort_keys=True))
        return

    snapshot = collect_snapshot(
        max_markets=1 if args.health_only else args.max_markets,
        min_liquidity=args.min_liquidity,
    )
    if args.health_only:
        print(json.dumps({"schema_version": HEALTH_SCHEMA_VERSION, "stage": "full", "status": "PASS"}, sort_keys=True))
        return

    assert args.output is not None
    digest = write_snapshot(snapshot, args.output)
    print(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "PASS",
                "artifact_sha256": digest,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
