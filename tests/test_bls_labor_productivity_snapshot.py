from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.bls_labor_productivity_snapshot import build_payload, materialize_snapshot


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class BlsLaborProductivitySnapshotTest(unittest.TestCase):
    def make_fixture(self, root: Path, *, include_2024_index: bool = True) -> dict[str, Path]:
        paths = {
            name: root / name
            for name in ["pr.series", "pr.sector", "pr.measure", "pr.duration", "pr.period", "pr.data"]
        }
        write(paths["pr.sector"], "sector_code\tsector_name\n8500\tNonfarm Business\n")
        write(paths["pr.measure"], "measure_code\tmeasure_text\n09\tLabor productivity (output per hour)\n")
        write(
            paths["pr.duration"],
            "duration_code\tduration_text\n"
            "1\t% Change same quarter 1 year ago\n"
            "2\t% Change from previous quarter\n"
            "3\tIndex (2017=100)\n",
        )
        write(paths["pr.period"], "period\tperiod_name\nQ01\t1st Quarter\nQ05\tAnnual Average\n")
        write(
            paths["pr.series"],
            "series_id\tsector_code\tmeasure_code\tduration_code\tseasonal\tbase_year\n"
            "PRS85006091\t8500\t09\t1\tS\t-\n"
            "PRS85006093\t8500\t09\t3\tS\t2017\n",
        )
        index_2024 = "PRS85006093\t2024\tQ05\t115.366\n" if include_2024_index else ""
        write(
            paths["pr.data"],
            "series_id\tyear\tperiod\tvalue\n"
            "PRS85006091\t2024\tQ01\t3.3\n"
            "PRS85006091\t2024\tQ05\t3.0\n"
            "PRS85006091\t2025\tQ05\t2.1\n"
            f"{index_2024}"
            "PRS85006093\t2025\tQ05\t117.785\n",
        )
        return paths

    def test_extracts_only_official_annual_average_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.make_fixture(Path(tmp))
            payload = build_payload(
                series_path=paths["pr.series"],
                sector_path=paths["pr.sector"],
                measure_path=paths["pr.measure"],
                duration_path=paths["pr.duration"],
                period_path=paths["pr.period"],
                data_path=paths["pr.data"],
            )

            self.assertEqual(payload["series_ids"]["percent_change"], "PRS85006091")
            self.assertEqual(payload["series_ids"]["index"], "PRS85006093")
            self.assertEqual(payload["records"], [
                {"year": 2024, "percent_change": 3.0, "index": 115.366},
                {"year": 2025, "percent_change": 2.1, "index": 117.785},
            ])

    def test_fails_closed_when_index_history_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.make_fixture(Path(tmp), include_2024_index=False)
            with self.assertRaisesRegex(AssertionError, "index missing annual years"):
                build_payload(
                    series_path=paths["pr.series"],
                    sector_path=paths["pr.sector"],
                    measure_path=paths["pr.measure"],
                    duration_path=paths["pr.duration"],
                    period_path=paths["pr.period"],
                    data_path=paths["pr.data"],
                )

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
