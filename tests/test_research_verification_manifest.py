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

    assert manifest["summary"] == {
        "tested_hypotheses": 8,
        "confirmed": 0,
        "not_confirmed": 8,
        "external_claims_unverified": 2,
        "latest_factor_data_end": "2020-02",
        "latest_momentum_data_end": "2017-12",
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
