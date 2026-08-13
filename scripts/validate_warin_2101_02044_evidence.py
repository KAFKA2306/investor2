#!/usr/bin/env python3
"""Fail-closed validator for the canonical Warin empirical evidence chain."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "docs/research/runs/warin_2101_02044_v4_beta2_seed2306"
DEFAULT_REGISTRY = ROOT / "docs/research/2021_arxiv_finance_registry.json"


def load_materializer() -> Any:
    path = ROOT / "scripts/materialize_warin_2101_02044_evidence.py"
    spec = importlib.util.spec_from_file_location("warin_materializer_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Warin materializer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(run_dir: Path, registry_path: Path) -> dict[str, Any]:
    materializer = load_materializer()
    report = materializer.validate_run_dir(run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Warin evidence manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "investor2.paper-evidence-manifest.v1":
        raise ValueError("unexpected Warin evidence manifest schema")
    if manifest.get("empirical_reproduction_state") != "EMPIRICALLY_RUN":
        raise ValueError("manifest is not empirical")
    if manifest.get("empirical_verdict") != report.get("empirical_verdict"):
        raise ValueError("manifest/report verdict mismatch")
    for filename in ("report.json", "training_trace.json", "model_state.json"):
        item = manifest.get("artifacts", {}).get(filename)
        if not isinstance(item, dict) or item.get("sha256") != sha256_file(run_dir / filename):
            raise ValueError(f"manifest hash mismatch for {filename}")
    if manifest.get("artifact_storage", {}).get("mutable_hf_path_alone_is_evidence") is not False:
        raise ValueError("mutable HF path evidence policy was weakened")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    papers = [paper for paper in registry.get("papers", []) if paper.get("id") == "warin_2101_02044"]
    if len(papers) != 1:
        raise ValueError("Warin registry record is missing or duplicated")
    paper = papers[0]
    if paper.get("source_version") != "v4":
        raise ValueError("registry did not pin Warin v4")
    if paper.get("empirical_reproduction_state") != "EMPIRICALLY_RUN":
        raise ValueError("registry empirical state mismatch")
    if paper.get("empirical_verdict") != report.get("empirical_verdict"):
        raise ValueError("registry/report verdict mismatch")
    relative_manifest = str(manifest_path.relative_to(ROOT))
    if paper.get("empirical_evidence_manifest") != relative_manifest:
        raise ValueError("registry evidence path mismatch")
    if paper.get("empirical_evidence_manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("registry evidence manifest hash mismatch")

    artifacts = [
        row
        for row in registry.get("materialized_artifacts", [])
        if isinstance(row, dict)
        and row.get("paper_id") == "warin_2101_02044"
        and row.get("run_id") == "v4_table1_beta2_seed2306"
    ]
    if len(artifacts) != 4:
        raise ValueError("registry must contain four Warin materialized artifact records")
    by_kind = {row["kind"]: row for row in artifacts}
    expected = {
        "empirical_evaluation": run_dir / "report.json",
        "training_trace": run_dir / "training_trace.json",
        "trained_state": run_dir / "model_state.json",
        "evidence_manifest": run_dir / "manifest.json",
    }
    if set(by_kind) != set(expected):
        raise ValueError("registry Warin artifact kinds are incomplete")
    for kind, path in expected.items():
        record = by_kind[kind]
        if record.get("sha256") != sha256_file(path):
            raise ValueError(f"registry hash mismatch for {kind}")
        if record.get("hf_uri") is not None:
            raise ValueError("small Warin artifacts must not invent an HF URI")

    return {
        "empirical_verdict": report["empirical_verdict"],
        "mean": report["evaluation"]["terminal_wealth_mean"],
        "variance": report["evaluation"]["terminal_wealth_population_variance"],
        "manifest_sha256": sha256_file(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    print(json.dumps(validate(args.run_dir, args.registry), sort_keys=True))


if __name__ == "__main__":
    main()
