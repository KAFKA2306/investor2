from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = load_module(
    ROOT / "scripts" / "build_research_verification_manifest.py",
    "build_research_verification_manifest_for_semantic_tests",
)
VALIDATOR = load_module(
    ROOT / "scripts" / "validate_research_dashboard.py",
    "validate_research_dashboard_for_tests",
)


def valid_manifest():
    manifest = BUILDER.build_manifest()
    BUILDER.validate_manifest(manifest)
    VALIDATOR.validate_manifest(manifest)
    return manifest


def test_valid_manifest_passes_semantic_validation() -> None:
    valid_manifest()


def test_ninth_hypothesis_is_allowed_when_counts_and_evidence_are_consistent() -> None:
    manifest = valid_manifest()
    extra = copy.deepcopy(manifest["repository_results"][0])
    extra["id"] = "fixture_ninth_hypothesis"
    manifest["repository_results"].append(extra)
    manifest["summary"]["tested_hypotheses"] += 1
    manifest["summary"]["not_confirmed"] += 1

    BUILDER.validate_manifest(manifest)
    VALIDATOR.validate_manifest(manifest)


def test_tampered_summary_is_rejected() -> None:
    manifest = valid_manifest()
    manifest["summary"]["tested_hypotheses"] += 1

    with pytest.raises(ValueError, match="tested_hypotheses"):
        VALIDATOR.validate_manifest(manifest)


def test_duplicate_hypothesis_id_is_rejected() -> None:
    manifest = valid_manifest()
    duplicate = copy.deepcopy(manifest["repository_results"][0])
    manifest["repository_results"].append(duplicate)
    manifest["summary"]["tested_hypotheses"] += 1
    manifest["summary"]["not_confirmed"] += 1

    with pytest.raises(ValueError, match="unique"):
        VALIDATOR.validate_manifest(manifest)


def test_confirmed_without_all_promotion_evidence_is_rejected() -> None:
    manifest = valid_manifest()
    record = manifest["repository_results"][0]
    record["dashboard_verdict"] = "CONFIRMED"
    manifest["summary"]["confirmed"] += 1
    manifest["summary"]["not_confirmed"] -= 1

    with pytest.raises(ValueError, match="incomplete gates"):
        VALIDATOR.validate_manifest(manifest)


def test_method_only_paper_cannot_claim_empirical_verification() -> None:
    manifest = valid_manifest()
    paper = manifest["paper_reproduction_2021"]["papers"][0]
    paper["reproduction_verdict"] = "VERIFIED"

    with pytest.raises(ValueError, match="empirical-looking verdict"):
        VALIDATOR.validate_manifest(manifest)


def test_paper_summary_tampering_is_rejected() -> None:
    manifest = valid_manifest()
    manifest["summary"]["papers_2021_materialized"] += 1

    with pytest.raises(ValueError, match="papers_2021_materialized"):
        VALIDATOR.validate_manifest(manifest)


def test_missing_build_provenance_is_rejected() -> None:
    manifest = valid_manifest()
    manifest["build"]["code_sha"] = ""

    with pytest.raises(ValueError, match="build.code_sha"):
        VALIDATOR.validate_manifest(manifest)


def test_broken_candidate_html_is_rejected() -> None:
    html = (ROOT / "docs" / "aaarts-dashboard" / "index.html").read_text(encoding="utf-8")
    VALIDATOR.validate_html(html)

    with pytest.raises(ValueError, match="resultRows"):
        VALIDATOR.validate_html(html.replace('id="resultRows"', 'id="removedRows"'))

    with pytest.raises(ValueError, match="paperRows"):
        VALIDATOR.validate_html(html.replace('id="paperRows"', 'id="removedPaperRows"'))
