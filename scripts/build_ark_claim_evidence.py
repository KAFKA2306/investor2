#!/usr/bin/env python3
"""Connect ARK 2026 directional hypotheses to observed cross-theme evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERIES = ROOT / "api" / "v1" / "ark-big-ideas" / "series.json"
DEFAULT_CLAIMS = ROOT / "data" / "ark-big-ideas" / "claim-catalog.json"
DEFAULT_FUNDS = ROOT / "data" / "ark-big-ideas" / "fund-claim-map.json"
DEFAULT_OUTPUT = ROOT / "api" / "v1" / "ark-big-ideas"
VALID_CLASSES = {"directionally_supporting", "mixed", "unresolved", "deferred"}


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def evidence_ref(row: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "feed_id",
        "logical_repo",
        "metric_id",
        "period",
        "value",
        "unit",
        "entity",
        "fact_class",
        "mirror_snapshot_id",
        "mirror_sha256",
        "source_url",
        "dimensions",
    )
    return {key: row[key] for key in keep if key in row}


def rows_for(claim: dict[str, Any], series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feeds = set(claim["source_feed_ids"])
    metrics = set(claim["measurement_variables"])
    return [row for row in series if row.get("feed_id") in feeds and row.get("metric_id") in metrics]


def classify_trend(first: float, last: float) -> str:
    if last > first:
        return "directionally_supporting"
    if last == first:
        return "mixed"
    return "mixed"


def evaluation_result(classification: str, observation: dict[str, Any], gap: str) -> dict[str, Any]:
    if classification not in VALID_CLASSES:
        raise ValueError(f"invalid classification: {classification}")
    thesis_state = {
        "directionally_supporting": "strengthening",
        "mixed": "mixed",
        "unresolved": "insufficient_evidence",
        "deferred": "deferred",
    }[classification]
    text = {
        "directionally_supporting": "Observed proxies move in the direction of the ARK hypothesis, but the stated measurement gap remains material; this strengthens only the measured part of the thesis.",
        "mixed": "Observed evidence establishes activity or scale but does not test the full ARK hypothesis; treat the thesis as mixed rather than confirmed or rejected.",
        "unresolved": "Current evidence is insufficient to compare the ARK hypothesis with observation without inventing a proxy or denominator.",
        "deferred": "Evaluation is intentionally deferred; no zero or negative inference is created from the absence of active measurements.",
    }[classification]
    return {
        "classification": classification,
        "observation": observation,
        "measurement_gap": gap,
        "research_implication": {"thesis_state": thesis_state, "text": text, "prescriptive_action": None},
    }


def evaluate(claim: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    rule = claim["evaluation_rule"]
    gap = claim["measurement_gap"]
    if rule == "deferred":
        return evaluation_result("deferred", {"evidence_row_count": 0}, gap)
    if not rows:
        return evaluation_result("unresolved", {"evidence_row_count": 0}, gap)

    if rule == "cross_theme_coverage":
        feeds = sorted({row["feed_id"] for row in rows})
        classification = "mixed" if len(feeds) >= 3 else "unresolved"
        return evaluation_result(classification, {"evidence_row_count": len(rows), "covered_feeds": feeds}, gap)

    if rule == "entity_trend_share":
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get("entity", "unknown"))].append(row)
        comparisons = []
        for entity, entity_rows in groups.items():
            ordered = sorted(entity_rows, key=lambda row: str(row["period"]))
            if len(ordered) < 2:
                continue
            first, last = ordered[0], ordered[-1]
            comparisons.append(
                {
                    "entity": entity,
                    "first": first["value"],
                    "last": last["value"],
                    "increased": last["value"] > first["value"],
                }
            )
        positive = sum(1 for item in comparisons if item["increased"] is True)
        share = positive / len(comparisons) if comparisons else 0.0
        classification = "directionally_supporting" if comparisons and share >= 0.6 else "mixed"
        return evaluation_result(
            classification,
            {
                "entities_compared": len(comparisons),
                "share_increasing": round(share, 4),
                "comparisons": comparisons[:10],
            },
            gap,
        )

    if rule == "consumer_scale_evidence":
        latest = sorted(rows, key=lambda row: str(row["period"]))[-8:]
        return evaluation_result(
            "mixed",
            {"evidence_row_count": len(rows), "latest_observations": [evidence_ref(row) for row in latest]},
            gap,
        )

    if rule == "latest_productivity_direction":
        productivity = sorted(
            [row for row in rows if row["metric_id"] == "labor_productivity"], key=lambda row: str(row["period"])
        )
        if not productivity:
            return evaluation_result("unresolved", {"evidence_row_count": len(rows)}, gap)
        latest = productivity[-1]
        classification = "directionally_supporting" if latest["value"] > 0 else "mixed"
        return evaluation_result(
            classification,
            {"latest_labor_productivity": evidence_ref(latest), "causal_attribution": "not_established"},
            gap,
        )

    if rule == "bitcoin_partial":
        holdings = sorted(
            [row for row in rows if row["metric_id"] == "bitcoin_holdings"], key=lambda row: str(row["period"])
        )
        derivatives = [row for row in rows if row["feed_id"] == "bitcoin-derivatives-daily"]
        observation: dict[str, Any] = {
            "derivatives_metric_rows": len(derivatives),
            "bitcoin_network": "blocked_external_evidence",
        }
        if holdings:
            observation["treasury_first"] = evidence_ref(holdings[0])
            observation["treasury_latest"] = evidence_ref(holdings[-1])
            observation["treasury_holdings_increased"] = holdings[-1]["value"] > holdings[0]["value"]
        return evaluation_result("mixed", observation, gap)

    if rule == "issuer_supply_trend":
        supply = sorted(
            [row for row in rows if row["metric_id"] == "circulation_usdc"], key=lambda row: str(row["period"])
        )
        if len(supply) < 2:
            return evaluation_result("mixed", {"evidence_row_count": len(rows)}, gap)
        classification = classify_trend(supply[0]["value"], supply[-1]["value"])
        return evaluation_result(
            classification, {"first": evidence_ref(supply[0]), "latest": evidence_ref(supply[-1])}, gap
        )

    if rule in {"recent_vs_early_activity", "launch_cadence_trend"}:
        ordered = sorted(rows, key=lambda row: str(row["period"]))
        window = min(7 if rule == "recent_vs_early_activity" else 6, max(1, len(ordered) // 2))
        early = mean(float(row["value"]) for row in ordered[:window])
        recent = mean(float(row["value"]) for row in ordered[-window:])
        classification = classify_trend(early, recent)
        return evaluation_result(
            classification,
            {
                "window": window,
                "early_mean": early,
                "recent_mean": recent,
                "first_period": ordered[0]["period"],
                "latest_period": ordered[-1]["period"],
            },
            gap,
        )

    if rule == "robotics_deployment_evidence":
        status_counts = Counter(
            str(row.get("dimensions", {}).get("status", "unknown"))
            for row in rows
            if row["metric_id"] == "deployment_evidence"
        )
        classification = "mixed" if sum(status_counts.values()) else "unresolved"
        return evaluation_result(
            classification,
            {"deployment_events": sum(status_counts.values()), "status_counts": dict(sorted(status_counts.items()))},
            gap,
        )

    if rule == "distributed_energy_partial":
        construction = [
            row
            for row in rows
            if row["metric_id"] == "net_electrical_capacity"
            and "construction" in str(row.get("dimensions", {}).get("status", "")).casefold()
        ]
        return evaluation_result(
            "mixed",
            {
                "nuclear_capacity_rows": len(rows),
                "under_construction_capacity": [evidence_ref(row) for row in construction],
            },
            gap,
        )

    if rule == "autonomous_vehicle_evidence":
        metrics = {
            row["metric_id"]: evidence_ref(row)
            for row in rows
            if row["metric_id"] in {"autonomous_testing_miles", "permitted_company_groups"}
        }
        classification = "mixed" if metrics else "unresolved"
        return evaluation_result(classification, {"deployment_metrics": metrics, "safety_rate_computed": False}, gap)

    if rule == "autonomous_logistics_commercial":
        commercial = 0
        for row in rows:
            dims = row.get("dimensions", {})
            if "commercial" in " ".join(str(value) for value in dims.values()).casefold():
                commercial += 1
        classification = "directionally_supporting" if commercial > 0 else "mixed"
        return evaluation_result(
            classification, {"operation_events": len(rows), "commercial_marked_events": commercial}, gap
        )

    raise ValueError(f"unknown evaluation rule: {rule}")


def build_fund_links(
    fund_map: dict[str, Any], series: list[dict[str, Any]], claims_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    holdings = [row for row in series if row.get("feed_id") == "ark-etf-holdings-latest"]
    by_fund: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in holdings:
        entity = str(row.get("entity", ""))
        if entity in fund_map["funds"]:
            by_fund[entity][row["metric_id"]] = {
                "value": row["value"],
                "unit": row["unit"],
                "period": row["period"],
                "mirror_snapshot_id": row["mirror_snapshot_id"],
                "mirror_sha256": row["mirror_sha256"],
            }
    records = []
    for fund, mapping in fund_map["funds"].items():
        records.append(
            {
                "fund": fund,
                "relation": mapping["relation"],
                "claim_ids": mapping["claim_ids"],
                "claim_themes": [claims_by_id[claim_id]["theme"] for claim_id in mapping["claim_ids"]],
                "holdings_snapshot_audit": by_fund.get(fund, {}),
                "boundary": fund_map["derivation_rule"],
            }
        )
    return {"schema_version": 1, "records": records}


def build(
    series_doc: dict[str, Any], claims_doc: dict[str, Any], fund_map: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    series = series_doc["records"]
    claims = claims_doc["claims"]
    if len(claims) != 13 or len({claim["claim_id"] for claim in claims}) != 13:
        raise ValueError("claim catalog must contain exactly 13 unique ARK 2026 themes")
    records: list[dict[str, Any]] = []
    for claim in claims:
        selected = rows_for(claim, series)
        result = evaluate(claim, selected)
        records.append(
            {
                "claim_id": claim["claim_id"],
                "theme": claim["theme"],
                "claim_kind": claims_doc["source_kind"],
                "claim_source_url": claims_doc["source_url"],
                "claim_paraphrase": claim["claim_paraphrase"],
                "measurement_variables": claim["measurement_variables"],
                "source_feed_ids": claim["source_feed_ids"],
                "evidence_row_count": len(selected),
                "deviation": {"kind": "directional_evidence_gap", **result},
            }
        )
    counts: Counter[str] = Counter()
    for record in records:
        deviation = record.get("deviation")
        if not isinstance(deviation, dict):
            raise ValueError("claim evidence missing deviation object")
        classification = deviation.get("classification")
        if not isinstance(classification, str):
            raise ValueError("claim evidence missing classification")
        counts[classification] += 1
    summary = {
        "schema_version": 1,
        "claim_count": len(records),
        "classification_counts": dict(sorted(counts.items())),
        "rules": [
            claims_doc["target_rule"],
            "A directional-support classification is not causal proof and is not investment advice.",
            "Missing/deferred evidence is never converted to zero or a negative fact.",
        ],
    }
    by_id = {claim["claim_id"]: claim for claim in claims}
    return summary, {"schema_version": 1, "records": records}, build_fund_links(fund_map, series, by_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--fund-map", type=Path, default=DEFAULT_FUNDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary, evidence, funds = build(load(args.series), load(args.claims), load(args.fund_map))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "claim-summary.json").write_bytes(canonical_json(summary))
    (args.output_dir / "claim-evidence.json").write_bytes(canonical_json(evidence))
    (args.output_dir / "fund-claim-links.json").write_bytes(canonical_json(funds))
    print(
        json.dumps(
            {
                "claims": summary["claim_count"],
                "classes": summary["classification_counts"],
                "funds": len(funds["records"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
