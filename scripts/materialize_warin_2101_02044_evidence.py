#!/usr/bin/env python3
"""Materialize a completed Warin empirical run into canonical Git evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/research/2021_arxiv_finance_registry.json"
DESTINATION = ROOT / "docs/research/runs/warin_2101_02044_v4_beta2_seed2306"
ALLOWED_VERDICTS = {"REPRODUCED", "FAILED", "BLOCKED"}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_run_dir(run_dir: Path) -> dict[str, Any]:
    required = ["report.json", "training_trace.json", "model_state.json"]
    missing = [name for name in required if not (run_dir / name).is_file()]
    if missing:
        raise ValueError("missing Warin run artifacts: " + ", ".join(missing))
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    if report.get("schema_version") != "investor2.warin-2101.02044-empirical.v1":
        raise ValueError("unexpected Warin report schema")
    if report.get("empirical_reproduction_state") != "EMPIRICALLY_RUN":
        raise ValueError("Warin report must be empirically run")
    if report.get("empirical_verdict") not in ALLOWED_VERDICTS:
        raise ValueError("Warin report verdict is invalid")
    if report.get("paper_version") != "v4":
        raise ValueError("Warin report must use pinned v4")
    if report.get("training", {}).get("gradient_iterations") != 15000:
        raise ValueError("Warin report did not execute 15,000 gradient iterations")
    if report.get("training", {}).get("batch_size") != 300:
        raise ValueError("Warin report batch size does not match paper protocol")
    if report.get("evaluation", {}).get("simulation_count") != 100000:
        raise ValueError("Warin report did not execute 100,000 evaluation simulations")
    if report.get("training", {}).get("trace_sha256") != sha256_file(run_dir / "training_trace.json"):
        raise ValueError("training trace SHA-256 mismatch")
    if report.get("training", {}).get("model_state_sha256") != sha256_file(run_dir / "model_state.json"):
        raise ValueError("model state SHA-256 mismatch")
    source = report.get("source_pdf", {})
    if not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64:
        raise ValueError("source PDF SHA-256 is missing")
    if source.get("stored_in_repository") is not False:
        raise ValueError("paper bytes must not be redistributed by this evidence materializer")
    if report.get("artifact_policy", {}).get("mutable_path_without_git_hash_is_evidence") is not False:
        raise ValueError("mutable-path-only evidence must remain forbidden")
    return report


def update_registry(registry: dict[str, Any], report: dict[str, Any], manifest_path: Path, manifest_sha: str) -> dict[str, Any]:
    papers = registry.get("papers")
    if not isinstance(papers, list):
        raise ValueError("registry papers are required")
    matches = [paper for paper in papers if paper.get("id") == "warin_2101_02044"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Warin registry record")
    paper = matches[0]
    paper["source_url"] = "https://arxiv.org/abs/2101.02044v4"
    paper["source_version"] = "v4"
    paper["source_version_submitted_at"] = "2022-02-15T10:34:34Z"
    paper["implementation_scope"] = (
        "Method-contract simplex projection plus an independent empirical reproduction of "
        "Section 3.2 Table 1, point-by-point direct formulation at beta=2.0. Other paper "
        "figures/tables remain outside this run scope."
    )
    paper["empirical_reproduction_state"] = "EMPIRICALLY_RUN"
    paper["empirical_verdict"] = report["empirical_verdict"]
    paper["empirical_evidence_manifest"] = str(manifest_path.relative_to(ROOT))
    paper["empirical_evidence_manifest_sha256"] = manifest_sha
    paper["unreproduced_evidence"] = (
        "This run covers one locked Table 1 point only. Dimension-20, constrained, Heston, "
        "Mean-CVaR, global, and remaining point-by-point experiments are not claimed reproduced."
    )

    artifacts = registry.setdefault("materialized_artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("registry materialized_artifacts must be a list")
    artifacts[:] = [
        row
        for row in artifacts
        if not (
            isinstance(row, dict)
            and row.get("paper_id") == "warin_2101_02044"
            and row.get("run_id") == "v4_table1_beta2_seed2306"
        )
    ]
    for kind, filename in (
        ("empirical_evaluation", "report.json"),
        ("training_trace", "training_trace.json"),
        ("trained_state", "model_state.json"),
        ("evidence_manifest", "manifest.json"),
    ):
        path = DESTINATION / filename
        artifacts.append(
            {
                "paper_id": "warin_2101_02044",
                "arxiv_id": "2101.02044",
                "run_id": "v4_table1_beta2_seed2306",
                "kind": kind,
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "provenance": "generated by scripts/run_warin_2101_02044_empirical.py and materialized by scripts/materialize_warin_2101_02044_evidence.py",
                "license_state": "REPOSITORY_LICENSE_NOT_DECLARED",
                "hf_uri": None,
                "canonical_evidence_rule": "Git-committed path plus exact SHA-256; no mutable HF path is used for this small artifact"
            }
        )
    return registry


def materialize(run_dir: Path, registry_path: Path) -> dict[str, Any]:
    report = validate_run_dir(run_dir)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename in ("report.json", "training_trace.json", "model_state.json"):
        shutil.copyfile(run_dir / filename, DESTINATION / filename)

    manifest = {
        "schema_version": "investor2.paper-evidence-manifest.v1",
        "paper_id": "warin_2101_02044",
        "arxiv_id": "2101.02044",
        "paper_version": "v4",
        "run_id": "v4_table1_beta2_seed2306",
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": report["empirical_verdict"],
        "source_pdf": report["source_pdf"],
        "artifacts": {
            filename: {
                "sha256": sha256_file(DESTINATION / filename),
                "size_bytes": (DESTINATION / filename).stat().st_size,
            }
            for filename in ("report.json", "training_trace.json", "model_state.json")
        },
        "protocol": report["protocol"],
        "runtime": report["runtime"],
        "licenses": report["licenses"],
        "artifact_storage": {
            "large_artifacts": "NONE",
            "huggingface_used": False,
            "reason": "all generated artifacts are small enough for Git and contain no third-party paper bytes",
            "mutable_hf_path_alone_is_evidence": False,
        },
    }
    manifest_path = DESTINATION / "manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest))
    manifest_sha = sha256_file(manifest_path)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry = update_registry(registry, report, manifest_path, manifest_sha)
    registry_path.write_bytes(canonical_bytes(registry))
    return {
        "destination": str(DESTINATION.relative_to(ROOT)),
        "manifest_sha256": manifest_sha,
        "verdict": report["empirical_verdict"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    result = materialize(args.run_dir, args.registry)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
