from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
EXPECTED_DIRECTORIES = {
    "assets",
    "catalogs",
    "contracts",
    "data",
    "data_access",
    "frontier",
    "protocols",
    "results",
    "runs",
    "studies",
}
MOVED_PATHS = {
    ".github/workflows/alphazerobeta-market-snapshot.yml": ".github/workflows/market-snapshot-daily-session.yml",
    "docs/research/2010s_paper_catalog.json": "docs/research/catalogs/2010s_paper_catalog.json",
    "docs/research/2010s_paper_catalog.md": "docs/research/catalogs/2010s_paper_catalog.md",
    "docs/research/2010s_paper_validation_repeated.json": "docs/research/results/2010s_paper_validation_repeated.json",
    "docs/research/2019_arxiv_finance_registry.json": "docs/research/catalogs/2019_arxiv_finance_registry.json",
    "docs/research/2021_arxiv_finance_registry.json": "docs/research/catalogs/2021_arxiv_finance_registry.json",
    "docs/research/2026-08-14-sandisk-investor-day-edinet50.md": "docs/research/studies/2026-08-14-sandisk-investor-day-edinet50.md",
    "docs/research/2026-08-16-sb-energy-ai-infrastructure-thesis.md": "docs/research/studies/2026-08-16-sb-energy-ai-infrastructure-thesis.md",
    "docs/research/2026-08-16-sbg-edinet-related-companies.md": "docs/research/studies/2026-08-16-sbg-edinet-related-companies.md",
    "docs/research/ai_strategy_validation_protocol.md": "docs/research/protocols/ai_strategy_validation_protocol.md",
    "docs/research/alphazerobeta-paper-reproduction.md": "docs/research/results/alphazerobeta-paper-reproduction.md",
    "docs/research/alphazerobeta_validation.md": "docs/research/results/alphazerobeta_validation.md",
    "docs/research/arxiv_data_requirement_schema_v1.json": "docs/research/catalogs/arxiv_data_requirement_schema_v1.json",
    "docs/research/arxiv_qfin_2019_data_requirements.json": "docs/research/catalogs/arxiv_qfin_2019_data_requirements.json",
    "docs/research/arxiv_qfin_2019_selection_manifest.json": "docs/research/catalogs/arxiv_qfin_2019_selection_manifest.json",
    "docs/research/arxiv_qfin_2019_split_contracts.json": "docs/research/contracts/arxiv_qfin_2019_split_contracts.json",
    "docs/research/arxiv_qfin_2019_version_pins.json": "docs/research/catalogs/arxiv_qfin_2019_version_pins.json",
    "docs/research/arxiv_qfin_2021_selection_manifest.json": "docs/research/catalogs/arxiv_qfin_2021_selection_manifest.json",
    "docs/research/arxiv_qfin_2021_version_pins.json": "docs/research/catalogs/arxiv_qfin_2021_version_pins.json",
    "docs/research/arxiv_qfin_selector_rules_v1.json": "docs/research/catalogs/arxiv_qfin_selector_rules_v1.json",
    "docs/research/arxiv_split_contract_schema_v1.json": "docs/research/catalogs/arxiv_split_contract_schema_v1.json",
    "docs/research/arxiv_version_pin_schema_v1.json": "docs/research/catalogs/arxiv_version_pin_schema_v1.json",
    "docs/research/hypothesis-lab.md": "docs/research/studies/hypothesis-lab.md",
    "docs/research/jr_west_ureshito_eps.md": "docs/research/studies/jr_west_ureshito_eps.md",
    "docs/research/kenneth_french_current_snapshot_2026-06.json": "docs/research/data/kenneth_french_current_snapshot_2026-06.json",
    "docs/research/kenneth_french_factor_vintage_contract.json": "docs/research/contracts/kenneth_french_factor_vintage_contract.json",
    "docs/research/multi_paper_oos_summary.md": "docs/research/results/multi_paper_oos_summary.md",
    "docs/research/official_current_paper_factor_suite.json": "docs/research/frontier/official_current_paper_factor_suite.json",
    "docs/research/paper_factor_registry.json": "docs/research/frontier/paper_factor_registry.json",
    "docs/research/paper_family_frontier.json": "docs/research/frontier/paper_family_frontier.json",
    "docs/research/post_publication_momentum_oos.json": "docs/research/results/post_publication_momentum_oos.json",
    "docs/research/post_publication_momentum_oos.md": "docs/research/results/post_publication_momentum_oos.md",
    "docs/research/sandisk_growth_decision_contract.json": "docs/research/contracts/sandisk_growth_decision_contract.json",
    "docs/research/session_state_161_evidence_plan.md": "docs/research/protocols/daily_market_session_161_evidence_plan.md",
    "docs/research/session_state_161_preregistration.md": "docs/research/protocols/daily_market_session_161_preregistration.md",
    "docs/research/us-corporate-profits-2026-08-21.md": "docs/research/studies/us-corporate-profits-2026-08-21.md",
    "docs/research/warin_2101_02044_v4_experiment_matrix.json": "docs/research/contracts/warin_2101_02044_v4_experiment_matrix.json",
    "scripts/session_state_baseline.py": "scripts/daily_market_session_baseline.py",
    "scripts/session_state_oos.py": "scripts/daily_market_session_oos.py",
    "src/research/session_state.py": "src/research/daily_market_session_features.py",
    "tests/test_session_state.py": "tests/test_daily_market_session_features.py",
    "tests/test_session_state_baseline.py": "tests/test_daily_market_session_baseline.py",
    "tests/test_session_state_oos.py": "tests/test_daily_market_session_oos.py",
}
FORBIDDEN_REFERENCES = {
    "investor2.session-state-baseline.v1": "investor2.daily-market-session-baseline.v1",
    "investor2.session-state-oos.v1": "investor2.daily-market-session-oos.v1",
    "scripts.session_state_baseline": "scripts.daily_market_session_baseline",
    "scripts.session_state_oos": "scripts.daily_market_session_oos",
    "src.research.session_state": "src.research.daily_market_session_features",
}


class ResearchLayoutTest(unittest.TestCase):
    def test_research_root_contains_only_navigation(self) -> None:
        self.assertEqual({p.name for p in RESEARCH.iterdir() if p.is_file()}, {"README.md"})

    def test_research_role_directories_are_explicit(self) -> None:
        self.assertLessEqual(EXPECTED_DIRECTORIES, {p.name for p in RESEARCH.iterdir() if p.is_dir()})

    def test_superseded_paths_do_not_return(self) -> None:
        existing = sorted(path for path in MOVED_PATHS if (ROOT / path).exists())
        self.assertFalse(existing, f"superseded paths returned: {existing}")

    def test_stale_references_do_not_return(self) -> None:
        stale = []
        forbidden = set(MOVED_PATHS) | set(FORBIDDEN_REFERENCES)
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative == "tests/test_research_layout.py":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for old in forbidden:
                if old in text:
                    stale.append(f"{relative}: {old}")
        self.assertFalse(stale, "stale research references remain:\n" + "\n".join(sorted(stale)))


if __name__ == "__main__":
    unittest.main()
