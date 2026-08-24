#!/usr/bin/env python3
"""Empirically audit factor results against an historical Kenneth French data cut.

This job deliberately uses the July 2020 Kenneth French historical archive,
released in August 2020, instead of today's revised factor history. It also
reconstructs factor returns from the archived 2x3 portfolio legs before
re-running the repository's locked statistical gates.

Important scope boundary: Kenneth French's public archive exposes factor and
portfolio return vintages, not the security identifiers/weights or historical
stock-loan inventory required for a security-level PIT/borrow reconstruction.
This script therefore proves vintage robustness at the factor/portfolio level
and refuses to label security-level or borrow evidence as completed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
import urllib.request
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T_HURDLE = 3.0
VINTAGE = "2020-08"
VINTAGE_DATA_CUT = "2020-07"
BASE = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "Data_Library/Historical_Archives/08%202020%20Update/ftp/"
)
SOURCES = {
    "ff3": BASE + "F-F_Research_Data_Factors_CSV.zip",
    "ff5": BASE + "F-F_Research_Data_5_Factors_2x3_CSV.zip",
    "bm_2x3": BASE + "6_Portfolios_2x3_CSV.zip",
    "op_2x3": BASE + "6_Portfolios_ME_OP_2x3_CSV.zip",
    "inv_2x3": BASE + "6_Portfolios_ME_INV_2x3_CSV.zip",
}
ARCHIVE_PAGES = {
    "ff3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors_archive.html",
    "ff5": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3_archive.html",
    "bm_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_archive.html",
    "op_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_me_op_archive.html",
    "inv_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_me_inv_archive.html",
}
METHOD_PAGES = {
    "ff3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html",
    "ff5": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html",
    "bm_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios.html",
    "op_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_me_op.html",
    "inv_2x3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/six_portfolios_me_inv.html",
}


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def download_zip_csv(url: str) -> tuple[str, str, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "investor2-research-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_members = [
            name for name in archive.namelist() if name.lower().endswith(".csv")
        ]
        if len(csv_members) != 1:
            raise ValueError(f"expected one CSV in {url}, got {csv_members}")
        member = csv_members[0]
        raw = archive.read(member)
    text = raw.decode("utf-8-sig", errors="replace")
    return text, digest, member


def parse_first_monthly_table(
    text: str,
) -> tuple[list[str], dict[str, list[float]]]:
    rows = list(csv.reader(io.StringIO(text)))
    header_index: int | None = None
    for index in range(len(rows) - 1):
        header = [cell.strip() for cell in rows[index]]
        following = [cell.strip() for cell in rows[index + 1]]
        if (
            header
            and header[0] == ""
            and len(header) >= 3
            and following
            and len(following[0]) == 6
            and following[0].isdigit()
        ):
            header_index = index
            break
    if header_index is None:
        raise ValueError("could not locate first monthly table")

    header = [cell.strip() for cell in rows[header_index]]
    data: dict[str, list[float]] = {}
    for row in rows[header_index + 1 :]:
        cells = [cell.strip() for cell in row]
        if not cells or len(cells[0]) != 6 or not cells[0].isdigit():
            break
        if len(cells) < len(header):
            raise ValueError(f"short row for {cells[0]}")
        month = f"{cells[0][:4]}-{cells[0][4:6]}"
        values = [float(value) / 100.0 for value in cells[1 : len(header)]]
        data[month] = values
    if not data:
        raise ValueError("monthly table contains no data")
    return header[1:], data


def normalized_header(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def factor_series(
    header: list[str], data: dict[str, list[float]], factor: str
) -> list[tuple[str, float]]:
    normalized = [normalized_header(value) for value in header]
    key = normalized_header(factor)
    try:
        position = normalized.index(key)
    except ValueError as error:
        raise ValueError(f"factor {factor!r} not found in {header}") from error
    return [(month, values[position]) for month, values in sorted(data.items())]


def six_portfolio_components(
    header: list[str], data: dict[str, list[float]]
) -> dict[str, list[float]]:
    if len(header) != 6:
        raise ValueError(f"expected six portfolio columns, got {header}")
    if any(len(values) != 6 for values in data.values()):
        raise ValueError("portfolio table contains a row that is not six-wide")
    return data


def avg(values: list[float]) -> float:
    return sum(values) / len(values)


def reconstruct_from_2x3(
    bm: dict[str, list[float]],
    op: dict[str, list[float]],
    inv: dict[str, list[float]],
) -> dict[str, dict[str, float]]:
    months = sorted(set(bm) & set(op) & set(inv))
    output: dict[str, dict[str, float]] = {}
    for month in months:
        bm_row = bm[month]
        op_row = op[month]
        inv_row = inv[month]
        smb_bm = avg(bm_row[:3]) - avg(bm_row[3:])
        smb_op = avg(op_row[:3]) - avg(op_row[3:])
        smb_inv = avg(inv_row[:3]) - avg(inv_row[3:])
        output[month] = {
            "ff3_smb": smb_bm,
            "ff3_hml": avg([bm_row[2], bm_row[5]])
            - avg([bm_row[0], bm_row[3]]),
            "ff5_smb": avg([smb_bm, smb_op, smb_inv]),
            "ff5_hml": avg([bm_row[2], bm_row[5]])
            - avg([bm_row[0], bm_row[3]]),
            "ff5_rmw": avg([op_row[2], op_row[5]])
            - avg([op_row[0], op_row[3]]),
            "ff5_cma": avg([inv_row[0], inv_row[3]])
            - avg([inv_row[2], inv_row[5]]),
        }
    return output


def reconstruction_audit(
    reconstructed: dict[str, dict[str, float]],
    ff3_header: list[str],
    ff3_data: dict[str, list[float]],
    ff5_header: list[str],
    ff5_data: dict[str, list[float]],
) -> dict[str, Any]:
    targets = {
        "ff3_smb": (ff3_header, ff3_data, "SMB"),
        "ff3_hml": (ff3_header, ff3_data, "HML"),
        "ff5_smb": (ff5_header, ff5_data, "SMB"),
        "ff5_hml": (ff5_header, ff5_data, "HML"),
        "ff5_rmw": (ff5_header, ff5_data, "RMW"),
        "ff5_cma": (ff5_header, ff5_data, "CMA"),
    }
    result: dict[str, Any] = {}
    for name, (header, data, factor) in targets.items():
        official = dict(factor_series(header, data, factor))
        common = sorted(set(reconstructed) & set(official))
        errors_bps = [
            10_000.0 * (reconstructed[month][name] - official[month])
            for month in common
        ]
        max_abs = max(abs(value) for value in errors_bps)
        result[name] = {
            "months": len(common),
            "start": common[0],
            "end": common[-1],
            "max_abs_rounding_error_bps": max_abs,
            "mean_abs_rounding_error_bps": sum(abs(value) for value in errors_bps)
            / len(errors_bps),
            "pass_within_3bps_rounding_tolerance": max_abs <= 3.0 + 1e-12,
        }
    return result


def gate_snapshot(full: Any, late: Any, cost_25: Any) -> dict[str, bool]:
    ci = full.block_bootstrap_95pct_mean_ci
    return {
        "t_stat_ge_3": full.newey_west_t_stat_lag_6 >= T_HURDLE,
        "block_bootstrap_lower_gt_0": ci is not None and ci[0] > 0.0,
        "late_period_mean_gt_0": late.annualized_arithmetic_mean > 0.0,
        "after_25bps_monthly_haircut_gt_0": (
            cost_25.annualized_arithmetic_mean > 0.0
        ),
    }


def empirical_studies(
    suite: Any,
    registry: dict[str, Any],
    ff3_header: list[str],
    ff3_data: dict[str, list[float]],
    ff5_header: list[str],
    ff5_data: dict[str, list[float]],
) -> dict[str, Any]:
    archive_by_dataset = {
        "ff3_1992_2020": (ff3_header, ff3_data),
        "ff5_2015_2020": (ff5_header, ff5_data),
    }
    current = suite.build_report(ROOT / "docs/research/frontier/paper_factor_registry.json")
    studies: dict[str, Any] = {}
    for study in registry["studies"]:
        archive_header, archive_data = archive_by_dataset[study["dataset"]]
        factor = study["column"].removesuffix("_percent").upper()
        rows = suite.select(
            factor_series(archive_header, archive_data, factor),
            study["oos_start"],
            study["oos_end"],
        )
        split = len(rows) // 2
        full = suite.calculate_metrics(rows, bootstrap_seed=2306)
        late = suite.calculate_metrics(rows[split:], bootstrap_seed=2306)
        cost_25 = suite.calculate_metrics(
            suite.subtract_monthly_cost(rows, 25), bootstrap=False
        )
        gates = gate_snapshot(full, late, cost_25)

        current_study = current["studies"][study["id"]]
        current_full = current_study["gross_results"]["full_oos"]
        current_late = current_study["gross_results"]["late_half"]
        current_cost = current_study["monthly_haircut_sensitivity_bps"]["25"]
        current_gates = {
            "t_stat_ge_3": current_full["newey_west_t_stat_lag_6"] >= T_HURDLE,
            "block_bootstrap_lower_gt_0": (
                current_full["block_bootstrap_95pct_mean_ci"] is not None
                and current_full["block_bootstrap_95pct_mean_ci"][0] > 0.0
            ),
            "late_period_mean_gt_0": current_late["annualized_arithmetic_mean"]
            > 0.0,
            "after_25bps_monthly_haircut_gt_0": current_cost[
                "annualized_arithmetic_mean"
            ]
            > 0.0,
        }
        studies[study["id"]] = {
            "paper": study["paper"],
            "implementation": study["implementation"],
            "factor": factor,
            "oos_window": [study["oos_start"], study["oos_end"]],
            "vintage_metrics": {
                "full_oos": asdict(full),
                "late_half": asdict(late),
                "after_25bps_monthly_haircut": asdict(cost_25),
            },
            "locked_statistical_gates": gates,
            "current_snapshot_gates": current_gates,
            "gate_result_changed_by_vintage": gates != current_gates,
            "strategy_state_from_tested_statistical_gates": (
                "REJECTED" if not all(gates.values()) else "NO_STATISTICAL_REJECTION"
            ),
            "point_in_time_factor_vintage": "PASS",
            "point_in_time_security_level_rebuild": (
                "NOT_EVALUATED_NO_SECURITY_LEVEL_PUBLIC_ARCHIVE"
            ),
            "historical_borrow_availability_and_cost": (
                "NOT_EVALUATED_NO_BORROW_DATA_IN_SOURCE"
            ),
        }
    return studies


def build_report() -> dict[str, Any]:
    suite = load_module(
        ROOT / "scripts" / "verify_paper_factor_suite.py",
        "factor_suite_for_vintage_audit",
    )
    registry = json.loads(
        (ROOT / "docs/research/frontier/paper_factor_registry.json").read_text(encoding="utf-8")
    )

    downloaded: dict[str, dict[str, Any]] = {}
    tables: dict[str, tuple[list[str], dict[str, list[float]]]] = {}
    for source_id, url in SOURCES.items():
        text, digest, member = download_zip_csv(url)
        header, data = parse_first_monthly_table(text)
        tables[source_id] = (header, data)
        downloaded[source_id] = {
            "url": url,
            "archive_page": ARCHIVE_PAGES[source_id],
            "method_page": METHOD_PAGES[source_id],
            "sha256": digest,
            "zip_member": member,
            "first_month": min(data),
            "last_month": max(data),
            "columns": header,
        }

    bm = six_portfolio_components(*tables["bm_2x3"])
    op = six_portfolio_components(*tables["op_2x3"])
    inv = six_portfolio_components(*tables["inv_2x3"])
    reconstructed = reconstruct_from_2x3(bm, op, inv)
    reconstruction = reconstruction_audit(
        reconstructed,
        *tables["ff3"],
        *tables["ff5"],
    )
    studies = empirical_studies(
        suite,
        registry,
        *tables["ff3"],
        *tables["ff5"],
    )

    reconstruction_pass = all(
        item["pass_within_3bps_rounding_tolerance"]
        for item in reconstruction.values()
    )
    changed = [
        study_id
        for study_id, result in studies.items()
        if result["gate_result_changed_by_vintage"]
    ]
    rejected = [
        study_id
        for study_id, result in studies.items()
        if result["strategy_state_from_tested_statistical_gates"] == "REJECTED"
    ]
    return {
        "schema_version": 1,
        "audit": "kenneth_french_historical_vintage_empirical_audit",
        "vintage_release": VINTAGE,
        "vintage_data_cut": VINTAGE_DATA_CUT,
        "method": {
            "purpose": (
                "Re-run repository factor hypotheses on a historical data release and "
                "independently reconstruct factors from the archived 2x3 portfolio legs."
            ),
            "statistical_policy": (
                "Repository promotion hurdle Newey-West t >= 3.0 plus existing "
                "bootstrap, late-period, and 25 bps/month gates."
            ),
            "security_level_scope": (
                "Not claimed. Public Kenneth French historical archives contain "
                "factor/portfolio return vintages but not the underlying security "
                "identifiers and weights."
            ),
            "borrow_scope": (
                "Not claimed. These archives contain no date-indexed shortability, "
                "locate inventory, or borrow fee observations."
            ),
        },
        "sources": downloaded,
        "portfolio_leg_reconstruction": reconstruction,
        "repository_factor_studies": studies,
        "summary": {
            "factor_studies_retested": len(studies),
            "rejected_on_tested_statistical_gates": len(rejected),
            "rejected_ids": rejected,
            "gate_results_changed_vs_repository_snapshot": changed,
            "portfolio_leg_reconstruction_pass": reconstruction_pass,
            "security_level_pit_completed": 0,
            "historical_borrow_completed": 0,
        },
    }


def validate(report: dict[str, Any]) -> None:
    """Validate audit mechanics, never an expected empirical conclusion."""
    summary = report["summary"]
    if summary["factor_studies_retested"] != 7:
        raise ValueError("expected seven registry studies to be evaluated")
    if not summary["portfolio_leg_reconstruction_pass"]:
        raise ValueError("factor reconstruction does not match archived factor files")
    for study_id, result in report["repository_factor_studies"].items():
        if result["point_in_time_factor_vintage"] != "PASS":
            raise ValueError(f"{study_id}: historical factor vintage was not evaluated")
        if set(result["locked_statistical_gates"]) != {
            "t_stat_ge_3",
            "block_bootstrap_lower_gt_0",
            "late_period_mean_gt_0",
            "after_25bps_monthly_haircut_gt_0",
        }:
            raise ValueError(f"{study_id}: incomplete statistical gate output")


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
    print(json.dumps(report["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
