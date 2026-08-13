#!/usr/bin/env python3
"""Build the machine-readable internal evidence manifest used to derive public output."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T_HURDLE = 3.0
REQUIRED_PROMOTION_GATES = {
    "chronological_oos",
    "t_stat_ge_3",
    "block_bootstrap_lower_gt_0",
    "late_period_mean_gt_0",
    "after_25bps_monthly_haircut_gt_0",
    "point_in_time_security_level_rebuild",
    "tradability_and_borrowability",
}
EMPIRICAL_VERDICTS = {"REPRODUCED", "FAILED", "BLOCKED"}


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


def code_sha() -> str:
    value = os.environ.get("GITHUB_SHA", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", value):
        return value
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip().lower()
    except (OSError, subprocess.CalledProcessError):
        return "LOCAL_WORKTREE"
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else "LOCAL_WORKTREE"


def run_id(revision: str) -> str:
    candidate = os.environ.get("GITHUB_RUN_ID", "").strip()
    return f"github-actions:{candidate}" if candidate.isdigit() else f"local:{revision[:12]}"


def factor_record(study_id: str, study: dict[str, Any]) -> dict[str, Any]:
    full = study["gross_results"]["full_oos"]
    late = study["gross_results"]["late_half"]
    cost_25 = study["monthly_haircut_sensitivity_bps"]["25"]
    ci = full["block_bootstrap_95pct_mean_ci"]
    gates = {
        "chronological_oos": True,
        "t_stat_ge_3": full["newey_west_t_stat_lag_6"] >= T_HURDLE,
        "block_bootstrap_lower_gt_0": ci is not None and ci[0] > 0.0,
        "late_period_mean_gt_0": late["annualized_arithmetic_mean"] > 0.0,
        "after_25bps_monthly_haircut_gt_0": cost_25["annualized_arithmetic_mean"] > 0.0,
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
        "gates": {name: status(value) for name, value in gates.items()},
        "scope_note": study["scope_note"],
    }


def momentum_record(momentum: dict[str, Any]) -> dict[str, Any]:
    full = momentum["gross_results"]["post_publication_1994_2017"]
    late = momentum["gross_results"]["late_holdout_2006_2017"]
    cost_25 = momentum["monthly_cost_sensitivity_bps"]["25"]
    ci = full["block_bootstrap_95pct_mean_ci"]
    gates = {
        "chronological_oos": True,
        "t_stat_ge_3": full["newey_west_t_stat_lag_6"] >= T_HURDLE,
        "block_bootstrap_lower_gt_0": ci[0] > 0.0,
        "late_period_mean_gt_0": late["annualized_arithmetic_mean"] > 0.0,
        "after_25bps_monthly_haircut_gt_0": cost_25["annualized_arithmetic_mean"] > 0.0,
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
        "gates": {name: status(value) for name, value in gates.items()},
        "scope_note": "Published factor-return series; not a point-in-time reconstruction from individual securities.",
    }


def external_claims() -> list[dict[str, Any]]:
    return [
        {
            "id": "x_tse_20y_chart_patterns",
            "claim": "An AI-assisted search over roughly twenty years of Tokyo Stock Exchange data found no robust edge in familiar chart patterns.",
            "source_type": "X trend summary and quoted posts",
            "source_url": "https://x.com/i/trending/2079048977861734436",
            "evidence_state": "UNVERIFIED",
            "reason": "The repository does not contain the original point-in-time TSE universe, exact pattern definitions, parameter grid, trial count, signals, trades, or frozen out-of-sample result artifact.",
        },
        {
            "id": "x_tse_short_false_positive",
            "claim": "An apparent short-side edge disappeared after noticing that non-shortable securities had been mixed into the test universe.",
            "source_type": "quoted X post",
            "source_url": "https://x.com/i/trending/2079048977861734436",
            "evidence_state": "UNVERIFIED",
            "reason": "No date-indexed shortability, borrow availability, borrow cost, or order-level reproduction artifact is committed here.",
        },
    ]


def build_manifest() -> dict[str, Any]:
    suite_module = load_python_module(
        ROOT / "scripts" / "verify_paper_factor_suite.py",
        "verify_paper_factor_suite_for_dashboard",
    )
    paper_2021_module = load_python_module(
        ROOT / "scripts" / "verify_2021_arxiv_methods.py",
        "verify_2021_arxiv_methods_for_dashboard",
    )
    suite = suite_module.build_report(ROOT / "docs" / "research" / "paper_factor_registry.json")
    paper_2021 = paper_2021_module.build_report(ROOT / "docs" / "research" / "2021_arxiv_finance_registry.json")
    momentum = load_json(ROOT / "docs" / "research" / "post_publication_momentum_oos.json")
    repeated = load_json(ROOT / "docs" / "research" / "2010s_paper_validation_repeated.json")
    records = [momentum_record(momentum)]
    records.extend(factor_record(study_id, study) for study_id, study in suite["studies"].items())
    claims = external_claims()
    revision = code_sha()
    paper_summary = paper_2021["summary"]
    return {
        "schema_version": 2,
        "build": {"code_sha": revision, "run_id": run_id(revision)},
        "generated_from": {
            "momentum_result": "docs/research/post_publication_momentum_oos.json",
            "factor_registry": "docs/research/paper_factor_registry.json",
            "factor_verifier": "scripts/verify_paper_factor_suite.py",
            "repeated_2010s_result": "docs/research/2010s_paper_validation_repeated.json",
            "paper_2021_registry": "docs/research/2021_arxiv_finance_registry.json",
            "paper_2021_verifier": "scripts/verify_2021_arxiv_methods.py",
        },
        "summary": {
            "tested_hypotheses": len(records),
            "confirmed": sum(record["dashboard_verdict"] == "CONFIRMED" for record in records),
            "not_confirmed": sum(record["dashboard_verdict"] == "NOT_CONFIRMED" for record in records),
            "external_claims_unverified": sum(claim["evidence_state"] == "UNVERIFIED" for claim in claims),
            "latest_factor_data_end": "2020-02",
            "latest_momentum_data_end": "2017-12",
            "papers_2021_indexed": paper_summary["indexed"],
            "papers_2021_method_contract_pass": paper_summary["method_contract_pass"],
            "papers_2021_materialized": paper_summary["materialized"],
            "papers_2021_empirically_run": paper_summary["empirically_run"],
            "papers_2021_empirically_reproduced": paper_summary["empirically_reproduced"],
            "papers_2021_empirically_failed": paper_summary["empirically_failed"],
            "papers_2021_empirically_blocked": paper_summary["empirically_blocked"],
            "papers_2021_empirically_not_run": paper_summary["empirically_not_run"],
        },
        "locked_protocol": {
            "selection_test_separation": "Chronological post-publication OOS; no result-driven boundary changes.",
            "multiple_testing": "Record the complete tried rule family. New return predictors require Newey-West t >= 3.0; searched technical-rule families also require a family-wise data-snooping test.",
            "bootstrap": "12-month moving-block bootstrap, 20,000 repetitions.",
            "stability": "Late-period mean must remain positive.",
            "costs": "A 25 bps monthly haircut must remain positive, followed by a strategy-specific spread, turnover, market-impact, tax, and borrow model.",
            "universe_integrity": "Point-in-time constituents, delistings, corporate actions, price limits, and security eligibility must be applied before signal evaluation.",
            "short_side": "A short trade is eligible only when date-indexed shortability and borrow availability are true; borrow cost must be charged.",
            "promotion_rule": "Any material NOT RUN or FAIL gate prevents promotion to a live strategy.",
        },
        "repository_results": records,
        "paper_reproduction_2021": paper_2021,
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
        "external_claims": claims,
        "primary_method_sources": [
            {"label": "Sullivan, Timmermann & White (1999)", "url": "https://doi.org/10.1111/0022-1082.00163", "role": "Technical-rule data-snooping and White's Reality Check."},
            {"label": "Harvey, Liu & Zhu (2016)", "url": "https://doi.org/10.1093/rfs/hhv059", "role": "Higher statistical hurdle under multiple testing."},
            {"label": "Hansen (2005), A Test for Superior Predictive Ability", "url": "https://doi.org/10.1198/073500105000000063", "role": "Family-wise SPA test for searched model or rule sets."},
            {"label": "Bailey et al., Probability of Backtest Overfitting", "url": "https://doi.org/10.21314/JCF.2016.322", "role": "Backtest-selection overfitting and CSCV/PBO."},
            {"label": "Japan Exchange Group: Short Selling Restrictions", "url": "https://www.jpx.co.jp/english/equities/trading/regulations/02.html", "role": "Short-sale classification and execution restrictions."},
        ],
        "interpretation": [
            "The committed repository evidence rejects promotion of the currently displayed hypotheses; it does not prove that every market edge is impossible.",
            "The 2021 arXiv queue separates primary-source verification, method implementation, artifact materialization, and empirical reproduction. METHOD_ONLY is never empirical confirmation.",
            "The social-media TSE claims are useful hypotheses about failure modes, but remain UNVERIFIED here because their original artifacts are absent.",
            "AI is used as an implementation and falsification tool. Hypothesis provenance, trial accounting, and market-mechanism constraints remain mandatory inputs.",
        ],
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 2:
        raise ValueError("unsupported internal schema_version")
    records = manifest.get("repository_results")
    summary = manifest.get("summary")
    if not isinstance(records, list) or not isinstance(summary, dict):
        raise ValueError("manifest records and summary are required")
    ids = [record.get("id") for record in records]
    if any(not isinstance(record_id, str) or not record_id for record_id in ids):
        raise ValueError("every hypothesis requires a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("hypothesis ids must be unique")
    verdicts = [record.get("dashboard_verdict") for record in records]
    if any(verdict not in {"CONFIRMED", "NOT_CONFIRMED"} for verdict in verdicts):
        raise ValueError("unknown dashboard verdict")
    expected = {
        "tested_hypotheses": len(records),
        "confirmed": verdicts.count("CONFIRMED"),
        "not_confirmed": verdicts.count("NOT_CONFIRMED"),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ValueError(f"summary {key} does not match repository results")
    for record in records:
        gates = record.get("gates")
        if not isinstance(gates, dict) or not REQUIRED_PROMOTION_GATES <= set(gates):
            raise ValueError(f"required gates missing for {record['id']}")
        if record["dashboard_verdict"] == "CONFIRMED" and any(
            gates.get(name) != "PASS" for name in REQUIRED_PROMOTION_GATES
        ):
            raise ValueError(f"confirmed record has incomplete evidence: {record['id']}")

    paper_2021 = manifest.get("paper_reproduction_2021")
    if not isinstance(paper_2021, dict):
        raise ValueError("paper_reproduction_2021 is required")
    paper_summary = paper_2021.get("summary")
    papers = paper_2021.get("papers")
    if not isinstance(paper_summary, dict) or not isinstance(papers, list):
        raise ValueError("2021 paper summary and records are required")
    paper_ids = [paper.get("id") for paper in papers]
    if any(not isinstance(paper_id, str) or not paper_id for paper_id in paper_ids) or len(paper_ids) != len(set(paper_ids)):
        raise ValueError("2021 paper ids must be unique non-empty strings")
    expected_paper = {
        "indexed": len(papers),
        "method_contract_pass": sum(paper.get("method_contract_state") == "PASS" for paper in papers),
        "materialized": sum(paper.get("artifact_state") == "MATERIALIZED" for paper in papers),
        "empirically_run": sum(paper.get("empirical_reproduction_state") == "EMPIRICALLY_RUN" for paper in papers),
        "empirically_reproduced": sum(paper.get("empirical_verdict") == "REPRODUCED" for paper in papers),
        "empirically_failed": sum(paper.get("empirical_verdict") == "FAILED" for paper in papers),
        "empirically_blocked": sum(paper.get("empirical_verdict") == "BLOCKED" for paper in papers),
        "empirically_not_run": sum(paper.get("empirical_reproduction_state") == "NOT_RUN" for paper in papers),
    }
    if paper_summary != expected_paper:
        raise ValueError("2021 paper summary does not match paper records")
    for key, value in expected_paper.items():
        if summary.get(f"papers_2021_{key}") != value:
            raise ValueError(f"summary papers_2021_{key} does not match 2021 paper records")
    for paper in papers:
        if paper.get("source_metadata_state") != "VERIFIED_PRIMARY":
            raise ValueError(f"primary source not verified for {paper['id']}")
        empirical_state = paper.get("empirical_reproduction_state")
        if empirical_state == "NOT_RUN":
            if paper.get("empirical_verdict") is not None:
                raise ValueError(f"NOT_RUN paper has empirical verdict: {paper['id']}")
            if paper.get("reproduction_verdict") not in {"METHOD_ONLY", "METHOD_CONTRACT_FAIL"}:
                raise ValueError(f"unrun paper has empirical-looking verdict: {paper['id']}")
            if paper.get("empirical_evidence_manifest") is not None:
                raise ValueError(f"NOT_RUN paper has empirical evidence manifest: {paper['id']}")
        elif empirical_state == "EMPIRICALLY_RUN":
            if paper.get("empirical_verdict") not in EMPIRICAL_VERDICTS:
                raise ValueError(f"empirically run paper lacks final verdict: {paper['id']}")
            if paper.get("reproduction_verdict") != paper.get("empirical_verdict"):
                raise ValueError(f"empirical/reproduction verdict mismatch: {paper['id']}")
            if not paper.get("empirical_evidence_manifest") or not re.fullmatch(
                r"[0-9a-f]{64}", str(paper.get("empirical_evidence_manifest_sha256", ""))
            ):
                raise ValueError(f"empirically run paper lacks evidence reference/hash: {paper['id']}")
        else:
            raise ValueError(f"unknown empirical state: {paper['id']}")

    repeated = manifest.get("repeated_validation", {})
    if repeated.get("study_count") != len(repeated.get("studies", {})):
        raise ValueError("repeated validation study_count is inconsistent")
    if repeated.get("all_verdicts_stable") is not True:
        raise ValueError("repeated validation verdicts are not stable")
    claims = manifest.get("external_claims", [])
    if summary.get("external_claims_unverified") != sum(
        claim.get("evidence_state") == "UNVERIFIED" for claim in claims
    ):
        raise ValueError("external claim summary is inconsistent")
    build = manifest.get("build", {})
    if not build.get("code_sha") or not build.get("run_id"):
        raise ValueError("build code_sha and run_id are required")


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
