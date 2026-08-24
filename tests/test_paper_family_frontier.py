from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.paper_family_frontier import render, validate


class PaperFamilyFrontierTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs" / "paper").mkdir(parents=True)
        return root

    @staticmethod
    def family(
        family_id: str,
        page: str,
        url: str = "https://arxiv.org/abs/2602.14670",
        verdict: str | None = None,
        head_to_head: str = "NOT_RUN",
    ) -> dict[str, object]:
        return {
            "family_id": family_id,
            "canonical_name": family_id,
            "canonical_page": page,
            "primary_url": url,
            "historical_aliases": [],
            "task_class": "alpha_discovery",
            "claimed_capability": "test capability",
            "representative": "paper method",
            "market_dataset_universe": None,
            "original_sample_dates": None,
            "native_benchmark": None,
            "primary_metric": "test metric",
            "required_data_license_state": "TO_VERIFY",
            "reproduction_state": "NOT_RUN",
            "head_to_head": head_to_head,
            "canonical_reproduction": {
                "benchmark_contract_issue": 51,
                "inspection_queue_issue": 55,
                "japan_equity_contract_issue": 184,
                "artifact": None,
            },
            "superseded_files": [],
            "verdict": verdict,
        }

    @staticmethod
    def registry(families: list[dict[str, object]]) -> dict[str, object]:
        return {
            "schema_version": "investor2.paper-family-frontier.v2",
            "families": families,
            "repository_material": [],
        }

    def test_duplicate_paper_identity_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/b.md").write_text("arXiv 2602.14670", encoding="utf-8")
        registry = self.registry(
            [
                self.family("a", "docs/paper/a.md"),
                self.family("b", "docs/paper/b.md"),
            ]
        )
        with self.assertRaisesRegex(AssertionError, "duplicate paper identity"):
            validate(root, registry)

    def test_filename_content_identity_mismatch_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 9999.99999", encoding="utf-8")
        registry = self.registry([self.family("a", "docs/paper/a.md")])
        with self.assertRaisesRegex(AssertionError, "filename/content identity mismatch"):
            validate(root, registry)

    def test_superseded_alias_fails_if_it_returns(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/old.md").write_text("duplicate", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md")
        family["historical_aliases"] = ["docs/paper/old.md"]
        family["superseded_files"] = ["docs/paper/old.md"]
        with self.assertRaisesRegex(AssertionError, "superseded paper alias"):
            validate(root, self.registry([family]))

    def test_unmapped_markdown_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/unmapped.md").write_text("unmapped", encoding="utf-8")
        registry = self.registry([self.family("a", "docs/paper/a.md")])
        with self.assertRaisesRegex(AssertionError, "unmapped docs/paper markdown"):
            validate(root, registry)

    def test_missing_contract_field_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md")
        del family["required_data_license_state"]
        with self.assertRaisesRegex(AssertionError, "missing required fields"):
            validate(root, self.registry([family]))

    def test_verdict_without_head_to_head_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", verdict="BEAT")
        with self.assertRaisesRegex(AssertionError, "verdict without head-to-head evidence"):
            validate(root, self.registry([family]))

    def test_global_superiority_stays_unproven_until_every_family_beats(self) -> None:
        unresolved = self.registry(
            [
                self.family("a", "docs/paper/a.md", verdict="BEAT", head_to_head="EVIDENCE"),
                self.family("b", "docs/paper/b.md", url="https://arxiv.org/abs/2602.14671"),
            ]
        )
        self.assertIn("Global superiority:** UNPROVEN", render(unresolved))
        self.assertIn("1/2 families are BEAT", render(unresolved))

    def test_global_superiority_becomes_proven_only_when_all_beat(self) -> None:
        all_beat = self.registry(
            [
                self.family("a", "docs/paper/a.md", verdict="BEAT", head_to_head="EVIDENCE"),
                self.family(
                    "b",
                    "docs/paper/b.md",
                    url="https://arxiv.org/abs/2602.14671",
                    verdict="BEAT",
                    head_to_head="EVIDENCE",
                ),
            ]
        )
        self.assertIn("Global superiority:** PROVEN", render(all_beat))
        self.assertIn("2/2 families are BEAT; 0 remain unresolved", render(all_beat))


if __name__ == "__main__":
    unittest.main()
