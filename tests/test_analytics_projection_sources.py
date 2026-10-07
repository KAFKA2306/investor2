from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analytics.projection_sources import ProjectionSourceError, load_projection_rows


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_snapshot_catalog(root: Path, rows: list[dict[str, object]]) -> None:
    path = root / "data/input_ledger/snapshot_catalog.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def snapshot(snapshot_id: str = "snap-1") -> dict[str, object]:
    return {
        "snapshot_id": snapshot_id,
        "dataset_id": "dataset-1",
        "reuse_key": "fixture/reuse",
        "artifact_path": "data/fixture.json",
        "artifact_sha256": "a" * 64,
        "record_count": 2,
        "schema_version": "fixture.v1",
        "source": "fixture-source",
        "source_kind": "official_web",
        "observed_at": "2026-01-01T00:00:00Z",
        "provenance": {"source_urls": ["https://example.com"]},
        "status": "accepted",
    }


class ProjectionSourceTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        write_snapshot_catalog(root, [snapshot()])
        write_json(
            root / "data/hypothesis_lab/hypotheses/h1.json",
            {
                "schema_version": "1.0",
                "hypothesis_id": "h1",
                "thesis": "Fixture thesis",
                "falsifiers": ["fixture falsifier"],
            },
        )
        write_json(
            root / "docs/research/results/fixture/summary.json",
            {
                "research_question": "Does the fixture survive OOS?",
                "verdict": "REJECT",
                "as_of": "2026-01-02",
            },
        )
        write_json(
            root / "data/benchmarks/fixture.json",
            {
                "schema_version": 1,
                "split_id": "benchmark-1",
                "source": {
                    "dataset": "fixture-dataset",
                    "revision": "abc123",
                    "row_count": 10,
                },
            },
        )

    def test_loads_all_canonical_projection_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)

            rows = load_projection_rows(root)

            self.assertEqual(set(rows), {
                "input_snapshots",
                "hypotheses",
                "oos_results",
                "benchmark_contracts",
            })
            self.assertEqual(rows["input_snapshots"][0]["snapshot_id"], "snap-1")
            self.assertIn(
                '"source_urls":["https://example.com"]',
                rows["input_snapshots"][0]["provenance_json"],
            )
            self.assertEqual(rows["hypotheses"][0]["falsifier_count"], 1)
            self.assertEqual(rows["oos_results"][0]["verdict"], "REJECT")
            self.assertEqual(rows["benchmark_contracts"][0]["row_count"], 10)

    def test_snapshot_projection_fails_closed_on_nonaccepted_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            rejected = snapshot()
            rejected["status"] = "rejected"
            write_snapshot_catalog(root, [rejected])

            with self.assertRaisesRegex(ProjectionSourceError, "non-accepted"):
                load_projection_rows(root)

    def test_snapshot_projection_rejects_duplicate_point_in_time_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            second = snapshot("snap-2")
            write_snapshot_catalog(root, [snapshot(), second])

            with self.assertRaisesRegex(
                ProjectionSourceError,
                "duplicate reuse_key \+ observed_at",
            ):
                load_projection_rows(root)


if __name__ == "__main__":
    unittest.main()
