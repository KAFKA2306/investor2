import copy
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_frozen_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_frozen_manifest", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


VALID = {
    "schema_version": 1,
    "split_id": "example-v1",
    "source": {
        "dataset": "owner/dataset",
        "config": "config",
        "split": "train",
        "revision": "a" * 40,
        "parquet_path": "data/train.parquet",
        "sha256": "b" * 64,
        "row_count": 10,
    },
    "policy": {
        "algorithm": "stratified_sha256_rank_v1",
        "seed": 1,
        "evaluation_fraction": 0.2,
        "id_column": "doc_id",
        "group_column": "industry",
    },
    "contract": {"source_change_policy": "fail_closed"},
}


class FrozenManifestValidationTests(unittest.TestCase):
    def test_valid_manifest(self):
        self.assertEqual(MODULE.validate_manifest(copy.deepcopy(VALID)), [])

    def test_rejects_mutable_revision_and_bad_digest(self):
        manifest = copy.deepcopy(VALID)
        manifest["source"]["revision"] = "main"
        manifest["source"]["sha256"] = "not-a-digest"
        errors = MODULE.validate_manifest(manifest)
        self.assertTrue(any("40-character" in error for error in errors))
        self.assertTrue(any("SHA-256" in error for error in errors))

    def test_requires_fail_closed_policy(self):
        manifest = copy.deepcopy(VALID)
        manifest["contract"]["source_change_policy"] = "refresh"
        self.assertIn(
            "contract.source_change_policy must be fail_closed",
            MODULE.validate_manifest(manifest),
        )


if __name__ == "__main__":
    unittest.main()
