from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.snapshot_store import latest_snapshot

ROOT = Path(__file__).resolve().parents[1]
REUSE_KEY = "us/bls/employment-situation"
EXPECTED_ARTIFACT = "data/market_snapshots/bls_employment_situation_2026_08.json"
OFFICIAL_URL = "https://www.bls.gov/news.release/archives/empsit_09042026.htm"


class BlsEmploymentSituationSnapshotTest(unittest.TestCase):
    def test_latest_snapshot_resolves_registered_real_release(self) -> None:
        snapshot = latest_snapshot(reuse_key=REUSE_KEY, root=ROOT)
        self.assertEqual(snapshot["artifact_path"], EXPECTED_ARTIFACT)
        self.assertEqual(snapshot["source"], "public_web_research")
        self.assertEqual(snapshot["source_kind"], "official_web")
        self.assertEqual(snapshot["observed_at"], "2026-09-04T08:30:00-04:00")
        self.assertEqual(snapshot["provenance"]["source_urls"], [OFFICIAL_URL])

    def test_actual_and_revision_claims_stay_separate_from_market_inference(self) -> None:
        payload = json.loads((ROOT / EXPECTED_ARTIFACT).read_text(encoding="utf-8"))
        self.assertEqual(payload["source_url"], OFFICIAL_URL)
        self.assertEqual(payload["event"]["observation_period"], "2026-08")
        self.assertEqual(payload["event"]["published_at"], "2026-09-04T08:30:00-04:00")

        actual = {row["metric"]: row for row in payload["records"] if row["classification"] == "actual"}
        revisions = {row["metric"]: row for row in payload["records"] if row["classification"] == "revision"}

        self.assertEqual(actual["total_nonfarm_payroll_employment_change"]["value"], 162)
        self.assertEqual(actual["unemployment_rate"]["value"], 4.1)
        self.assertEqual(actual["average_hourly_earnings_all_private"]["value"], 37.75)
        self.assertEqual(actual["average_hourly_earnings_monthly_change"]["value"], 0.3)
        self.assertEqual(actual["average_hourly_earnings_yearly_change"]["value"], 3.1)

        self.assertEqual(revisions["june_nonfarm_payroll_change"]["previous_value"], 20)
        self.assertEqual(revisions["june_nonfarm_payroll_change"]["revised_value"], 31)
        self.assertEqual(revisions["july_nonfarm_payroll_change"]["previous_value"], -23)
        self.assertEqual(revisions["july_nonfarm_payroll_change"]["revised_value"], 21)
        self.assertEqual(revisions["june_july_combined_revision"]["value"], 55)

        forbidden = {"consensus", "forecast", "market_reaction", "usd_jpy", "fed_policy_inference"}
        self.assertTrue(forbidden.isdisjoint(payload))
        for row in payload["records"]:
            self.assertTrue(forbidden.isdisjoint(row))


if __name__ == "__main__":
    unittest.main()
