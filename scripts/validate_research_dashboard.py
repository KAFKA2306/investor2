#!/usr/bin/env python3
"""Semantically validate the AAARTS internal manifest and public HTML shell."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ALLOWED_VERDICTS = {"CONFIRMED", "NOT_CONFIRMED"}
EMPIRICAL_VERDICTS = {"REPRODUCED", "FAILED", "BLOCKED"}
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
    'id="paperRows"',
    'id="methodSources"',
    'data/research_public_manifest.json',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_nonempty_string(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a non-empty string")
    return value


def validate_manifest(data: dict[str, Any], expected_revision: str | None = None) -> None:
    require(data.get("schema_version") == 2, "unsupported manifest schema_version")
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

    paper_queue = data.get("paper_reproduction_2021")
    require(isinstance(paper_queue, dict), "paper_reproduction_2021 must be an object")
    paper_summary = paper_queue.get("summary")
    papers = paper_queue.get("papers")
    require(isinstance(paper_summary, dict), "paper_reproduction_2021.summary must be an object")
    require(isinstance(papers, list), "paper_reproduction_2021.papers must be a list")
    paper_ids: list[str] = []
    for index, paper in enumerate(papers):
        require(isinstance(paper, dict), f"paper_reproduction_2021.papers[{index}] must be an object")
        paper_id = require_nonempty_string(paper.get("id"), f"paper_reproduction_2021.papers[{index}].id")
        paper_ids.append(paper_id)
        require(paper.get("source_metadata_state") == "VERIFIED_PRIMARY", f"primary metadata not verified for {paper_id}")
        require(paper.get("method_contract_state") in {"PASS", "FAIL"}, f"invalid method state for {paper_id}")
        require(paper.get("artifact_state") in {"MATERIALIZED", "NOT_MATERIALIZED"}, f"invalid artifact state for {paper_id}")
        empirical = paper.get("empirical_reproduction_state")
        require(empirical in {"NOT_RUN", "EMPIRICALLY_RUN"}, f"invalid empirical state for {paper_id}")
        if empirical == "NOT_RUN":
            require(
                paper.get("reproduction_verdict") in {"METHOD_ONLY", "METHOD_CONTRACT_FAIL"},
                f"unrun paper has empirical-looking verdict: {paper_id}",
            )
            require(paper.get("empirical_verdict") is None, f"NOT_RUN paper has empirical verdict: {paper_id}")
            require(paper.get("empirical_evidence_manifest") is None, f"NOT_RUN paper has empirical evidence: {paper_id}")
        else:
            verdict = paper.get("empirical_verdict")
            require(verdict in EMPIRICAL_VERDICTS, f"empirically run paper lacks final verdict: {paper_id}")
            require(paper.get("reproduction_verdict") == verdict, f"empirical/reproduction verdict mismatch: {paper_id}")
            require_nonempty_string(paper.get("empirical_evidence_manifest"), f"{paper_id}.empirical_evidence_manifest")
            evidence_sha = require_nonempty_string(
                paper.get("empirical_evidence_manifest_sha256"),
                f"{paper_id}.empirical_evidence_manifest_sha256",
            )
            require(bool(re.fullmatch(r"[0-9a-f]{64}", evidence_sha)), f"invalid empirical evidence SHA-256 for {paper_id}")

    require(len(paper_ids) == len(set(paper_ids)), "paper reproduction IDs must be unique")
    expected_paper = {
        "indexed": len(papers),
        "method_contract_pass": sum(paper.get("method_contract_state") == "PASS" for paper in papers),
        "materialized": sum(paper.get("artifact_state") == "MATERIALIZED" for paper in papers),
        "empirically_run": sum(paper.get("empirical_reproduction_state") == "EMPIRICALLY_RUN" for paper in papers),
        "empirically_reproduced": sum(paper.get("empirical_verdict") == "REPRODUCED" for paper in papers),
        "empirically_failed": sum(paper.get("empirical_verdict") == "FAILED" for paper in papers),
        "empirically_blocked": sum(paper.get("empirical_verdict") == "BLOCKED" for paper in papers),
        "empirically_not_run": sum(paper.get("empirical_reproduction_state") == "NOT_RUN" for paper in papers),
    }
    require(paper_summary == expected_paper, "paper reproduction summary does not match records")
    for key, value in expected_paper.items():
        require(summary.get(f"papers_2021_{key}") == value, f"papers_2021_{key} summary mismatch")

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
    require("<details" in html, "plain-language page must offer progressive disclosure for technical detail")
    require("fetch(" in html, "dashboard does not fetch its public manifest")
    require("実証再現" in html, "dashboard must explain the empirical reproduction boundary")


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
        "papers_2021_indexed": data["summary"]["papers_2021_indexed"],
        "papers_2021_empirically_run": data["summary"]["papers_2021_empirically_run"],
        "papers_2021_empirically_reproduced": data["summary"]["papers_2021_empirically_reproduced"],
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
