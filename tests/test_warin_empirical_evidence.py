#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


materializer = load(
    ROOT / "scripts/materialize_warin_2101_02044_evidence.py",
    "materialize_warin_evidence_test",
)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_run(directory: Path, verdict: str = "FAILED") -> dict:
    trace = b'{"trace":[]}\n'
    model = b'{"layers":[]}\n'
    (directory / "training_trace.json").write_bytes(trace)
    (directory / "model_state.json").write_bytes(model)
    report = {
        "schema_version": "investor2.warin-2101.02044-empirical.v1",
        "paper_version": "v4",
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": verdict,
        "training": {
            "gradient_iterations": 15000,
            "batch_size": 300,
            "trace_sha256": sha(trace),
            "model_state_sha256": sha(model),
        },
        "evaluation": {"simulation_count": 100000},
        "source_pdf": {
            "sha256": "a" * 64,
            "stored_in_repository": False,
        },
        "artifact_policy": {"mutable_path_without_git_hash_is_evidence": False},
    }
    (directory / "report.json").write_text(
        json.dumps(report, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def test_protocol_is_locked_to_paper_table_1_beta_2() -> None:
    protocol = json.loads(
        (ROOT / "docs/research/protocols/warin_2101_02044_v4_beta2.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["paper"]["selected_version"] == "v4"
    assert protocol["reproduction_scope"]["paper_table"] == 1
    assert protocol["reproduction_scope"]["beta"] == 2.0
    assert protocol["network"]["gradient_iterations"] == 15000
    assert protocol["network"]["batch_size"] == 300
    assert protocol["evaluation"]["simulation_count"] == 100000
    assert protocol["implementation_lock"]["seed"] == 2306
    assert protocol["promotion_policy"]["states"] == ["REPRODUCED", "FAILED", "BLOCKED"]


def test_completed_run_accepts_all_three_verdicts() -> None:
    for verdict in ("REPRODUCED", "FAILED", "BLOCKED"):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_run(directory, verdict)
            report = materializer.validate_run_dir(directory)
            assert report["empirical_verdict"] == verdict


def test_method_only_or_missing_training_cannot_promote() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        report = make_run(directory)
        report["empirical_reproduction_state"] = "METHOD_ONLY"
        (directory / "report.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
        try:
            materializer.validate_run_dir(directory)
        except ValueError as error:
            assert "empirically run" in str(error)
        else:
            raise AssertionError("METHOD_ONLY must not be accepted as empirical evidence")


def test_tampered_trace_fails_hash_validation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        make_run(directory)
        (directory / "training_trace.json").write_text('{"trace":[1]}\n', encoding="utf-8")
        try:
            materializer.validate_run_dir(directory)
        except ValueError as error:
            assert "trace SHA-256 mismatch" in str(error)
        else:
            raise AssertionError("tampered raw trace must fail closed")


def test_reduced_training_or_evaluation_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        report = make_run(directory)
        report["training"]["gradient_iterations"] = 14999
        (directory / "report.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
        try:
            materializer.validate_run_dir(directory)
        except ValueError as error:
            assert "15,000" in str(error)
        else:
            raise AssertionError("reduced training count must fail closed")


if __name__ == "__main__":
    test_protocol_is_locked_to_paper_table_1_beta_2()
    test_completed_run_accepts_all_three_verdicts()
    test_method_only_or_missing_training_cannot_promote()
    test_tampered_trace_fails_hash_validation()
    test_reduced_training_or_evaluation_fails_closed()
    print("PASS")
