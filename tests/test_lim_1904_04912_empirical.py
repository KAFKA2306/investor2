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
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
    split = json.loads((ROOT / "docs/research/arxiv_qfin_2019_split_contracts.json").read_text())
    result = mod.validate_upstream(protocol, data, split)
    assert result["status"] == "PASS", result
    assert len(mod.expected_tickers(result["data_contract"])) == 88
    assert result["split_contract"]["test_window"]["start"] == 1995
    assert result["split_contract"]["test_window"]["end"] == 2015


def test_missing_data_is_blocked() -> None:
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
    record = mod.find_record(data, "1904.04912")
    old = mod.os.environ.pop("PINNACLE_CLC_DATA_DIR", None)
    try:
        gate = mod.validate_local_dataset(record)
    finally:
        if old is not None:
            mod.os.environ["PINNACLE_CLC_DATA_DIR"] = old
    assert gate["status"] == "BLOCKED"
    assert gate["reason_codes"] == ["PINNACLE_CLC_DATA_DIR_NOT_CONFIGURED"]


def test_invalid_dataset_never_passes() -> None:
    data = json.loads((ROOT / "docs/research/arxiv_qfin_2019_data_requirements.json").read_text())
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
        assert "EXACT_88_TICKER_SET_MISMATCH" in gate["reason_codes"]
        assert any("VENDOR" in code for code in gate["reason_codes"])


if __name__ == "__main__":
    test_method_contract()
    test_upstream_contracts()
    test_missing_data_is_blocked()
    test_invalid_dataset_never_passes()
    print("ok")
