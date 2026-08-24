from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.paper_family_frontier import render, render_readme_block, validate


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
        url: str | None,
        verdict: str | None = None,
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
            "primary_metric": "test metric",
            "reproduction_state": "NOT_RUN",
            "verdict": verdict,
        }

    @staticmethod
    def registry(families: list[dict[str, object]]) -> dict[str, object]:
        return {
            "schema_version": "investor2.paper-family-frontier.v1",
            "families": families,
            "repository_material": [],
        }

    def test_duplicate_paper_identity_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/b.md").write_text("arXiv 2602.14670", encoding="utf-8")
        registry = self.registry(
            [
                self.family(
                    "a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670"
                ),
                self.family(
                    "b", "docs/paper/b.md", "https://arxiv.org/abs/2602.14670"
                ),
            ]
        )
        with self.assertRaisesRegex(AssertionError, "duplicate paper identity"):
            validate(root, registry)

    def test_filename_content_identity_mismatch_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 9999.99999", encoding="utf-8")
        registry = self.registry(
            [
                self.family(
                    "a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670"
                )
            ]
        )
        with self.assertRaisesRegex(
            AssertionError, "filename/content identity mismatch"
        ):
            validate(root, registry)

    def test_superseded_alias_fails_if_it_returns(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/old.md").write_text("duplicate", encoding="utf-8")
        family = self.family(
            "a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670"
        )
        family["historical_aliases"] = ["docs/paper/old.md"]
        with self.assertRaisesRegex(AssertionError, "superseded paper alias"):
            validate(root, self.registry([family]))

    def test_unmapped_markdown_fails(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("arXiv 2602.14670", encoding="utf-8")
        (root / "docs/paper/unmapped.md").write_text("unmapped", encoding="utf-8")
        registry = self.registry(
            [
                self.family(
                    "a", "docs/paper/a.md", "https://arxiv.org/abs/2602.14670"
                )
            ]
        )
        with self.assertRaisesRegex(AssertionError, "unmapped docs/paper markdown"):
            validate(root, registry)

    def test_global_superiority_stays_unproven_until_every_family_beats(self) -> None:
        unresolved = self.registry(
            [
                self.family("a", "docs/paper/a.md", None, "BEAT"),
                self.family("b", "docs/paper/b.md", None, None),
            ]
        )
        self.assertIn("Global superiority:** UNPROVEN", render(unresolved))
        self.assertIn("1/2 families are BEAT", render(unresolved))

    def test_readme_shows_loss_and_blocks_unmeasured_family(self) -> None:
        root = self.make_root()
        (root / "docs/paper/a.md").write_text("paper", encoding="utf-8")
        hypothesis_path = (
            root
            / "data/hypothesis_lab/hypotheses/alphazerobeta_market_neutral_v1.json"
        )
        hypothesis_path.parent.mkdir(parents=True)
        hypothesis_path.write_text(
            json.dumps(
                {
                    "replication_boundary": {
                        "reason": "licensed Bloomberg-dependent data"
                    }
                }
            ),
            encoding="utf-8",
        )
        result_path = (
            root
            / "docs/research/results/alphazerobeta_jquants_free/summary.json"
        )
        result_path.parent.mkdir(parents=True)
        result_path.write_text(
            json.dumps(
                {
                    "trained_asset_count": 64,
                    "walk_forward": {"folds": 2},
                    "primary_lambda_corr_0_5": {
                        "cumulative_return": -0.057240358021085624,
                        "annualized_sharpe": -2.12854850143814,
                        "benchmark_correlation": 0.05283990465526373,
                        "max_drawdown": -0.08076075113144454,
                    },
                    "verdict": "reject",
                }
            ),
            encoding="utf-8",
        )

        block = render_readme_block(
            root,
            self.registry([self.family("a", "docs/paper/a.md", None)]),
        )

        self.assertIn("LOSE 1 / BLOCKED 1", block)
        self.assertIn("return -5.7240%", block)
        self.assertIn("Sharpe -2.1285", block)
        self.assertIn("**LOSE**", block)
        self.assertIn("**BLOCKED**", block)
        self.assertLess(block.index("[AlphaZeroBeta]"), block.index("[a]"))


if __name__ == "__main__":
    unittest.main()
