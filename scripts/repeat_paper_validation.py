#!/usr/bin/env python3
"""Repeat frozen paper-factor validation and report verdict stability."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SUITE_PATH = Path(__file__).with_name("verify_paper_factor_suite.py")
SPEC = importlib.util.spec_from_file_location("verify_paper_factor_suite", SUITE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SUITE_PATH}")
SUITE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUITE
SPEC.loader.exec_module(SUITE)


def build_repeat_report(
    registry_path: Path,
    *,
    repetitions: int = 5,
    publication_start: str = "2010-01",
    publication_end: str = "2019-12",
    seed_start: int = 2306,
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")

    reports = [
        SUITE.build_report(
            registry_path,
            publication_start=publication_start,
            publication_end=publication_end,
            bootstrap_seed=seed_start + index,
        )
        for index in range(repetitions)
    ]
    study_ids = list(reports[0]["studies"])
    studies: dict[str, Any] = {}

    for study_id in study_ids:
        runs = []
        for index, report in enumerate(reports):
            study = report["studies"][study_id]
            full = study["gross_results"]["full_oos"]
            late = study["gross_results"]["late_half"]
            cost_25 = study["monthly_haircut_sensitivity_bps"]["25"]
            runs.append(
                {
                    "seed": seed_start + index,
                    "verdict": study["verdict"],
                    "newey_west_t_stat_lag_6": full["newey_west_t_stat_lag_6"],
                    "bootstrap_lower_bound": full[
                        "block_bootstrap_95pct_mean_ci"
                    ][0],
                    "late_half_annualized_mean": late[
                        "annualized_arithmetic_mean"
                    ],
                    "cost_25bps_annualized_mean": cost_25[
                        "annualized_arithmetic_mean"
                    ],
                }
            )
        verdict_counts = Counter(run["verdict"] for run in runs)
        studies[study_id] = {
            "paper": reports[0]["studies"][study_id]["paper"],
            "publication_month": reports[0]["studies"][study_id][
                "publication_month"
            ],
            "verdict_counts": dict(sorted(verdict_counts.items())),
            "verdict_stable": len(verdict_counts) == 1,
            "runs": runs,
        }

    return {
        "suite": "repeated 2010s paper-factor validation",
        "publication_window": {
            "start": publication_start,
            "end": publication_end,
        },
        "repetitions": repetitions,
        "seed_start": seed_start,
        "study_count": len(studies),
        "all_verdicts_stable": all(
            study["verdict_stable"] for study in studies.values()
        ),
        "studies": studies,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry", type=Path, default=Path("docs/research/paper_factor_registry.json")
    )
    parser.add_argument("--publication-start", default="2010-01")
    parser.add_argument("--publication-end", default="2019-12")
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=2306)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    report = build_repeat_report(
        args.registry,
        repetitions=args.repetitions,
        publication_start=args.publication_start,
        publication_end=args.publication_end,
        seed_start=args.seed_start,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
