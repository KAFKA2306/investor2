#!/usr/bin/env python3
"""Materialize domain-repository JSON and build a cross-theme ARK evidence projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from scripts import snapshot_store

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CATALOG = ROOT / "data" / "ark-big-ideas" / "source-catalog.json"
DEFAULT_METRIC_CATALOG = ROOT / "data" / "ark-big-ideas" / "metric-catalog.json"
DEFAULT_SNAPSHOT_ROOT = ROOT / "data" / "ark-big-ideas" / "snapshots"
DEFAULT_API_DIR = ROOT / "api" / "v1" / "ark-big-ideas"
DEFAULT_SNAPSHOT_CATALOG = ROOT / "data" / "input_ledger" / "snapshot_catalog.ndjson"
MIRROR_SOURCE = "github_domain_repo_snapshot"
UA = "investor2-ark-cross-theme/1.0 github.com/KAFKA2306/investor2"
ACTIVE_STATUSES = {"ready", "accumulating"}


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def fetch_json(url: str) -> tuple[bytes, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
    if not raw:
        raise ValueError(f"empty domain JSON: {url}")
    return raw, json.loads(raw)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_catalogs(source_catalog: dict[str, Any], metric_catalog: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sources = source_catalog.get("sources")
    feeds = metric_catalog.get("feeds")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source catalog requires sources")
    if not isinstance(feeds, list) or not feeds:
        raise ValueError("metric catalog requires feeds")

    source_map = {str(row["logical_repo"]): row for row in sources}
    if len(source_map) != len(sources):
        raise ValueError("duplicate logical_repo in source catalog")
    feed_ids = [str(row["feed_id"]) for row in feeds]
    if len(feed_ids) != len(set(feed_ids)):
        raise ValueError("duplicate feed_id")

    feeds_by_repo = Counter(str(row["logical_repo"]) for row in feeds)
    active_repos = {repo for repo, row in source_map.items() if row["status"] in ACTIVE_STATUSES}
    if set(feeds_by_repo) != active_repos:
        missing = sorted(active_repos - set(feeds_by_repo))
        extra = sorted(set(feeds_by_repo) - active_repos)
        raise ValueError(f"metric feed readiness drift: missing={missing} extra={extra}")
    if any(count != 1 for count in feeds_by_repo.values()):
        raise ValueError("each active logical_repo must have exactly one metric feed")

    required = {"feed_id", "logical_repo", "adapter", "repository", "ref", "raw_url"}
    for feed in feeds:
        missing = required - feed.keys()
        if missing:
            raise ValueError(f"feed missing fields {sorted(missing)}: {feed}")
        source = source_map[str(feed["logical_repo"])]
        if source["status"] not in ACTIVE_STATUSES:
            raise ValueError(f"inactive source has a metric feed: {feed['logical_repo']}")
        if str(feed["repository"]) != str(source["current_repo"]):
            raise ValueError(f"feed repository drift: {feed['feed_id']}")
        if not str(feed["raw_url"]).startswith("https://raw.githubusercontent.com/KAFKA2306/"):
            raise ValueError(f"feed must use KAFKA2306 raw GitHub JSON: {feed['feed_id']}")
    return source_map, feeds


def metric_row(
    *,
    metric_id: str,
    period: str,
    granularity: str,
    value: int | float,
    unit: str,
    entity: str | None = None,
    qualifier: str | None = None,
    fact_class: str = "observed",
    source_url: str | None = None,
    dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"metric must be numeric: {metric_id}={value!r}")
    row: dict[str, Any] = {
        "metric_id": metric_id,
        "period": period,
        "period_granularity": granularity,
        "value": value,
        "unit": unit,
        "fact_class": fact_class,
    }
    if entity is not None:
        row["entity"] = entity
    if qualifier is not None:
        row["qualifier"] = qualifier
    if source_url is not None:
        row["source_url"] = source_url
    if dimensions:
        row["dimensions"] = dimensions
    return row


def adapt_bls_productivity(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observation in payload["observations"]:
        for metric_id in ("labor_productivity", "unit_labor_costs"):
            value = observation.get(metric_id)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rows.append(
                    metric_row(
                        metric_id=metric_id,
                        period=str(observation["period"]),
                        granularity="quarter",
                        value=value,
                        unit="percent_change_qoq_annualized",
                        entity=str(payload.get("sector", "Nonfarm business")),
                        source_url=payload.get("source_url"),
                        dimensions={"rate_basis": payload.get("rate_basis")},
                    )
                )
    return rows


def adapt_ai_infrastructure_capex(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for observation in payload.get("observations", []):
        if observation.get("concept_id") != "capital_expenditures" or observation.get("value_type") != "actual":
            continue
        rows.append(
            metric_row(
                metric_id="capital_expenditures",
                period=str(observation["period_end"]),
                granularity=str(observation.get("period_type", "quarter")),
                value=observation["value"],
                unit=str(observation["unit"]),
                entity=str(observation.get("ticker") or observation["entity"]),
                source_url=observation.get("source_url"),
                dimensions={"fiscal_period": observation.get("fiscal_period"), "source_tier": observation.get("source_tier")},
            )
        )
    return rows


def adapt_ai_consumer_metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for observation in payload.get("observations", []):
        value = observation.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        rows.append(
            metric_row(
                metric_id=str(observation["metric"]),
                period=str(observation["as_of"]),
                granularity="as_of_date",
                value=value,
                unit=str(observation["unit"]),
                entity=f"{observation['provider']} / {observation['product']}",
                qualifier=observation.get("qualifier"),
                source_url=observation.get("source_url"),
                dimensions={"geography": observation.get("geography"), "reported_period": observation.get("period")},
            )
        )
    return rows


def adapt_nuclear_capacity(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    period = str(payload["observed_at"])
    for key in ("operating", "under_construction", "suspended_operation", "permanent_shutdown"):
        state = payload[key]
        dimensions = {"status": state["status"]}
        rows.append(metric_row(metric_id="reactor_count", period=period, granularity="snapshot", value=state["reactor_count"], unit="reactors", entity="Global nuclear fleet", dimensions=dimensions))
        rows.append(metric_row(metric_id="net_electrical_capacity", period=period, granularity="snapshot", value=state["net_electrical_capacity_mw"], unit="MW", entity="Global nuclear fleet", dimensions=dimensions))
    return rows


def adapt_autonomous_vehicles_summary(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dmv = payload["california_dmv"]
    period = str(dmv["period"]["end"])
    source_url = dmv["source_urls"][0]
    rows = [
        metric_row(metric_id="autonomous_testing_miles", period=period, granularity="reporting_period_end", value=dmv["autonomous_testing_miles"], unit="miles", entity="California DMV autonomous testing", source_url=source_url),
        metric_row(metric_id="reported_disengagements", period=period, granularity="reporting_period_end", value=dmv["reported_disengagements"], unit="events", entity="California DMV autonomous testing", source_url=source_url, dimensions={"warning": dmv["metric_warning"]}),
        metric_row(metric_id="permitted_company_groups", period=period, granularity="reporting_period_end", value=dmv["company_permit_group_count"], unit="company_groups", entity="California DMV autonomous testing", source_url=source_url),
    ]
    nhtsa = payload["nhtsa_sgo"]
    for system, label in (("ads", "ADS"), ("level_2_adas", "Level 2 ADAS")):
        rows.append(
            metric_row(
                metric_id="sgo_report_count_2024_plus",
                period="2024+",
                granularity="open_interval",
                value=nhtsa[system]["report_count_2024_plus"],
                unit="reports",
                entity=label,
                source_url=nhtsa["source_page"],
                dimensions={"warning": nhtsa["comparison_warning"]},
                fact_class="domain_derived",
            )
        )
    return rows


def adapt_bitcoin_treasury_snapshots(payload: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {
        "bitcoin_holdings",
        "bitcoin_aggregate_purchase_price_usd",
        "convertible_notes_principal_outstanding_usd",
        "preferred_stock_notional_outstanding_usd",
        "usd_reserve",
    }
    entity = str(payload.get("entity", {}).get("name", "Strategy Inc"))
    rows = []
    for snapshot in payload.get("snapshots", []):
        for name, fact in snapshot.get("state", {}).items():
            if name not in selected:
                continue
            rows.append(
                metric_row(
                    metric_id=name,
                    period=str(snapshot["known_at"]),
                    granularity="known_at",
                    value=fact["value"],
                    unit=str(fact["unit"]),
                    entity=entity,
                    source_url=fact.get("source_url"),
                    fact_class="state",
                    dimensions={"effective_at": fact.get("effective_at"), "trigger_event_id": snapshot.get("trigger_event_id")},
                )
            )
    return rows


def adapt_bitcoin_derivatives_daily(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in payload.get("records", []):
        contract_type = str(record["contract_type"])
        metrics = (
            ("funding_rate_sum", "rate_decimal"),
            ("perpetual_premium_pct", "percent"),
        ) if contract_type == "PERPETUAL" else (("annualized_delivery_basis_pct", "percent"),)
        for metric_id, unit in metrics:
            value = record.get(metric_id)
            if value is None:
                continue
            rows.append(
                metric_row(
                    metric_id=metric_id,
                    period=str(record["date"]),
                    granularity="day",
                    value=value,
                    unit=unit,
                    entity=str(record["symbol"]),
                    fact_class="domain_derived",
                    dimensions={"contract_type": contract_type},
                )
            )
    return rows


def adapt_tokenized_assets_issuer(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in payload.get("records", []):
        for metric_id, unit in (("circulation_usdc", "USDC"), ("reserve_fair_value_usd", "USD")):
            rows.append(
                metric_row(
                    metric_id=metric_id,
                    period=str(record["as_of"]),
                    granularity="as_of_date",
                    value=record[metric_id],
                    unit=unit,
                    entity=str(record["asset_id"]).upper(),
                    source_url=record.get("source_url"),
                    dimensions={"issuer_scope": record.get("issuer_scope"), "report_published_at": record.get("report_published_at")},
                )
            )
    return rows


def adapt_defi_daily(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in payload.get("records", []):
        for metric_id, entity in (("aave_event_count", "Aave V3"), ("aave_liquidation_count", "Aave V3"), ("uniswap_swap_count", "Uniswap V3")):
            rows.append(metric_row(metric_id=metric_id, period=str(record["date"]), granularity="day", value=record[metric_id], unit="events", entity=entity, fact_class="domain_derived"))
    return rows


def adapt_robotics_deployments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in payload.get("records", []):
        dimensions = {
            "status": record["status"],
            "deployment_stage": record["deployment_stage"],
            "equipment_type": record["equipment_type"],
            "factory": record["factory"],
            "country": record["country"],
        }
        rows.append(metric_row(metric_id="deployment_evidence", period=str(record["observed_at"]), granularity="event_date", value=1, unit="evidence_events", entity=str(record["company"]), source_url=record.get("source_url"), fact_class="evidence_event", dimensions=dimensions))
        if "quantity" in record:
            rows.append(metric_row(metric_id="disclosed_equipment_quantity", period=str(record["observed_at"]), granularity="event_date", value=record["quantity"], unit=str(record["quantity_unit"]), entity=str(record["company"]), qualifier=record.get("quantity_qualifier"), source_url=record.get("source_url"), dimensions=dimensions))
        metric = record.get("performance_metric")
        if isinstance(metric, dict) and isinstance(metric.get("value"), (int, float)):
            rows.append(metric_row(metric_id=str(metric["name"]), period=str(record["observed_at"]), granularity="event_date", value=metric["value"], unit=str(metric["unit"]), entity=str(record["company"]), qualifier=metric.get("qualifier"), source_url=record.get("source_url"), dimensions=dimensions))
    return rows


def adapt_autonomous_logistics_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for record in payload.get("records", []):
        rows.append(
            metric_row(
                metric_id="operation_evidence_event",
                period=str(record["effective_at"]),
                granularity="event_date",
                value=1,
                unit="evidence_events",
                entity=str(record["operator_id"]),
                source_url=record.get("source_url"),
                fact_class="evidence_event",
                dimensions={"event_type": record["event_type"], "mode": record["mode"], "operation_status": record["operation_status"]},
            )
        )
    return rows


def adapt_space_launches_monthly(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        metric_row(metric_id="completed_launch_count", period=str(record["month"]), granularity="month", value=record["launch_count"], unit="launches", entity="Tracked reusable-launch operators", fact_class="domain_derived")
        for record in payload.get("records", [])
    ]


def adapt_ark_etf_holdings_latest(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = datetime.strptime(str(payload["as_of"]), "%m/%d/%Y").date().isoformat()
    rows = [metric_row(metric_id="snapshot_count", period=parsed, granularity="as_of_date", value=payload["snapshot_count"], unit="snapshots", entity="ARK ETF holdings archive", fact_class="audit")]
    for fund, record in payload.get("funds", {}).items():
        rows.append(metric_row(metric_id="holding_row_count", period=parsed, granularity="as_of_date", value=record["row_count"], unit="holdings", entity=fund, fact_class="audit", source_url=record.get("source_csv_url")))
        rows.append(metric_row(metric_id="portfolio_weight_total", period=parsed, granularity="as_of_date", value=record["audit"]["weight_total"], unit="percent", entity=fund, fact_class="audit", source_url=record.get("source_csv_url")))
    return rows


ADAPTERS: dict[str, Callable[[dict[str, Any]], list[dict[str, Any]]]] = {
    "bls_productivity": adapt_bls_productivity,
    "ai_infrastructure_capex": adapt_ai_infrastructure_capex,
    "ai_consumer_metrics": adapt_ai_consumer_metrics,
    "nuclear_capacity": adapt_nuclear_capacity,
    "autonomous_vehicles_summary": adapt_autonomous_vehicles_summary,
    "bitcoin_treasury_snapshots": adapt_bitcoin_treasury_snapshots,
    "bitcoin_derivatives_daily": adapt_bitcoin_derivatives_daily,
    "tokenized_assets_issuer": adapt_tokenized_assets_issuer,
    "defi_daily": adapt_defi_daily,
    "robotics_deployments": adapt_robotics_deployments,
    "autonomous_logistics_events": adapt_autonomous_logistics_events,
    "space_launches_monthly": adapt_space_launches_monthly,
    "ark_etf_holdings_latest": adapt_ark_etf_holdings_latest,
}


def materialize_snapshot(
    *,
    feed: dict[str, Any],
    raw: bytes,
    snapshot_root: Path,
    retrieved_at: str,
    register: bool,
    snapshot_catalog: Path,
) -> dict[str, Any]:
    digest = hashlib.sha256(raw).hexdigest()
    artifact = snapshot_root / str(feed["feed_id"]) / f"{digest}.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    if not artifact.exists():
        artifact.write_bytes(raw)

    reuse_key = f"ark-big-ideas:{feed['feed_id']}"
    artifact_path = artifact.relative_to(ROOT).as_posix()
    if not register:
        return {"snapshot_id": f"preview:{digest[:20]}", "artifact_path": artifact_path, "artifact_sha256": digest, "registered": False}

    entries = snapshot_store.load_ndjson(snapshot_catalog)
    prior = [entry for entry in entries if entry.get("reuse_key") == reuse_key]
    if prior:
        latest = max(prior, key=lambda entry: snapshot_store.parse_observed_at(entry["observed_at"]))
        if latest["artifact_sha256"] == digest:
            return {"snapshot_id": latest["snapshot_id"], "artifact_path": latest["artifact_path"], "artifact_sha256": digest, "registered": True, "reused": True}

    registry = snapshot_store.load_registry()
    entry = snapshot_store.build_entry(
        root=ROOT,
        registry=registry,
        dataset_id="ark-big-ideas-domain-mirror",
        reuse_key=reuse_key,
        artifact_path=artifact_path,
        source=MIRROR_SOURCE,
        source_kind="connector",
        observed_at=retrieved_at,
        schema_version="ark-domain-mirror.v1",
        provenance={
            "repository": feed["repository"],
            "ref": feed["ref"],
            "query_or_scope": feed["feed_id"],
            "retrieved_at": retrieved_at,
            "source_urls": [feed["raw_url"]],
        },
    )
    snapshot_store.append_entry(entry, snapshot_catalog)
    return {"snapshot_id": entry["snapshot_id"], "artifact_path": artifact_path, "artifact_sha256": digest, "registered": True, "reused": False}


def build_projection(
    source_catalog: dict[str, Any],
    metric_catalog: dict[str, Any],
    *,
    snapshot_root: Path,
    snapshot_catalog: Path,
    register: bool,
    fetcher: Callable[[str], tuple[bytes, Any]] = fetch_json,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_map, feeds = validate_catalogs(source_catalog, metric_catalog)
    retrieved_at = datetime.now(UTC).isoformat()
    series: list[dict[str, Any]] = []
    feed_evidence: dict[str, dict[str, Any]] = {}

    for feed in feeds:
        adapter_name = str(feed["adapter"])
        if adapter_name not in ADAPTERS:
            raise ValueError(f"unknown ARK metric adapter: {adapter_name}")
        raw, payload = fetcher(str(feed["raw_url"]))
        if not isinstance(payload, dict):
            raise ValueError(f"domain feed must be a JSON object: {feed['feed_id']}")
        snapshot = materialize_snapshot(feed=feed, raw=raw, snapshot_root=snapshot_root, retrieved_at=retrieved_at, register=register, snapshot_catalog=snapshot_catalog)
        source = source_map[str(feed["logical_repo"])]
        adapted = ADAPTERS[adapter_name](payload)
        if not adapted:
            raise ValueError(f"adapter produced no metrics: {feed['feed_id']}")
        for row in adapted:
            series.append(
                {
                    "theme": source["theme"],
                    "logical_repo": feed["logical_repo"],
                    "feed_id": feed["feed_id"],
                    "domain_canonical_url": source["canonical_url"],
                    "domain_json_url": feed["raw_url"],
                    "mirror_snapshot_id": snapshot["snapshot_id"],
                    "mirror_sha256": snapshot["artifact_sha256"],
                    **row,
                }
            )
        feed_evidence[str(feed["logical_repo"])] = {
            "feed_id": feed["feed_id"],
            "adapter": adapter_name,
            "row_count": len(adapted),
            "mirror_snapshot_id": snapshot["snapshot_id"],
            "mirror_sha256": snapshot["artifact_sha256"],
            "artifact_path": snapshot["artifact_path"],
        }

    series.sort(key=lambda row: (str(row["logical_repo"]), str(row["metric_id"]), str(row.get("entity", "")), str(row["period"])))
    matrix_rows = []
    for source in source_catalog["sources"]:
        evidence = feed_evidence.get(str(source["logical_repo"]))
        matrix_rows.append(
            {
                "theme": source["theme"],
                "logical_repo": source["logical_repo"],
                "current_repo": source["current_repo"],
                "status": source["status"],
                "issue_url": source["issue_url"],
                "canonical_url": source["canonical_url"],
                "projection": evidence if evidence is not None else {"excluded": True, "reason": source["status"]},
            }
        )

    status_counts = dict(sorted(Counter(str(row["status"]) for row in source_catalog["sources"]).items()))
    index = {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "authority_rule": metric_catalog["authority_rule"],
        "source_count": len(source_catalog["sources"]),
        "active_feed_count": len(feeds),
        "metric_row_count": len(series),
        "theme_count": len({str(row["theme"]) for row in series}),
        "status_counts": status_counts,
        "excluded": [
            {"logical_repo": row["logical_repo"], "status": row["status"]}
            for row in source_catalog["sources"]
            if row["status"] not in ACTIVE_STATUSES
        ],
        "views": {"series": "series.json", "evidence_matrix": "evidence-matrix.json"},
        "rules": [
            "domain repositories remain authoritative; mirrored JSON is evidence only",
            "deferred and externally blocked domains emit no zero-filled metrics",
            "observed/state/evidence-event/domain-derived/audit fact classes remain explicit",
            "ADS and Level 2 ADAS report counts are not safety rates",
            "Bitcoin perpetual funding/premium and delivery basis remain separate metrics",
            "issuer-reported token supply and chain-observed supply are never implicitly merged",
            "robotics evidence counts are evidence events, not an estimate of the global installed robot population",
        ],
    }
    return index, {"schema_version": 1, "records": series}, {"schema_version": 1, "sources": matrix_rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-catalog", type=Path, default=DEFAULT_SOURCE_CATALOG)
    parser.add_argument("--metric-catalog", type=Path, default=DEFAULT_METRIC_CATALOG)
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--snapshot-catalog", type=Path, default=DEFAULT_SNAPSHOT_CATALOG)
    parser.add_argument("--api-dir", type=Path, default=DEFAULT_API_DIR)
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()

    source_catalog = load_json(args.source_catalog)
    metric_catalog = load_json(args.metric_catalog)
    index, series, matrix = build_projection(
        source_catalog,
        metric_catalog,
        snapshot_root=args.snapshot_root,
        snapshot_catalog=args.snapshot_catalog,
        register=args.register,
    )
    args.api_dir.mkdir(parents=True, exist_ok=True)
    (args.api_dir / "index.json").write_bytes(canonical_json(index))
    (args.api_dir / "series.json").write_bytes(canonical_json(series))
    (args.api_dir / "evidence-matrix.json").write_bytes(canonical_json(matrix))
    print(json.dumps({"feeds": index["active_feed_count"], "rows": index["metric_row_count"], "status_counts": index["status_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
