#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "select_arxiv_qfin_papers.py"
sys.path.insert(0, str(MODULE_PATH.parent))
spec = importlib.util.spec_from_file_location("select_arxiv_qfin_papers", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

RULES = {
    "schema_version": "investor2.arxiv-qfin-selector-rules.v1",
    "selector_version": "test-1",
    "required_metadata": [
        "arxiv_id",
        "title",
        "abstract",
        "published",
        "primary_category",
        "categories",
        "abs_url",
    ],
    "decision_thresholds": {
        "select": {
            "min_investment_relevance_terms": 2,
            "min_method_terms": 1,
            "min_empirical_or_data_terms": 1,
        },
        "review": {"min_investment_relevance_terms": 1},
    },
    "score_weights": {
        "investment_relevance": 4,
        "method": 2,
        "empirical_or_data": 2,
        "oos": 2,
        "transaction_cost": 1,
        "pit_data": 1,
    },
    "term_groups": {
        "investment_relevance": ["portfolio", "stock", "trading"],
        "method": ["strategy", "model"],
        "empirical_or_data": ["data", "empirical"],
        "oos": ["out-of-sample"],
        "transaction_cost": ["transaction cost"],
        "pit_data": ["prices", "returns"],
    },
    "forbidden_decision_inputs": ["citation_count", "journal_ref"],
    "stable_tie_breaker": ["decision_rank", "priority_score_desc", "arxiv_id_asc"],
}


def record(arxiv_id: str = "2101.00002") -> dict:
    return {
        "arxiv_id": arxiv_id,
        "title": "Stock portfolio trading strategy",
        "abstract": "We use empirical price data and returns to test a portfolio model.",
        "published": "2021-01-01T00:00:00Z",
        "updated": "2021-01-02T00:00:00Z",
        "primary_category": "q-fin.PM",
        "categories": ["q-fin.PM"],
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def snapshot_entry(count: int) -> dict:
    return {
        "reuse_key": "arxiv/q-fin/2021/metadata",
        "snapshot_id": "snapshot-test",
        "artifact_path": "docs/research/data/arxiv_qfin_2021.json",
        "artifact_sha256": "a" * 64,
        "record_count": count,
        "schema_version": "investor2.arxiv-qfin-metadata.v1",
        "observed_at": "2026-08-13T09:02:34Z",
    }


def build(records: list[dict]) -> dict:
    snapshot = {"record_count": len(records), "records": records}
    return module.build_manifest(
        snapshot,
        snapshot_entry=snapshot_entry(len(records)),
        rules=RULES,
        rules_sha256="b" * 64,
    )


def test_select_means_paper_inspection_only() -> None:
    manifest = build([record()])
    candidate = manifest["candidates"][0]
    assert candidate["decision"] == "SELECT"
    assert candidate["research_importance"] == "UNASSESSED"
    assert candidate["lookahead_risk"] == "CURRENT_ARXIV_METADATA_NOT_2021_VINTAGE"
    assert "#claims" in manifest["selection_semantics"]["SELECT"]
    assert "not a reconstruction" in manifest["lookahead_contract"]["selection_time_basis"]


def test_missing_metadata_fails_closed() -> None:
    broken = record()
    broken["abstract"] = None
    candidate = build([broken])["candidates"][0]
    assert candidate["decision"] == "REJECT"
    assert candidate["reason_codes"] == ["MISSING_REQUIRED_METADATA"]
    assert any(
        item["dimension"] == "missing_required_metadata"
        and "abstract" in item["matched_terms"]
        for item in candidate["evidence"]
    )


def test_current_citation_count_cannot_change_selection() -> None:
    base = record()
    contaminated = copy.deepcopy(base)
    contaminated["citation_count"] = 999_999
    contaminated["journal_ref"] = "Later journal outcome"
    assert build([base])["candidates"] == build([contaminated])["candidates"]


def test_stable_tie_breaker_uses_arxiv_id() -> None:
    manifest = build([record("2101.00002"), record("2101.00001")])
    ids = [item["arxiv_id"] for item in manifest["candidates"]]
    assert ids == ["2101.00001", "2101.00002"]


def test_byte_stable_for_identical_input() -> None:
    records = [record("2101.00002"), record("2101.00001")]
    first = module.canonical_json_bytes(build(records))
    second = module.canonical_json_bytes(build(copy.deepcopy(records)))
    assert first == second
    decoded = json.loads(first)
    assert decoded["source_snapshot"]["artifact_sha256"] == "a" * 64


def test_term_matching_does_not_match_data_inside_metadata() -> None:
    assert module.matched_terms("metadata only", ["data"]) == []
    assert module.matched_terms("market data only", ["data"]) == ["data"]


if __name__ == "__main__":
    test_select_means_paper_inspection_only()
    test_missing_metadata_fails_closed()
    test_current_citation_count_cannot_change_selection()
    test_stable_tie_breaker_uses_arxiv_id()
    test_byte_stable_for_identical_input()
    test_term_matching_does_not_match_data_inside_metadata()
    print("PASS")
