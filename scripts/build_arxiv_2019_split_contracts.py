#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "investor2.arxiv-qfin-2019-split-manifest.v1"
NS = "NOT_SPECIFIED"
WINDOW_FIELDS = ("sample_window", "train_window", "validation_window", "test_window")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unknown_window() -> dict[str, str]:
    return {"start": NS, "end": NS, "precision": NS}


def year_window(start: int, end: int) -> dict[str, Any]:
    return {"start": start, "end": end, "precision": "YEAR"}


def base(pin: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "sample_window", "train_window", "validation_window", "test_window",
        "split_semantics", "feature_lookbacks", "warmup_policy", "retraining_cadence",
        "overlap_rule", "embargo_rule", "model_selection_rule", "benchmark_evaluation_window",
        "transaction_cost_evaluation_window", "sample_selection_filters"
    ]
    return {
        "arxiv_id": pin["arxiv_id"],
        "title": pin["title"],
        "selected_version": pin["selected_version"],
        "selected_version_url": pin["selected_version_url"],
        "extraction_status": "FAIL_CLOSED_NOT_EXTRACTED",
        "sample_window": unknown_window(),
        "train_window": unknown_window(),
        "validation_window": unknown_window(),
        "test_window": unknown_window(),
        "split_semantics": NS,
        "feature_lookbacks": NS,
        "warmup_policy": NS,
        "retraining_cadence": NS,
        "overlap_rule": NS,
        "embargo_rule": NS,
        "model_selection_rule": NS,
        "benchmark_evaluation_window": unknown_window(),
        "transaction_cost_evaluation_window": unknown_window(),
        "sample_selection_filters": NS,
        "not_specified_fields": fields,
        "unresolved_blockers": ["FULL_TEXT_SPLIT_NOT_VERIFIED"],
        "evidence_locations": [{
            "url": pin["selected_version_url"],
            "pages": NS,
            "section": NS,
            "claim": "Exact pinned version; split semantics are not promoted until verified against full text."
        }]
    }


def lim(pin: dict[str, Any]) -> dict[str, Any]:
    r = base(pin)
    url = "https://arxiv.org/pdf/1904.04912v2"
    r.update({
        "extraction_status": "VERIFIED_FULL_TEXT",
        "sample_window": year_window(1990, 2015),
        "train_window": {
            "start": 1990,
            "end": NS,
            "precision": "MIXED",
            "rule": "At each five-year recalibration point use all data available up to that point; absolute recalibration calendar endpoints are not enumerated here because the paper describes the rule rather than a complete machine-readable date table."
        },
        "validation_window": {
            "start": NS,
            "end": NS,
            "precision": "RELATIVE",
            "rule": "Most recent 10% of each training block; preceding 90% used for gradient-based training."
        },
        "test_window": year_window(1995, 2015),
        "split_semantics": "EXPANDING",
        "feature_lookbacks": {
            "return_horizons": ["1_day", "1_month", "3_months", "6_months", "1_year"],
            "maximum_return_lookback_days": 252,
            "lstm_trajectory_steps": 63
        },
        "warmup_policy": NS,
        "retraining_cadence": {
            "interval_years": 5,
            "from_scratch": True,
            "training_data": "ALL_AVAILABLE_UP_TO_RECALIBRATION",
            "weights_fixed_for_following_years": 5
        },
        "overlap_rule": NS,
        "embargo_rule": NS,
        "model_selection_rule": {
            "training_fraction": 0.90,
            "validation_fraction": 0.10,
            "validation_position": "MOST_RECENT_PART_OF_TRAINING_BLOCK",
            "max_epochs": 100,
            "early_stopping_patience_epochs": 25,
            "hyperparameter_search": "50_ITERATION_RANDOM_SEARCH",
            "selection_basis": "VALIDATION_LOSS"
        },
        "benchmark_evaluation_window": year_window(1995, 2015),
        "transaction_cost_evaluation_window": year_window(1995, 2015),
        "sample_selection_filters": "Use the 88 ratio-adjusted Pinnacle CLC contracts retained by the paper's <10% missing-data rule.",
        "paper_cross_validation_description": "Paper describes six 5-year blocks spanning 1990-2015, an expanding calibration window, and testing on the next block outside the training set. The apparent block-count/calendar interpretation is retained as paper text rather than silently normalised into invented dates.",
        "not_specified_fields": ["train_window.end", "validation_window.start", "validation_window.end", "warmup_policy", "overlap_rule", "embargo_rule"],
        "unresolved_blockers": [
            "EXACT_RECALIBRATION_DATE_TABLE_NOT_SPECIFIED",
            "ABSOLUTE_VALIDATION_BOUNDARIES_NOT_SPECIFIED",
            "WARMUP_POLICY_NOT_SPECIFIED",
            "OVERLAP_OR_EMBARGO_NOT_SPECIFIED"
        ],
        "evidence_locations": [
            {"url": url, "pages": "7", "section": "IV.B / V.A-V.B", "claim": "90/10 train-validation rule; validation for early stopping/model selection; five-year from-scratch expanding recalibration; next five years OOS."},
            {"url": url, "pages": "8", "section": "V.C", "claim": "Aggregated OOS predictions from 1995 to 2015."},
            {"url": url, "pages": "17", "section": "Appendix B.C", "claim": "Cross-validation description with 5-year blocks, expanding calibration and next-block OOS testing."}
        ]
    })
    return r


def zhang(pin: dict[str, Any]) -> dict[str, Any]:
    r = base(pin)
    url = "https://arxiv.org/pdf/1911.10107v1"
    r.update({
        "extraction_status": "VERIFIED_FULL_TEXT",
        "sample_window": year_window(2005, 2019),
        "train_window": {
            "start": 2005,
            "end": NS,
            "precision": "MIXED",
            "rule": "At every five-year retraining point use all data available up to that point. The paper does not enumerate the exact first/second calibration boundary dates."
        },
        "validation_window": unknown_window(),
        "test_window": year_window(2011, 2019),
        "split_semantics": "EXPANDING",
        "feature_lookbacks": {
            "sign_return_days": 252,
            "volatility_ewm_window_days": 60,
            "macd_price_std_days": 63,
            "macd_normalisation_days": 252
        },
        "warmup_policy": NS,
        "retraining_cadence": {
            "interval_years": 5,
            "training_data": "ALL_AVAILABLE_UP_TO_RETRAINING_POINT",
            "parameters_fixed_for_following_years": 5
        },
        "overlap_rule": NS,
        "embargo_rule": NS,
        "model_selection_rule": NS,
        "benchmark_evaluation_window": year_window(2011, 2019),
        "transaction_cost_evaluation_window": year_window(2011, 2019),
        "sample_selection_filters": "Use the paper's fixed Appendix A universe of 50 ratio-adjusted Pinnacle CLC futures; the operational liquidity-ranking rule used to arrive at those 50 is not specified in the pinned paper.",
        "not_specified_fields": [
            "train_window.end", "validation_window.start", "validation_window.end",
            "warmup_policy", "overlap_rule", "embargo_rule", "model_selection_rule",
            "exact_retraining_calendar_boundaries"
        ],
        "unresolved_blockers": [
            "VALIDATION_PROTOCOL_NOT_SPECIFIED",
            "MODEL_SELECTION_RULE_NOT_SPECIFIED",
            "EXACT_RETRAINING_DATE_TABLE_NOT_SPECIFIED",
            "WARMUP_POLICY_NOT_SPECIFIED",
            "OVERLAP_OR_EMBARGO_NOT_SPECIFIED"
        ],
        "evidence_locations": [
            {"url": url, "pages": "6", "section": "4.1-4.3", "claim": "2005-2019 dataset, retrain every five years on all available data, freeze parameters for next five years, total testing period 2011-2019."},
            {"url": url, "pages": "4", "section": "3", "claim": "252-day return, 60-day volatility and MACD lookback components used by model/baselines."},
            {"url": url, "pages": "7", "section": "4.4", "claim": "Baseline and RL methods are evaluated from 2011-2019 net of transaction costs."}
        ]
    })
    return r


def validate_window(window: dict[str, Any], name: str, paper: str) -> None:
    start, end = window.get("start"), window.get("end")
    if isinstance(start, int) and isinstance(end, int) and start > end:
        raise AssertionError(f"{paper} {name} reversed: {start}>{end}")


def validate(records: list[dict[str, Any]], pins: list[dict[str, Any]]) -> None:
    assert len(records) == len(pins) == 129
    assert len({r["arxiv_id"] for r in records}) == 129
    for record, pin in zip(records, pins):
        assert record["arxiv_id"] == pin["arxiv_id"]
        assert record["selected_version"] == pin["selected_version"]
        for field in WINDOW_FIELDS:
            validate_window(record[field], field, record["arxiv_id"])
        if record["extraction_status"] != "VERIFIED_FULL_TEXT":
            assert record["split_semantics"] == NS
            assert record["validation_window"] == unknown_window()
            assert record["model_selection_rule"] == NS
            assert "FULL_TEXT_SPLIT_NOT_VERIFIED" in record["unresolved_blockers"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--data-contracts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pins_path = args.pins if args.pins.is_absolute() else ROOT / args.pins
    data_path = args.data_contracts if args.data_contracts.is_absolute() else ROOT / args.data_contracts
    out = args.output if args.output.is_absolute() else ROOT / args.output
    pins_manifest = read_json(pins_path)
    data_manifest = read_json(data_path)
    data_by_id = {r["arxiv_id"]: r for r in data_manifest["records"]}
    pins = pins_manifest["pins"]
    records = []
    for pin in pins:
        if pin["arxiv_id"] not in data_by_id:
            raise SystemExit(f"missing #64 data contract for {pin['arxiv_id']}")
        if pin["arxiv_id"] == "1904.04912":
            assert data_by_id[pin["arxiv_id"]]["extraction_status"] == "VERIFIED_FULL_TEXT"
            record = lim(pin)
        elif pin["arxiv_id"] == "1911.10107":
            assert data_by_id[pin["arxiv_id"]]["extraction_status"] == "VERIFIED_FULL_TEXT"
            record = zhang(pin)
        else:
            record = base(pin)
        records.append(record)
    validate(records, pins)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_version_pins_sha256": digest(pins_path),
        "source_data_contracts_sha256": digest(data_path),
        "record_count": len(records),
        "summary": {
            "verified_full_text": sum(r["extraction_status"] == "VERIFIED_FULL_TEXT" for r in records),
            "fail_closed_not_extracted": sum(r["extraction_status"] == "FAIL_CLOSED_NOT_EXTRACTED" for r in records)
        },
        "fail_closed_policy": "Unstated or unverified time-series split boundaries remain NOT_SPECIFIED. Random, validation, rolling, expanding, holdout and OOS semantics are never substituted for one another.",
        "records": records
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
