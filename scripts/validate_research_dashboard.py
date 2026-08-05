#!/usr/bin/env python3
"""Semantically validate the AAARTS dashboard manifest and HTML shell."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ALLOWED_VERDICTS = {"CONFIRMED", "NOT_CONFIRMED"}
REQUIRED_PROMOTION_GATES = {
    "chronological_oos",
    "t_stat_ge_3",
    "block_bootstrap_lower_gt_0",
    "late_period_mean_gt_0",
    "after_25bps_monthly_haircut_gt_0",
    "point_in_time_security_level_rebuild",
    "tradability_and_borrowability",
}
REQUIRED_HTML_MARKERS = (
    '<html lang="ja">',
    "<main",
    'id="resultRows"',
    'id="protocolGates"',
    'id="claimCards"',
    'data/research_verification_manifest.json',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_nonempty_string(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a non-empty string")
    return value


def validate_manifest(data: dict[str, Any], expected_revision: str | None = None) -> None:
    require(data.get("schema_version") == 1, "unsupported manifest schema_version")
    records = data.get("repository_results")
    summary = data.get("summary")
    require(isinstance(records, list), "repository_results must be a list")
    require(isinstance(summary, dict), "summary must be an object")

    ids: list[str] = []
    verdict_counts = {verdict: 0 for verdict in ALLOWED_VERDICTS}
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"repository_results[{index}] must be an object")
        record_id = require_nonempty_string(record.get("id"), f"repository_results[{index}].id")
        ids.append(record_id)
        verdict = require_nonempty_string(
            record.get("dashboard_verdict"), f"repository_results[{index}].dashboard_verdict"
        )
        require(verdict in ALLOWED_VERDICTS, f"unknown dashboard_verdict for {record_id}: {verdict}")
        verdict_counts[verdict] += 1
        gates = record.get("gates")
        require(isinstance(gates, dict), f"gates missing for {record_id}")
        require(REQUIRED_PROMOTION_GATES <= set(gates), f"required gates missing for {record_id}")
        require(all(value in {"PASS", "FAIL", "NOT_RUN"} for value in gates.values()), f"invalid gate state for {record_id}")
        if verdict == "CONFIRMED":
            failed = sorted(name for name in REQUIRED_PROMOTION_GATES if gates.get(name) != "PASS")
            require(not failed, f"CONFIRMED record {record_id} has incomplete gates: {failed}")

    require(len(ids) == len(set(ids)), "hypothesis IDs must be unique")
    require(summary.get("tested_hypotheses") == len(records), "tested_hypotheses does not match repository_results")
    require(summary.get("confirmed") == verdict_counts["CONFIRMED"], "confirmed summary does not match records")
    require(summary.get("not_confirmed") == verdict_counts["NOT_CONFIRMED"], "not_confirmed summary does not match records")

    claims = data.get("external_claims")
    require(isinstance(claims, list), "external_claims must be a list")
    claim_ids = [require_nonempty_string(item.get("id"), "external_claim.id") for item in claims]
    require(len(claim_ids) == len(set(claim_ids)), "external claim IDs must be unique")
    unverified = sum(item.get("evidence_state") == "UNVERIFIED" for item in claims)
    require(summary.get("external_claims_unverified") == unverified, "external claim summary does not match records")

    generated_from = data.get("generated_from")
    require(isinstance(generated_from, dict) and generated_from, "generated_from must be a non-empty object")
    evidence_refs = [require_nonempty_string(value, f"generated_from.{key}") for key, value in generated_from.items()]
    require(len(evidence_refs) == len(set(evidence_refs)), "generated_from references must be unique")

    repeated = data.get("repeated_validation")
    require(isinstance(repeated, dict), "repeated_validation must be an object")
    studies = repeated.get("studies")
    require(isinstance(studies, dict), "repeated_validation.studies must be an object")
    require(repeated.get("study_count") == len(studies), "repeated_validation.study_count does not match studies")
    require(repeated.get("all_verdicts_stable") is True, "repeated validation verdicts are unstable")

    build = data.get("build")
    require(isinstance(build, dict), "build provenance must be an object")
    revision = require_nonempty_string(build.get("code_sha"), "build.code_sha")
    run_id = require_nonempty_string(build.get("run_id"), "build.run_id")
    require(bool(re.fullmatch(r"[0-9a-f]{40}|LOCAL_WORKTREE", revision)), "build.code_sha must be a commit SHA or LOCAL_WORKTREE")
    require(bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", run_id)), "build.run_id contains unsupported characters")
    if expected_revision:
        require(revision == expected_revision, f"deployed revision {revision} does not match expected {expected_revision}")


def validate_html(html: str) -> None:
    for marker in REQUIRED_HTML_MARKERS:
        require(marker in html, f"required HTML marker missing: {marker}")
    require("<title>" in html and "</title>" in html, "HTML title is missing")
    require("<header" in html and "<nav" in html and "<footer" in html, "required page landmarks are missing")
    require("<table" in html and "<thead" in html and "<tbody" in html, "results table structure is incomplete")
    require("fetch(" in html, "dashboard does not fetch its manifest")


def validate_files(manifest_path: Path, html_path: Path, expected_revision: str | None = None) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(data, expected_revision=expected_revision)
    validate_html(html_path.read_text(encoding="utf-8"))
    return {
        "manifest": str(manifest_path),
        "html": str(html_path),
        "code_sha": data["build"]["code_sha"],
        "run_id": data["build"]["run_id"],
        "tested_hypotheses": data["summary"]["tested_hypotheses"],
        "confirmed": data["summary"]["confirmed"],
        "status": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--expected-revision")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_files(args.manifest, args.html, args.expected_revision)
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
