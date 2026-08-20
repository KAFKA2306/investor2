from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts import build_ark_repository_coverage as MODULE

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def verified_probe(
    repository: str,
    evidence_url: str | None = None,
) -> dict[str, Any]:
    return {
        "exists": True,
        "scheduled": True,
        "latest_passed": True,
        "evidence_commit": "a" * 40,
    }


def verified_output_probe(url: str | None) -> dict[str, bool]:
    return {"available": True, "primary": True, "raw": True}


class ArkRepositoryCoverageTest(unittest.TestCase):
    def build(self):
        return MODULE.build(
            load("data/ark-big-ideas/repository-coverage-catalog.json"),
            load("data/ark-big-ideas/source-catalog.json"),
            load("api/v1/ark-big-ideas/evidence-matrix.json"),
            load("api/v1/ark-big-ideas/claim-evidence.json"),
            live=True,
            repo_probe=verified_probe,
            output_probe=verified_output_probe,
            checked_at="2026-08-20T00:00:00+00:00",
        )

    def test_catalog_has_exactly_13_ark_themes(self):
        themes = MODULE.validate_catalog(
            load("data/ark-big-ideas/repository-coverage-catalog.json")
        )
        self.assertEqual(len(themes), 13)
        self.assertEqual(len({row["theme"] for row in themes}), 13)

    def test_bitcoin_requires_all_three_components(self):
        result = self.build()
        bitcoin = next(row for row in result["records"] if row["theme"] == "Bitcoin")
        self.assertEqual(len(bitcoin["components"]), 3)
        network = next(
            row
            for row in bitcoin["components"]
            if row["logical_repo"] == "bitcoin-network"
        )
        self.assertFalse(network["real_data_exists"])
        self.assertFalse(network["investor2_integration_exists"])
        self.assertFalse(bitcoin["real_data_exists"])
        self.assertFalse(bitcoin["investor2_integration_exists"])

    def test_multiomics_legacy_feed_does_not_complete_canonical_repo(self):
        result = self.build()
        multiomics = next(
            row for row in result["records"] if row["theme"] == "Multiomics"
        )
        component = multiomics["components"][0]
        self.assertEqual(component["current_repo"], "KAFKA2306/multiomics")
        self.assertEqual(component["source_catalog_repo"], "KAFKA2306/kafin3")
        self.assertFalse(component["canonical_alignment"])
        self.assertFalse(component["real_data_exists"])
        self.assertTrue(component["investor2_integration_exists"])
        self.assertFalse(multiomics["real_data_exists"])

    def test_great_acceleration_does_not_require_a_dedicated_repo(self):
        result = self.build()
        row = next(
            record
            for record in result["records"]
            if record["theme"] == "The Great Acceleration"
        )
        self.assertFalse(row["dedicated_repository_required"])
        self.assertEqual(row["canonical_repositories"], ["KAFKA2306/investor2"])
        self.assertTrue(row["real_data_exists"])
        self.assertTrue(row["investor2_integration_exists"])

    def test_noncanonical_robot_and_space_repos_are_never_counted(self):
        result = self.build()
        repos = {
            repo
            for row in result["records"]
            for repo in row["canonical_repositories"]
        }
        self.assertNotIn("KAFKA2306/robot", repos)
        self.assertNotIn("KAFKA2306/space", repos)
        self.assertIn("KAFKA2306/factory", repos)
        self.assertIn("KAFKA2306/trahist", repos)

    def test_csv_has_one_row_per_theme(self):
        result = self.build()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coverage.csv"
            MODULE.write_csv(path, result)
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 13)
        self.assertEqual(
            set(rows[0]),
            {
                "theme",
                "canonical_repo",
                "real_data",
                "primary_source_provenance",
                "reproducible",
                "scheduled_workflow",
                "latest_workflow_passed",
                "public_view",
                "investor2_integration",
                "evidence_commit",
            },
        )


if __name__ == "__main__":
    unittest.main()
