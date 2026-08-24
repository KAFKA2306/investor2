#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from snapshot_store import ROOT, latest_snapshot, resolve_artifact, sha256_file

DEFAULT_REUSE_KEY = "arxiv/q-fin/2021/metadata"
DEFAULT_RULES = ROOT / "docs/research/catalogs/arxiv_qfin_selector_rules_v1.json"
DEFAULT_OUTPUT = ROOT / "docs/research/catalogs/arxiv_qfin_2021_selection_manifest.json"
MANIFEST_SCHEMA_VERSION = "investor2.arxiv-qfin-selection-manifest.v1"
DECISION_RANK = {"SELECT": 0, "REVIEW": 1, "REJECT": 2}


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def load_rules(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    rules = json.loads(raw)
    if not isinstance(rules, dict):
        raise AssertionError("selector rules must be a JSON object")
    required = {
        "schema_version",
        "selector_version",
        "required_metadata",
        "decision_thresholds",
        "score_weights",
        "term_groups",
        "forbidden_decision_inputs",
        "stable_tie_breaker",
    }
    missing = sorted(required - rules.keys())
    if missing:
        raise AssertionError(f"selector rules missing fields: {missing}")
    return rules, hashlib.sha256(raw).hexdigest()


def normalized_text(record: dict[str, Any]) -> str:
    title = record.get("title")
    abstract = record.get("abstract")
    values = [value for value in (title, abstract) if isinstance(value, str)]
    return " ".join(" ".join(values).casefold().split())


def matched_terms(text: str, terms: list[str]) -> list[str]:
    matches: set[str] = set()
    for term in terms:
        pattern = rf"(?<!\w){re.escape(term.casefold())}(?!\w)"
        if re.search(pattern, text):
            matches.add(term)
    return sorted(matches)


def missing_required_metadata(record: dict[str, Any], required: list[str]) -> list[str]:
    missing: list[str] = []
    for field in required:
        value = record.get(field)
        if value in (None, "", []):
            missing.append(field)
    return missing


def dimension_status(matches: list[str], positive: str = "METADATA_CUE") -> str:
    return positive if matches else "UNKNOWN"


def classify_record(
    record: dict[str, Any],
    *,
    rules: dict[str, Any],
    source_snapshot_sha256: str,
) -> dict[str, Any]:
    required = rules["required_metadata"]
    missing = missing_required_metadata(record, required)
    text = normalized_text(record)

    term_groups: dict[str, list[str]] = rules["term_groups"]
    evidence_by_group = {
        name: matched_terms(text, terms)
        for name, terms in sorted(term_groups.items())
    }

    if missing:
        decision = "REJECT"
        reason_codes = ["MISSING_REQUIRED_METADATA"]
        priority_score = 0
    else:
        relevance_count = len(evidence_by_group["investment_relevance"])
        method_count = len(evidence_by_group["method"])
        empirical_count = len(evidence_by_group["empirical_or_data"])
        select_threshold = rules["decision_thresholds"]["select"]
        review_threshold = rules["decision_thresholds"]["review"]

        if (
            relevance_count >= select_threshold["min_investment_relevance_terms"]
            and method_count >= select_threshold["min_method_terms"]
            and empirical_count >= select_threshold["min_empirical_or_data_terms"]
        ):
            decision = "SELECT"
            reason_codes = ["STRONG_METADATA_EVIDENCE_FOR_PAPER_INSPECTION"]
        elif relevance_count >= review_threshold["min_investment_relevance_terms"]:
            decision = "REVIEW"
            reason_codes = ["INSUFFICIENT_METADATA_EVIDENCE_FOR_AUTOMATIC_PROMOTION"]
        else:
            decision = "REJECT"
            reason_codes = ["NO_INVESTMENT_RELEVANCE_EVIDENCE"]

        weights = rules["score_weights"]
        priority_score = sum(
            weights[group] * len(evidence_by_group[group])
            for group in sorted(weights)
        )

    evidence = [
        {"dimension": group, "matched_terms": terms}
        for group, terms in sorted(evidence_by_group.items())
        if terms
    ]
    if missing:
        evidence.append({"dimension": "missing_required_metadata", "matched_terms": sorted(missing)})

    return {
        "arxiv_id": record.get("arxiv_id"),
        "title": record.get("title"),
        "primary_category": record.get("primary_category"),
        "categories": sorted(record.get("categories") or []),
        "published": record.get("published"),
        "updated": record.get("updated"),
        "abs_url": record.get("abs_url"),
        "research_importance": "UNASSESSED",
        "investment_relevance": dimension_status(
            evidence_by_group["investment_relevance"], positive="METADATA_CUE"
        ),
        "method_clarity": dimension_status(evidence_by_group["method"]),
        "data_reproducibility": dimension_status(evidence_by_group["empirical_or_data"]),
        "pit_data_feasibility": dimension_status(evidence_by_group["pit_data"]),
        "oos_testability": dimension_status(evidence_by_group["oos"]),
        "transaction_cost_testability": dimension_status(evidence_by_group["transaction_cost"]),
        "lookahead_risk": "CURRENT_ARXIV_METADATA_NOT_2021_VINTAGE",
        "implementation_cost": "UNASSESSED",
        "decision": decision,
        "priority_score": priority_score,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "selector_version": rules["selector_version"],
        "source_snapshot_sha256": source_snapshot_sha256,
    }


def build_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = Counter(candidate["decision"] for candidate in candidates)
    category_totals = Counter(
        candidate["primary_category"] or "UNKNOWN" for candidate in candidates
    )
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for candidate in candidates:
        category = candidate["primary_category"] or "UNKNOWN"
        by_category[category][candidate["decision"]] += 1

    return {
        "record_count": len(candidates),
        "decision_counts": {
            decision: decisions.get(decision, 0)
            for decision in ("SELECT", "REVIEW", "REJECT")
        },
        "primary_category_counts": dict(sorted(category_totals.items())),
        "decision_counts_by_primary_category": {
            category: {
                decision: counts.get(decision, 0)
                for decision in ("SELECT", "REVIEW", "REJECT")
            }
            for category, counts in sorted(by_category.items())
        },
    }


def build_manifest(
    snapshot: dict[str, Any],
    *,
    snapshot_entry: dict[str, Any],
    rules: dict[str, Any],
    rules_sha256: str,
) -> dict[str, Any]:
    records = snapshot.get("records")
    if not isinstance(records, list):
        raise AssertionError("arXiv snapshot must contain a records list")
    if snapshot.get("record_count") != len(records):
        raise AssertionError(
            f"snapshot record_count mismatch: {snapshot.get('record_count')} != {len(records)}"
        )
    if snapshot_entry.get("record_count") != len(records):
        raise AssertionError(
            f"ledger record_count mismatch: {snapshot_entry.get('record_count')} != {len(records)}"
        )

    source_sha256 = snapshot_entry["artifact_sha256"]
    candidates = [
        classify_record(record, rules=rules, source_snapshot_sha256=source_sha256)
        for record in records
    ]
    candidates.sort(
        key=lambda item: (
            DECISION_RANK[item["decision"]],
            -item["priority_score"],
            item["arxiv_id"] or "",
        )
    )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "selector_version": rules["selector_version"],
        "rules_sha256": rules_sha256,
        "source_snapshot": {
            "reuse_key": snapshot_entry["reuse_key"],
            "snapshot_id": snapshot_entry["snapshot_id"],
            "artifact_path": snapshot_entry["artifact_path"],
            "artifact_sha256": source_sha256,
            "record_count": snapshot_entry["record_count"],
            "schema_version": snapshot_entry["schema_version"],
            "observed_at": snapshot_entry["observed_at"],
        },
        "selection_semantics": {
            "SELECT": (
                "Promote to paper-level inspection only. This is not an alpha, reproducibility, "
                "PIT, OOS, cost, or #claims approval."
            ),
            "REVIEW": "Potentially relevant, but metadata evidence is insufficient for automatic inspection priority.",
            "REJECT": "Do not prioritize from metadata; malformed records fail closed.",
        },
        "lookahead_contract": {
            "selection_time_basis": (
                "Ex-post research triage using the canonical arXiv metadata snapshot observed at "
                f"{snapshot_entry['observed_at']}. This is not a reconstruction of what was selectable in 2021."
            ),
            "metadata_revision_risk": (
                "arXiv title/abstract/version metadata may reflect revisions after the initial 2021 submission. "
                "Paper-level PIT work must pin the version and public-availability timestamp separately."
            ),
            "research_importance": (
                "UNASSESSED in Stage A. Citation counts, later journal outcomes, and later performance "
                "are not decision inputs."
            ),
            "forbidden_decision_inputs": sorted(rules["forbidden_decision_inputs"]),
        },
        "summary": build_summary(candidates),
        "candidates": candidates,
    }


def resolve_snapshot(reuse_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    entry = latest_snapshot(reuse_key=reuse_key)
    artifact = resolve_artifact(ROOT, entry["artifact_path"])
    actual_sha256 = sha256_file(artifact)
    if actual_sha256 != entry["artifact_sha256"]:
        raise AssertionError(
            f"source snapshot SHA-256 mismatch: {actual_sha256} != {entry['artifact_sha256']}"
        )
    snapshot = load_json(artifact)
    return snapshot, entry


def write_manifest(manifest: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(manifest))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a deterministic metadata-only arXiv q-fin paper inspection manifest."
    )
    parser.add_argument("--reuse-key", default=DEFAULT_REUSE_KEY)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rules_path = args.rules if args.rules.is_absolute() else ROOT / args.rules
    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    rules, rules_sha256 = load_rules(rules_path)
    snapshot, snapshot_entry = resolve_snapshot(args.reuse_key)
    manifest = build_manifest(
        snapshot,
        snapshot_entry=snapshot_entry,
        rules=rules,
        rules_sha256=rules_sha256,
    )
    write_manifest(manifest, output_path)
    print(
        json.dumps(
            {
                "output": output_path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "selector_version": manifest["selector_version"],
                "source_snapshot_sha256": manifest["source_snapshot"]["artifact_sha256"],
                "summary": manifest["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
