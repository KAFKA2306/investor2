#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-f]{64}$")
VERDICTS = {"REPRODUCED", "FAILED", "BLOCKED"}
STATES = {"NOT_RUN", "EMPIRICALLY_RUN"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    path.relative_to(ROOT.resolve())
    return path


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != "investor2.arxiv-2019-empirical-registry.v1":
        raise ValueError("unsupported 2019 empirical registry schema")
    papers = registry.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError("2019 empirical registry requires papers")
    ids: set[str] = set()
    verdict_counts = {v: 0 for v in sorted(VERDICTS)}
    not_run = 0
    for paper in papers:
        pid = str(paper.get("id", ""))
        if not pid or pid in ids:
            raise ValueError("paper ids must be unique")
        ids.add(pid)
        state = paper.get("empirical_reproduction_state")
        if state not in STATES:
            raise ValueError(f"{pid}: invalid empirical state")
        if state == "NOT_RUN":
            not_run += 1
            if paper.get("empirical_verdict") is not None or paper.get("evidence_manifest") is not None:
                raise ValueError(f"{pid}: NOT_RUN cannot carry verdict/evidence")
            continue
        verdict = paper.get("empirical_verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"{pid}: invalid empirical verdict")
        verdict_counts[verdict] += 1
        path_value = paper.get("evidence_manifest")
        sha = str(paper.get("evidence_manifest_sha256", ""))
        if not isinstance(path_value, str) or not SHA.fullmatch(sha):
            raise ValueError(f"{pid}: evidence manifest path/SHA required")
        path = repo_path(path_value)
        if not path.is_file() or digest(path) != sha:
            raise ValueError(f"{pid}: evidence manifest missing or SHA mismatch")
        manifest = load(path)
        if manifest.get("paper_id") != pid or manifest.get("arxiv_id") != paper.get("arxiv_id"):
            raise ValueError(f"{pid}: evidence identity mismatch")
        if manifest.get("empirical_verdict") != verdict or manifest.get("empirical_reproduction_state") != state:
            raise ValueError(f"{pid}: evidence state/verdict mismatch")
        source = manifest.get("source_pdf", {})
        if source.get("url") != paper.get("source_pdf_url") or not SHA.fullmatch(str(source.get("sha256", ""))):
            raise ValueError(f"{pid}: exact source PDF evidence missing")
        for artifact_name in ("trace", "report"):
            artifact = manifest.get("artifacts", {}).get(artifact_name, {})
            apath = repo_path(str(artifact.get("path", "")))
            asha = str(artifact.get("sha256", ""))
            if not apath.is_file() or not SHA.fullmatch(asha) or digest(apath) != asha:
                raise ValueError(f"{pid}: {artifact_name} evidence missing or SHA mismatch")
        report = load(repo_path(manifest["artifacts"]["report"]["path"]))
        if report.get("empirical_verdict") != verdict:
            raise ValueError(f"{pid}: report verdict mismatch")
        if verdict == "BLOCKED":
            if report.get("observed_metrics") is not None:
                raise ValueError(f"{pid}: BLOCKED run cannot invent metrics")
            if report.get("training_executed") or report.get("evaluation_executed"):
                raise ValueError(f"{pid}: current BLOCKED evidence unexpectedly claims execution")
    return {
        "indexed": len(papers),
        "empirically_run": len(papers) - not_run,
        "not_run": not_run,
        "reproduced": verdict_counts["REPRODUCED"],
        "failed": verdict_counts["FAILED"],
        "blocked": verdict_counts["BLOCKED"],
    }


def build_report(path: Path) -> dict[str, Any]:
    registry = load(path)
    summary = validate_registry(registry)
    return {"schema_version": 1, "summary": summary, "papers": registry["papers"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=ROOT / "docs/research/2019_arxiv_finance_registry.json")
    args = parser.parse_args()
    path = args.registry if args.registry.is_absolute() else ROOT / args.registry
    report = build_report(path)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
