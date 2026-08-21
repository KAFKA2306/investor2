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
        self.assertEqual(len(catalog["forecasts"]), 3)

        forecasts = {row["forecast_id"]: row for row in catalog["forecasts"]}

        acceleration = forecasts["global-real-gdp-growth-2030"]
        self.assertEqual(acceleration["target_value"], 7.3)
        self.assertEqual(acceleration["target_unit"], "percent")
        self.assertEqual(acceleration["target_period"], "2030")
        self.assertEqual(acceleration["source_page"], 11)
        self.assertEqual(acceleration["comparison"]["status"], "comparable")
        self.assertEqual(acceleration["comparison"]["observed_value"], 2.9)
        self.assertEqual(acceleration["comparison"]["observed_period"], "2025")
        self.assertEqual(acceleration["comparison"]["observed_unit"], "percent")
        self.assertEqual(acceleration["comparison"]["absolute_gap"], 4.4)
        self.assertEqual(acceleration["comparison"]["absolute_gap_unit"], "percentage_points")
        self.assertFalse(acceleration["comparison"]["target_date_reached"])
        self.assertEqual(acceleration["comparison"]["observed_repository"], "KAFKA2306/econalert")
        self.assertEqual(
            acceleration["comparison"]["observed_sha256"],
            "48fa167bc1f554188c7d94f441fd3ac903ee9772ddb3fb2041c15cbb8927c9b0",
        )

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

        for forecast in forecasts.values():
            comparison = forecast["comparison"]
            self.assertNotIn("verdict", comparison)
            self.assertNotIn("required_cagr", comparison)
            self.assertNotIn("observed_cagr", comparison)
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
