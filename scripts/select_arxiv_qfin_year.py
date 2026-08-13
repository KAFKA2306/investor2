#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from select_arxiv_qfin_papers import (
    ROOT,
    build_manifest,
    load_rules,
    resolve_snapshot,
    write_manifest,
)

ADAPTER_VERSION = "investor2.arxiv-qfin-year-selection-adapter.v1"


def _metadata_status(value: str) -> str:
    if value == "METADATA_CUE":
        return "METADATA_CUE_ONLY"
    return "UNKNOWN"


def adapt_manifest_for_year(manifest: dict[str, Any], *, year: int) -> dict[str, Any]:
    source = manifest.get("source_snapshot")
    if not isinstance(source, dict):
        raise AssertionError("selection manifest source_snapshot is required")
    expected_reuse_key = f"arxiv/q-fin/{year}/metadata"
    if source.get("reuse_key") != expected_reuse_key:
        raise AssertionError(
            f"source reuse_key mismatch: {source.get('reuse_key')!r} != {expected_reuse_key!r}"
        )

    manifest["year_selection_adapter_version"] = ADAPTER_VERSION
    manifest["population_year"] = year
    manifest["year_specific_contract"] = {
        "assessment_basis": "TITLE_ABSTRACT_AND_ARXIV_METADATA_ONLY",
        "paper_text_fields": (
            "Any field requiring full-paper inspection remains PAPER_TEXT_NOT_INSPECTED at Stage A. "
            "No public/proprietary data status, split boundary, benchmark definition, or code link is inferred."
        ),
        "forbidden_hindsight_inputs": [
            "citation_count",
            "later_journal_outcome",
            f"post_{year}_performance",
            "current_repository_implementation",
        ],
    }

    lookahead = manifest.get("lookahead_contract")
    if isinstance(lookahead, dict):
        lookahead["selection_time_basis"] = (
            "Ex-post research triage using the canonical arXiv metadata snapshot observed at "
            f"{source['observed_at']}. This is not a reconstruction of what was selectable in {year}."
        )
        lookahead["metadata_revision_risk"] = (
            "arXiv title/abstract/version metadata may reflect revisions after the initial "
            f"{year} submission. Paper-level PIT work must pin the exact version and public-availability "
            "timestamp separately."
        )

    for candidate in manifest.get("candidates", []):
        candidate["lookahead_risk"] = f"CURRENT_ARXIV_METADATA_NOT_{year}_VINTAGE"
        candidate["empirical_experiment"] = _metadata_status(
            str(candidate.get("data_reproducibility", "UNKNOWN"))
        )
        candidate["financial_empirical_relevance"] = _metadata_status(
            str(candidate.get("investment_relevance", "UNKNOWN"))
        )
        candidate["input_output_metric_identifiability"] = "PAPER_TEXT_NOT_INSPECTED"
        candidate["sample_split_protocol_extractability"] = "PAPER_TEXT_NOT_INSPECTED"
        candidate["data_access_status"] = "PAPER_TEXT_NOT_INSPECTED"
        candidate["author_code_data_link_status"] = "PAPER_TEXT_NOT_INSPECTED"
        candidate["benchmark_definition_status"] = "PAPER_TEXT_NOT_INSPECTED"
        candidate["reproduction_blockers"] = ["PAPER_TEXT_NOT_INSPECTED"]

    return manifest


def build_year_manifest(*, year: int, rules_path: Path) -> dict[str, Any]:
    rules, rules_sha256 = load_rules(rules_path)
    snapshot, snapshot_entry = resolve_snapshot(f"arxiv/q-fin/{year}/metadata")
    if snapshot.get("year") != year:
        raise AssertionError(f"snapshot year mismatch: {snapshot.get('year')!r} != {year}")
    manifest = build_manifest(
        snapshot,
        snapshot_entry=snapshot_entry,
        rules=rules,
        rules_sha256=rules_sha256,
    )
    return adapt_manifest_for_year(manifest, year=year)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic year-specific arXiv q-fin Stage A selection manifest."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument(
        "--rules",
        type=Path,
        default=ROOT / "docs/research/arxiv_qfin_selector_rules_v1.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rules_path = args.rules if args.rules.is_absolute() else ROOT / args.rules
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = build_year_manifest(year=args.year, rules_path=rules_path)
    write_manifest(manifest, output_path)
    print(
        json.dumps(
            {
                "output": output_path.resolve().relative_to(ROOT.resolve()).as_posix(),
                "population_year": args.year,
                "source_snapshot_sha256": manifest["source_snapshot"]["artifact_sha256"],
                "selector_version": manifest["selector_version"],
                "adapter_version": ADAPTER_VERSION,
                "summary": manifest["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
