from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "io" / "edinetdb_projection.py"
SPEC = importlib.util.spec_from_file_location("edinetdb_projection", MODULE_PATH)
assert SPEC and SPEC.loader
projection_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = projection_module
SPEC.loader.exec_module(projection_module)


def sample_projection() -> dict:
    return {
        "schema_version": "edinetdb.consumer-projection.v1",
        "consumer": "KAFKA2306/investor2",
        "projection_id": "investor2-kioxia-financials",
        "provider": "EDINET DB",
        "attribution": "Powered by EDINET DB",
        "source_endpoint": "/v1/companies/E35948/financials",
        "request_fingerprint": "a" * 64,
        "response_sha256": "b" * 64,
        "fetched_at": "2026-08-10T00:00:00Z",
        "records": [
            {
                "fiscal_year": "2026",
                "accounting_standard": "IFRS",
                "revenue": 1,
                "source_doc_id": "S100XXXX",
            }
        ],
    }


def test_valid_projection_is_accepted() -> None:
    payload = sample_projection()
    projection_module.validate_projection(payload)
    assert projection_module.records(payload) == payload["records"]


def test_projection_rejects_cross_repo_consumer() -> None:
    payload = sample_projection()
    payload["consumer"] = "KAFKA2306/semiconductor-earnings-model"
    try:
        projection_module.validate_projection(payload)
    except ValueError as exc:
        assert "consumer" in str(exc)
    else:
        raise AssertionError("cross-repo projection must fail")


def test_projection_contains_provenance_without_api_secret(tmp_path: Path) -> None:
    path = tmp_path / "projection.json"
    path.write_text(json.dumps(sample_projection()), encoding="utf-8")
    payload, transport_hash = projection_module.load_projection(path)
    evidence = projection_module.provenance(payload, transport_hash)
    assert evidence["provider"] == "EDINET DB"
    assert evidence["attribution"] == "Powered by EDINET DB"
    assert evidence["request_fingerprint"] == "a" * 64
    assert evidence["provider_response_sha256"] == "b" * 64
    assert evidence["projection_transport_sha256"]
    assert "api_key" not in payload
    assert "raw_response" not in payload


def test_projection_records_are_not_reinterpreted() -> None:
    payload = sample_projection()
    result = projection_module.records(payload)
    assert result[0]["revenue"] == 1
    assert result[0]["source_doc_id"] == "S100XXXX"
