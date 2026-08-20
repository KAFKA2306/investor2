from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.bls_labor_productivity_snapshot import EXPECTED_HEADER, build_payload, materialize_snapshot


class BlsLaborProductivitySnapshotTest(unittest.TestCase):
    def test_extracts_official_annual_rows(self) -> None:
        rows = [
            EXPECTED_HEADER,
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "% Change from previous year",
                "2024",
                "Annual",
                "3.0",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "% Change from previous year",
                "2025",
                "Annual",
                "2.1",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "Index (2017=100)",
                "2024",
                "Annual",
                "115.366",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "Index (2017=100)",
                "2025",
                "Annual",
                "117.785",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "% Change from previous year",
                "2025",
                "1",
                "9.9",
            ],
        ]

        payload = build_payload(rows)

        self.assertEqual(payload["index_definition"], "Index (2017=100)")
        self.assertEqual(
            payload["records"],
            [
                {"year": 2024, "percent_change": 3.0, "index": 115.366},
                {"year": 2025, "percent_change": 2.1, "index": 117.785},
            ],
        )

    def test_fails_closed_when_index_history_is_incomplete(self) -> None:
        rows = [
            EXPECTED_HEADER,
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "% Change from previous year",
                "2024",
                "Annual",
                "3.0",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "% Change from previous year",
                "2025",
                "Annual",
                "2.1",
            ],
            [
                "Nonfarm business sector",
                "All workers",
                "Labor productivity",
                "Index (2017=100)",
                "2025",
                "Annual",
                "117.785",
            ],
        ]

        with self.assertRaisesRegex(AssertionError, "index missing annual years"):
            build_payload(rows)

    def test_materialized_filename_is_content_addressed(self) -> None:
        payload: dict[str, object] = {
            "schema_version": "investor2.bls-nonfarm-business-labor-productivity-annual.v1",
            "source": "U.S. Bureau of Labor Statistics",
            "latest_year": 2025,
            "records": [{"year": 2025, "percent_change": 2.1, "index": 117.785}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / "latest.json"
            artifact = materialize_snapshot(payload, root / "snapshots", latest)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            expected_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
            self.assertEqual(
                artifact.name,
                f"bls_nonfarm_business_labor_productivity_annual_2025_{expected_hash}.json",
            )
            self.assertEqual(latest.read_text(encoding="utf-8"), serialized)


if __name__ == "__main__":
    unittest.main()
