from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

EDINET_CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
EDINET_LIST_ENDPOINT = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
EDINET_DOCUMENT_ENDPOINT = "https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"
SECURITY_CODE_LETTERS = "ACDFGHJKLMNPRSTUWXY"
SECURITY_CODE_PATTERN = re.compile(
    rf"[0-9][0-9{SECURITY_CODE_LETTERS}][0-9][0-9{SECURITY_CODE_LETTERS}]"
)

# EDINET API Specification v2 (June 2026), document type codes.
EDINET_TARGET_DOC_TYPE_CODES = {
    "120",  # Annual Securities Report
    "130",  # Amendment to Annual Securities Report
    "140",  # Quarterly Securities Report
    "150",  # Amendment to Quarterly Securities Report
    "160",  # Semiannual Securities Report
    "170",  # Amendment to Semiannual Securities Report
    "180",  # Extraordinary Report
    "190",  # Amendment to Extraordinary Report
    "350",  # Large Shareholding Report
    "360",  # Amendment to Large Shareholding Report
}
EDINET_TARGET_DESCRIPTION_TERMS = ("変更報告書",)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def normalize_security_code(value: str | None) -> str | None:
    if value is None:
        return None
    code = str(value).strip()
    if not code:
        return None
    # EDINET's security-code field is conventionally five characters, while TDnet/JPX joins use four.
    # Keep the original separately and remove only a trailing filler zero when present.
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code


def _decode_csv(payload: bytes) -> str:
    for encoding in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("EDINET code-list CSV encoding is unsupported")


def _csv_value(row: list[str], index: dict[str, int | None], key: str) -> str | None:
    idx = index[key]
    if idx is None or idx >= len(row):
        return None
    value = row[idx].strip()
    return value or None


def parse_edinet_code_zip(
    payload: bytes,
    *,
    source_url: str = EDINET_CODELIST_URL,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    retrieved_at = retrieved_at or utc_now_iso()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"expected exactly one CSV in EDINET archive, got {csv_names}")
        text = _decode_csv(archive.read(csv_names[0]))

    rows = list(csv.reader(io.StringIO(text)))
    header_index = next(
        (i for i, row in enumerate(rows) if "ＥＤＩＮＥＴコード" in row or "EDINETコード" in row),
        None,
    )
    if header_index is None:
        raise ValueError("EDINET code-list header not found")
    headers = [h.strip() for h in rows[header_index]]
    aliases = {
        "edinet_code": ("ＥＤＩＮＥＴコード", "EDINETコード"),
        "submitter_type": ("提出者種別",),
        "listing_category": ("上場区分",),
        "fiscal_year_end": ("決算日",),
        "issuer_name": ("提出者名",),
        "issuer_name_en": ("提出者名（英字）", "提出者名(英字)"),
        "industry": ("提出者業種",),
        "edinet_security_code": ("証券コード",),
        "corporate_number": ("提出者法人番号", "法人番号"),
    }
    index: dict[str, int | None] = {}
    for key, names in aliases.items():
        index[key] = next((headers.index(name) for name in names if name in headers), None)
    required = ("edinet_code", "issuer_name", "edinet_security_code", "industry")
    missing = [key for key in required if index[key] is None]
    if missing:
        raise ValueError(f"EDINET code-list missing required columns: {missing}")

    source_hash = sha256_bytes(payload)
    issuers: list[dict[str, Any]] = []
    for raw in rows[header_index + 1 :]:
        if not raw or not any(cell.strip() for cell in raw):
            continue
        source_security_code = _csv_value(raw, index, "edinet_security_code")
        security_code = normalize_security_code(source_security_code)
        if security_code is None:
            continue
        issuer = {
            "security_code": security_code,
            "edinet_security_code": source_security_code,
            "edinet_code": _csv_value(raw, index, "edinet_code"),
            "corporate_number": _csv_value(raw, index, "corporate_number"),
            "issuer_name": _csv_value(raw, index, "issuer_name"),
            "issuer_name_en": _csv_value(raw, index, "issuer_name_en"),
            "submitter_type": _csv_value(raw, index, "submitter_type"),
            "listing_category": _csv_value(raw, index, "listing_category"),
            "industry": _csv_value(raw, index, "industry"),
            "fiscal_year_end": _csv_value(raw, index, "fiscal_year_end"),
        }
        issuers.append(issuer)

    issuers.sort(key=lambda row: (row["security_code"], row.get("edinet_code") or ""))
    audit_edinet_issuers(issuers)
    return {
        "schema_version": "investor2.edinet-issuer-master.v1",
        "source_url": source_url,
        "source_retrieved_at": retrieved_at,
        "source_sha256": source_hash,
        "issuer_count": len(issuers),
        "issuers_sha256": canonical_json_sha256(issuers),
        "issuers": issuers,
    }


def audit_edinet_issuers(issuers: Iterable[dict[str, Any]]) -> None:
    rows = list(issuers)
    if not rows:
        raise ValueError("EDINET issuer master is empty")
    for field in ("security_code", "edinet_code"):
        values = [str(row.get(field) or "") for row in rows]
        if any(not value for value in values):
            raise ValueError(f"missing {field}")
        duplicates = {value for value, count in Counter(values).items() if count > 1}
        if duplicates:
            raise ValueError(f"duplicate {field}: {sorted(duplicates)[:5]}")

    corporate_numbers = [str(row["corporate_number"]) for row in rows if row.get("corporate_number")]
    duplicate_corporate_numbers = {
        value for value, count in Counter(corporate_numbers).items() if count > 1
    }
    if duplicate_corporate_numbers:
        raise ValueError(f"duplicate corporate_number: {sorted(duplicate_corporate_numbers)[:5]}")

    invalid_codes = [
        str(row["security_code"])
        for row in rows
        if not SECURITY_CODE_PATTERN.fullmatch(str(row.get("security_code") or ""))
    ]
    if invalid_codes:
        raise ValueError(f"invalid security_code: {invalid_codes[:5]}")
    if any(not row.get("industry") for row in rows):
        raise ValueError("listed EDINET issuer has missing industry")


def diff_issuer_masters(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    old = {row["security_code"]: row for row in (previous or {}).get("issuers", [])}
    new = {row["security_code"]: row for row in current.get("issuers", [])}
    changes: list[dict[str, Any]] = []
    for code in sorted(old.keys() | new.keys()):
        if code not in old:
            changes.append({"security_code": code, "change": "added", "after": new[code]})
        elif code not in new:
            changes.append({"security_code": code, "change": "removed", "before": old[code]})
        else:
            fields = [
                "issuer_name",
                "issuer_name_en",
                "industry",
                "listing_category",
                "fiscal_year_end",
                "corporate_number",
                "edinet_code",
            ]
            changed = {
                field: {"before": old[code].get(field), "after": new[code].get(field)}
                for field in fields
                if old[code].get(field) != new[code].get(field)
            }
            if changed:
                changes.append({"security_code": code, "change": "modified", "fields": changed})
    return {
        "schema_version": "investor2.edinet-issuer-master-diff.v1",
        "changes": changes,
        "change_count": len(changes),
    }


def classify_edinet_documents(
    payload: dict[str, Any],
    *,
    known_doc_ids: set[str],
    issuer_by_edinet_code: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        status = str(metadata.get("status") or metadata.get("statusCode") or "")
        if status and status != "200":
            raise ValueError(f"EDINET API returned status {status}")

    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("EDINET document-list response is missing results")

    accepted: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for row in results:
        if not isinstance(row, dict):
            reasons["invalid_record"] += 1
            continue
        doc_id = str(row.get("docID") or "").strip()
        description = str(row.get("docDescription") or "")
        doc_type_code = str(row.get("docTypeCode") or "").strip()
        edinet_code = str(row.get("edinetCode") or "").strip()
        is_target = doc_type_code in EDINET_TARGET_DOC_TYPE_CODES or any(
            term in description for term in EDINET_TARGET_DESCRIPTION_TERMS
        )
        if not doc_id:
            reasons["missing_doc_id"] += 1
            continue
        if not is_target:
            reasons["non_target_document_type"] += 1
            continue
        if doc_id in known_doc_ids:
            reasons["already_known_doc_id"] += 1
            continue

        issuer = issuer_by_edinet_code.get(edinet_code, {})
        accepted.append(
            {
                "doc_id": doc_id,
                "parent_doc_id": row.get("parentDocID"),
                "edinet_code": edinet_code or None,
                "security_code": issuer.get("security_code")
                or normalize_security_code(row.get("secCode")),
                "document_type_code": doc_type_code or None,
                "document_description": description or None,
                "submitted_at": row.get("submitDateTime"),
                "operation_at": row.get("opeDateTime"),
                "period_start": row.get("periodStart"),
                "period_end": row.get("periodEnd"),
                "issuer_name": row.get("filerName") or issuer.get("issuer_name"),
                "withdrawal_status": row.get("withdrawalStatus"),
                "document_info_edit_status": row.get("docInfoEditStatus"),
                "disclosure_status": row.get("disclosureStatus"),
                "xbrl_flag": row.get("xbrlFlag"),
                "pdf_flag": row.get("pdfFlag"),
                "csv_flag": row.get("csvFlag"),
                "accepted_reason": "target_document_type",
            }
        )
        reasons["accepted"] += 1

    accepted.sort(key=lambda row: (str(row.get("submitted_at") or ""), row["doc_id"]))
    return accepted, dict(sorted(reasons.items()))


def filter_edinet_documents(
    payload: dict[str, Any],
    *,
    known_doc_ids: set[str],
    issuer_by_edinet_code: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    accepted, _ = classify_edinet_documents(
        payload,
        known_doc_ids=known_doc_ids,
        issuer_by_edinet_code=issuer_by_edinet_code,
    )
    return accepted


def parse_gdelt_last_update(text: str) -> str:
    candidates = [line.split()[-1] for line in text.splitlines() if line.strip() and line.split()]
    gkg = [url for url in candidates if url.endswith(".gkg.csv.zip")]
    if not gkg:
        raise ValueError("GDELT lastupdate.txt has no GKG archive")
    return gkg[-1]


def _normalize_alias(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value.casefold(), flags=re.UNICODE)


def build_company_aliases(issuer_master: dict[str, Any]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for issuer in issuer_master.get("issuers", []):
        code = issuer["security_code"]
        values = [issuer.get("issuer_name"), issuer.get("issuer_name_en")]
        normalized = sorted(
            {_normalize_alias(v) for v in values if isinstance(v, str) and len(_normalize_alias(v)) >= 4}
        )
        if normalized:
            aliases[code] = normalized
    return aliases


def parse_gdelt_gkg_zip(
    payload: bytes,
    *,
    issuer_master: dict[str, Any],
    source_url: str,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    aliases = build_company_aliases(issuer_master)
    alias_to_codes: dict[str, set[str]] = {}
    for code, code_aliases in aliases.items():
        for alias in code_aliases:
            alias_to_codes.setdefault(alias, set()).add(code)
    issuer_by_code = {
        row["security_code"]: row for row in issuer_master.get("issuers", [])
    }
    retrieved_at = retrieved_at or utc_now_iso()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [
            name for name in archive.namelist() if name.lower().endswith(".csv")
        ]
        if len(csv_names) != 1:
            raise ValueError("expected one GDELT GKG CSV")
        text = archive.read(csv_names[0]).decode("utf-8", errors="replace")

    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in text.splitlines():
        cols = raw_line.split("\t")
        if len(cols) < 15:
            continue
        record_id, observed, source_domain, article_url = (
            cols[0],
            cols[1],
            cols[3],
            cols[4],
        )
        organization_tokens = [
            token.rsplit("#", 1)[-1]
            for token in cols[13].split(";")
            if token.strip()
        ]
        matched_codes: set[str] = set()
        evidence_by_code: dict[str, str] = {}
        for token in organization_tokens:
            alias = _normalize_alias(token)
            for code in alias_to_codes.get(alias, set()):
                matched_codes.add(code)
                evidence_by_code.setdefault(code, alias)

        for code in sorted(matched_codes):
            key = (article_url, code)
            if not article_url or key in seen:
                continue
            seen.add(key)
            issuer = issuer_by_code.get(code, {})
            events.append(
                {
                    "gdelt_record_id": record_id,
                    "observed_at": observed,
                    "source_domain": source_domain or urlparse(article_url).netloc,
                    "article_url": article_url,
                    "security_code": code,
                    "industry": issuer.get("industry"),
                    "mapping_status": "candidate",
                    "mapping_evidence": {
                        "type": "gdelt_organization_exact_alias",
                        "alias": evidence_by_code[code],
                    },
                }
            )
    events.sort(
        key=lambda row: (
            row["security_code"],
            row["article_url"],
            row["gdelt_record_id"],
        )
    )
    return {
        "schema_version": "investor2.gdelt-company-news-discovery.v1",
        "source_url": source_url,
        "source_retrieved_at": retrieved_at,
        "source_sha256": sha256_bytes(payload),
        "attribution": "GDELT Project",
        "event_count": len(events),
        "events_sha256": canonical_json_sha256(events),
        "events": events,
    }


def query_gdelt_events(
    datasets: Iterable[dict[str, Any]],
    *,
    security_code: str | None = None,
    industry: str | None = None,
    observed_from: str | None = None,
    observed_to: str | None = None,
) -> list[dict[str, Any]]:
    """Filter normalized GDELT discovery records without promoting candidate mappings to facts."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for dataset in datasets:
        for row in dataset.get("events", []):
            if security_code is not None and str(row.get("security_code")) != security_code:
                continue
            if industry is not None and str(row.get("industry")) != industry:
                continue
            observed = str(row.get("observed_at") or "")
            if observed_from is not None and observed < observed_from:
                continue
            if observed_to is not None and observed > observed_to:
                continue
            key = (str(row.get("article_url") or ""), str(row.get("security_code") or ""))
            if not key[0] or key in seen:
                continue
            seen.add(key)
            rows.append(dict(row))
    rows.sort(
        key=lambda row: (
            str(row.get("observed_at") or ""),
            str(row.get("security_code") or ""),
            str(row.get("article_url") or ""),
        )
    )
    return rows


@dataclass(frozen=True)
class AlphaVantageResult:
    security_code: str
    symbol: str
    status: str
    observations: int
    error: str | None = None


def parse_alpha_vantage_daily(payload: dict[str, Any], *, security_code: str, symbol: str) -> AlphaVantageResult:
    if "Note" in payload:
        return AlphaVantageResult(security_code, symbol, "rate_limited", 0, str(payload["Note"]))
    if "Information" in payload:
        return AlphaVantageResult(security_code, symbol, "provider_information", 0, str(payload["Information"]))
    if "Error Message" in payload:
        return AlphaVantageResult(security_code, symbol, "unsupported", 0, str(payload["Error Message"]))
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict):
        return AlphaVantageResult(security_code, symbol, "invalid_response", 0, "Time Series (Daily) missing")
    return AlphaVantageResult(security_code, symbol, "supported", len(series))
