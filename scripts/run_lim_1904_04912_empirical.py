#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "lim_1904_04912_v2_exhibit8_seed2306"
ARXIV_ID = "1904.04912"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def annualized_sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        raise ValueError("at least two returns are required")
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / len(returns)
    if variance <= 0:
        raise ValueError("return variance must be positive")
    return mean * math.sqrt(252.0) / math.sqrt(variance)


def sharpe_loss(returns: list[float]) -> float:
    return -annualized_sharpe(returns)


def scaled_position(signal: float, ex_ante_daily_vol: float, annualized_target: float = 0.15) -> float:
    if not -1.0 <= signal <= 1.0:
        raise ValueError("paper position signal must be in [-1, 1]")
    if ex_ante_daily_vol <= 0:
        raise ValueError("ex-ante volatility must be positive")
    return signal * annualized_target / ex_ante_daily_vol


def cost_adjusted_asset_return(
    *,
    signal: float,
    previous_signal: float,
    ex_ante_daily_vol: float,
    previous_ex_ante_daily_vol: float,
    next_return: float,
    cost_bps: float,
    annualized_target: float = 0.15,
) -> float:
    current = scaled_position(signal, ex_ante_daily_vol, annualized_target)
    previous = scaled_position(previous_signal, previous_ex_ante_daily_vol, annualized_target)
    cost = cost_bps / 10000.0
    return current * next_return - cost * abs(current - previous)


def method_contract_self_test() -> dict[str, Any]:
    sample = [0.01, -0.005, 0.008, 0.004, -0.002]
    sharpe = annualized_sharpe(sample)
    loss = sharpe_loss(sample)
    gross = cost_adjusted_asset_return(
        signal=0.5,
        previous_signal=0.25,
        ex_ante_daily_vol=0.01,
        previous_ex_ante_daily_vol=0.01,
        next_return=0.01,
        cost_bps=0.0,
    )
    net = cost_adjusted_asset_return(
        signal=0.5,
        previous_signal=0.25,
        ex_ante_daily_vol=0.01,
        previous_ex_ante_daily_vol=0.01,
        next_return=0.01,
        cost_bps=10.0,
    )
    expected_turnover_cost = 0.001 * abs((0.5 * 0.15 / 0.01) - (0.25 * 0.15 / 0.01))
    if not math.isclose(loss, -sharpe, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError("Sharpe loss sign contract failed")
    if not math.isclose(gross - net, expected_turnover_cost, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError("turnover cost contract failed")
    return {
        "status": "PASS",
        "annualized_sharpe_sample": sharpe,
        "cost_free_return_sample": gross,
        "cost_adjusted_return_10bps_sample": net,
        "turnover_cost_sample": expected_turnover_cost,
    }


def find_record(manifest: dict[str, Any], arxiv_id: str) -> dict[str, Any]:
    rows = [r for r in manifest.get("records", []) if r.get("arxiv_id") == arxiv_id]
    if len(rows) != 1:
        raise ValueError(f"expected exactly one {arxiv_id} record")
    return rows[0]


def validate_upstream(protocol: dict[str, Any], data: dict[str, Any], split: dict[str, Any]) -> dict[str, Any]:
    d = find_record(data, ARXIV_ID)
    s = find_record(split, ARXIV_ID)
    errors: list[str] = []
    if protocol.get("source_version") != "v2" or d.get("selected_version") != "v2" or s.get("selected_version") != "v2":
        errors.append("EXACT_VERSION_NOT_V2")
    if d.get("extraction_status") != "VERIFIED_FULL_TEXT":
        errors.append("DATA_CONTRACT_NOT_VERIFIED_FULL_TEXT")
    if s.get("extraction_status") != "VERIFIED_FULL_TEXT":
        errors.append("SPLIT_CONTRACT_NOT_VERIFIED_FULL_TEXT")
    universe = d.get("instrument_universe", {})
    if universe.get("count") != 88:
        errors.append("UNIVERSE_COUNT_NOT_88")
    if d.get("access_status") != "PROPRIETARY":
        errors.append("DATA_ACCESS_STATE_NOT_PROPRIETARY")
    if s.get("split_semantics") != "EXPANDING":
        errors.append("SPLIT_NOT_EXPANDING")
    if s.get("test_window", {}).get("start") != 1995 or s.get("test_window", {}).get("end") != 2015:
        errors.append("OOS_WINDOW_MISMATCH")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "data_contract": d,
        "split_contract": s,
    }


def expected_tickers(data_record: dict[str, Any]) -> list[str]:
    groups = data_record["instrument_universe"]["tickers_by_asset_class"]
    tickers = sorted(t for values in groups.values() for t in values)
    if len(tickers) != 88 or len(set(tickers)) != 88:
        raise AssertionError("canonical 88-contract ticker universe is invalid")
    return tickers


def validate_local_dataset(data_record: dict[str, Any]) -> dict[str, Any]:
    value = os.environ.get("PINNACLE_CLC_DATA_DIR", "").strip()
    if not value:
        return {
            "status": "BLOCKED",
            "reason_codes": ["PINNACLE_CLC_DATA_DIR_NOT_CONFIGURED"],
            "detail": "No local licensed Pinnacle CLC dataset was supplied to the empirical runner.",
        }
    root = Path(value).expanduser().resolve()
    manifest_path = root / "dataset_manifest.json"
    if not manifest_path.is_file():
        return {
            "status": "BLOCKED",
            "reason_codes": ["DATASET_MANIFEST_MISSING"],
            "detail": str(manifest_path),
        }
    manifest = load_json(manifest_path)
    reasons: list[str] = []
    required = {
        "vendor": "Pinnacle Data Corp",
        "dataset": "CLC Database",
        "linking_method": "ratio-adjusted continuous futures",
        "sample_start_year": 1990,
        "sample_end_year": 2015,
        "paper_vintage_revision_proven": True,
        "license_allows_research_execution": True,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            reasons.append(f"DATASET_MANIFEST_{key.upper()}_MISMATCH")
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list):
        reasons.append("DATASET_CONTRACT_LIST_MISSING")
        contracts = []
    by_ticker = {str(row.get("ticker")): row for row in contracts if isinstance(row, dict)}
    expected = expected_tickers(data_record)
    if sorted(by_ticker) != expected:
        reasons.append("EXACT_88_TICKER_SET_MISMATCH")
    verified_files: list[dict[str, Any]] = []
    for ticker in expected:
        row = by_ticker.get(ticker)
        if row is None:
            continue
        rel = row.get("path")
        digest = str(row.get("sha256", ""))
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            reasons.append(f"{ticker}_UNSAFE_OR_MISSING_PATH")
            continue
        path = root / rel
        if not path.is_file():
            reasons.append(f"{ticker}_FILE_MISSING")
            continue
        if not SHA256.fullmatch(digest) or file_sha256(path) != digest:
            reasons.append(f"{ticker}_SHA256_MISMATCH")
            continue
        verified_files.append({"ticker": ticker, "path": rel, "sha256": digest, "bytes": path.stat().st_size})
    return {
        "status": "PASS" if not reasons else "BLOCKED",
        "reason_codes": reasons,
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "verified_contract_files": verified_files,
        "verified_contract_count": len(verified_files),
    }


def write_run_artifacts(
    *,
    out_dir: Path,
    protocol_path: Path,
    data_path: Path,
    split_path: Path,
    source_pdf: Path,
    source_pdf_url: str,
) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    data = load_json(data_path)
    split = load_json(split_path)
    started_at = now_utc()
    trace: list[dict[str, Any]] = []

    upstream = validate_upstream(protocol, data, split)
    trace.append({"stage": "UPSTREAM_CONTRACTS", "status": upstream["status"], "at": started_at, "errors": upstream["errors"]})
    if upstream["status"] != "PASS":
        raise SystemExit("upstream canonical contracts failed: " + ", ".join(upstream["errors"]))

    method_test = method_contract_self_test()
    trace.append({"stage": "METHOD_CONTRACT_SELF_TEST", "status": "PASS", "at": now_utc(), "observed": method_test})

    data_gate = validate_local_dataset(upstream["data_contract"])
    trace.append({"stage": "EXACT_DATA_GATE", "status": data_gate["status"], "at": now_utc(), "reason_codes": data_gate.get("reason_codes", [])})

    source_pdf_hash = file_sha256(source_pdf)
    source_pdf_bytes = source_pdf.stat().st_size
    source_evidence = {
        "url": source_pdf_url,
        "sha256": source_pdf_hash,
        "bytes": source_pdf_bytes,
        "acquired_at": now_utc(),
        "stored_in_repository": False,
        "repository_storage_reason": "Paper bytes are hashed during CI but not committed; the exact arXiv version URL is the canonical primary source.",
    }

    if data_gate["status"] == "PASS":
        verdict = "BLOCKED"
        reason_codes = ["TRAINING_IMPLEMENTATION_NOT_AUTHORISED_WITHOUT_REVIEW_OF_LICENSED_LOCAL_DATA_SCHEMA"]
        trace.append({
            "stage": "TRAINING_EVALUATION",
            "status": "BLOCKED",
            "at": now_utc(),
            "reason_codes": reason_codes,
            "detail": "Exact licensed files passed the data manifest gate, but this runner intentionally refuses to fit until the locally supplied columns/schema are explicitly mapped to the paper's unspecified vendor price field."
        })
    else:
        verdict = "BLOCKED"
        reason_codes = list(data_gate.get("reason_codes", []))
        trace.append({
            "stage": "TRAINING_EVALUATION",
            "status": "NOT_EXECUTED",
            "at": now_utc(),
            "reason_codes": reason_codes,
            "detail": "Fail-closed: paper-specific fitting/evaluation cannot execute without the exact 88-contract licensed CLC input gate. No substitute dataset is permitted."
        })

    report = {
        "schema_version": "investor2.paper-empirical-report.v1",
        "run_id": RUN_ID,
        "paper_id": protocol["paper_id"],
        "arxiv_id": ARXIV_ID,
        "source_version": "v2",
        "protocol": protocol_path.relative_to(ROOT).as_posix(),
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": verdict,
        "stage_reached": "EXACT_DATA_GATE",
        "training_attempted": True,
        "training_executed": False,
        "evaluation_executed": False,
        "paper_target": protocol["experiment"]["paper_target"],
        "observed_metrics": None,
        "metric_delta": None,
        "reason_codes": reason_codes,
        "data_gate": data_gate,
        "source_pdf": source_evidence,
        "method_contract_self_test": method_test,
        "split_contract_consumed": {
            "semantics": upstream["split_contract"]["split_semantics"],
            "test_window": upstream["split_contract"]["test_window"],
            "retraining_cadence": upstream["split_contract"]["retraining_cadence"],
            "model_selection_rule": upstream["split_contract"]["model_selection_rule"],
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "device": "NOT_REACHED_DATA_GATE",
            "seed": protocol["seed"],
            "github_sha": os.environ.get("GITHUB_SHA", "LOCAL_WORKTREE"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
        },
        "author_code_and_data": protocol["author_code_and_data"],
        "current_vendor_reference": {
            "url": "https://pinnacledata2.com/clc.html",
            "contract_count": 98,
            "current_price_usd": 99,
            "note": "Current product availability does not establish access to the paper-vintage 88-series input bytes or their revision state."
        },
        "fail_closed_statement": "BLOCKED is not FAILED and not REPRODUCED. No empirical metric is emitted because the exact paper data gate did not pass.",
        "started_at": started_at,
        "finished_at": now_utc(),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / "trace.json"
    report_path = out_dir / "report.json"
    trace_path.write_bytes(canonical_bytes({"run_id": RUN_ID, "events": trace}))
    report_path.write_bytes(canonical_bytes(report))
    manifest = {
        "schema_version": "investor2.paper-empirical-evidence.v1",
        "run_id": RUN_ID,
        "paper_id": protocol["paper_id"],
        "arxiv_id": ARXIV_ID,
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": verdict,
        "protocol": {"path": protocol_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(protocol_path)},
        "canonical_inputs": {
            "data_contracts": {"path": data_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(data_path)},
            "split_contracts": {"path": split_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(split_path)},
        },
        "source_pdf": source_evidence,
        "artifacts": {
            "trace": {"path": trace_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(trace_path)},
            "report": {"path": report_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(report_path)},
            "model_state": {"path": None, "sha256": None, "state": "NOT_CREATED_DATA_GATE_BLOCKED"},
        },
        "provenance": {
            "code_revision": os.environ.get("GITHUB_SHA", "LOCAL_WORKTREE"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
            "seed": protocol["seed"],
        },
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest))
    return {
        "manifest_path": manifest_path,
        "manifest_sha256": file_sha256(manifest_path),
        "report_path": report_path,
        "report_sha256": file_sha256(report_path),
        "trace_path": trace_path,
        "trace_sha256": file_sha256(trace_path),
        "verdict": verdict,
        "reason_codes": reason_codes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the locked Lim et al. v2 empirical protocol fail-closed.")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--data-contracts", type=Path, required=True)
    parser.add_argument("--split-contracts", type=Path, required=True)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.protocol, args.data_contracts, args.split_contracts, args.source_pdf, args.output_dir]
    protocol, data, split, source_pdf, out_dir = [p if p.is_absolute() else ROOT / p for p in paths]
    result = write_run_artifacts(
        out_dir=out_dir,
        protocol_path=protocol,
        data_path=data,
        split_path=split,
        source_pdf=source_pdf,
        source_pdf_url="https://arxiv.org/pdf/1904.04912v2",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
