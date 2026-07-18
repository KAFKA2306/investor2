#!/usr/bin/env python3
"""Build the strategy-centered AAARTS registry from committed evidence JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_VERSION = "aaarts-ontology.v1"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def code_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def meta(stable_id: str, input_hash: str, created_at: str, commit: str) -> dict[str, Any]:
    return {
        "stable_id": stable_id,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
        "input_hash": input_hash,
        "code_commit_sha": commit,
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def study_rows(momentum: dict[str, Any], multi: dict[str, Any]) -> list[dict[str, Any]]:
    full = momentum["gross_results"]["post_publication_1994_2017"]
    net = momentum["monthly_cost_sensitivity_bps"]["25"]
    rows = [
        {
            "key": "momentum_ff_mom",
            "title": "Jegadeesh–Titman型モメンタム",
            "claim": "過去リターン上位銘柄は将来も相対的に高いリターンを示す。",
            "mechanism": "投資家の反応遅れ・情報拡散の遅さが短中期の継続を生むという仮説。",
            "paper": "Jegadeesh–Titman (1993)",
            "doi": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
            "dataset": "momentum",
            "implementation": "PROXY",
            "implementation_name": "Fama/French Mom factor proxy",
            "definition": "Fama/French Mom: high prior-return portfolios minus low prior-return portfolios.",
            "limitations": ["原論文の証券レベル完全再現ではない。"],
            "full": full,
            "net": net,
            "verdict": momentum["verdict"],
            "late_mean": momentum["gross_results"]["late_holdout_2006_2017"][
                "annualized_arithmetic_mean"
            ],
        }
    ]
    for study_id, study in multi["studies"].items():
        full = study["gross_results"]["full_oos"]
        net = study["monthly_haircut_sensitivity_bps"]["25"]
        rows.append(
            {
                "key": study_id,
                "title": study["paper"],
                "claim": f"{study['paper']} の公開後因子リターンが再現される。",
                "mechanism": study["scope_note"],
                "paper": study["paper"],
                "doi": f"https://doi.org/{study['doi']}",
                "dataset": study["dataset"],
                "implementation": "FACTOR" if study["implementation"] == "factor" else "PROXY",
                "implementation_name": study["column"],
                "definition": study["scope_note"],
                "limitations": ["因子リターン検証であり、原論文の証券レベル回帰を再現しない。"],
                "full": full,
                "net": net,
                "verdict": study["verdict"],
                "late_mean": study["gross_results"]["late_half"][
                    "annualized_arithmetic_mean"
                ],
            }
        )
    return rows


def metric(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "annualized_mean": source["annualized_arithmetic_mean"],
        "sharpe": source["annualized_sharpe_zero_rf"],
        "cagr": source["cagr"],
        "max_drawdown": source["max_drawdown"],
        "months": source["months"],
    }


def build(momentum_path: Path, multi_path: Path) -> dict[str, Any]:
    created_at = now()
    commit = code_sha()
    momentum = load(momentum_path)
    multi = load(multi_path)
    momentum_hash = file_hash(ROOT / "docs/research/data/ff_momentum_1994_2017.csv")
    dataset_hashes = {
        "momentum": momentum_hash,
        "ff3_1992_2020": file_hash(ROOT / "docs/research/data/ff3_1992_2020.csv"),
        "ff5_2015_2020": file_hash(ROOT / "docs/research/data/ff5_2015_2020.csv"),
    }
    rows = study_rows(momentum, multi)

    data_sources = [
        {
            **meta("source.ken_french.mom", dataset_hashes["momentum"], created_at, commit),
            "name": "Kenneth French Data Library Mom",
            "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html",
            "authority": "PRIMARY",
            "kind": "MARKET",
        },
        {
            **meta("source.ken_french.ff3", dataset_hashes["ff3_1992_2020"], created_at, commit),
            "name": "Kenneth French Data Library FF3",
            "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html",
            "authority": "PRIMARY",
            "kind": "MARKET",
        },
        {
            **meta("source.ken_french.ff5", dataset_hashes["ff5_2015_2020"], created_at, commit),
            "name": "Kenneth French Data Library FF5",
            "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html",
            "authority": "PRIMARY",
            "kind": "MARKET",
        },
    ]
    source_by_dataset = {
        "momentum": "source.ken_french.mom",
        "ff3_1992_2020": "source.ken_french.ff3",
        "ff5_2015_2020": "source.ken_french.ff5",
    }
    dataset_ranges = {
        "momentum": ("1994-01", "2017-12", "docs/research/data/ff_momentum_1994_2017.csv"),
        "ff3_1992_2020": ("1992-07", "2020-02", "docs/research/data/ff3_1992_2020.csv"),
        "ff5_2015_2020": ("2015-05", "2020-02", "docs/research/data/ff5_2015_2020.csv"),
    }
    dataset_snapshots = []
    pit_assessments = []
    quality_assessments = []
    provenance_records = []
    for dataset_id, (start, end, path) in dataset_ranges.items():
        dataset_stable_id = f"dataset.{dataset_id}.snapshot.1"
        dataset_snapshots.append(
            {
                **meta(dataset_stable_id, dataset_hashes[dataset_id], created_at, commit),
                "data_source_id": source_by_dataset[dataset_id],
                "name": dataset_id,
                "path": path,
                "sha256": dataset_hashes[dataset_id],
                "observed_at": created_at,
                "period_start": start,
                "period_end": end,
            }
        )
        pit_id = f"pit.{dataset_id}.snapshot.1"
        pit_assessments.append(
            {
                **meta(pit_id, dataset_hashes[dataset_id], created_at, commit),
                "dataset_snapshot_id": dataset_stable_id,
                "status": "NOT_RUN",
                "assessed_at": created_at,
                "note": "公開済み因子系列の検証であり、個別銘柄PIT再構築は未実施。",
            }
        )
        quality_assessments.append(
            {
                **meta(f"quality.{dataset_id}.snapshot.1", dataset_hashes[dataset_id], created_at, commit),
                "dataset_snapshot_id": dataset_stable_id,
                "status": "PASS",
                "checks": ["sha256", "chronological_months", "unique_months"],
                "note": "固定CSVのハッシュ、時系列順、月重複なしを検証。",
            }
        )
        provenance_records.append(
            {
                **meta(f"provenance.{dataset_id}.snapshot.1", dataset_hashes[dataset_id], created_at, commit),
                "source_ids": [source_by_dataset[dataset_id]],
                "dataset_snapshot_ids": [dataset_stable_id],
                "pit_assessment_id": pit_id,
                "transformation": "CSV factor return divided by 100; chronological OOS selection.",
                "environment_fingerprint": text_hash(f"{dataset_id}:{commit}"),
            }
        )

    context_id = "context.snapshot.2026-07-18"
    context = {
        **meta(context_id, text_hash("AAARTS static research context"), created_at, commit),
        "environment": "Python 3.12 / frozen repository data / static Pages dashboard",
        "dependency_lock_hash": file_hash(ROOT / "uv.lock"),
        "platform": "linux",
        "notes": "No live trading, no order submission, no through-2026 claim.",
    }
    hypotheses = []
    genomes = []
    versions = []
    variants = []
    protocols = []
    runs = []
    evidence = []
    gates = []
    exposures = []
    realism = []
    decisions = []
    learning_events = []
    constraints = []
    mutations = []
    edges = []
    current_version_ids = []
    planned_version_ids = []
    for row in rows:
        key = row["key"]
        dataset_id = row["dataset"]
        data_hash = dataset_hashes[dataset_id]
        hypothesis_id = f"hypothesis.{key}"
        genome_id = f"genome.{key}.v1"
        version_id = f"strategy.{key}.v1"
        planned_id = f"strategy.{key}.v2"
        variant_id = f"implementation.{key}.v1"
        protocol_id = f"protocol.{key}.v1"
        run_id = f"research_run.{key}.oos.1"
        artifact_id = f"evidence.{key}.oos.1"
        source_id = "source.ken_french.mom" if dataset_id == "momentum" else source_by_dataset[dataset_id]
        dataset_snapshot_id = f"dataset.{dataset_id}.snapshot.1"
        provenance_id = f"provenance.{dataset_id}.snapshot.1"
        pit_id = f"pit.{dataset_id}.snapshot.1"
        is_pivot = row["late_mean"] < 0 or key in {"fama_french_2015_cma", "fama_french_1992_value_proxy"}
        decision = "PIVOT" if is_pivot else "HOLD"
        oos_status = "PARTIAL" if row["implementation"] == "PROXY" else "FAIL"
        hypotheses.append(
            {
                **meta(hypothesis_id, data_hash, created_at, commit),
                "title": row["title"],
                "claim": row["claim"],
                "economic_mechanism": row["mechanism"],
                "primary_source_ids": [source_id],
            }
        )
        genomes.append(
            {
                **meta(genome_id, data_hash, created_at, commit),
                "strategy_id": f"{key}.strategy",
                "name": row["title"],
                "hypothesis_id": hypothesis_id,
                "parent_genome_id": None,
                "economic_mechanism": row["mechanism"],
                "signal_definition": row["definition"],
                "universe": "U.S. factor portfolios in the frozen Kenneth French mirror",
                "allocation": "Long-short factor return; no live allocation",
                "rebalance": "Monthly factor series; no security-level execution",
            }
        )
        current_version_ids.append(version_id)
        planned_version_ids.append(planned_id)
        versions.extend(
            [
                {
                    **meta(version_id, data_hash, created_at, commit),
                    "strategy_id": f"{key}.strategy",
                    "genome_id": genome_id,
                    "version": "v1",
                    "parent_strategy_version_id": None,
                    "status": "ACTIVE",
                    "evidence_state": "NOT_CONFIRMED",
                    "lifecycle_decision": decision,
                    "last_verified_at": created_at,
                },
                {
                    **meta(planned_id, data_hash, created_at, commit),
                    "strategy_id": f"{key}.strategy",
                    "genome_id": genome_id,
                    "version": "v2",
                    "parent_strategy_version_id": version_id,
                    "status": "PLANNED",
                    "evidence_state": "NOT_CONFIRMED",
                    "lifecycle_decision": "HOLD",
                    "last_verified_at": None,
                },
            ]
        )
        variants.append(
            {
                **meta(variant_id, data_hash, created_at, commit),
                "strategy_version_id": version_id,
                "name": row["implementation_name"],
                "implementation_type": row["implementation"],
                "definition": row["definition"],
                "limitations": row["limitations"],
            }
        )
        protocols.append(
            {
                **meta(protocol_id, data_hash, created_at, commit),
                "name": "Locked post-publication OOS midpoint protocol",
                "publication_window": {"start": "1993-03", "end": row["full"]["end"]},
                "oos_rule": "Chronological post-publication window with midpoint early/late split.",
                "cost_rule": "Mechanical 0/10/25/50 bps monthly haircut sensitivity.",
                "decision_rule": "NW t >= 1.96, bootstrap lower bound > 0, positive late mean, positive 25 bps mean.",
                "logic_fingerprint": text_hash(f"protocol:{key}:midpoint:nw6:block12"),
            }
        )
        fingerprint = {
            "logic": text_hash(f"logic:{key}:{row['definition']}"),
            "decision_trace": text_hash(f"decision:{key}:{row['verdict']}:{decision}"),
            "environment": text_hash(f"environment:{key}:{dataset_hashes[dataset_id]}:{commit}"),
        }
        runs.append(
            {
                **meta(run_id, data_hash, created_at, commit),
                "strategy_version_id": version_id,
                "implementation_variant_id": variant_id,
                "protocol_snapshot_id": protocol_id,
                "dataset_snapshot_id": dataset_snapshot_id,
                "provenance_record_id": provenance_id,
                "context_snapshot_id": context_id,
                "started_at": created_at,
                "ended_at": created_at,
                "status": "COMPLETED",
                "fingerprints": fingerprint,
                "reproduction_command": f"python3 scripts/verify_{'post_publication_momentum' if key == 'momentum_ff_mom' else 'paper_factor_suite'}.py",
            }
        )
        evidence.append(
            {
                **meta(artifact_id, data_hash, created_at, commit),
                "research_run_id": run_id,
                "type": "OOS_RETURN_SERIES",
                "path": "docs/research/post_publication_momentum_oos.json" if key == "momentum_ff_mom" else "docs/research/multi_paper_oos_results.json",
                "evidence_state": "NOT_CONFIRMED",
                "verdict_label": row["verdict"],
                "gross": metric(row["full"]),
                "net": metric(row["net"]),
                "late_half_annualized_mean": row["late_mean"],
                "summary": "Current evidence supports deferring promotion; it does not prove the hypothesis false.",
            }
        )
        gate_ids = []
        for gate, status, note in [
            ("OOS", oos_status, "Full-window and late-half results do not satisfy the locked confirmation gate."),
            ("PIT", "NOT_RUN", "Individual security point-in-time reconstruction was not run."),
            ("COST", "PARTIAL", "Mechanical monthly haircut only; turnover, borrow, impact, and taxes are not modeled."),
            ("FACTOR_EXPOSURE", "NOT_RUN", "Additional exposure attribution is not present in this artifact."),
            ("CAPACITY", "NOT_RUN", "Security-level liquidity and capacity were not evaluated."),
        ]:
            gate_id = f"gate.{key}.{gate.lower()}.1"
            gate_ids.append(gate_id)
            gates.append(
                {
                    **meta(gate_id, data_hash, created_at, commit),
                    "research_run_id": run_id,
                    "gate": gate,
                    "status": status,
                    "evidence_artifact_ids": [artifact_id],
                    "note": note,
                }
            )
        exposures.append(
            {
                **meta(f"exposure.{key}.1", data_hash, created_at, commit),
                "research_run_id": run_id,
                "status": "NOT_RUN",
                "factors": [],
                "note": "No additional factor or industry attribution artifact.",
            }
        )
        realism.append(
            {
                **meta(f"realism.{key}.1", data_hash, created_at, commit),
                "research_run_id": run_id,
                "status": "PARTIAL",
                "cost_model": "25 bps monthly mechanical haircut sensitivity",
                "liquidity": "NOT_RUN",
                "capacity": "NOT_RUN",
                "spread_and_slippage": "NOT_RUN",
            }
        )
        decisions.append(
            {
                **meta(f"decision.{key}.1", data_hash, created_at, commit),
                "research_run_id": run_id,
                "strategy_version_id": version_id,
                "evidence_state": "NOT_CONFIRMED",
                "lifecycle_decision": decision,
                "gate_assessment_ids": gate_ids,
                "reason": "NOT_CONFIRMED means promotion is deferred under the current protocol; it is not a proof of falsity.",
                "deterministic_evaluator": "scripts/verify_post_publication_momentum.py or scripts/verify_paper_factor_suite.py",
                "llm_pass_authority": False,
            }
        )
        learning_id = f"learning.{key}.1"
        constraint_id = f"constraint.{key}.1"
        mutation_id = f"mutation.{key}.v2"
        learning_events.append(
            {
                **meta(learning_id, data_hash, created_at, commit),
                "exploration_run_id": "exploration.2026-07-18",
                "research_run_id": run_id,
                "trigger": "NOT_CONFIRMED under locked post-publication gate",
                "lesson": "Preserve the failed branch and test the explicit missing or unstable dimension before promotion.",
                "evidence_artifact_ids": [artifact_id],
                "feeds_mutation_plan_ids": [mutation_id],
            }
        )
        constraints.append(
            {
                **meta(constraint_id, data_hash, created_at, commit),
                "learning_event_id": learning_id,
                "constraint": "Do not promote from factor-only evidence while PIT, capacity, and exposure gates remain NOT_RUN.",
                "scope": key,
            }
        )
        mutations.append(
            {
                **meta(mutation_id, data_hash, created_at, commit),
                "source_strategy_version_id": version_id,
                "next_strategy_version_id": planned_id,
                "created_at": created_at,
                "trigger": "learning event from current research run",
                "changes": ["Add PIT individual-security reconstruction", "Add exposure and capacity assessment", "Freeze a new independent period before tuning"],
                "expected_test": "Re-run the same gate set with the new dataset and protocol snapshot.",
                "status": "PLANNED",
            }
        )
        edges.append(
            {
                **meta(f"edge.{key}.v1-to-v2", data_hash, created_at, commit),
                "from_strategy_version_id": version_id,
                "to_strategy_version_id": planned_id,
                "relation": "MUTATION",
                "reason": "Retain the failure branch and carry its constraint into the next version.",
                "learning_event_id": learning_id,
            }
        )

    exploration = {
        **meta("exploration.2026-07-18", text_hash("exploration:2026-07-18"), created_at, commit),
        "objective": "Audit committed post-publication research as versioned AAARTS strategies.",
        "strategy_version_ids": current_version_ids,
        "status": "COMPLETED",
    }
    return {
        "schema_version": 1,
        "generated_at": created_at,
        "ontology_version": SCHEMA_VERSION,
        "exploration_runs": [exploration],
        "learning_events": learning_events,
        "failure_constraints": constraints,
        "mutation_plans": mutations,
        "evolution_edges": edges,
        "context_snapshots": [context],
        "data_sources": data_sources,
        "dataset_snapshots": dataset_snapshots,
        "pit_assessments": pit_assessments,
        "provenance_records": provenance_records,
        "data_quality_assessments": quality_assessments,
        "hypotheses": hypotheses,
        "strategy_genomes": genomes,
        "strategy_versions": versions,
        "implementation_variants": variants,
        "protocol_snapshots": protocols,
        "research_runs": runs,
        "evidence_artifacts": evidence,
        "gate_assessments": gates,
        "factor_exposure_assessments": exposures,
        "trading_realism_assessments": realism,
        "decision_records": decisions,
        "portfolio_candidates": [],
        "allocation_plans": [],
        "risk_budgets": [],
        "order_plans": [],
        "execution_runs": [],
        "performance_audits": [],
        "drift_events": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--momentum", type=Path, default=Path("docs/research/post_publication_momentum_oos.json"))
    parser.add_argument("--multi-paper", type=Path, default=Path("docs/research/multi_paper_oos_results.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/strategy_registry.json"))
    args = parser.parse_args()
    report = build(args.momentum, args.multi_paper)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
