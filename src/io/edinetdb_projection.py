from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

DEFAULT_KIOXIA_PROJECTION_URL = (
    "https://raw.githubusercontent.com/KAFKA2306/semiconductor-earnings-model/main/"
    "data/edinetdb_projections/KAFKA2306__investor2/investor2-kioxia-financials.json"
)
EXPECTED_SCHEMA = "edinetdb.consumer-projection.v1"
EXPECTED_CONSUMER = "KAFKA2306/investor2"
EXPECTED_PROVIDER = "EDINET DB"
EXPECTED_ATTRIBUTION = "Powered by EDINET DB"


def _decode(body: bytes) -> tuple[dict[str, Any], str]:
    payload = json.loads(body.decode("utf-8"))
    validate_projection(payload)
    return payload, hashlib.sha256(body).hexdigest()


def load_projection(path: str | Path) -> tuple[dict[str, Any], str]:
    return _decode(Path(path).read_bytes())


def fetch_projection(url: str = DEFAULT_KIOXIA_PROJECTION_URL) -> tuple[dict[str, Any], str]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "KAFKA2306-investor2-edinetdb-consumer/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        return _decode(response.read())


def validate_projection(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("unsupported EDINETDB projection schema")
    if payload.get("consumer") != EXPECTED_CONSUMER:
        raise ValueError(f"projection consumer must be {EXPECTED_CONSUMER}")
    if payload.get("provider") != EXPECTED_PROVIDER:
        raise ValueError("unexpected projection provider")
    if payload.get("attribution") != EXPECTED_ATTRIBUTION:
        raise ValueError("EDINET DB attribution is missing")
    if not payload.get("request_fingerprint"):
        raise ValueError("request_fingerprint is required")
    if not payload.get("response_sha256"):
        raise ValueError("response_sha256 is required")
    if not payload.get("fetched_at"):
        raise ValueError("fetched_at is required")
    if not isinstance(payload.get("records"), list):
        raise TypeError("projection records must be a list")


def records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validate_projection(payload)
    return payload["records"]


def provenance(payload: dict[str, Any], transport_sha256: str) -> dict[str, Any]:
    validate_projection(payload)
    return {
        "provider": payload["provider"],
        "attribution": payload["attribution"],
        "projection_id": payload.get("projection_id"),
        "source_endpoint": payload.get("source_endpoint"),
        "request_fingerprint": payload["request_fingerprint"],
        "provider_response_sha256": payload["response_sha256"],
        "projection_transport_sha256": transport_sha256,
        "fetched_at": payload["fetched_at"],
    }
