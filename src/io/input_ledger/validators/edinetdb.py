from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from src.io.input_ledger.common import canonical_json_sha256


def _close(actual: float, expected: float, *, rel_tol: float = 1e-9) -> bool:
    return math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=1e-12)


def audit_edinetdb_annual_financials(
    entry: Mapping[str, Any],
    _source_config: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    artifact_path = root / str(entry["artifact_path"])
    snapshot = json.loads(artifact_path.read_text(encoding="utf-8"))
    records = snapshot["records"]

    if snapshot["schema_version"] != entry["schema_version"]:
        raise AssertionError("schema version mismatch")
    if snapshot["observed_at"] != entry["observed_at"]:
        raise AssertionError("observed_at mismatch")
    if snapshot["company"] != entry["company"]:
        raise AssertionError("company identity mismatch")
    if snapshot["period"] != entry["period"]:
        raise AssertionError("period metadata mismatch")
    if len(records) != entry["period"]["rows"]:
        raise AssertionError("row-count mismatch")

    years = [row["fiscalYear"] for row in records]
    expected_years = list(range(entry["period"]["from_fiscal_year"], entry["period"]["to_fiscal_year"] + 1))
    if years != expected_years:
        raise AssertionError(f"non-contiguous or misordered fiscal years: {years}")
    if len(years) != len(set(years)):
        raise AssertionError("duplicate fiscal year")

    doc_ids = [row["docID"] for row in records]
    if len(doc_ids) != len(set(doc_ids)):
        raise AssertionError("duplicate EDINET docID")

    required = {
        "fiscalYear",
        "revenue",
        "netIncome",
        "roeOfficial",
        "equityRatioOfficial",
        "cfOperating",
        "cfInvesting",
        "docID",
        "edinetFilingUrl",
    }
    for row in records:
        missing = sorted(key for key in required if row.get(key) is None)
        if missing:
            raise AssertionError(f"missing required fields in FY{row.get('fiscalYear')}: {missing}")
        if not row["edinetFilingUrl"].startswith("https://disclosure2.edinet-fsa.go.jp/"):
            raise AssertionError(f"non-official EDINET URL: {row['edinetFilingUrl']}")

    actual_hash = canonical_json_sha256(records)
    expected_hash = entry["source_rows_sha256"]
    if actual_hash != expected_hash:
        raise AssertionError(f"source-row SHA-256 mismatch: {actual_hash} != {expected_hash}")
    if snapshot["source"]["raw_rows_sha256"] != expected_hash:
        raise AssertionError("snapshot source hash differs from ledger")
    if snapshot["audit"].get("nulls_imputed") is not False or entry.get("nulls_imputed") is not False:
        raise AssertionError("null imputation must remain disabled")

    first, last = records[0], records[-1]
    periods = len(records) - 1
    derived = snapshot["derived"]
    checks = {
        "revenue_cagr_2022_2026": (last["revenue"] / first["revenue"]) ** (1 / periods) - 1,
        "net_income_cagr_2022_2026": (last["netIncome"] / first["netIncome"]) ** (1 / periods) - 1,
        "mean_roe_2022_2026": sum(row["roeOfficial"] for row in records) / len(records),
        "operating_margin_2022": first["operatingIncome"] / first["revenue"],
        "operating_margin_2026": last["operatingIncome"] / last["revenue"],
        "free_cash_flow_2026": last["cfOperating"] + last["cfInvesting"],
    }
    for key, actual in checks.items():
        if not _close(float(actual), float(derived[key])):
            raise AssertionError(f"derived metric mismatch for {key}: {actual} != {derived[key]}")

    if snapshot["audit"].get("jquants_status") != "prepared_not_fetched":
        raise AssertionError("J-Quants status must not claim market data was fetched")

    return {
        "artifact_path": entry["artifact_path"],
        "rows": len(records),
        "fiscal_years": [years[0], years[-1]],
        "edinet_doc_ids": len(doc_ids),
        "source_rows_sha256": actual_hash,
        "duplicate_fiscal_years": 0,
        "duplicate_doc_ids": 0,
        "missing_required_fields": 0,
        "derived_metrics_verified": len(checks),
        "status": "PASS",
    }
