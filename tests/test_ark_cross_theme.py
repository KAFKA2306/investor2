import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import build_ark_cross_theme as MODULE


class ArkCrossThemeTest(unittest.TestCase):
    def test_deferred_source_has_no_feed_and_is_not_zero_filled(self):
        source_catalog = {
            "sources": [
                {
                    "theme": "Productivity",
                    "logical_repo": "economic-releases",
                    "current_repo": "KAFKA2306/econalert",
                    "status": "ready",
                    "canonical_url": "https://github.com/KAFKA2306/econalert/blob/main/latest.json",
                    "issue_url": "https://github.com/KAFKA2306/econalert/issues/12",
                },
                {
                    "theme": "Multiomics",
                    "logical_repo": "multiomics",
                    "current_repo": "KAFKA2306/kafin3",
                    "status": "deferred_by_user",
                    "canonical_url": "https://github.com/KAFKA2306/kafin3/blob/main/index.json",
                    "issue_url": "https://github.com/KAFKA2306/kafin3/issues/6",
                },
            ]
        }
        metric_catalog = {
            "authority_rule": "domain authoritative",
            "feeds": [
                {
                    "feed_id": "productivity",
                    "logical_repo": "economic-releases",
                    "adapter": "bls_productivity",
                    "repository": "KAFKA2306/econalert",
                    "ref": "main",
                    "raw_url": "https://raw.githubusercontent.com/KAFKA2306/econalert/main/latest.json",
                }
            ],
        }
        payload = {
            "sector": "Nonfarm business",
            "rate_basis": "qoq annualized",
            "source_url": "https://api.bls.gov/",
            "observations": [{"period": "2026-Q2", "labor_productivity": 1.4, "unit_labor_costs": 1.3}],
        }
        raw = json.dumps(payload).encode()
        temp = Path(tempfile.mkdtemp(dir=MODULE.ROOT))
        try:
            index, series, matrix = MODULE.build_projection(
                source_catalog,
                metric_catalog,
                snapshot_root=temp / "snapshots",
                snapshot_catalog=temp / "catalog.ndjson",
                register=False,
                fetcher=lambda _: (raw, payload),
            )
        finally:
            shutil.rmtree(temp)
        self.assertEqual(index["active_feed_count"], 1)
        self.assertEqual(index["status_counts"]["deferred_by_user"], 1)
        self.assertFalse(any(row["logical_repo"] == "multiomics" for row in series["records"]))
        deferred = next(row for row in matrix["sources"] if row["logical_repo"] == "multiomics")
        self.assertEqual(deferred["projection"], {"excluded": True, "reason": "deferred_by_user"})

    def test_autonomous_vehicle_adapter_never_makes_a_safety_rate(self):
        payload = {
            "california_dmv": {
                "autonomous_testing_miles": 1000.0,
                "company_permit_group_count": 2,
                "reported_disengagements": 4,
                "metric_warning": "not a safety rate",
                "period": {"end": "2024-11-30"},
                "source_urls": ["https://www.dmv.ca.gov/source"],
            },
            "nhtsa_sgo": {
                "ads": {"report_count_2024_plus": 7},
                "level_2_adas": {"report_count_2024_plus": 9},
                "comparison_warning": "not exposure normalized",
                "source_page": "https://www.nhtsa.gov/source",
            },
        }
        rows = MODULE.adapt_autonomous_vehicles_summary(payload)
        metrics = {row["metric_id"] for row in rows}
        self.assertIn("autonomous_testing_miles", metrics)
        self.assertIn("reported_disengagements", metrics)
        self.assertNotIn("safety_rate", metrics)
        self.assertNotIn("miles_per_disengagement", metrics)

    def test_bitcoin_derivatives_keep_perpetual_and_delivery_separate(self):
        payload = {
            "records": [
                {"date": "2026-08-19", "contract_type": "PERPETUAL", "symbol": "BTCUSDT", "funding_rate_sum": 0.0001, "perpetual_premium_pct": -0.03},
                {"date": "2026-08-19", "contract_type": "CURRENT_QUARTER", "symbol": "BTCUSDT_260925", "annualized_delivery_basis_pct": 2.1},
            ]
        }
        rows = MODULE.adapt_bitcoin_derivatives_daily(payload)
        by_entity = {}
        for row in rows:
            by_entity.setdefault(row["entity"], set()).add(row["metric_id"])
        self.assertEqual(by_entity["BTCUSDT"], {"funding_rate_sum", "perpetual_premium_pct"})
        self.assertEqual(by_entity["BTCUSDT_260925"], {"annualized_delivery_basis_pct"})

    def test_robotics_events_are_evidence_not_population_estimates(self):
        payload = {
            "records": [
                {
                    "company": "Example Corp",
                    "factory": "Plant A",
                    "country": "JP",
                    "deployment_stage": "production",
                    "equipment_type": "industrial_robot",
                    "status": "operational",
                    "observed_at": "2026-04-01",
                    "source_url": "https://example.com/official",
                    "quantity": 4,
                    "quantity_unit": "industrial_robots",
                    "quantity_qualifier": "exact",
                }
            ]
        }
        rows = MODULE.adapt_robotics_deployments(payload)
        event = next(row for row in rows if row["metric_id"] == "deployment_evidence")
        quantity = next(row for row in rows if row["metric_id"] == "disclosed_equipment_quantity")
        self.assertEqual(event["value"], 1)
        self.assertEqual(event["unit"], "evidence_events")
        self.assertEqual(quantity["value"], 4)
        self.assertEqual(quantity["unit"], "industrial_robots")

    def test_source_readiness_and_metric_feeds_must_match_one_to_one(self):
        source_catalog = {
            "sources": [
                {"logical_repo": "a", "status": "ready", "current_repo": "KAFKA2306/a"},
                {"logical_repo": "b", "status": "blocked_external_evidence", "current_repo": "KAFKA2306/b"},
            ]
        }
        metric_catalog = {"feeds": []}
        with self.assertRaisesRegex(ValueError, "metric catalog requires feeds"):
            MODULE.validate_catalogs(source_catalog, metric_catalog)


if __name__ == "__main__":
    unittest.main()
