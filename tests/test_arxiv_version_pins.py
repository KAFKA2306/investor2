#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pins_module = load(ROOT / "scripts/pin_arxiv_versions.py", "pin_arxiv_versions_test")
stage_module = load(ROOT / "scripts/build_arxiv_stage_b_inputs.py", "stage_b_inputs_test")

INSPECTED_AT = "2026-08-13T09:55:00Z"
SELECTION_SHA = "c" * 64
SOURCE_SHA = pins_module.EXPECTED_SOURCE_SNAPSHOT_SHA256


def candidate(
    *,
    arxiv_id: str = "2105.11376",
    abs_url: str = "https://arxiv.org/abs/2105.11376v2",
    published: str = "2021-05-24T16:08:58Z",
    updated: str = "2022-01-13T14:15:37Z",
) -> dict:
    return {
        "arxiv_id": arxiv_id,
        "title": "Can we imitate the principal investor's behavior to learn option price?",
        "primary_category": "q-fin.PR",
        "priority_score": 30,
        "decision": "SELECT",
        "abs_url": abs_url,
        "published": published,
        "updated": updated,
    }


def selection(rows: list[dict]) -> dict:
    return {
        "source_snapshot": {"artifact_sha256": SOURCE_SHA},
        "candidates": rows,
    }


def atom_entry(
    query_id: str = "2105.11376v2",
    published: str = "2021-05-24T16:08:58Z",
    updated: str = "2022-01-13T14:15:37Z",
) -> dict[str, str]:
    return {
        "query_id": query_id,
        "published": published,
        "updated": updated,
        "title": "Can we imitate the principal investor's behavior to learn option price?",
    }


def build(rows: list[dict], entries: dict[str, dict[str, str]]) -> dict:
    return pins_module.build_manifest(
        selection(rows),
        selection_manifest_sha256=SELECTION_SHA,
        entries=entries,
        request_provenance=[],
        inspected_at=INSPECTED_AT,
    )


def test_specific_version_not_latest_metadata_is_pinned() -> None:
    report = build([candidate()], {"2105.11376v2": atom_entry()})
    pin = report["pins"][0]
    assert pin["availability_status"] == "VERIFIED"
    assert pin["selected_version"] == "v2"
    assert pin["first_submitted_at"] == "2021-05-24T16:08:58Z"
    assert pin["version_submitted_at"] == "2022-01-13T14:15:37Z"
    assert pin["available_by_2021_end"] is False
    assert report["selection_time_basis"] == "EX_POST_2026_METADATA_NOT_2021_VINTAGE"
    assert report["summary"]["post_2021_selected_versions"] == 1


def test_missing_specific_version_is_unknown_and_fails_closed() -> None:
    report = build([candidate()], {})
    pin = report["pins"][0]
    assert pin["availability_status"] == "UNKNOWN"
    try:
        pins_module.validate_pin_manifest(report, require_all_verified=True)
    except ValueError as error:
        assert "Stage B blocked" in str(error)
    else:
        raise AssertionError("missing version evidence must fail closed")


def test_timestamp_mismatch_is_conflict() -> None:
    report = build(
        [candidate()],
        {"2105.11376v2": atom_entry(updated="2022-01-14T14:15:37Z")},
    )
    pin = report["pins"][0]
    assert pin["availability_status"] == "CONFLICT"
    assert any(item["kind"] == "timestamp_or_version_conflict" for item in pin["evidence"])


def test_select_without_explicit_version_is_conflict() -> None:
    row = candidate(abs_url="https://arxiv.org/abs/2105.11376")
    report = build([row], {})
    assert report["pins"][0]["availability_status"] == "CONFLICT"


def test_identical_inputs_are_byte_stable() -> None:
    rows = [candidate()]
    entries = {"2105.11376v2": atom_entry()}
    first = pins_module.canonical_json_bytes(build(rows, entries))
    second = pins_module.canonical_json_bytes(build(copy.deepcopy(rows), copy.deepcopy(entries)))
    assert first == second


def test_stage_b_requires_verified_pins() -> None:
    rows = [candidate()]
    report = build(rows, {"2105.11376v2": atom_entry()})
    selection_value = selection(rows)
    pins_sha = hashlib.sha256(pins_module.canonical_json_bytes(report)).hexdigest()
    stage = stage_module.build_stage_b_inputs(
        selection_value,
        report,
        selection_sha256=SELECTION_SHA,
        pins_sha256=pins_sha,
    )
    assert stage["record_count"] == 1
    assert stage["records"][0]["selected_version"] == "v2"

    blocked = copy.deepcopy(report)
    blocked["pins"][0]["availability_status"] = "UNKNOWN"
    try:
        stage_module.build_stage_b_inputs(
            selection_value,
            blocked,
            selection_sha256=SELECTION_SHA,
            pins_sha256=pins_sha,
        )
    except ValueError as error:
        assert "blocked" in str(error)
    else:
        raise AssertionError("Stage B must reject an unverified pin")


if __name__ == "__main__":
    test_specific_version_not_latest_metadata_is_pinned()
    test_missing_specific_version_is_unknown_and_fails_closed()
    test_timestamp_mismatch_is_conflict()
    test_select_without_explicit_version_is_conflict()
    test_identical_inputs_are_byte_stable()
    test_stage_b_requires_verified_pins()
    print("PASS")
