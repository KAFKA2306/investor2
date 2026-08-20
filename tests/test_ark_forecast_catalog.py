from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/ark-big-ideas/forecast-catalog.json"


class ArkForecastCatalogTest(unittest.TestCase):
    def test_ai_consumer_forecast_source_is_pinned_and_not_overinterpreted(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema_version"], "investor2.ark-big-ideas-forecast-catalog.v1")
        self.assertEqual(len(catalog["forecasts"]), 1)

        forecast = catalog["forecasts"][0]
        self.assertEqual(forecast["forecast_id"], "ai-consumer-mediated-revenue-2030")
        self.assertEqual(forecast["claim_id"], "ai-consumer-operating-system")
        self.assertEqual(forecast["baseline_value"], 20)
        self.assertEqual(forecast["baseline_unit"], "USD billion")
        self.assertIsNone(forecast["baseline_period"])
        self.assertEqual(forecast["target_value"], 900)
        self.assertEqual(forecast["target_unit"], "USD billion")
        self.assertEqual(forecast["target_period"], "2030")
        self.assertEqual(forecast["growth_rate"], 105)
        self.assertEqual(forecast["growth_rate_unit"], "percent_per_year")
        self.assertEqual(forecast["source_page"], 31)
        self.assertEqual(forecast["comparison"]["status"], "not_comparable")
        self.assertIsNone(forecast["comparison"]["observed_series_id"])

        forbidden = {"absolute_gap", "relative_gap", "required_cagr", "observed_cagr", "verdict"}
        self.assertTrue(forbidden.isdisjoint(forecast))
        self.assertTrue(forbidden.isdisjoint(forecast["comparison"]))

        snapshot_path = ROOT / forecast["source_snapshot_path"]
        snapshot_bytes = snapshot_path.read_bytes()
        self.assertEqual(hashlib.sha256(snapshot_bytes).hexdigest(), forecast["source_snapshot_sha256"])

        snapshot = json.loads(snapshot_bytes)
        self.assertEqual(snapshot["publisher"], "ARK Investment Management LLC")
        self.assertEqual(snapshot["published_at"], "2026-01-26")
        self.assertEqual(snapshot["big_ideas_2026_page"], 31)
        self.assertEqual(snapshot["source_boundaries"]["actual_periods_explicitly_noted"], ["2024", "2025"])
        self.assertTrue(snapshot["source_boundaries"]["forecast_is_not_observed_fact"])
        self.assertIsNone(snapshot["records"][0]["baseline_period"])


if __name__ == "__main__":
    unittest.main()
