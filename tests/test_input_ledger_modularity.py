from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.io.input_ledger import audit_entries, audit_entry

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/input_ledger/accepted.ndjson"
REGISTRY = ROOT / "data/input_ledger/source_registry.json"


def _load_current() -> tuple[list[dict], dict]:
    entries = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return entries, registry


def test_current_accepted_ledger_uses_registered_validator() -> None:
    entries, registry = _load_current()
    results = audit_entries(entries, registry, ROOT)

    assert len(results) == len(entries)
    assert results[0]["source"] == "edinetdb_annual_financials"
    assert results[0]["adapter"] == "edinetdb_mcp_projection"
    assert results[0]["status"] == "PASS"


def test_entry_adapter_must_match_source_registry() -> None:
    entries, registry = _load_current()
    entry = copy.deepcopy(entries[0])
    entry["adapter"] = "different_adapter"

    with pytest.raises(AssertionError, match="adapter mismatch"):
        audit_entry(entry, registry, ROOT)


def test_unimplemented_registered_adapter_fails_closed() -> None:
    entries, registry = _load_current()
    entry = copy.deepcopy(entries[0])
    registry = copy.deepcopy(registry)
    registry["sources"][entry["source"]]["adapter"] = "future_provider_adapter"
    entry["adapter"] = "future_provider_adapter"

    with pytest.raises(AssertionError, match="unsupported input-ledger adapter"):
        audit_entry(entry, registry, ROOT)
