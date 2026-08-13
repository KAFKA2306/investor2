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
RUN_ID = "zhang_1911_10107_v1_dqn_table2_seed2306"
ARXIV_ID = "1911.10107"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACTIONS = {-1, 0, 1}


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


def paper_reward(
    *,
    action_t_minus_1: int,
    action_t_minus_2: int,
    sigma_target: float,
    sigma_t_minus_1: float,
    sigma_t_minus_2: float,
    additive_return_t: float,
    price_t_minus_1: float,
    cost_rate: float,
    mu: float = 1.0,
) -> float:
    if action_t_minus_1 not in ACTIONS or action_t_minus_2 not in ACTIONS:
        raise ValueError("DQN actions must be one of {-1,0,1}")
    if min(sigma_target, sigma_t_minus_1, sigma_t_minus_2) <= 0:
        raise ValueError("volatilities must be positive")
    if price_t_minus_1 <= 0 or cost_rate < 0 or mu <= 0:
        raise ValueError("price, cost rate and mu must be valid")
    scaled_current = sigma_target / sigma_t_minus_1 * action_t_minus_1
    scaled_previous = sigma_target / sigma_t_minus_2 * action_t_minus_2
    gross = scaled_current * additive_return_t
    cost = cost_rate * price_t_minus_1 * abs(scaled_current - scaled_previous)
    return mu * (gross - cost)


def sign_return_baseline(current_price: float, price_252_days_ago: float) -> int:
    delta = current_price - price_252_days_ago
    return 1 if delta > 0 else -1 if delta < 0 else 0


def method_contract_self_test() -> dict[str, Any]:
    sigma_target = 0.02  # synthetic self-test only; the pinned paper does not specify the calibrated numeric target.
    gross = paper_reward(
        action_t_minus_1=1,
        action_t_minus_2=0,
        sigma_target=sigma_target,
        sigma_t_minus_1=0.01,
        sigma_t_minus_2=0.01,
        additive_return_t=2.0,
        price_t_minus_1=1000.0,
        cost_rate=0.0,
    )
    net = paper_reward(
        action_t_minus_1=1,
        action_t_minus_2=0,
        sigma_target=sigma_target,
        sigma_t_minus_1=0.01,
        sigma_t_minus_2=0.01,
        additive_return_t=2.0,
        price_t_minus_1=1000.0,
        cost_rate=0.0020,
    )
    expected_cost = 0.0020 * 1000.0 * abs(2.0 - 0.0)
    if not math.isclose(gross - net, expected_cost, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError("Equation 4 turnover-cost contract failed")
    if not math.isclose(0.0020 / 0.0001, 20.0, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError("paper bp definition failed")
    if sign_return_baseline(110.0, 100.0) != 1 or sign_return_baseline(90.0, 100.0) != -1:
        raise AssertionError("Sign(R) 252-day baseline contract failed")
    return {
        "status": "PASS",
        "synthetic_sigma_target": sigma_target,
        "synthetic_sigma_target_scope": "SELF_TEST_ONLY_NOT_PAPER_CALIBRATION",
        "gross_reward_sample": gross,
        "cost_adjusted_reward_sample": net,
        "turnover_cost_sample": expected_cost,
        "paper_training_cost_rate": 0.0020,
        "paper_training_cost_basis_points": 20.0,
        "discrete_actions": sorted(ACTIONS),
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
    if protocol.get("source_version") != "v1" or d.get("selected_version") != "v1" or s.get("selected_version") != "v1":
        errors.append("EXACT_VERSION_NOT_V1")
    if d.get("extraction_status") != "VERIFIED_FULL_TEXT":
        errors.append("DATA_CONTRACT_NOT_VERIFIED_FULL_TEXT")
    if s.get("extraction_status") != "VERIFIED_FULL_TEXT":
        errors.append("SPLIT_CONTRACT_NOT_VERIFIED_FULL_TEXT")
    universe = d.get("instrument_universe", {})
    if universe.get("count") != 50:
        errors.append("UNIVERSE_COUNT_NOT_50")
    if d.get("access_status") != "PROPRIETARY":
        errors.append("DATA_ACCESS_STATE_NOT_PROPRIETARY")
    if s.get("split_semantics") != "EXPANDING":
        errors.append("SPLIT_NOT_EXPANDING")
    if s.get("test_window", {}).get("start") != 2011 or s.get("test_window", {}).get("end") != 2019:
        errors.append("OOS_WINDOW_MISMATCH")
    if s.get("model_selection_rule") != "NOT_SPECIFIED":
        errors.append("MODEL_SELECTION_SHOULD_REMAIN_NOT_SPECIFIED")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "data_contract": d,
        "split_contract": s,
    }


def expected_tickers(data_record: dict[str, Any]) -> list[str]:
    groups = data_record["instrument_universe"]["tickers_by_asset_class"]
    tickers = sorted(t for values in groups.values() for t in values)
    if len(tickers) != 50 or len(set(tickers)) != 50:
        raise AssertionError("canonical 50-contract ticker universe is invalid")
    return tickers


def validate_local_dataset(data_record: dict[str, Any]) -> dict[str, Any]:
    value = os.environ.get("PINNACLE_CLC_DATA_DIR", "").strip()
    if not value:
        return {
            "status": "BLOCKED",
            "reason_codes": ["PINNACLE_CLC_DATA_DIR_NOT_CONFIGURED"],
            "detail": "No licensed paper-vintage Pinnacle CLC dataset was supplied to the empirical runner.",
        }
    root = Path(value).expanduser().resolve()
    manifest_path = root / "dataset_manifest.json"
    if not manifest_path.is_file():
        return {"status": "BLOCKED", "reason_codes": ["DATASET_MANIFEST_MISSING"], "detail": str(manifest_path)}
    manifest = load_json(manifest_path)
    reasons: list[str] = []
    required = {
        "vendor": "Pinnacle Data Corp",
        "dataset": "CLC Database",
        "linking_method": "ratio-adjusted continuous futures",
        "sample_start_year": 2005,
        "sample_end_year": 2019,
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
    tickers = expected_tickers(data_record)
    if sorted(by_ticker) != tickers:
        reasons.append("EXACT_50_TICKER_SET_MISMATCH")
    verified: list[dict[str, Any]] = []
    for ticker in tickers:
        row = by_ticker.get(ticker)
        if row is None:
            continue
        rel = row.get("path")
        claimed = str(row.get("sha256", ""))
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            reasons.append(f"{ticker}_UNSAFE_OR_MISSING_PATH")
            continue
        path = root / rel
        if not path.is_file():
            reasons.append(f"{ticker}_FILE_MISSING")
            continue
        if not SHA256.fullmatch(claimed) or file_sha256(path) != claimed:
            reasons.append(f"{ticker}_SHA256_MISMATCH")
            continue
        verified.append({"ticker": ticker, "path": rel, "sha256": claimed, "bytes": path.stat().st_size})
    return {
        "status": "PASS" if not reasons else "BLOCKED",
        "reason_codes": reasons,
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "verified_contract_files": verified,
        "verified_contract_count": len(verified),
    }


def write_run_artifacts(*, out_dir: Path, protocol_path: Path, data_path: Path, split_path: Path, source_pdf: Path) -> dict[str, Any]:
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

    source_evidence = {
        "url": "https://arxiv.org/pdf/1911.10107v1",
        "sha256": file_sha256(source_pdf),
        "bytes": source_pdf.stat().st_size,
        "acquired_at": now_utc(),
        "stored_in_repository": False,
        "repository_storage_reason": "Exact arXiv bytes are hashed during CI but not committed; the pinned version URL is the primary source.",
    }

    if data_gate["status"] != "PASS":
        reason_codes = list(data_gate.get("reason_codes", []))
        training_detail = "Fail-closed: DQN fitting/evaluation cannot execute without the exact licensed 50-contract CLC data gate. No substitute dataset is permitted."
    else:
        reason_codes = [
            "NUMERIC_VOLATILITY_TARGET_NOT_SPECIFIED_IN_PINNED_PAPER",
            "EXACT_VENDOR_PRICE_FIELD_NOT_SPECIFIED_BY_PINNED_PAPER",
            "VALIDATION_AND_MODEL_SELECTION_PROTOCOL_NOT_SPECIFIED"
        ]
        training_detail = "Licensed files passed the data gate, but the pinned paper leaves the numeric volatility target, exact vendor price field, and validation/model-selection protocol unspecified; fitting remains blocked rather than inventing them."
    trace.append({"stage": "TRAINING_EVALUATION", "status": "NOT_EXECUTED", "at": now_utc(), "reason_codes": reason_codes, "detail": training_detail})

    report = {
        "schema_version": "investor2.paper-empirical-report.v1",
        "run_id": RUN_ID,
        "paper_id": protocol["paper_id"],
        "arxiv_id": ARXIV_ID,
        "source_version": "v1",
        "protocol": protocol_path.relative_to(ROOT).as_posix(),
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": "BLOCKED",
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
            "validation_window": upstream["split_contract"]["validation_window"],
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
            "note": "Current commercial availability does not establish access to the paper-vintage 50-series bytes or their revision state."
        },
        "fail_closed_statement": "BLOCKED is neither FAILED nor REPRODUCED. No empirical metric is emitted because required exact evidence did not pass its gate.",
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
        "empirical_verdict": "BLOCKED",
        "protocol": {"path": protocol_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(protocol_path)},
        "canonical_inputs": {
            "data_contracts": {"path": data_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(data_path)},
            "split_contracts": {"path": split_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(split_path)},
        },
        "source_pdf": source_evidence,
        "artifacts": {
            "trace": {"path": trace_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(trace_path)},
            "report": {"path": report_path.relative_to(ROOT).as_posix(), "sha256": file_sha256(report_path)},
            "model_state": {"path": None, "sha256": None, "state": "NOT_CREATED_EVIDENCE_GATE_BLOCKED"},
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
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": file_sha256(manifest_path),
        "report_sha256": file_sha256(report_path),
        "trace_sha256": file_sha256(trace_path),
        "verdict": "BLOCKED",
        "reason_codes": reason_codes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the locked Zhang et al. v1 DQN empirical protocol fail-closed.")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--data-contracts", type=Path, required=True)
    parser.add_argument("--split-contracts", type=Path, required=True)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    protocol = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    data = args.data_contracts if args.data_contracts.is_absolute() else ROOT / args.data_contracts
    split = args.split_contracts if args.split_contracts.is_absolute() else ROOT / args.split_contracts
    source_pdf = args.source_pdf if args.source_pdf.is_absolute() else ROOT / args.source_pdf
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    result = write_run_artifacts(out_dir=out_dir, protocol_path=protocol, data_path=data, split_path=split, source_pdf=source_pdf)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
