from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.paper_family_frontier import merge_readme, render, render_readme_block, validate


class PaperFamilyFrontierTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs" / "paper").mkdir(parents=True)
        return root

    @staticmethod
    def family(family_id: str, page: str, url: str | None, verdict: str | None = None) -> dict[str, object]:
        return {
            "family_id": family_id,
            "canonical_name": family_id,
            "canonical_page": page,
            "primary_url": url,
            "historical_aliases": [],
            "task_class": "alpha_discovery",
            "claimed_capability": "test capability",
            "representative": "paper method",
            "market_dataset_universe": "test universe",
            "original_sample_dates": "test dates",
            "native_benchmark": "test benchmark",
            "primary_metric": "test metric",
            "required_data_license_state": "OPEN",
            "reproduction_state": "NOT_RUN",
            "head_to_head": "NOT_RUN",
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
                self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670"),
                self.family("b", "docs/paper/b.md", "https://arxiv.org/abs/2602.14670"),
            ]
        )
        with self.assertRaisesRegex(AssertionError, "duplicate paper identity"):
            validate(root, registry)

    def test_filename_content_identity_mismatch_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 9999.99999", encoding="utf-8")
        registry = self.registry([self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")])
        with self.assertRaisesRegex(AssertionError, "filename/content identity mismatch"):
            validate(root, registry)

    def test_missing_primary_url_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("paper", encoding="utf-8")
        with self.assertRaisesRegex(AssertionError, "missing canonical primary URL"):
            validate(root, self.registry([self.family("a", "docs/paper/a.md", None)]))

    def test_missing_required_contract_field_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")
        del family["native_benchmark"]
        with self.assertRaisesRegex(AssertionError, "family missing required fields"):
            validate(root, self.registry([family]))

    def test_superseded_alias_fails_if_it_returns(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/old.md").write_text("duplicate", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")
        family["historical_aliases"] = ["docs/paper/old.md"]
        family["superseded_files"] = ["docs/paper/old.md"]
        with self.assertRaisesRegex(AssertionError, "superseded paper alias"):
            validate(root, self.registry([family]))

    def test_alias_and_superseded_lists_must_match(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")
        family["historical_aliases"] = ["docs/paper/old.md"]
        with self.assertRaisesRegex(AssertionError, "alias/superseded mismatch"):
            validate(root, self.registry([family]))

    def test_canonical_authorities_are_fixed(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")
        family["canonical_reproduction"]["benchmark_contract_issue"] = 999  # type: ignore[index]
        with self.assertRaisesRegex(AssertionError, "does not reuse #51"):
            validate(root, self.registry([family]))

    def test_verdict_requires_head_to_head_evidence(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        family = self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670", "BEAT")
        with self.assertRaisesRegex(AssertionError, "verdict without head-to-head evidence"):
            validate(root, self.registry([family]))

    def test_unmapped_markdown_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/unmapped.md").write_text("unmapped", encoding="utf-8")
        registry = self.registry([self.family("a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670")])
        with self.assertRaisesRegex(AssertionError, "unmapped docs/paper markdown"):
            validate(root, registry)

    def test_global_superiority_stays_unproven_until_every_family_beats(self) -> None:
        winner = self.family("a", "docs/paper/a.md", None, "BEAT")
        winner["head_to_head"] = "COMPLETE"
        unresolved = self.registry([winner, self.family("b", "docs/paper/b.md", None, None)])
        self.assertIn("Global superiority:** UNPROVEN", render(unresolved))
        self.assertIn("1/2 families are BEAT", render(unresolved))

    def test_readme_uses_only_registry_families_and_head_to_head_state(self) -> None:
        winner = self.family("winner", "docs/paper/winner.md", None, "BEAT")
        winner["head_to_head"] = "COMPLETE"
        registry = self.registry([winner, self.family("unknown", "docs/paper/unknown.md", None, None)])
        block = render_readme_block(registry)
        self.assertIn("BEAT 1 / TIE 0 / LOSE 0 / BLOCKED 1", block)
        self.assertIn("[winner](docs/paper/winner.md)", block)
        self.assertIn("[unknown](docs/paper/unknown.md)", block)
        self.assertIn("COMPLETE", block)
        self.assertNotIn("AlphaZeroBeta", block)

    def test_readme_block_replaces_itself(self) -> None:
        registry = self.registry([self.family("a", "docs/paper/a.md", None)])
        first = merge_readme("# Repo\n\ntext\n", render_readme_block(registry))
        second = merge_readme(first, render_readme_block(registry))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
