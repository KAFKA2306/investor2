import unittest

from scripts import build_ark_claim_evidence as MODULE


class ArkClaimEvidenceTest(unittest.TestCase):
    def test_ai_productivity_is_directional_not_causal(self):
        claim = {
            "evaluation_rule": "latest_productivity_direction",
            "measurement_gap": "economy-wide, not AI causal",
        }
        rows = [
            {
                "metric_id": "labor_productivity",
                "period": "2026-Q2",
                "value": 1.4,
                "unit": "percent_change_qoq_annualized",
                "feed_id": "ai-productivity",
                "logical_repo": "economic-releases",
                "mirror_snapshot_id": "snap",
                "mirror_sha256": "a" * 64,
            }
        ]
        result = MODULE.evaluate(claim, rows)
        self.assertEqual(result["classification"], "directionally_supporting")
        self.assertEqual(result["observation"]["causal_attribution"], "not_established")
        self.assertIsNone(result["research_implication"]["prescriptive_action"])

    def test_deferred_multiomics_creates_no_false_zero(self):
        claim = {"evaluation_rule": "deferred", "measurement_gap": "deferred"}
        result = MODULE.evaluate(claim, [])
        self.assertEqual(result["classification"], "deferred")
        self.assertEqual(result["observation"]["evidence_row_count"], 0)
        self.assertEqual(result["research_implication"]["thesis_state"], "deferred")

    def test_autonomous_vehicle_does_not_create_safety_rate(self):
        claim = {"evaluation_rule": "autonomous_vehicle_evidence", "measurement_gap": "no denominator"}
        rows = [
            {
                "metric_id": "autonomous_testing_miles",
                "period": "2024-11-30",
                "value": 1000.0,
                "unit": "miles",
                "feed_id": "autonomous-vehicles-summary",
                "logical_repo": "autonomous-vehicles",
                "mirror_snapshot_id": "snap",
                "mirror_sha256": "b" * 64,
            }
        ]
        result = MODULE.evaluate(claim, rows)
        self.assertFalse(result["observation"]["safety_rate_computed"])
        self.assertEqual(result["classification"], "mixed")

    def test_fund_claim_links_remain_derived_from_holdings_facts(self):
        fund_map = {
            "derivation_rule": "derived, not constituent-level fact",
            "funds": {"ARKQ": {"claim_ids": ["robotics"], "relation": "mandate_proxy"}},
        }
        claims = {"robotics": {"theme": "Robotics"}}
        series = [
            {
                "feed_id": "ark-etf-holdings-latest",
                "entity": "ARKQ",
                "metric_id": "holding_row_count",
                "value": 39,
                "unit": "holdings",
                "period": "2026-08-19",
                "mirror_snapshot_id": "snap",
                "mirror_sha256": "c" * 64,
            }
        ]
        output = MODULE.build_fund_links(fund_map, series, claims)
        record = output["records"][0]
        self.assertEqual(record["claim_themes"], ["Robotics"])
        self.assertIn("derived", record["boundary"])
        self.assertEqual(record["holdings_snapshot_audit"]["holding_row_count"]["value"], 39)

    def test_numeric_target_is_not_part_of_directional_claim_output(self):
        result = MODULE.evaluation_result("mixed", {"evidence_row_count": 1}, "gap")
        self.assertNotIn("target", result)
        self.assertNotIn("target_value", result)
        self.assertNotIn("buy", result["research_implication"]["text"].lower())


if __name__ == "__main__":
    unittest.main()
