from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/ark-big-ideas/forecast-catalog.json"


class ArkForecastCatalogTest(unittest.TestCase):
    def test_forecast_sources_are_pinned_and_not_overinterpreted(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema_version"], "investor2.ark-big-ideas-forecast-catalog.v1")
        self.assertEqual(len(catalog["forecasts"]), 2)

        forecasts = {row["forecast_id"]: row for row in catalog["forecasts"]}
        consumer = forecasts["ai-consumer-mediated-revenue-2030"]
        self.assertEqual(consumer["target_value"], 900)
        self.assertEqual(consumer["target_unit"], "USD billion")
        self.assertEqual(consumer["source_page"], 31)
        self.assertEqual(consumer["comparison"]["status"], "not_comparable")

        autonomous = forecasts["autonomous-technology-platform-enterprise-value-2030"]
        self.assertEqual(autonomous["claim_id"], "autonomous-vehicles")
        self.assertIsNone(autonomous["baseline_value"])
        self.assertEqual(autonomous["target_value"], 34)
        self.assertEqual(autonomous["target_unit"], "USD trillion")
        self.assertEqual(autonomous["target_period"], "2030")
        self.assertEqual(autonomous["source_page"], 99)
        self.assertEqual(autonomous["published_at"], "2026-04-27")
        self.assertEqual(autonomous["comparison"]["status"], "not_comparable")
        self.assertIsNone(autonomous["comparison"]["observed_series_id"])

        forbidden = {"absolute_gap", "relative_gap", "required_cagr", "observed_cagr", "verdict"}
        for forecast in forecasts.values():
            self.assertTrue(forbidden.isdisjoint(forecast))
            self.assertTrue(forbidden.isdisjoint(forecast["comparison"]))
            snapshot_path = ROOT / forecast["source_snapshot_path"]
            snapshot_bytes = snapshot_path.read_bytes()
            self.assertEqual(hashlib.sha256(snapshot_bytes).hexdigest(), forecast["source_snapshot_sha256"])
            snapshot = json.loads(snapshot_bytes)
            self.assertEqual(snapshot["publisher"], "ARK Investment Management LLC")
            self.assertTrue(snapshot["source_boundaries"]["forecast_is_not_observed_fact"])

        autonomous_snapshot = json.loads((ROOT / autonomous["source_snapshot_path"]).read_text(encoding="utf-8"))
        self.assertEqual(autonomous_snapshot["big_ideas_2026_page"], 99)
        self.assertEqual(autonomous_snapshot["records"][0]["target_value"], 34)
        self.assertEqual(autonomous_snapshot["source_boundaries"]["official_newsletter_cites_big_ideas_2026_page"], 99)


if __name__ == "__main__":
    unittest.main()
