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

    def test_all_thirteen_themes_remain_visible_without_invented_comparisons(self) -> None:
        payload = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        themes = payload["themes"]
        self.assertEqual(len(themes), 13)
        self.assertEqual(len({row["theme"] for row in themes}), 13)
        self.assertEqual(sum(row["forecast_count"] for row in themes), 2)

        forbidden = {
            "absolute_gap",
            "relative_gap",
            "required_cagr",
            "observed_cagr",
            "verdict",
        }
        forecasts = [forecast for row in themes for forecast in row["forecasts"]]
        self.assertEqual({row["comparison_status"] for row in forecasts}, {"not_comparable"})
        for forecast in forecasts:
            self.assertTrue(forbidden.isdisjoint(forecast))
            self.assertIsNone(forecast["observed_series_id"])
            self.assertTrue(forecast["source_url"].startswith("https://www.ark-invest.com/"))
            self.assertIsInstance(forecast["source_page"], int)


if __name__ == "__main__":
    unittest.main()
