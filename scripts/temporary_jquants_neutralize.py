from pathlib import Path


MOVES = {
    "scripts/alphazerobeta_jquants_free_ephemeral.py": "scripts/jquants_free_ephemeral.py",
    "scripts/alphazerobeta_jquants_private_hf_cache.py": "scripts/jquants_private_hf_cache.py",
    "scripts/alphazerobeta_jquants_pit_master_ephemeral.py": "scripts/jquants_pit_master_ephemeral.py",
    "scripts/alphazerobeta_japan_free_prepare.py": "scripts/jquants_japan_panel.py",
}

REPLACEMENTS = {
    "alphazerobeta_jquants_free_ephemeral": "jquants_free_ephemeral",
    "alphazerobeta_jquants_private_hf_cache": "jquants_private_hf_cache",
    "alphazerobeta_jquants_pit_master_ephemeral": "jquants_pit_master_ephemeral",
    "alphazerobeta_japan_free_prepare": "jquants_japan_panel",
}

CONSUMERS = (
    "scripts/jquants_private_hf_cache.py",
    "scripts/jquants_pit_master_ephemeral.py",
    ".github/workflows/jquants-personal-hf-cache.yml",
    ".github/workflows/alphacrafter-jquants-frontier.yml",
    ".github/workflows/alphazerobeta-jquants-free-validation.yml",
    ".github/workflows/alphazerobeta-eda-stats.yml",
    "docs/specs/jquants-personal-hf-cache.md",
)


def replace_references() -> None:
    for path_str in CONSUMERS:
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        for old, new in REPLACEMENTS.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def neutralize_schemas() -> None:
    free = Path("scripts/jquants_free_ephemeral.py")
    free.write_text(
        free.read_text(encoding="utf-8").replace(
            "investor2.alphazerobeta-jquants-free-ephemeral.v1",
            "investor2.jquants-free-ephemeral.v1",
        ),
        encoding="utf-8",
    )

    cache = Path("scripts/jquants_private_hf_cache.py")
    cache.write_text(
        cache.read_text(encoding="utf-8").replace(
            "investor2.alphazerobeta-jquants-personal-hf-cache.v1",
            "investor2.jquants-personal-hf-cache.v1",
        ),
        encoding="utf-8",
    )

    panel = Path("scripts/jquants_japan_panel.py")
    text = panel.read_text(encoding="utf-8")
    marker = "#!/usr/bin/env python3\n"
    if not text.startswith(marker):
        raise RuntimeError("unexpected jquants_japan_panel header")
    panel.write_text(
        text.replace(
            marker,
            marker + '"""Shared PIT Japanese-equity panel adapter for J-Quants frontier families."""\n',
            1,
        ),
        encoding="utf-8",
    )

    prepare = Path("scripts/alphazerobeta_prepare.py")
    text = prepare.read_text(encoding="utf-8")
    text = text.replace(
        "investor2.alphazerobeta-prepared-dataset.v2",
        "investor2.jquants-prepared-panel.v1",
    )
    text = text.replace(
        "Prepare a PIT-safe AlphaZeroBeta panel from local files or a materialized central market cache.",
        "Prepare a PIT-safe research panel from local files or a materialized market snapshot.",
    )
    prepare.write_text(text, encoding="utf-8")


def separate_alphazerobeta_workflow() -> None:
    workflow = Path(".github/workflows/alphazerobeta-jquants-free-validation.yml")
    text = workflow.read_text(encoding="utf-8")
    text = "".join(
        line
        for line in text.splitlines(keepends=True)
        if "src/research/alphacrafter_frontier.py" not in line
        and "scripts/alphacrafter_jquants_frontier.py" not in line
        and "pytest -q tests/test_alphacrafter_frontier.py" not in line
    )

    start_marker = "      - name: Execute matched AlphaCrafter representative\n"
    end_marker = "      - name: Persist derived evidence only\n"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("AlphaCrafter execution block not found")
    text = text[:start] + text[end:]

    text = text.replace('          alpha_target=""\n', "")
    text = text.replace("            alpha_target=docs/research/results/alphacrafter_jquants_256\n", "")

    copy_start_marker = '          if [ "$MAX_ASSETS" = "256" ]; then\n            rm -rf "$alpha_target"\n'
    copy_start = text.find(copy_start_marker)
    python_marker = '          TARGET="$target" MAX_ASSETS="$MAX_ASSETS" ALPHA_TARGET="$alpha_target" python - <<\'PY\'\n'
    copy_end = text.find(python_marker, copy_start)
    if copy_start < 0 or copy_end < 0:
        raise RuntimeError("AlphaCrafter persistence block not found")
    text = text[:copy_start] + text[copy_end:]
    text = text.replace(
        python_marker,
        '          TARGET="$target" MAX_ASSETS="$MAX_ASSETS" python - <<\'PY\'\n',
        1,
    )

    alpha_start_marker = "              alpha_root = Path(os.environ['ALPHA_TARGET'])\n"
    alpha_start = text.find(alpha_start_marker)
    print_marker = "          print(json.dumps(payload, ensure_ascii=False, sort_keys=True))\n"
    alpha_end = text.find(print_marker, alpha_start)
    if alpha_start < 0 or alpha_end < 0:
        raise RuntimeError("AlphaCrafter comparison block not found")
    text = text[:alpha_start] + text[alpha_end:]

    git_add_block = '''          if [ "$MAX_ASSETS" = "256" ]; then
            git add "$target" "$alpha_target"
          else
            git add "$target"
          fi
'''
    if git_add_block not in text:
        raise RuntimeError("AlphaCrafter git-add block not found")
    text = text.replace(git_add_block, '          git add "$target"\n', 1)
    if "alphacrafter" in text.lower():
        raise RuntimeError("AlphaCrafter remains in AlphaZeroBeta validation workflow")
    workflow.write_text(text, encoding="utf-8")


def write_contract_test() -> None:
    Path("tests/test_jquants_strategy_neutrality.py").write_text(
        '''from pathlib import Path


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
''',
        encoding="utf-8",
    )


def main() -> None:
    for old, new in MOVES.items():
        source = Path(old)
        target = Path(new)
        if not source.is_file():
            raise RuntimeError(f"missing migration source: {old}")
        if target.exists():
            raise RuntimeError(f"migration target already exists: {new}")
        source.rename(target)
    replace_references()
    neutralize_schemas()
    separate_alphazerobeta_workflow()
    write_contract_test()
    for temporary in (
        ".github/workflows/temporary-jquants-neutralize.yml",
        ".github/workflows/temporary-jquants-neutralize-pr.yml",
        "scripts/temporary_jquants_neutralize.py",
    ):
        Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
