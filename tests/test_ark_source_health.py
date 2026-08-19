import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_ark_source_health", ROOT / "scripts" / "build_ark_source_health.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ArkSourceHealthTest(unittest.TestCase):
    def test_ready_sources_must_be_live_checked(self):
        catalog = {
            "authority_rule": "domain repo authoritative",
            "sources": [{
                "theme": "X",
                "logical_repo": "x",
                "current_repo": "KAFKA2306/x",
                "status": "ready",
                "check_live": False,
                "canonical_url": "https://github.com/KAFKA2306/x/blob/main/index.json",
                "raw_url": None,
                "issue_url": "https://github.com/KAFKA2306/x/issues/1",
            }],
        }
        with self.assertRaisesRegex(ValueError, "ready source must be live checked"):
            MODULE.validate_catalog(catalog)

    def test_blocked_and_deferred_sources_are_not_fetched(self):
        catalog = {
            "authority_rule": "domain repo authoritative",
            "sources": [
                {
                    "theme": "A",
                    "logical_repo": "a",
                    "current_repo": "KAFKA2306/a",
                    "status": "blocked_external_evidence",
                    "check_live": False,
                    "canonical_url": "https://github.com/KAFKA2306/a/issues/1",
                    "raw_url": None,
                    "issue_url": "https://github.com/KAFKA2306/a/issues/1",
                },
                {
                    "theme": "B",
                    "logical_repo": "b",
                    "current_repo": "KAFKA2306/b",
                    "status": "deferred_by_user",
                    "check_live": False,
                    "canonical_url": "https://github.com/KAFKA2306/b/tree/main/api/v1",
                    "raw_url": None,
                    "issue_url": "https://github.com/KAFKA2306/b/issues/1",
                },
            ],
        }
        with patch.object(MODULE, "fetch_json") as fetch:
            result = MODULE.build_health(catalog)
        fetch.assert_not_called()
        self.assertEqual(result["status_counts"]["blocked_external_evidence"], 1)
        self.assertEqual(result["status_counts"]["deferred_by_user"], 1)

    def test_ready_source_records_hash_without_copying_payload(self):
        catalog = {
            "authority_rule": "domain repo authoritative",
            "sources": [{
                "theme": "X",
                "logical_repo": "x",
                "current_repo": "KAFKA2306/x",
                "status": "ready",
                "check_live": True,
                "canonical_url": "https://github.com/KAFKA2306/x/blob/main/index.json",
                "raw_url": "https://raw.githubusercontent.com/KAFKA2306/x/main/index.json",
                "issue_url": "https://github.com/KAFKA2306/x/issues/1",
            }],
        }
        with patch.object(MODULE, "fetch_json", return_value=(b'{"coverage":{"count":3},"dataset":"x"}', {"coverage":{"count":3},"dataset":"x"})):
            result = MODULE.build_health(catalog)
        row = result["sources"][0]
        self.assertEqual(row["live_check"], "ok")
        self.assertEqual(row["top_level_keys"], ["coverage", "dataset"])
        self.assertEqual(len(row["sha256"]), 64)
        self.assertNotIn("coverage", row)


if __name__ == "__main__":
    unittest.main()
