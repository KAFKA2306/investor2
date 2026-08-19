from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.treasury_rates_snapshot import build_payload, materialize_snapshot


class TreasuryRatesSnapshotTest(unittest.TestCase):
    def test_builds_nominal_and_real_records_without_filling_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nominal = root / "nominal.csv"
            real = root / "real.csv"
            nominal.write_text(
                "Date,1 Mo,10 Yr,30 Yr\n"
                "08/17/2026,3.80,4.72,5.31\n"
                "08/18/2026,3.79,4.71,5.28\n",
                encoding="utf-8",
            )
            real.write_text(
                "Date,5 Yr,10 Yr,20 Yr,30 Yr\n"
                "08/17/2026,2.22,2.44,2.84,3.06\n"
                "08/18/2026,N/A,2.43,2.83,3.05\n",
                encoding="utf-8",
            )

            payload = build_payload(nominal, real)

            self.assertEqual(payload["latest_nominal_date"], "2026-08-18")
            self.assertEqual(payload["latest_real_date"], "2026-08-18")
            self.assertEqual(len(payload["records"]), 4)
            self.assertEqual(payload["records"][1]["30_yr"], 5.28)
            self.assertIsNone(payload["records"][3]["5_yr"])

    def test_materialized_filename_is_content_addressed(self) -> None:
        payload = {
            "schema_version": "investor2.us-treasury-yield-curves.v1",
            "source": "U.S. Department of the Treasury",
            "source_urls": {},
            "latest_nominal_date": "2026-08-18",
            "latest_real_date": "2026-08-18",
            "records": [{"curve": "nominal", "date": "2026-08-18", "30_yr": 5.28}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / "latest.json"
            artifact = materialize_snapshot(payload, root / "snapshots", latest)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            expected_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]

            self.assertEqual(artifact.name, f"us_treasury_yield_curves_2026-08-18_{expected_hash}.json")
            self.assertEqual(latest.read_text(encoding="utf-8"), serialized)


if __name__ == "__main__":
    unittest.main()
