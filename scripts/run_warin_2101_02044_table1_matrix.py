#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run_warin_2101_02044_empirical.py"

spec = importlib.util.spec_from_file_location("warin_empirical", RUNNER_PATH)
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

CASES = [
    ("beta005", ROOT / "docs/research/protocols/warin_2101_02044_v4_beta005.json"),
    ("beta02", ROOT / "docs/research/protocols/warin_2101_02044_v4_beta02.json"),
]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def normalize_report(report: dict, report_path: Path) -> dict:
    beta = report["scope"]["beta"]
    if report["empirical_verdict"] == "REPRODUCED":
        report["verdict_reason"] = (
            f"independent full-count training/evaluation matched the predeclared Table 1 beta={beta} tolerances"
        )
    elif report["empirical_verdict"] == "FAILED":
        report["verdict_reason"] = (
            f"independent full-count training/evaluation missed one or more predeclared Table 1 beta={beta} tolerances"
        )
    report.pop("report_content_sha256_without_self_hash", None)
    pre_hash = canonical_bytes(report)
    report["report_content_sha256_without_self_hash"] = runner.sha256_bytes(pre_hash)
    report_path.write_bytes(canonical_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    summary = {
        "schema_version": "investor2.warin-table1-matrix.v1",
        "paper_id": "warin_2101_02044",
        "source_version": "v4",
        "cases": [],
    }
    for case_id, protocol_path in CASES:
        out_dir = output_root / case_id
        report = runner.run(runner.load_protocol(protocol_path), out_dir)
        report = normalize_report(report, out_dir / "report.json")
        summary["cases"].append(
            {
                "case_id": case_id,
                "beta": report["scope"]["beta"],
                "protocol": str(protocol_path.relative_to(ROOT)),
                "empirical_verdict": report["empirical_verdict"],
                "mean": report["evaluation"]["terminal_wealth_mean"],
                "variance": report["evaluation"]["terminal_wealth_population_variance"],
                "analytical_match": report["comparison"]["analytical"]["within_tolerance"],
                "neural_match": report["comparison"]["neural"]["within_tolerance"],
                "report_sha256": runner.sha256_file(out_dir / "report.json"),
                "trace_sha256": runner.sha256_file(out_dir / "training_trace.json"),
                "model_state_sha256": runner.sha256_file(out_dir / "model_state.json"),
            }
        )
        print(json.dumps(summary["cases"][-1], sort_keys=True), flush=True)
    (output_root / "summary.json").write_bytes(canonical_bytes(summary))
    print(
        json.dumps(
            {"summary": str((output_root / "summary.json").relative_to(ROOT)), "cases": len(summary["cases"])},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
