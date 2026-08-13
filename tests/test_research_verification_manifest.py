from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_research_verification_manifest.py"
SPEC = importlib.util.spec_from_file_location(
    "build_research_verification_manifest", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_dashboard_manifest_is_fail_closed() -> None:
    manifest = MODULE.build_manifest()
    MODULE.validate_manifest(manifest)

    assert manifest["schema_version"] == 2
    assert manifest["summary"] == {
        "tested_hypotheses": 8,
        "confirmed": 0,
        "not_confirmed": 8,
        "external_claims_unverified": 2,
        "latest_factor_data_end": "2020-02",
        "latest_momentum_data_end": "2017-12",
        "papers_2021_indexed": 4,
        "papers_2021_method_contract_pass": 4,
        "papers_2021_materialized": 1,
        "papers_2021_empirically_run": 1,
        "papers_2021_empirically_reproduced": 1,
        "papers_2021_empirically_failed": 0,
        "papers_2021_empirically_blocked": 0,
        "papers_2021_empirically_not_run": 3,
    }
    assert manifest["repeated_validation"]["study_count"] == 2
    assert manifest["repeated_validation"]["repetitions"] == 5
    assert all(
        claim["evidence_state"] == "UNVERIFIED"
        for claim in manifest["external_claims"]
    )
    assert all(
        result["dashboard_verdict"] == "NOT_CONFIRMED"
        for result in manifest["repository_results"]
    )
    assert all(
        result["gates"]["point_in_time_security_level_rebuild"] == "FAIL"
        for result in manifest["repository_results"]
    )

    queue = manifest["paper_reproduction_2021"]
    assert queue["summary"] == {
        "indexed": 4,
        "method_contract_pass": 4,
        "materialized": 1,
        "empirically_run": 1,
        "empirically_reproduced": 1,
        "empirically_failed": 0,
        "empirically_blocked": 0,
        "empirically_not_run": 3,
    }
    by_id = {paper["id"]: paper for paper in queue["papers"]}
    warin = by_id["warin_2101_02044"]
    assert warin["empirical_reproduction_state"] == "EMPIRICALLY_RUN"
    assert warin["empirical_verdict"] == "REPRODUCED"
    assert warin["reproduction_verdict"] == "REPRODUCED"
    assert warin["artifact_state"] == "MATERIALIZED"
    assert warin["empirical_evidence_manifest"].endswith("manifest.json")
    assert len(warin["empirical_evidence_manifest_sha256"]) == 64

    not_run = [paper for paper in queue["papers"] if paper["id"] != "warin_2101_02044"]
    assert len(not_run) == 3
    assert all(paper["reproduction_verdict"] == "METHOD_ONLY" for paper in not_run)
    assert all(paper["empirical_reproduction_state"] == "NOT_RUN" for paper in not_run)
    assert all(paper["empirical_verdict"] is None for paper in not_run)
