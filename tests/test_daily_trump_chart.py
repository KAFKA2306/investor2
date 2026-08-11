from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.daily_trump_chart import aggregate_transactions, write_outputs


def fixture_payload() -> dict:
    return {
        "name": "Trump, Donald J.",
        "filingType": "278-T Periodic Transaction Report",
        "mostRecentFilingDate": "2026-07-01",
        "transactions": [
            {"date": "2026-05-01", "type": "Purchase"},
            {"date": "2026-05-01", "type": "Sale"},
            {"date": "2026-05-01", "type": "Purchase"},
            {"date": "2026-05-02", "type": "Sale"},
        ],
    }


def test_aggregate_transactions_preserves_counts_and_total() -> None:
    rows = aggregate_transactions(fixture_payload())
    assert rows == [
        {"date": "2026-05-01", "Purchase": 2, "Sale": 1, "Total": 3},
        {"date": "2026-05-02", "Purchase": 0, "Sale": 1, "Total": 1},
    ]
    assert sum(int(row["Purchase"]) for row in rows) == 2
    assert sum(int(row["Sale"]) for row in rows) == 2
    assert all(int(row["Total"]) == int(row["Purchase"]) + int(row["Sale"]) for row in rows)


def test_unexpected_transaction_type_fails_closed() -> None:
    payload = fixture_payload()
    payload["transactions"].append({"date": "2026-05-03", "type": "Exchange"})
    with pytest.raises(ValueError, match="unexpected transaction types"):
        aggregate_transactions(payload)


def test_output_contract_contains_chart_csv_and_provenance(tmp_path: Path) -> None:
    payload = fixture_payload()
    raw = json.dumps(payload, sort_keys=True).encode()
    rows = aggregate_transactions(payload)
    summary = write_outputs(payload, raw, rows, tmp_path, "https://example.invalid/trump.json")

    assert summary["row_count"] == 4
    assert summary["purchase_rows"] == 2
    assert summary["sale_rows"] == 2
    assert len(summary["source_sha256"]) == 64
    assert summary["source_type"] == "derived_parser_output"
    assert summary["unexpected_transaction_types"] == []

    with (tmp_path / "trump_daily_transactions.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert all(int(row["Total"]) == int(row["Purchase"]) + int(row["Sale"]) for row in csv_rows)
    assert (tmp_path / "trump_daily_transactions.png").stat().st_size > 0

    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "trump_daily_transactions.png" in html
    assert "trump_daily_transactions.csv" in html
    assert "summary.json" in html
    assert "U.S. Office of Government Ethics" in html
