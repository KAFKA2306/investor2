#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zhang_1911_10107_empirical.py"
spec = importlib.util.spec_from_file_location("zhang_empirical", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_method_contract() -> None:
    result = mod.method_contract_self_test()
    assert result["status"] == "PASS"
    assert result["discrete_actions"] == [-1, 0, 1]
    assert result["paper_training_cost_basis_points"] == 20.0
    assert math.isclose(result["turnover_cost_sample"], 4.0, abs_tol=1e-12)
    assert mod.sign_return_baseline(110.0, 100.0) == 1
    assert mod.sign_return_baseline(90.0, 100.0) == -1
    assert mod.sign_return_baseline(100.0, 100.0) == 0
    try:
        mod.paper_reward(
            action_t_minus_1=2,
            action_t_minus_2=0,
            sigma_target=0.02,
            sigma_t_minus_1=0.01,
            sigma_t_minus_2=0.01,
            additive_return_t=1.0,
            price_t_minus_1=1000.0,
            cost_rate=0.0020,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("non-paper action must be rejected")


def test_upstream_contracts() -> None:
    protocol = json.loads((ROOT / "docs/research/protocols/zhang_1911_10107_v1_dqn_table2.json").read_text())
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
    split = json.loads((ROOT / "docs/research/arxiv_qfin_2019_split_contracts.json").read_text())
    result = mod.validate_upstream(protocol, data, split)
    assert result["status"] == "PASS", result
    assert len(mod.expected_tickers(result["data_contract"])) == 50
    assert result["split_contract"]["test_window"] == {"start": 2011, "end": 2019, "precision": "YEAR"}
    assert result["split_contract"]["model_selection_rule"] == "NOT_SPECIFIED"


def test_access_evidence_is_explicit_and_fail_closed() -> None:
    evidence = mod.load_access_evidence()
    assert evidence["acquisition"]["state"] == "ACCESS_REQUIRED"
    assert evidence["acquisition"]["exact_paper_vintage_bytes_available"] is False
    assert evidence["acquisition"]["exact_paper_vintage_revision_proven"] is False
    assert evidence["acquisition"]["public_license_for_research_execution"] == "NOT_VERIFIED"
    assert evidence["rules"]["proxy_data_can_promote_exact_reproduction"] is False
    assert evidence["paper_requirement"]["contract_count"] == 50
    assert evidence["paper_requirement"]["dataset_start_year"] == 2005
    assert evidence["paper_requirement"]["dataset_end_year"] == 2019
    assert evidence["paper_requirement"]["oos_start_year"] == 2011
    assert evidence["paper_requirement"]["oos_end_year"] == 2019


def test_missing_data_is_access_required_not_env_placeholder() -> None:
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
    record = mod.find_record(data, "1911.10107")
    old = os.environ.pop("PINNACLE_CLC_DATA_DIR", None)
    try:
        gate = mod.validate_local_dataset(record)
    finally:
        if old is not None:
            os.environ["PINNACLE_CLC_DATA_DIR"] = old
    assert gate["status"] == "BLOCKED"
    assert gate["access_state"] == "ACCESS_REQUIRED"
    assert "PINNACLE_CLC_ACCESS_REQUIRED" in gate["reason_codes"]
    assert "PAPER_VINTAGE_REVISION_NOT_PROVEN" in gate["reason_codes"]
    assert "PINNACLE_CLC_DATA_DIR_NOT_CONFIGURED" not in gate["reason_codes"]
    assert gate["access_evidence"].endswith("zhang_1911_10107_v1_clc_access.json")


def test_substitute_dataset_never_passes() -> None:
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
    record = mod.find_record(data, "1911.10107")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "dataset_manifest.json").write_text(json.dumps({
            "vendor": "public proxy",
            "dataset": "other",
            "linking_method": "back-adjusted",
            "sample_start_year": 2005,
            "sample_end_year": 2019,
            "paper_vintage_revision_proven": False,
            "license_allows_research_execution": True,
            "contracts": []
        }), encoding="utf-8")
        old = os.environ.get("PINNACLE_CLC_DATA_DIR")
        os.environ["PINNACLE_CLC_DATA_DIR"] = td
        try:
            gate = mod.validate_local_dataset(record)
        finally:
            if old is None:
                os.environ.pop("PINNACLE_CLC_DATA_DIR", None)
            else:
                os.environ["PINNACLE_CLC_DATA_DIR"] = old
        assert gate["status"] == "BLOCKED"
        assert gate["access_state"] == "AVAILABLE_LOCAL"
        assert "EXACT_50_TICKER_SET_MISMATCH" in gate["reason_codes"]
        assert any("VENDOR" in code for code in gate["reason_codes"])


if __name__ == "__main__":
    test_method_contract()
    test_upstream_contracts()
    test_access_evidence_is_explicit_and_fail_closed()
    test_missing_data_is_access_required_not_env_placeholder()
    test_substitute_dataset_never_passes()
    print("ok")
