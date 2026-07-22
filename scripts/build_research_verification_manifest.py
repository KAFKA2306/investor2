#!/usr/bin/env python3
"""Build the machine-readable evidence manifest used by the public dashboard.

This script intentionally separates:
1. results that can be regenerated from committed repository inputs; and
2. external social-media claims for which no auditable data/code artifact exists.

An external claim remains UNVERIFIED until its exact universe, rules, point-in-time
eligibility data, trial count, and result files are added to this repository.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T_HURDLE = 3.0


def load_python_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def factor_record(study_id: str, study: dict[str, Any]) -> dict[str, Any]:
    full = study["gross_results"]["full_oos"]
    late = study["gross_results"]["late_half"]
    cost_25 = study["monthly_haircut_sensitivity_bps"]["25"]
    ci = full["block_bootstrap_95pct_mean_ci"]
    gate_values = {
        "chronological_oos": True,
        "t_stat_ge_3": full["newey_west_t_stat_lag_6"] >= T_HURDLE,
        "block_bootstrap_lower_gt_0": ci is not None and ci[0] > 0.0,
        "late_period_mean_gt_0": late["annualized_arithmetic_mean"] > 0.0,
        "after_25bps_monthly_haircut_gt_0": (
            cost_25["annualized_arithmetic_mean"] > 0.0
        ),
        "point_in_time_security_level_rebuild": False,
        "tradability_and_borrowability": False,
    }
    return {
        "id": study_id,
        "paper": study["paper"],
        "implementation": study["implementation"],
        "window": f'{full["start"]}–{full["end"]}',
        "months": full["months"],
        "annualized_mean": full["annualized_arithmetic_mean"],
        "sharpe": full["annualized_sharpe_zero_rf"],
        "max_drawdown": full["max_drawdown"],
        "newey_west_t": full["newey_west_t_stat_lag_6"],
        "block_bootstrap_ci": ci,
        "late_period_mean": late["annualized_arithmetic_mean"],
        "cost_25bps_annualized_mean": cost_25["annualized_arithmetic_mean"],
        "original_verdict": study["verdict"],
        "dashboard_verdict": "NOT_CONFIRMED",
        "gates": {name: status(value) for name, value in gate_values.items()},
        "scope_note": study["scope_note"],
    }


def momentum_record(momentum: dict[str, Any]) -> dict[str, Any]:
    full = momentum["gross_results"]["post_publication_1994_2017"]
    late = momentum["gross_results"]["late_holdout_2006_2017"]
    cost_25 = momentum["monthly_cost_sensitivity_bps"]["25"]
    ci = full["block_bootstrap_95pct_mean_ci"]
    gate_values = {
        "chronological_oos": True,
        "t_stat_ge_3": full["newey_west_t_stat_lag_6"] >= T_HURDLE,
        "block_bootstrap_lower_gt_0": ci[0] > 0.0,
        "late_period_mean_gt_0": late["annualized_arithmetic_mean"] > 0.0,
        "after_25bps_monthly_haircut_gt_0": (
            cost_25["annualized_arithmetic_mean"] > 0.0
        ),
        "point_in_time_security_level_rebuild": False,
        "tradability_and_borrowability": False,
    }
    return {
        "id": "jegadeesh_titman_1993_momentum",
        "paper": "Jegadeesh and Titman (1993), Returns to Buying Winners and Selling Losers",
        "implementation": "factor",
        "window": f'{full["start"]}–{full["end"]}',
        "months": full["months"],
        "annualized_mean": full["annualized_arithmetic_mean"],
        "sharpe": full["annualized_sharpe_zero_rf"],
        "max_drawdown": full["max_drawdown"],
        "newey_west_t": full["newey_west_t_stat_lag_6"],
        "block_bootstrap_ci": ci,
        "late_period_mean": late["annualized_arithmetic_mean"],
        "cost_25bps_annualized_mean": cost_25["annualized_arithmetic_mean"],
        "original_verdict": momentum["verdict"],
        "dashboard_verdict": "NOT_CONFIRMED",
        "gates": {name: status(value) for name, value in gate_values.items()},
        "scope_note": (
            "Published factor-return series; not a point-in-time reconstruction "
            "from individual securities."
        ),
    }


def external_claims() -> list[dict[str, Any]]:
    return [
        {
            "id": "x_tse_20y_chart_patterns",
            "claim": (
                "An AI-assisted search over roughly twenty years of Tokyo Stock "
                "Exchange data found no robust edge in familiar chart patterns."
            ),
            "source_type": "X trend summary and quoted posts",
            "source_url": "https://x.com/i/trending/2079048977861734436",
            "evidence_state": "UNVERIFIED",
            "reason": (
                "The repository does not contain the original point-in-time TSE "
                "universe, exact pattern definitions, parameter grid, trial count, "
                "signals, trades, or frozen out-of-sample result artifact."
            ),
        },
        {
            "id": "x_tse_short_false_positive",
            "claim": (
                "An apparent short-side edge disappeared after noticing that "
                "non-shortable securities had been mixed into the test universe."
            ),
            "source_type": "quoted X post",
            "source_url": "https://x.com/i/trending/2079048977861734436",
            "evidence_state": "UNVERIFIED",
            "reason": (
                "No date-indexed shortability, borrow availability, borrow cost, "
                "or order-level reproduction artifact is committed here."
            ),
        },
    ]


def build_manifest() -> dict[str, Any]:
    suite_module = load_python_module(
        ROOT / "scripts" / "verify_paper_factor_suite.py",
        "verify_paper_factor_suite_for_dashboard",
    )
    suite = suite_module.build_report(
        ROOT / "docs" / "research" / "paper_factor_registry.json"
    )
    momentum = load_json(
        ROOT / "docs" / "research" / "post_publication_momentum_oos.json"
    )
    repeated = load_json(
        ROOT / "docs" / "research" / "2010s_paper_validation_repeated.json"
    )

    records = [momentum_record(momentum)]
    records.extend(
        factor_record(study_id, study)
        for study_id, study in suite["studies"].items()
    )
    confirmed = sum(
        record["dashboard_verdict"] == "CONFIRMED" for record in records
    )
    not_confirmed = sum(
        record["dashboard_verdict"] == "NOT_CONFIRMED" for record in records
    )

    return {
        "schema_version": 1,
        "generated_from": {
            "momentum_result": "docs/research/post_publication_momentum_oos.json",
            "factor_registry": "docs/research/paper_factor_registry.json",
            "factor_verifier": "scripts/verify_paper_factor_suite.py",
            "repeated_2010s_result": (
                "docs/research/2010s_paper_validation_repeated.json"
            ),
        },
        "summary": {
            "tested_hypotheses": len(records),
            "confirmed": confirmed,
            "not_confirmed": not_confirmed,
            "external_claims_unverified": len(external_claims()),
            "latest_factor_data_end": "2020-02",
            "latest_momentum_data_end": "2017-12",
        },
        "locked_protocol": {
            "selection_test_separation": (
                "Chronological post-publication OOS; no result-driven boundary changes."
            ),
            "multiple_testing": (
                "Record the complete tried rule family. For new return predictors, "
                "use a research hurdle of Newey-West t >= 3.0; technical-rule families "
                "also require a family-wise data-snooping test such as White's Reality "
                "Check or Hansen's SPA."
            ),
            "bootstrap": "12-month moving-block bootstrap, 20,000 repetitions.",
            "stability": "Late-period mean must remain positive.",
            "costs": (
                "A 25 bps monthly haircut must remain positive, followed by a "
                "strategy-specific spread, turnover, market-impact, tax, and borrow model."
            ),
            "universe_integrity": (
                "Point-in-time constituents, delistings, corporate actions, price limits, "
                "and security eligibility must be applied before signal evaluation."
            ),
            "short_side": (
                "A short trade is eligible only when date-indexed shortability and "
                "borrow availability are true; borrow cost must be charged."
            ),
            "promotion_rule": (
                "Any material NOT RUN or FAIL gate prevents promotion to a live strategy."
            ),
        },
        "repository_results": records,
        "repeated_validation": {
            "study_count": repeated["study_count"],
            "repetitions": repeated["repetitions"],
            "all_verdicts_stable": repeated["all_verdicts_stable"],
            "studies": {
                study_id: {
                    "paper": study["paper"],
                    "verdict_counts": study["verdict_counts"],
                    "verdict_stable": study["verdict_stable"],
                }
                for study_id, study in repeated["studies"].items()
            },
        },
        "external_claims": external_claims(),
        "primary_method_sources": [
            {
                "label": "Sullivan, Timmermann & White (1999)",
                "url": "https://doi.org/10.1111/0022-1082.00163",
                "role": "Technical-rule data-snooping and White's Reality Check.",
            },
            {
                "label": "Harvey, Liu & Zhu (2016)",
                "url": "https://doi.org/10.1093/rfs/hhv059",
                "role": "Higher statistical hurdle under multiple testing.",
            },
            {
                "label": "Hansen (2005), A Test for Superior Predictive Ability",
                "url": "https://doi.org/10.1198/073500105000000063",
                "role": "Family-wise SPA test for searched model or rule sets.",
            },
            {
                "label": "Bailey et al., Probability of Backtest Overfitting",
                "url": "https://doi.org/10.21314/JCF.2016.322",
                "role": "Backtest-selection overfitting and CSCV/PBO.",
            },
            {
                "label": "Japan Exchange Group: Short Selling Restrictions",
                "url": "https://www.jpx.co.jp/english/equities/trading/regulations/02.html",
                "role": "Short-sale classification and execution restrictions.",
            },
        ],
        "interpretation": [
            (
                "The committed repository evidence rejects promotion of all eight "
                "currently displayed hypotheses; it does not prove that every market "
                "edge is impossible."
            ),
            (
                "The social-media TSE claims are useful hypotheses about failure modes, "
                "but remain UNVERIFIED here because their original artifacts are absent."
            ),
            (
                "AI is used as an implementation and falsification tool. Hypothesis "
                "provenance, trial accounting, and market-mechanism constraints remain "
                "mandatory inputs."
            ),
        ],
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    summary = manifest["summary"]
    if summary["tested_hypotheses"] != 8:
        raise ValueError("expected one momentum plus seven paper-factor hypotheses")
    if summary["confirmed"] != 0 or summary["not_confirmed"] != 8:
        raise ValueError("current committed evidence must remain 0 confirmed / 8 not confirmed")
    if not manifest["repeated_validation"]["all_verdicts_stable"]:
        raise ValueError("repeated 2010s verdicts are not stable")
    if any(
        claim["evidence_state"] != "UNVERIFIED"
        for claim in manifest["external_claims"]
    ):
        raise ValueError("external claims cannot be promoted without repository artifacts")
    for record in manifest["repository_results"]:
        if record["gates"]["tradability_and_borrowability"] != "FAIL":
            raise ValueError("factor-series results must not imply security-level tradability")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest()
    validate_manifest(manifest)
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    elif not args.check:
        print(rendered, end="")


if __name__ == "__main__":
    main()
