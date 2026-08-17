#!/usr/bin/env python3
"""Compare a pinned Kenneth French historical vintage with the current official files.

The comparison is deliberately revision-aware: it downloads the official July 2020
archive and the current Kenneth French FF3/FF5 CSV ZIPs, hashes both ZIP payloads,
compares only overlapping monthly observations, and reports per-factor revision
statistics. It does not merge vintages or silently rewrite the repository registry.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts" / "audit_french_factor_vintages.py"
CURRENT_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
ARCHIVE_BASE = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "Data_Library/Historical_Archives/08%202020%20Update/ftp/"
)
DATASETS = {
    "ff3": {
        "filename": "F-F_Research_Data_Factors_CSV.zip",
        "factors": ["Mkt-RF", "SMB", "HML", "RF"],
    },
    "ff5": {
        "filename": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "factors": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
    },
}


def load_audit_module() -> Any:
    spec = importlib.util.spec_from_file_location("factor_vintage_audit", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare_series(
    old: list[tuple[str, float]], new: list[tuple[str, float]]
) -> dict[str, Any]:
    old_map = dict(old)
    new_map = dict(new)
    common = sorted(set(old_map) & set(new_map))
    if not common:
        raise ValueError("no overlapping observations")
    deltas_bps = [10_000.0 * (new_map[m] - old_map[m]) for m in common]
    changed = [value for value in deltas_bps if abs(value) > 1e-12]
    return {
        "months": len(common),
        "start": common[0],
        "end": common[-1],
        "changed_months": len(changed),
        "changed_share": len(changed) / len(common),
        "mean_revision_bps": sum(deltas_bps) / len(deltas_bps),
        "mean_abs_revision_bps": sum(abs(v) for v in deltas_bps) / len(deltas_bps),
        "max_abs_revision_bps": max(abs(v) for v in deltas_bps),
    }


def dataset_report(audit: Any, dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    filename = spec["filename"]
    archive_url = ARCHIVE_BASE + filename
    current_url = CURRENT_BASE + filename

    old_text, old_hash, old_member = audit.download_zip_csv(archive_url)
    new_text, new_hash, new_member = audit.download_zip_csv(current_url)
    old_header, old_data = audit.parse_first_monthly_table(old_text)
    new_header, new_data = audit.parse_first_monthly_table(new_text)

    factors: dict[str, Any] = {}
    for factor in spec["factors"]:
        factors[factor] = compare_series(
            audit.factor_series(old_header, old_data, factor),
            audit.factor_series(new_header, new_data, factor),
        )

    return {
        "dataset": dataset_id,
        "archive": {
            "vintage_release": "2020-08",
            "data_cut": "2020-07",
            "url": archive_url,
            "sha256_zip": old_hash,
            "zip_member": old_member,
            "first_month": min(old_data),
            "last_month": max(old_data),
        },
        "current": {
            "url": current_url,
            "sha256_zip": new_hash,
            "zip_member": new_member,
            "first_month": min(new_data),
            "last_month": max(new_data),
        },
        "overlap_revision": factors,
    }


def build_report() -> dict[str, Any]:
    audit = load_audit_module()
    datasets = {
        dataset_id: dataset_report(audit, dataset_id, spec)
        for dataset_id, spec in DATASETS.items()
    }
    return {
        "schema_version": 1,
        "audit": "kenneth_french_current_vs_2020_revision_audit",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source_authority": "Kenneth R. French Data Library",
        "comparison_policy": (
            "Compare official current files with the pinned July-2020 historical "
            "archive on overlapping months only; do not blend vintages."
        ),
        "datasets": datasets,
    }


def validate(report: dict[str, Any]) -> None:
    if set(report["datasets"]) != {"ff3", "ff5"}:
        raise ValueError("expected FF3 and FF5")
    for dataset in report["datasets"].values():
        if dataset["archive"]["sha256_zip"] == dataset["current"]["sha256_zip"]:
            raise ValueError("current and historical ZIP hashes unexpectedly match")
        for factor, comparison in dataset["overlap_revision"].items():
            if comparison["months"] <= 0:
                raise ValueError(f"{factor}: no overlap")
            if not 0.0 <= comparison["changed_share"] <= 1.0:
                raise ValueError(f"{factor}: invalid changed share")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    validate(report)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
