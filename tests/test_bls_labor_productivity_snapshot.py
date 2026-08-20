from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.bls_labor_productivity_snapshot import (
    SERIES_IDS,
    build_payload,
    materialize_snapshot,
    request_windows,
)


class BlsLaborProductivitySnapshotTest(unittest.TestCase):
    def test_request_windows_respect_unregistered_api_limit(self) -> None:
        windows = request_windows(1948, 2026)
        self.assertEqual(windows[0], (1948, 1957))
        self.assertEqual(windows[-1], (2018, 2026))
        self.assertEqual(len(windows), 8)
        self.assertTrue(all(end - start + 1 <= 10 for start, end in windows))

    def test_extracts_only_official_annual_average_rows(self) -> None:
        series = [
            {
                "seriesID": SERIES_IDS["percent_change"],
                "data": [
                    {"year": "2024", "period": "Q01", "value": "3.3"},
                    {"year": "2024", "period": "Q05", "value": "3.0"},
                    {"year": "2025", "period": "Q05", "value": "2.1"},
                ],
            },
            {
                "seriesID": SERIES_IDS["index"],
                "data": [
                    {"year": "2024", "period": "Q05", "value": "115.366"},
                    {"year": "2025", "period": "Q05", "value": "117.785"},
                ],
            },
        ]

        payload = build_payload(series)

        self.assertEqual(payload["series_ids"]["percent_change"], "PRS85006091")
        self.assertEqual(payload["series_ids"]["index"], "PRS85006093")
        self.assertEqual(
            payload["records"],
            [
                {"year": 2024, "percent_change": 3.0, "index": 115.366},
                {"year": 2025, "percent_change": 2.1, "index": 117.785},
            ],
        )

    def test_fails_closed_when_index_history_is_incomplete(self) -> None:
        series = [
            {
                "seriesID": SERIES_IDS["percent_change"],
                "data": [
                    {"year": "2024", "period": "Q05", "value": "3.0"},
                    {"year": "2025", "period": "Q05", "value": "2.1"},
                ],
            },
            {
                "seriesID": SERIES_IDS["index"],
                "data": [{"year": "2025", "period": "Q05", "value": "117.785"}],
            },
        ]

        with self.assertRaisesRegex(AssertionError, "index missing annual years"):
            build_payload(series)

    def test_materialized_filename_is_content_addressed(self) -> None:
        payload = {
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
