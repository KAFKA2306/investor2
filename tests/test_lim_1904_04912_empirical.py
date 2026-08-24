#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_lim_1904_04912_empirical.py"

spec = importlib.util.spec_from_file_location("lim_empirical", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_method_contract() -> None:
    result = mod.method_contract_self_test()
    assert result["status"] == "PASS"
    values = [0.01, -0.005, 0.008, 0.004, -0.002]
    assert math.isclose(mod.sharpe_loss(values), -mod.annualized_sharpe(values), abs_tol=1e-12)
    try:
        mod.scaled_position(1.01, 0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("signal bounds must be enforced")


def test_upstream_contracts() -> None:
    protocol = json.loads((ROOT / "docs/research/protocols/lim_1904_04912_v2_exhibit8.json").read_text())
    data = json.loads((ROOT / "docs/research/catalogs/arxiv_qfin_2019_data_requirements.json").read_text())
    split = json.loads((ROOT / "docs/research/contracts/arxiv_qfin_2019_split_contracts.json").read_text())
    result = mod.validate_upstream(protocol, data, split)
    assert result["status"] == "PASS", result
    assert len(mod.expected_tickers(result["data_contract"])) == 88
    assert result["split_contract"]["test_window"]["start"] == 1995
    assert result["split_contract"]["test_window"]["end"] == 2015


def test_access_evidence_is_explicit_and_fail_closed() -> None:
    evidence = mod.load_access_evidence()
    assert evidence["acquisition"]["state"] == "ACCESS_REQUIRED"
    assert evidence["acquisition"]["exact_paper_vintage_bytes_available"] is False
    assert evidence["acquisition"]["exact_paper_vintage_revision_proven"] is False
    assert evidence["acquisition"]["public_license_for_research_execution"] == "NOT_VERIFIED"
    assert evidence["rules"]["proxy_data_can_promote_exact_reproduction"] is False
    assert evidence["paper_requirement"]["contract_count"] == 88
    assert evidence["current_vendor_observation"]["catalog_contract_count"] == 98


def test_missing_data_is_access_required_not_env_placeholder() -> None:
    data = json.loads((ROOT / "docs/research/catalogs/arxiv_qfin_2019_data_requirements.json").read_text())
    record = mod.find_record(data, "1904.04912")
    old = mod.os.environ.pop("PINNACLE_CLC_DATA_DIR", None)
    try:
        gate = mod.validate_local_dataset(record)
    finally:
        if old is not None:
            mod.os.environ["PINNACLE_CLC_DATA_DIR"] = old
    assert gate["status"] == "BLOCKED"
    assert gate["access_state"] == "ACCESS_REQUIRED"
    assert "PINNACLE_CLC_ACCESS_REQUIRED" in gate["reason_codes"]
    assert "PAPER_VINTAGE_REVISION_NOT_PROVEN" in gate["reason_codes"]
    assert "PINNACLE_CLC_DATA_DIR_NOT_CONFIGURED" not in gate["reason_codes"]
    assert gate["access_evidence"].endswith("lim_1904_04912_v2_clc_access.json")


def test_invalid_dataset_never_passes() -> None:
    data = json.loads((ROOT / "docs/research/catalogs/arxiv_qfin_2019_data_requirements.json").read_text())
    record = mod.find_record(data, "1904.04912")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "dataset_manifest.json").write_text(json.dumps({
            "vendor": "substitute",
            "dataset": "proxy",
            "linking_method": "back-adjusted",
            "sample_start_year": 1990,
            "sample_end_year": 2015,
            "paper_vintage_revision_proven": False,
            "license_allows_research_execution": True,
            "contracts": []
        }), encoding="utf-8")
        old = mod.os.environ.get("PINNACLE_CLC_DATA_DIR")
        mod.os.environ["PINNACLE_CLC_DATA_DIR"] = td
        try:
            gate = mod.validate_local_dataset(record)
        finally:
            if old is None:
                mod.os.environ.pop("PINNACLE_CLC_DATA_DIR", None)
            else:
                mod.os.environ["PINNACLE_CLC_DATA_DIR"] = old
        assert gate["status"] == "BLOCKED"
        assert gate["access_state"] == "AVAILABLE_LOCAL"
        assert "EXACT_88_TICKER_SET_MISMATCH" in gate["reason_codes"]
        assert any("VENDOR" in code for code in gate["reason_codes"])


if __name__ == "__main__":
    test_method_contract()
    test_upstream_contracts()
    test_access_evidence_is_explicit_and_fail_closed()
    test_missing_data_is_access_required_not_env_placeholder()
    test_invalid_dataset_never_passes()
    print("ok")
