#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "investor2.arxiv-data-requirements-manifest.v1"
UNKNOWN = "NOT_SPECIFIED"

LIM_TICKERS = {
    "commodities": "BC BG BO CC CL CT C DA FC GC GI HG HO JO KC KW LB LC LH MW NG NR O PA PL RB SB SI SM S W ZA ZB ZC ZF ZG ZH ZI ZK ZL ZM ZN ZO ZP ZR ZS ZT ZU ZW ZZ".split(),
    "equities": "AX CA EN ER ES HS LX MD SC SP XU XX YM".split(),
    "fixed_income": "AP DT FA FB GS TA TD TU TY UA UB US".split(),
    "fx": "AD AN BN CB CN DX FN FX JN MP NK SF SN".split(),
}
ZHANG_TICKERS = {
    "commodities": "CC DA GI JO KC KW LB NR SB ZA ZC ZF ZG ZH ZI ZK ZL ZN ZO ZP ZR ZT ZU ZW ZZ".split(),
    "equity_indices": "CA EN ER ES LX MD SC SP XU XX YM".split(),
    "fixed_income": "DT FB TY UB US".split(),
    "fx": "AN BN CN DX FN JN MP NK SN".split(),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(url: str, pages: str, section: str, claim: str) -> dict[str, str]:
    return {"url": url, "pages": pages, "section": section, "claim": claim}


def base_contract(pin: dict[str, Any]) -> dict[str, Any]:
    return {
        "arxiv_id": pin["arxiv_id"],
        "title": pin["title"],
        "selected_version": pin["selected_version"],
        "selected_version_url": pin["selected_version_url"],
        "extraction_status": "FAIL_CLOSED_NOT_EXTRACTED",
        "instrument_universe": UNKNOWN,
        "market_venue": UNKNOWN,
        "asset_classes": [],
        "raw_observations": [],
        "derived_features": [],
        "observation_frequency": UNKNOWN,
        "source_named_by_paper": UNKNOWN,
        "access_status": "AMBIGUOUS",
        "transformation_prerequisites": [],
        "transaction_cost_inputs": [],
        "benchmark_inputs": [],
        "unresolved_blockers": ["FULL_TEXT_REQUIREMENTS_NOT_VERIFIED"],
        "evidence_locations": [
            {
                "url": pin["selected_version_url"],
                "pages": UNKNOWN,
                "section": UNKNOWN,
                "claim": "Exact pinned paper version. Data-requirement fields remain fail-closed until full-text evidence is extracted."
            }
        ],
    }


def lim_contract(pin: dict[str, Any]) -> dict[str, Any]:
    c = base_contract(pin)
    url = "https://arxiv.org/pdf/1904.04912v2"
    c.update({
        "extraction_status": "VERIFIED_FULL_TEXT",
        "instrument_universe": {
            "description": "88 ratio-adjusted continuous futures contracts extracted from the full 98-contract Pinnacle CLC universe by retaining contracts with <10% missing data",
            "count": 88,
            "tickers_by_asset_class": LIM_TICKERS,
            "sample_period": {"start_year": 1990, "end_year": 2015},
        },
        "market_venue": UNKNOWN,
        "asset_classes": ["commodities", "equities", "fixed_income", "fx"],
        "raw_observations": [
            {
                "field": "continuous futures prices",
                "required": True,
                "exact_vendor_price_field": UNKNOWN,
                "note": "The pinned paper says prices from the ratio-adjusted CLC contracts; it does not identify Open/High/Low/Settle as the exact modeled price field."
            }
        ],
        "derived_features": [
            "returns over 1 day, 1 month, 3 months, 6 months and 1 year",
            "returns normalized by daily volatility at the corresponding horizon",
            "MACD indicators with short scales 8/16/32 and long scales 24/48/96",
            "daily volatility",
            "signal/position weights for turnover and strategy-return calculations"
        ],
        "observation_frequency": "DAILY",
        "source_named_by_paper": {
            "vendor": "Pinnacle Data Corp",
            "dataset": "CLC Database",
            "linking": "ratio-adjusted continuous futures",
            "paper_reference_url": "https://pinnacledata2.com/clc.html"
        },
        "access_status": "PROPRIETARY",
        "current_vendor_access": {
            "status": "COMMERCIAL_PURCHASE_REQUIRED",
            "verified_url": "https://pinnacledata2.com/clc.html",
            "current_price_usd": 99,
            "warning": "Current commercial availability does not prove byte-identical 2019 paper-vintage data or revision history."
        },
        "transformation_prerequisites": [
            "ratio-adjusted contract linking as used by the paper",
            "retain 88 contracts selected by <10% missing-data rule from the 98-contract CLC universe",
            "winsorize using EWM average and EWM standard deviation with 252-day half-life, capped/floored at 5 standard deviations",
            "volatility normalization for return features",
            "63-step trajectories for LSTM training"
        ],
        "transaction_cost_inputs": [
            "daily turnover from changes in volatility-scaled positions",
            "constant cost c applied to traded position change",
            "cost sensitivity including 2-3 bps and higher-cost experiments including c=10 bps"
        ],
        "benchmark_inputs": [
            "Long Only with volatility scaling",
            "Sgn(Returns) time-series momentum using past-year return sign",
            "MACD baseline using the paper's specified short/long timescales"
        ],
        "unresolved_blockers": [
            "EXACT_PINNACLE_CLC_DATA_NOT_PRESENT_IN_REPOSITORY",
            "PAPER_VINTAGE_DATA_REVISION_NOT_PROVEN",
            "EXACT_VENDOR_PRICE_FIELD_NOT_SPECIFIED_BY_PAPER"
        ],
        "evidence_locations": [
            evidence(url, "7", "V.A-V.B", "88 ratio-adjusted Pinnacle CLC futures; prices 1990-2015; five-year recalibration and daily model features."),
            evidence(url, "12", "VI", "Daily turnover and cost-adjusted return formulation; cost sensitivity in basis points."),
            evidence(url, "16", "Appendix A", "98-to-88 missing-data filter, exact ticker universe, and 252-day EWM winsorization."),
            evidence(url, "17", "Appendix B", "50-iteration random search, five-year recalibration and 63-step LSTM trajectories.")
        ]
    })
    assert sum(len(v) for v in LIM_TICKERS.values()) == 88
    return c


def zhang_contract(pin: dict[str, Any]) -> dict[str, Any]:
    c = base_contract(pin)
    url = "https://arxiv.org/pdf/1911.10107v1"
    c.update({
        "extraction_status": "VERIFIED_FULL_TEXT",
        "instrument_universe": {
            "description": "50 ratio-adjusted continuous futures contracts from the Pinnacle Data Corp CLC Database",
            "count": 50,
            "tickers_by_asset_class": ZHANG_TICKERS,
            "sample_period": {"start_year": 2005, "end_year": 2019},
            "reported_test_period": {"start_year": 2011, "end_year": 2019}
        },
        "market_venue": UNKNOWN,
        "asset_classes": ["commodities", "equity_indices", "fixed_income", "fx"],
        "raw_observations": [
            {
                "field": "continuous futures prices",
                "required": True,
                "exact_vendor_price_field": UNKNOWN,
                "note": "The pinned paper identifies ratio-adjusted CLC futures data but does not identify Open/High/Low/Settle as the exact modeled price field."
            }
        ],
        "derived_features": [
            "daily returns",
            "volatility-normalized annual return using a 60-day exponentially weighted moving standard deviation",
            "MACD indicators with short scales 8/16/32 and long scales 24/48/96",
            "63-day rolling price standard deviation inside the MACD construction",
            "60-day ex-ante volatility estimate for volatility-scaled reward/positions",
            "RL state representations and trade-position actions"
        ],
        "observation_frequency": "DAILY",
        "source_named_by_paper": {
            "vendor": "Pinnacle Data Corp",
            "dataset": "CLC Database",
            "linking": "ratio-adjusted continuous futures",
            "paper_reference_url": "https://pinnacledata2.com/clc.html"
        },
        "access_status": "PROPRIETARY",
        "current_vendor_access": {
            "status": "COMMERCIAL_PURCHASE_REQUIRED",
            "verified_url": "https://pinnacledata2.com/clc.html",
            "current_price_usd": 99,
            "warning": "Current commercial availability does not prove byte-identical 2019 paper-vintage data or revision history."
        },
        "transformation_prerequisites": [
            "ratio-adjusted contract linking as used by the paper",
            "partition contracts into the four paper asset classes",
            "compute 60-day volatility estimates and volatility scaling",
            "compute Sign(Returns) and MACD baseline indicators"
        ],
        "transaction_cost_inputs": [
            "bp cost rate applied in the reward/return formulation",
            "paper hyperparameter bp=0.0020 for DQN, PG and A2C",
            "net-of-transaction-cost evaluation from 2011-2019"
        ],
        "benchmark_inputs": [
            "Long Only",
            "Sign(R) using the past 252-day return",
            "MACD baseline using short scales 8/16/32 and long scales 24/48/96"
        ],
        "unresolved_blockers": [
            "EXACT_PINNACLE_CLC_DATA_NOT_PRESENT_IN_REPOSITORY",
            "PAPER_VINTAGE_DATA_REVISION_NOT_PROVEN",
            "EXACT_VENDOR_PRICE_FIELD_NOT_SPECIFIED_BY_PAPER"
        ],
        "evidence_locations": [
            evidence(url, "6", "4.1-4.3", "50 ratio-adjusted Pinnacle CLC futures, 2005-2019 sample, 2011-2019 testing, five-year retraining, baselines and RL action spaces."),
            evidence(url, "4", "3", "Daily technical inputs, 60-day volatility scaling and MACD construction."),
            evidence(url, "6-7", "Table 1 / 4.4", "RL hyperparameters including bp=0.0020 and net-of-cost evaluation."),
            evidence(url, "14-15", "Appendix A", "Exact 50-contract ticker universe by asset class.")
        ]
    })
    assert sum(len(v) for v in ZHANG_TICKERS.values()) == 50
    return c


def validate(records: list[dict[str, Any]], pins: list[dict[str, Any]]) -> None:
    if len(records) != len(pins):
        raise AssertionError((len(records), len(pins)))
    if len({r["arxiv_id"] for r in records}) != len(records):
        raise AssertionError("duplicate records")
    for record, pin in zip(records, pins):
        assert record["arxiv_id"] == pin["arxiv_id"]
        assert record["selected_version"] == pin["selected_version"]
        assert record["selected_version_url"] == pin["selected_version_url"]
        assert record["access_status"] in {"PUBLIC", "PROPRIETARY", "UNAVAILABLE", "AMBIGUOUS"}
        if record["extraction_status"] != "VERIFIED_FULL_TEXT":
            assert record["source_named_by_paper"] == UNKNOWN
            assert record["raw_observations"] == []
            assert record["derived_features"] == []
            assert record["benchmark_inputs"] == []
            assert record["transaction_cost_inputs"] == []
            assert record["access_status"] == "AMBIGUOUS"
            assert "FULL_TEXT_REQUIREMENTS_NOT_VERIFIED" in record["unresolved_blockers"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pins_path = args.pins if args.pins.is_absolute() else ROOT / args.pins
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    pin_manifest = load(pins_path)
    pins = pin_manifest["pins"]
    records = []
    for pin in pins:
        if pin["availability_status"] != "VERIFIED":
            raise SystemExit(f"unverified version pin: {pin['arxiv_id']}")
        if pin["arxiv_id"] == "1904.04912":
            record = lim_contract(pin)
        elif pin["arxiv_id"] == "1911.10107":
            record = zhang_contract(pin)
        else:
            record = base_contract(pin)
        records.append(record)
    validate(records, pins)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_version_pins_sha256": sha256(pins_path),
        "record_count": len(records),
        "summary": {
            "verified_full_text": sum(r["extraction_status"] == "VERIFIED_FULL_TEXT" for r in records),
            "fail_closed_not_extracted": sum(r["extraction_status"] == "FAIL_CLOSED_NOT_EXTRACTED" for r in records),
            "access_status_counts": {s: sum(r["access_status"] == s for r in records) for s in ("PUBLIC", "PROPRIETARY", "UNAVAILABLE", "AMBIGUOUS")}
        },
        "fail_closed_policy": "Fields absent from exact pinned-paper evidence are never inferred from current substitute datasets, vendor product pages, arXiv category labels, or selector keyword cues.",
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
