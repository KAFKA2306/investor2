#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]

MOVES = {
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
    "docs/research/us-corporate-profits-2026-08-21.md": "docs/research/studies/us-corporate-profits-2026-08-21.md",
    "docs/research/warin_2101_02044_v4_experiment_matrix.json": "docs/research/contracts/warin_2101_02044_v4_experiment_matrix.json",
    "docs/research/session_state_161_preregistration.md": "docs/research/protocols/daily_market_session_161_preregistration.md",
    "docs/research/session_state_161_evidence_plan.md": "docs/research/protocols/daily_market_session_161_evidence_plan.md",
    "src/research/session_state.py": "src/research/daily_market_session_features.py",
    "scripts/session_state_baseline.py": "scripts/daily_market_session_baseline.py",
    "scripts/session_state_oos.py": "scripts/daily_market_session_oos.py",
    "tests/test_session_state.py": "tests/test_daily_market_session_features.py",
    "tests/test_session_state_baseline.py": "tests/test_daily_market_session_baseline.py",
    "tests/test_session_state_oos.py": "tests/test_daily_market_session_oos.py",
    ".github/workflows/alphazerobeta-market-snapshot.yml": ".github/workflows/market-snapshot-daily-session.yml",
}
EXTRA = {
    "scripts.session_state_baseline": "scripts.daily_market_session_baseline",
    "scripts.session_state_oos": "scripts.daily_market_session_oos",
    "src.research.session_state": "src.research.daily_market_session_features",
    "investor2.session-state-oos.v1": "investor2.daily-market-session-oos.v1",
    "investor2.session-state-baseline.v1": "investor2.daily-market-session-baseline.v1",
}


def move_files() -> None:
    for old, new in MOVES.items():
        source, target = ROOT / old, ROOT / new
        if not source.is_file():
            raise SystemExit(f"missing migration source: {old}")
        if target.exists():
            raise SystemExit(f"migration target already exists: {new}")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)


def replace_references() -> None:
    replacements = {**MOVES, **EXTRA}
    excluded = {
        "scripts/migrate_research_layout_once.py",
        ".github/workflows/research-layout-migrate.yml",
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in excluded:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        updated = updated.replace("# Issue #161 — session-state research protocol", "# Issue #161 — daily market session research protocol")
        updated = updated.replace("assumptions in the session-state code", "assumptions in the daily-market-session code")
        updated = updated.replace("One generic session-state implementation", "One generic daily-market-session implementation")
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def write_contracts() -> None:
    (ROOT / "docs/research/README.md").write_text("""# Research evidence

`docs/research/` stores durable research evidence. Chat history, agent reasoning, and temporary implementation notes are not repository state.

## Directory contract

- `catalogs/` — paper registries, selection manifests, schemas, and version pins used to define research scope.
- `contracts/` — frozen experiment, data, split, and decision contracts fixed before evaluation.
- `data/` — small versioned research inputs and source snapshots.
- `data_access/` — data-access documentation and acquisition boundaries.
- `frontier/` — canonical machine-readable paper/factor frontier registries used to generate public comparison views.
- `protocols/` — preregistered research protocols and evaluation procedures.
- `results/` — canonical summaries and validated result artifacts.
- `runs/` — immutable run-level evidence bundles.
- `studies/` — standalone company, macro, and hypothesis studies.
- `assets/` — figures and supporting assets.

The root of `docs/research/` contains only this `README.md`. New evidence must be placed by responsibility rather than dropped into the root.

## State discipline

A path should reveal an artifact's role without opening it. Machine-readable artifacts are authoritative where a workflow declares them canonical. Markdown summaries and public views point to those artifacts rather than becoming independent state stores.

Durable continuation belongs in the existing Issue/PR and versioned evidence artifacts. Do not depend on chat memory to reconstruct research state.
""", encoding="utf-8")

    moved_repr = pformat(MOVES, sort_dicts=True, width=100)
    extra_repr = pformat(EXTRA, sort_dicts=True, width=100)
    (ROOT / "tests/test_research_layout.py").write_text(f'''from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
EXPECTED_DIRECTORIES = {{"assets", "catalogs", "contracts", "data", "data_access", "frontier", "protocols", "results", "runs", "studies"}}
MOVED_PATHS = {moved_repr}
FORBIDDEN_REFERENCES = {extra_repr}

class ResearchLayoutTest(unittest.TestCase):
    def test_research_root_contains_only_navigation(self) -> None:
        self.assertEqual({{p.name for p in RESEARCH.iterdir() if p.is_file()}}, {{"README.md"}})

    def test_research_role_directories_are_explicit(self) -> None:
        self.assertLessEqual(EXPECTED_DIRECTORIES, {{p.name for p in RESEARCH.iterdir() if p.is_dir()}})

    def test_superseded_paths_do_not_return(self) -> None:
        existing = sorted(path for path in MOVED_PATHS if (ROOT / path).exists())
        self.assertFalse(existing, f"superseded paths returned: {{existing}}")

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
                    stale.append(f"{{relative}}: {{old}}")
        self.assertFalse(stale, "stale research references remain:\\n" + "\\n".join(sorted(stale)))

if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def finalize_workflow() -> None:
    path = ROOT / ".github/workflows/paper-family-frontier.yml"
    text = path.read_text(encoding="utf-8")
    text = text.replace("permissions:\n  contents: write\n", "permissions:\n  contents: read\n")
    start = text.index("  # research-layout-migration:start\n")
    end = text.index("  # research-layout-migration:end\n") + len("  # research-layout-migration:end\n")
    text = text[:start] + text[end:]
    text = text.replace(
        "      - name: Prove duplicate, mismatch, alias, coverage, and README gates\n        run: python -m unittest discover -s tests -p 'test_paper_family_frontier.py'\n      - name: Compile validator\n        run: python -m py_compile scripts/paper_family_frontier.py tests/test_paper_family_frontier.py\n",
        "      - name: Prove family identity and research layout gates\n        run: |\n          python -m unittest discover -s tests -p 'test_paper_family_frontier.py'\n          python -m unittest discover -s tests -p 'test_research_layout.py'\n      - name: Compile validators\n        run: python -m py_compile scripts/paper_family_frontier.py tests/test_paper_family_frontier.py tests/test_research_layout.py\n",
    )
    path.write_text(text, encoding="utf-8")
    temporary = ROOT / ".github/workflows/research-layout-migrate.yml"
    if temporary.exists():
        temporary.unlink()
    Path(__file__).unlink()


def main() -> None:
    move_files()
    replace_references()
    write_contracts()
    finalize_workflow()


if __name__ == "__main__":
    main()
