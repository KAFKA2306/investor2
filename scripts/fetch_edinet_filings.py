from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.io.market_data_sources import (
    EDINET_DOCUMENT_ENDPOINT,
    EDINET_LIST_ENDPOINT,
    classify_edinet_documents,
    sha256_bytes,
    utc_now_iso,
)


def fetch(url: str, *, attempts: int = 3) -> bytes:
    req = Request(
        url,
        headers={"User-Agent": "KAFKA2306/investor2 EDINET filing collector"},
    )
    for attempt in range(attempts):
        try:
            with urlopen(req, timeout=90) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 60.0
            time.sleep(delay)
    raise RuntimeError("EDINET fetch exhausted retries")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--issuer-master", default="data/market/edinet_issuer_master.json")
    parser.add_argument("--state", default="data/market/edinet_filing_state.json")
    parser.add_argument("--output", default="data/market/edinet_filings.ndjson")
    parser.add_argument("--audit-output", default="data/market/edinet_filings_audit_latest.json")
    parser.add_argument("--download-documents", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("EDINET_API_KEY")
    if not api_key:
        raise SystemExit("EDINET_API_KEY is required")

    master = json.loads(Path(args.issuer_master).read_text())
    issuer_by_edinet = {row["edinet_code"]: row for row in master["issuers"]}
    state_path = Path(args.state)
    if state_path.exists():
        state: dict[str, object] = json.loads(state_path.read_text())
    else:
        state = {"known_doc_ids": list[str]()}
    known_values = state.get("known_doc_ids")
    known: set[str] = {str(value) for value in known_values} if isinstance(known_values, list) else set()

    query = urlencode({"date": args.date, "type": "2", "Subscription-Key": api_key})
    payload = json.loads(fetch(f"{EDINET_LIST_ENDPOINT}?{query}"))
    records, reason_counts = classify_edinet_documents(
        payload,
        known_doc_ids=known,
        issuer_by_edinet_code=issuer_by_edinet,
    )
    retrieved_at = utc_now_iso()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        for record in records:
            record["retrieved_at"] = retrieved_at
            record["source_url"] = f"{EDINET_LIST_ENDPOINT}?date={args.date}&type=2"
            record["accepted"] = True
            if args.download_documents:
                document_query = urlencode({"type": "1", "Subscription-Key": api_key})
                document_url = EDINET_DOCUMENT_ENDPOINT.format(doc_id=record["doc_id"]) + f"?{document_query}"
                raw = fetch(document_url)
                record["document_source_url"] = EDINET_DOCUMENT_ENDPOINT.format(doc_id=record["doc_id"]) + "?type=1"
                record["document_sha256"] = sha256_bytes(raw)
                record["document_bytes"] = len(raw)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            known.add(record["doc_id"])

    state_payload = {
        "schema_version": "investor2.edinet-filing-state.v1",
        "updated_at": retrieved_at,
        "known_doc_ids": sorted(known),
    }
    state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n")
    audit_payload = {
        "schema_version": "investor2.edinet-filing-audit.v1",
        "date": args.date,
        "retrieved_at": retrieved_at,
        "new_documents": len(records),
        "known_documents": len(known),
        "reason_counts": reason_counts,
        "status": "PASS",
    }
    audit_path = Path(args.audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(audit_payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
