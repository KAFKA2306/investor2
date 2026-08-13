#!/usr/bin/env python3
"""Build Stage B paper-inspection input queue from verified version pins.

Data requirements stay fail-closed until exact pinned full text is inspected.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "docs/research/arxiv_qfin_2021_selection_manifest.json"
DEFAULT_PINS = ROOT / "docs/research/arxiv_qfin_2021_version_pins.json"
SCHEMA_VERSION = "investor2.arxiv-stage-b-inputs.v2"
PIN_SCHEMA_VERSION = "investor2.arxiv-version-pins.v1"
UNKNOWN = "NOT_SPECIFIED"
DATA_REQUIREMENT_SCHEMA = "docs/research/arxiv_data_requirement_schema_v1.json"

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

def fail_closed_data_requirements(pin: dict[str, Any]) -> dict[str, Any]:
    return {
        "arxiv_id": pin["arxiv_id"], "selected_version": pin["selected_version"],
        "selected_version_url": pin["selected_version_url"],
        "extraction_status": "FAIL_CLOSED_NOT_EXTRACTED",
        "instrument_universe": UNKNOWN, "market_venue": UNKNOWN,
        "asset_classes": [], "raw_observations": [], "derived_features": [],
        "observation_frequency": UNKNOWN, "source_named_by_paper": UNKNOWN,
        "access_status": "AMBIGUOUS", "transformation_prerequisites": [],
        "transaction_cost_inputs": [], "benchmark_inputs": [],
        "unresolved_blockers": ["FULL_TEXT_REQUIREMENTS_NOT_VERIFIED"],
        "evidence_locations": [{"url": pin["selected_version_url"], "pages": UNKNOWN, "section": UNKNOWN,
            "claim": "Exact pinned paper version; unverified data fields remain fail-closed."}],
    }

def validate_data_requirements(value: dict[str, Any]) -> None:
    if value["extraction_status"] != "FAIL_CLOSED_NOT_EXTRACTED": raise ValueError("unexpected extraction status")
    if value["instrument_universe"] != UNKNOWN or value["source_named_by_paper"] != UNKNOWN: raise ValueError("unverified fields inferred")
    if value["access_status"] != "AMBIGUOUS": raise ValueError("unverified accessibility inferred")
    for key in ("asset_classes", "raw_observations", "derived_features", "transformation_prerequisites", "transaction_cost_inputs", "benchmark_inputs"):
        if value[key]: raise ValueError(f"unverified {key} inferred")

def build_stage_b_inputs(selection: dict[str, Any], pins: dict[str, Any], *, selection_sha256: str, pins_sha256: str) -> dict[str, Any]:
    if pins.get("schema_version") != PIN_SCHEMA_VERSION: raise ValueError("unsupported version pin schema")
    if pins.get("selection_manifest_sha256") != selection_sha256: raise ValueError("version pins were not built from this selection manifest")
    candidates, pin_rows = selection.get("candidates"), pins.get("pins")
    if not isinstance(candidates, list) or not isinstance(pin_rows, list): raise ValueError("selection candidates and version pins are required")
    selected = [row for row in candidates if row.get("decision") == "SELECT"]
    pin_by_id = {row.get("arxiv_id"): row for row in pin_rows}
    if len(pin_by_id) != len(pin_rows): raise ValueError("version pins contain duplicate arXiv ids")
    records, blocked = [], []
    for candidate in selected:
        arxiv_id, pin = candidate["arxiv_id"], pin_by_id.get(candidate["arxiv_id"])
        if pin is None or pin.get("availability_status") != "VERIFIED": blocked.append(arxiv_id); continue
        required = ("selected_version", "selected_version_url", "version_submitted_at", "first_submitted_at", "inspected_source_url")
        if any(not pin.get(key) for key in required): blocked.append(arxiv_id); continue
        data_requirements = fail_closed_data_requirements(pin); validate_data_requirements(data_requirements)
        records.append({"arxiv_id": arxiv_id, "title": candidate["title"], "primary_category": candidate["primary_category"],
            "priority_score": candidate["priority_score"], "selected_version": pin["selected_version"], "selected_version_url": pin["selected_version_url"],
            "first_submitted_at": pin["first_submitted_at"], "version_submitted_at": pin["version_submitted_at"],
            "available_by_2021_end": pin["available_by_2021_end"], "availability_evidence_url": pin["inspected_source_url"],
            "data_requirements": data_requirements})
    if blocked: raise ValueError("Stage B input generation blocked by missing/unverified version pins: " + ", ".join(sorted(set(blocked))))
    if len(records) != len(selected): raise ValueError("Stage B record count does not match selected papers")
    return {"schema_version": SCHEMA_VERSION, "selection_manifest_sha256": selection_sha256, "version_pin_manifest_sha256": pins_sha256,
        "source_snapshot_sha256": pins["source_snapshot_sha256"], "data_requirement_schema": DATA_REQUIREMENT_SCHEMA,
        "data_requirement_policy": "No data field is populated without exact pinned full-text evidence.",
        "record_count": len(records), "data_requirement_summary": {"verified_full_text": 0, "fail_closed_not_extracted": len(records)}, "records": records}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION); parser.add_argument("--pins", type=Path, default=DEFAULT_PINS); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8")); pins = json.loads(args.pins.read_text(encoding="utf-8"))
    result = build_stage_b_inputs(selection, pins, selection_sha256=sha256_file(args.selection), pins_sha256=sha256_file(args.pins))
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(canonical_json_bytes(result)); print(json.dumps({"record_count": result["record_count"]}, sort_keys=True))
if __name__ == "__main__": main()
