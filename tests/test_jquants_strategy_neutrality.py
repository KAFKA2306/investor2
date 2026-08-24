from pathlib import Path

OLD_SHARED_ENTRY_POINTS = (
    "scripts/alphazerobeta_jquants_free_ephemeral.py",
    "scripts/alphazerobeta_jquants_private_hf_cache.py",
    "scripts/alphazerobeta_jquants_pit_master_ephemeral.py",
    "scripts/alphazerobeta_japan_free_prepare.py",
)

NEUTRAL_ENTRY_POINTS = (
    "scripts/jquants_free_ephemeral.py",
    "scripts/jquants_private_hf_cache.py",
    "scripts/jquants_pit_master_ephemeral.py",
    "scripts/jquants_japan_panel.py",
)


def test_shared_jquants_entry_points_are_strategy_neutral() -> None:
    for path in OLD_SHARED_ENTRY_POINTS:
        assert not Path(path).exists(), path
    for path in NEUTRAL_ENTRY_POINTS:
        assert Path(path).is_file(), path


def test_alphazerobeta_workflow_does_not_execute_alphacrafter() -> None:
    text = Path(".github/workflows/alphazerobeta-jquants-free-validation.yml").read_text()
    assert "alphacrafter" not in text.lower()


def test_shared_consumers_use_neutral_jquants_entry_points() -> None:
    paths = (
        ".github/workflows/jquants-personal-hf-cache.yml",
        ".github/workflows/alphacrafter-jquants-frontier.yml",
        ".github/workflows/alphazerobeta-jquants-free-validation.yml",
        ".github/workflows/alphazerobeta-eda-stats.yml",
        "docs/specs/jquants-personal-hf-cache.md",
    )
    forbidden = (
        "alphazerobeta_jquants_free_ephemeral",
        "alphazerobeta_jquants_private_hf_cache",
        "alphazerobeta_jquants_pit_master_ephemeral",
        "alphazerobeta_japan_free_prepare",
    )
    for path in paths:
        text = Path(path).read_text()
        assert not any(name in text for name in forbidden), path
