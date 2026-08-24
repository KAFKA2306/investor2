from __future__ import annotations

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
FORBIDDEN_PATHS = {
    "src/research/session_state.py",
    "scripts/session_state_baseline.py",
    "tests/test_session_state.py",
    "tests/test_session_state_baseline.py",
    "docs/research/session_state_161_preregistration.md",
}


def test_research_root_contains_only_navigation() -> None:
    direct_files = {path.name for path in RESEARCH.iterdir() if path.is_file()}
    assert direct_files == {"README.md"}


def test_research_role_directories_are_explicit() -> None:
    direct_directories = {path.name for path in RESEARCH.iterdir() if path.is_dir()}
    assert EXPECTED_DIRECTORIES <= direct_directories


def test_ambiguous_session_state_paths_do_not_return() -> None:
    existing = sorted(path for path in FORBIDDEN_PATHS if (ROOT / path).exists())
    assert not existing, f"ambiguous legacy paths returned: {existing}"
