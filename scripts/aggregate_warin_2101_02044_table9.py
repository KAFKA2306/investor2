#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    protocol = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    downloads = args.downloads.resolve()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    all_runs: dict[str, list[dict[str, Any]]] = {"1": [], "4": []}
    selected: dict[str, dict[str, Any]] = {}
    artifact_hashes: dict[str, dict[str, str]] = {}

    for model in (1, 4):
        for restart in range(4):
            artifact = downloads / f"warin-table9-model{model}-restart{restart}"
            report_path = artifact / "report.json"
            trace_path = artifact / "training_trace.json"
            state_path = artifact / "model_state.json"
            for path in (report_path, trace_path, state_path):
                if not path.is_file():
                    raise FileNotFoundError(path)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report["model_id"] != model or report["restart"] != restart:
                raise ValueError(f"artifact identity mismatch for model {model} restart {restart}")
            destination = output_root / f"model{model}" / f"restart{restart}"
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report_path, destination / "report.json")
            shutil.copy2(trace_path, destination / "training_trace.json")
            shutil.copy2(state_path, destination / "model_state.json")
            all_runs[str(model)].append(report)
            artifact_hashes[f"model{model}_restart{restart}"] = {
                "report_sha256": sha256(destination / "report.json"),
                "training_trace_sha256": sha256(destination / "training_trace.json"),
                "model_state_sha256": sha256(destination / "model_state.json"),
            }

        best = max(all_runs[str(model)], key=lambda r: r["evaluation"]["opposite_penalized_objective"])
        selected[str(model)] = best

    model_verdicts = {
        model: "REPRODUCED" if report["comparison"]["within_predeclared_tolerance"] else "FAILED"
        for model, report in selected.items()
    }
    overall = "REPRODUCED" if all(v == "REPRODUCED" for v in model_verdicts.values()) else "FAILED"
    summary = {
        "schema_version": "investor2.warin-table9-summary.v1",
        "paper_id": "warin_2101_02044",
        "protocol": protocol.relative_to(ROOT).as_posix(),
        "protocol_sha256": sha256(protocol),
        "selection_rule": "maximum opposite penalized objective, equivalent to minimum penalized objective",
        "all_runs": all_runs,
        "selected": selected,
        "model_verdicts": model_verdicts,
        "empirical_verdict": overall,
        "paper_wide_reproduction_claim": False,
        "artifact_hashes": artifact_hashes,
    }
    summary_path = output_root / "summary.json"
    summary_path.write_bytes(canonical_bytes(summary))
    print(json.dumps({"summary": summary_path.relative_to(ROOT).as_posix(), "verdict": overall}, sort_keys=True))


if __name__ == "__main__":
    main()
