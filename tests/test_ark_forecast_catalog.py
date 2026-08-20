from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/ark-big-ideas/forecast-catalog.json"


def test_ai_consumer_forecast_source_is_pinned_and_not_overinterpreted() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["schema_version"] == "investor2.ark-big-ideas-forecast-catalog.v1"
    assert len(catalog["forecasts"]) == 1

    forecast = catalog["forecasts"][0]
    assert forecast["forecast_id"] == "ai-consumer-mediated-revenue-2030"
    assert forecast["claim_id"] == "ai-consumer-operating-system"
    assert forecast["baseline_value"] == 20
    assert forecast["baseline_unit"] == "USD billion"
    assert forecast["baseline_period"] is None
    assert forecast["target_value"] == 900
    assert forecast["target_unit"] == "USD billion"
    assert forecast["target_period"] == "2030"
    assert forecast["growth_rate"] == 105
    assert forecast["growth_rate_unit"] == "percent_per_year"
    assert forecast["source_page"] == 31
    assert forecast["comparison"]["status"] == "not_comparable"
    assert forecast["comparison"]["observed_series_id"] is None

    forbidden = {"absolute_gap", "relative_gap", "required_cagr", "observed_cagr", "verdict"}
    assert forbidden.isdisjoint(forecast)
    assert forbidden.isdisjoint(forecast["comparison"])

    snapshot_path = ROOT / forecast["source_snapshot_path"]
    snapshot_bytes = snapshot_path.read_bytes()
    assert hashlib.sha256(snapshot_bytes).hexdigest() == forecast["source_snapshot_sha256"]

    snapshot = json.loads(snapshot_bytes)
    assert snapshot["publisher"] == "ARK Investment Management LLC"
    assert snapshot["published_at"] == "2026-01-26"
    assert snapshot["big_ideas_2026_page"] == 31
    assert snapshot["source_boundaries"]["actual_periods_explicitly_noted"] == ["2024", "2025"]
    assert snapshot["source_boundaries"]["forecast_is_not_observed_fact"] is True
    assert snapshot["records"][0]["baseline_period"] is None
