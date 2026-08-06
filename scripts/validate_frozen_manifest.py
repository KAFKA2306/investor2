#!/usr/bin/env python3
"""Fail-closed validation for frozen dataset split manifests."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_TOP_LEVEL = {"schema_version", "split_id", "source", "policy", "contract"}


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - data.keys())
    if missing:
        errors.append(f"missing top-level keys: {', '.join(missing)}")
        return errors

    if data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if not isinstance(data["split_id"], str) or not data["split_id"].strip():
        errors.append("split_id must be a non-empty string")

    source = data["source"]
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        for key in ("dataset", "config", "split", "revision", "parquet_path", "sha256", "row_count"):
            if key not in source:
                errors.append(f"source.{key} is required")
        if "revision" in source and not REVISION_RE.fullmatch(str(source["revision"])):
            errors.append("source.revision must be a full 40-character git commit SHA")
        if "sha256" in source and not SHA256_RE.fullmatch(str(source["sha256"])):
            errors.append("source.sha256 must be a lowercase SHA-256 digest")
        if "row_count" in source and (not isinstance(source["row_count"], int) or source["row_count"] <= 0):
            errors.append("source.row_count must be a positive integer")

    policy = data["policy"]
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        fraction = policy.get("evaluation_fraction")
        if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 < fraction < 1:
            errors.append("policy.evaluation_fraction must be between 0 and 1")
        if not isinstance(policy.get("seed"), int):
            errors.append("policy.seed must be an integer")
        for key in ("algorithm", "id_column", "group_column"):
            if not isinstance(policy.get(key), str) or not policy[key].strip():
                errors.append(f"policy.{key} must be a non-empty string")

    contract = data["contract"]
    if not isinstance(contract, dict):
        errors.append("contract must be an object")
    elif contract.get("source_change_policy") != "fail_closed":
        errors.append("contract.source_change_policy must be fail_closed")

    return errors


def validate_file(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    errors = validate_manifest(data)
    return {
        "audit_schema_version": 1,
        "manifest": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "split_id": data.get("split_id"),
        "errors": errors,
        "error_count": len(errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        report = validate_file(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {"audit_schema_version": 1, "manifest": str(args.manifest), "errors": [str(exc)], "error_count": 1}

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
