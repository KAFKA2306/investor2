import unittest
from unittest.mock import patch

from scripts import build_ai_economics_source_health as MODULE


class AiEconomicsSourceHealthTest(unittest.TestCase):
    def test_locator_keeps_finanalist_authoritative(self):
        source = {
            "schema_version": 1,
            "theme": "AI Economics",
            "authority_rule": "finAnalist authoritative; locator/hash only",
            "repository": "KAFKA2306/finAnalist",
            "canonical_url": "https://github.com/KAFKA2306/finAnalist/blob/main/api/v1/ai-economics/index.json",
            "raw_url": "https://raw.githubusercontent.com/KAFKA2306/finAnalist/main/api/v1/ai-economics/index.json",
            "manifest_url": "https://raw.githubusercontent.com/KAFKA2306/finAnalist/main/api/v1/ai-economics/manifest.json",
            "issue_url": "https://github.com/KAFKA2306/finAnalist/issues/15",
            "minimum_observation_count": 36,
        }
        index_raw = b'{"observation_count":36,"updated_at":"2026-08-24T17:12:59Z"}'
        manifest_raw = b'{"observation_count":36,"content_digest":"' + b'a' * 64 + b'"}'
        with patch.object(MODULE, "fetch_json", side_effect=[
            (index_raw, {"observation_count": 36, "updated_at": "2026-08-24T17:12:59Z"}),
            (manifest_raw, {"observation_count": 36, "content_digest": "a" * 64}),
        ]):
            result = MODULE.build(source)
        self.assertEqual(result["repository"], "KAFKA2306/finAnalist")
        self.assertEqual(result["observation_count"], 36)
        self.assertEqual(result["content_digest"], "a" * 64)
        self.assertNotIn("observations", result)
        self.assertEqual(len(result["index_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
