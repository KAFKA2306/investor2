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
        "papers_2021_materialized": 0,
        "papers_2021_empirically_reproduced": 0,
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

    papers_2021 = manifest["paper_reproduction_2021"]
    assert papers_2021["summary"] == {
        "indexed": 4,
        "method_contract_pass": 4,
        "materialized": 0,
        "empirically_reproduced": 0,
    }
    assert all(paper["reproduction_verdict"] == "METHOD_ONLY" for paper in papers_2021["papers"])
    assert all(paper["empirical_reproduction_state"] == "NOT_RUN" for paper in papers_2021["papers"])
