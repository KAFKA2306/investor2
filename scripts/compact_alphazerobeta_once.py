#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs/research/results/alphazerobeta_2024"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new)


def compact_generator() -> None:
    path = ROOT / "scripts/alphazerobeta_empirical_run.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    return primary.with_suffix(".weights.npz"), ablation.with_suffix(".weights.npz")\n',
        '    primary_weight = primary.with_suffix(".weights.npz")\n'
        '    ablation_weight = ablation.with_suffix(".weights.npz")\n'
        '    primary.unlink()\n'
        '    ablation.unlink()\n'
        '    return primary_weight, ablation_weight\n',
        "drop transient fold reports",
    )
    text = replace_once(
        text,
        '    return output\n\n\ndef money(cumulative_return: float, initial: float) -> dict[str, float]:\n',
        '''    return output\n\n\ndef compact_comparisons(\n    output_dir: Path, comparison: Path, sensitivity: list[Path]\n) -> Path:\n    scenarios: dict[str, dict[str, Any]] = {}\n    for path in sensitivity:\n        payload = read_json(path)\n        assumptions = payload["cost_assumptions"]\n        trading = int(float(assumptions["transaction_cost_bps_per_side"]))\n        borrow = int(float(assumptions["borrow_fee_bps_per_year"]))\n        scenarios[f"{trading}bps_borrow_{borrow}bps"] = payload\n    default_scenario = f"{int(PRIMARY_TRANSACTION_COST_BPS)}bps_borrow_{int(PRIMARY_BORROW_FEE_BPS)}bps"\n    if read_json(comparison) != scenarios[default_scenario]:\n        raise AssertionError("default comparison must equal matching sensitivity scenario")\n    output = output_dir / "cost_sensitivity.json"\n    write_json(\n        output,\n        {\n            "schema_version": "investor2.alphazerobeta-cost-sensitivity.v1",\n            "default_scenario": default_scenario,\n            "scenarios": scenarios,\n        },\n    )\n    for path in {comparison, *sensitivity}:\n        path.unlink()\n    return output\n\n\ndef money(cumulative_return: float, initial: float) -> dict[str, float]:\n''',
        "add consolidated sensitivity writer",
    )
    text = replace_once(text, '    primary_folds: list[Path],\n    ablation_folds: list[Path],\n', '', "drop fold args")
    text = replace_once(
        text,
        '        "schema_version": "investor2.alphazerobeta-empirical-summary.v1",\n',
        '        "schema_version": "investor2.alphazerobeta-empirical-summary.v2",\n',
        "summary schema",
    )
    text = replace_once(
        text,
        '        "primary_fold_results": [str(path) for path in primary_folds],\n'
        '        "ablation_fold_results": [str(path) for path in ablation_folds],\n',
        '',
        "drop fold pointers",
    )
    text = replace_once(
        text,
        '        "cost_sensitivity": [str(path) for path in sensitivity],\n',
        '        "cost_sensitivity": str(output_dir / "cost_sensitivity.json"),\n',
        "single sensitivity pointer",
    )
    text = replace_once(text, '    primary_results: list[Path] = []\n    ablation_results: list[Path] = []\n', '', "drop result lists")
    text = replace_once(
        text,
        '        primary_result = output_dir / f"primary_fold{fold_index}.json"\n'
        '        ablation_result = output_dir / f"ablation_fold{fold_index}.json"\n'
        '        primary_results.append(primary_result)\n'
        '        ablation_results.append(ablation_result)\n',
        '',
        "drop result collection",
    )
    text = replace_once(
        text,
        '        source_manifest,\n        primary_results,\n        ablation_results,\n        primary_audits,\n',
        '        source_manifest,\n        primary_audits,\n',
        "drop summary result args",
    )
    text = replace_once(
        text,
        '        comparison,\n        sensitivity,\n    )\n\n\ndef main() -> None:\n',
        '        comparison,\n        sensitivity,\n    )\n    compact_comparisons(output_dir, comparison, sensitivity)\n\n\ndef main() -> None:\n',
        "compact after summary",
    )
    path.write_text(text, encoding="utf-8")
    py_compile.compile(str(path), doraise=True)


def compact_validation_workflow() -> None:
    path = ROOT / ".github/workflows/alphazerobeta-empirical.yml"
    text = path.read_text(encoding="utf-8")
    start = text.index("      - name: Recompute aggregate and cost sensitivity\n")
    end = text.index("      - name: Verify hashes, summary, and monetary scaling\n", start)
    block = '''      - name: Recompute aggregate and cost sensitivity\n        env:\n          PYTHONPATH: .\n        shell: bash\n        run: |\n          set -euo pipefail\n          ROOT=docs/research/results/alphazerobeta_2024\n          DATASET="$ROOT/etf_panel.npz"\n          PRIMARY=("$ROOT/primary_fold0.weights.npz" "$ROOT/primary_fold1.weights.npz")\n          ABLATION=("$ROOT/ablation_fold0.weights.npz" "$ROOT/ablation_fold1.weights.npz")\n          python scripts/alphazerobeta_compare.py --dataset "$DATASET" --primary-weights "${PRIMARY[@]}" --ablation-weights "${ABLATION[@]}" --output /tmp/alphazerobeta_comparison.json --transaction-cost-bps 15 --borrow-fee-bps 100\n          for trading in 5 15 30; do\n            for borrow in 0 100; do\n              name="comparison_cost_${trading}bps_borrow_${borrow}bps.json"\n              python scripts/alphazerobeta_compare.py --dataset "$DATASET" --primary-weights "${PRIMARY[@]}" --ablation-weights "${ABLATION[@]}" --output "/tmp/$name" --transaction-cost-bps "$trading" --borrow-fee-bps "$borrow"\n            done\n          done\n          python - <<'PY'\n          import json\n          from pathlib import Path\n          root = Path("docs/research/results/alphazerobeta_2024")\n          store = json.loads((root / "cost_sensitivity.json").read_text())\n          expected = {f"{trading}bps_borrow_{borrow}bps" for trading in (5, 15, 30) for borrow in (0, 100)}\n          assert set(store["scenarios"]) == expected\n          assert json.loads(Path("/tmp/alphazerobeta_comparison.json").read_text()) == store["scenarios"][store["default_scenario"]]\n          for key, expected_payload in store["scenarios"].items():\n              assert json.loads(Path(f"/tmp/comparison_cost_{key}.json").read_text()) == expected_payload\n          PY\n\n'''
    text = text[:start] + block + text[end:]
    text = replace_once(
        text,
        '          comparison = json.loads((root / "alphazerobeta_comparison.json").read_text())\n',
        '          sensitivity = json.loads((root / "cost_sensitivity.json").read_text())\n'
        '          comparison = sensitivity["scenarios"][sensitivity["default_scenario"]]\n',
        "validation default comparison",
    )
    path.write_text(text, encoding="utf-8")


def compact_checked_evidence() -> None:
    scenarios: dict[str, dict[str, object]] = {}
    for trading in (5, 15, 30):
        for borrow in (0, 100):
            name = f"comparison_cost_{trading}bps_borrow_{borrow}bps.json"
            scenarios[f"{trading}bps_borrow_{borrow}bps"] = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    default_key = "15bps_borrow_100bps"
    default = json.loads((RESULTS / "alphazerobeta_comparison.json").read_text(encoding="utf-8"))
    if default != scenarios[default_key]:
        raise RuntimeError("default comparison differs from matching sensitivity scenario")
    (RESULTS / "cost_sensitivity.json").write_text(
        json.dumps(
            {
                "schema_version": "investor2.alphazerobeta-cost-sensitivity.v1",
                "default_scenario": default_key,
                "scenarios": scenarios,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    summary_path = RESULTS / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["schema_version"] = "investor2.alphazerobeta-empirical-summary.v2"
    summary.pop("primary_fold_results", None)
    summary.pop("ablation_fold_results", None)
    summary["cost_sensitivity"] = str(RESULTS.relative_to(ROOT) / "cost_sensitivity.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    obsolete = [
        "primary_fold0.json", "primary_fold1.json", "ablation_fold0.json", "ablation_fold1.json",
        "alphazerobeta_comparison.json",
        "comparison_cost_5bps_borrow_0bps.json", "comparison_cost_5bps_borrow_100bps.json",
        "comparison_cost_15bps_borrow_0bps.json", "comparison_cost_15bps_borrow_100bps.json",
        "comparison_cost_30bps_borrow_0bps.json", "comparison_cost_30bps_borrow_100bps.json",
    ]
    for name in obsolete:
        (RESULTS / name).unlink()


def verify() -> None:
    summary = json.loads((RESULTS / "summary.json").read_text())
    store = json.loads((RESULTS / "cost_sensitivity.json").read_text())
    assert summary["schema_version"] == "investor2.alphazerobeta-empirical-summary.v2"
    assert summary["cost_sensitivity"] == "docs/research/results/alphazerobeta_2024/cost_sensitivity.json"
    assert "primary_fold_results" not in summary and "ablation_fold_results" not in summary
    assert store["default_scenario"] == "15bps_borrow_100bps" and len(store["scenarios"]) == 6
    default = store["scenarios"][store["default_scenario"]]
    assert default["primary_lambda_corr_0_5"] == summary["primary_lambda_corr_0_5"]
    assert default["ablation_lambda_corr_0"] == summary["ablation_lambda_corr_0"]
    assert default["gates"] == summary["gates"]
    keep = [
        "etf_panel.npz", "etf_panel.npz.manifest.json", "source_manifest.json", "summary.json", "cost_sensitivity.json",
        "primary_fold0.weights.npz", "primary_fold1.weights.npz", "ablation_fold0.weights.npz", "ablation_fold1.weights.npz",
        "primary_fold0.audit.json", "primary_fold1.audit.json", "ablation_fold0.audit.json", "ablation_fold1.audit.json",
    ]
    assert all((RESULTS / name).exists() for name in keep)


def main() -> None:
    compact_generator()
    compact_validation_workflow()
    compact_checked_evidence()
    verify()


if __name__ == "__main__":
    main()
