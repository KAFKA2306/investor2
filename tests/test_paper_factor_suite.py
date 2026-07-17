from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_paper_factor_suite.py"
SPEC = importlib.util.spec_from_file_location("verify_paper_factor_suite", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_frozen_multi_paper_suite() -> None:
    report = MODULE.build_report(ROOT / "docs/research/paper_factor_registry.json")
    studies = report["studies"]

    assert len(studies) == 7
    assert report["datasets"]["ff3_1992_2020"]["actual_sha256"] == (
        "8eabadd6ace08a6dd15c30129143920aef47b083b55ecf7976c8620496d6547d"
    )
    assert report["datasets"]["ff5_2015_2020"]["actual_sha256"] == (
        "aec5d51c49cb9f94bf5079c9e5c71bda0dd6a2c4d9160379c256f6a21fd8d31a"
    )

    smb = studies["fama_french_1993_smb"]
    assert smb["gross_results"]["full_oos"]["months"] == 324
    assert smb["gross_results"]["full_oos"]["annualized_arithmetic_mean"] == pytest.approx(
        0.012570370370370364
    )
    assert smb["gross_results"]["late_half"]["annualized_arithmetic_mean"] == pytest.approx(
        0.0017925925925925913
    )
    assert smb["verdict"] == "not_confirmed"

    hml = studies["fama_french_1993_hml"]
    assert hml["gross_results"]["late_half"]["annualized_arithmetic_mean"] == pytest.approx(
        -0.035370370370370365
    )
    assert hml["verdict"] == "not_confirmed"

    rmw = studies["fama_french_2015_rmw"]
    assert rmw["gross_results"]["full_oos"]["months"] == 58
    assert rmw["gross_results"]["full_oos"]["newey_west_t_stat_lag_6"] == pytest.approx(
        1.1564036112151215
    )
    assert rmw["monthly_haircut_sensitivity_bps"]["25"][
        "annualized_arithmetic_mean"
    ] == pytest.approx(-0.01104827586206896)
    assert rmw["verdict"] == "not_confirmed"

    cma = studies["fama_french_2015_cma"]
    assert cma["gross_results"]["full_oos"]["annualized_arithmetic_mean"] == pytest.approx(
        -0.027868965517241384
    )
    assert cma["verdict"] == "not_confirmed"

    assert all(
        study["verdict"] in {"not_confirmed", "proxy_not_confirmed"}
        for study in studies.values()
    )
