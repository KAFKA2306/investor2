from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_ark_forecast_comparison.py"
COMMITTED_JSON = ROOT / "api/v1/ark-big-ideas/forecast-comparison.json"
COMMITTED_CSV = ROOT / "api/v1/ark-big-ideas/forecast-comparison.csv"


class ArkForecastComparisonTest(unittest.TestCase):
    def test_committed_views_are_byte_stable_rebuilds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated_json = output / "forecast-comparison.json"
            generated_csv = output / "forecast-comparison.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--json-output",
                    str(generated_json),
                    "--csv-output",
                    str(generated_csv),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(generated_json.read_bytes(), COMMITTED_JSON.read_bytes())
            self.assertEqual(generated_csv.read_bytes(), COMMITTED_CSV.read_bytes())

    def test_all_thirteen_themes_and_comparison_boundaries(self) -> None:
        payload = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        themes = payload["themes"]
        self.assertEqual(len(themes), 13)
        self.assertEqual(len({row["theme"] for row in themes}), 13)
        self.assertEqual(sum(row["forecast_count"] for row in themes), 3)

        forecasts = [forecast for row in themes for forecast in row["forecasts"]]
        by_id = {row["forecast_id"]: row for row in forecasts}
        self.assertEqual({row["comparison_status"] for row in forecasts}, {"comparable", "not_comparable"})

        acceleration = by_id["global-real-gdp-growth-2030"]
        self.assertEqual(acceleration["observed_series_id"], "econalert/world-gdp-growth")
        self.assertEqual(acceleration["observed_value"], 2.9)
        self.assertEqual(acceleration["observed_period"], "2025")
        self.assertEqual(acceleration["absolute_gap"], 4.4)
        self.assertEqual(acceleration["absolute_gap_unit"], "percentage_points")
        self.assertFalse(acceleration["target_date_reached"])

        for forecast in forecasts:
            self.assertNotIn("verdict", forecast)
            self.assertNotIn("required_cagr", forecast)
            self.assertNotIn("observed_cagr", forecast)
            self.assertIsInstance(forecast["source_page"], int)
            if forecast["comparison_status"] == "not_comparable":
                self.assertIsNone(forecast["observed_series_id"])
                self.assertIsNone(forecast["absolute_gap"])
            else:
                self.assertTrue(forecast["observed_source_url"].startswith("https://raw.githubusercontent.com/"))
                self.assertEqual(len(forecast["observed_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
