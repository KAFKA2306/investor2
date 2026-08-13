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


INTERNAL = load_module(
    ROOT / "scripts" / "build_research_verification_manifest.py",
    "internal_manifest_for_public_tests",
)
PUBLIC = load_module(
    ROOT / "scripts" / "build_public_research_manifest.py",
    "public_manifest_for_tests",
)


def test_public_manifest_is_small_safe_and_human_readable() -> None:
    internal = INTERNAL.build_manifest()
    INTERNAL.validate_manifest(internal)
    public = PUBLIC.build_public_manifest(internal)
    PUBLIC.validate_public_manifest(public)

    assert public["schema_version"] == 2
    assert public["summary"]["tested_hypotheses"] == len(public["results"])
    assert public["summary"]["tested_hypotheses"] == 8
    assert all(item["question"].endswith("？") for item in public["results"])
    assert all(item["why"] for item in public["results"])
    assert public["paper_reproduction"]["summary"] == {
        "indexed": 4,
        "method_contract_pass": 4,
        "materialized": 1,
        "empirically_run": 1,
        "empirically_reproduced": 1,
        "empirically_failed": 0,
        "empirically_blocked": 0,
        "empirically_not_run": 3,
    }
    papers = public["paper_reproduction"]["papers"]
    warin = next(paper for paper in papers if paper["id"] == "warin_2101_02044")
    assert warin["method_state"] == "PASS"
    assert warin["empirical_state"] == "EMPIRICALLY_RUN"
    assert warin["empirical_verdict"] == "REPRODUCED"
    assert warin["empirical_evidence"]["path"].endswith("manifest.json")
    assert len(warin["empirical_evidence"]["sha256"]) == 64
    assert "事前条件内で再現" in warin["stage_label"]

    not_run = [paper for paper in papers if paper["empirical_state"] == "NOT_RUN"]
    assert len(not_run) == 3
    assert all(paper["empirical_verdict"] is None for paper in not_run)
    assert all(paper["empirical_evidence"] is None for paper in not_run)
    assert all("実証再現は未実施" in paper["stage_label"] for paper in not_run)

    keys = set(PUBLIC.walk_keys(public))
    assert not (keys & PUBLIC.FORBIDDEN_PUBLIC_KEYS)


def test_public_projection_scales_when_a_hypothesis_is_added() -> None:
    internal = INTERNAL.build_manifest()
    extra = copy.deepcopy(internal["repository_results"][0])
    extra["id"] = "future_hypothesis_fixture"
    extra["paper"] = "Future paper fixture"
    internal["repository_results"].append(extra)
    internal["summary"]["tested_hypotheses"] += 1
    internal["summary"]["not_confirmed"] += 1

    public = PUBLIC.build_public_manifest(internal)
    PUBLIC.validate_public_manifest(public)

    assert public["summary"]["tested_hypotheses"] == 9
    assert len(public["results"]) == 9
    assert public["results"][-1]["question"] == "Future paper fixture"


def test_public_projection_scales_when_a_2021_not_run_paper_is_added() -> None:
    internal = INTERNAL.build_manifest()
    source = next(
        paper
        for paper in internal["paper_reproduction_2021"]["papers"]
        if paper["empirical_reproduction_state"] == "NOT_RUN"
    )
    extra = copy.deepcopy(source)
    extra["id"] = "future_2021_paper_fixture"
    extra["arxiv_id"] = "2101.99999"
    extra["title"] = "Future 2021 paper fixture"
    internal["paper_reproduction_2021"]["papers"].append(extra)
    internal["paper_reproduction_2021"]["summary"]["indexed"] += 1
    internal["paper_reproduction_2021"]["summary"]["method_contract_pass"] += 1
    internal["paper_reproduction_2021"]["summary"]["empirically_not_run"] += 1
    internal["summary"]["papers_2021_indexed"] += 1
    internal["summary"]["papers_2021_method_contract_pass"] += 1
    internal["summary"]["papers_2021_empirically_not_run"] += 1

    public = PUBLIC.build_public_manifest(internal)
    PUBLIC.validate_public_manifest(public)

    assert public["paper_reproduction"]["summary"]["indexed"] == 5
    assert public["paper_reproduction"]["summary"]["empirically_not_run"] == 4
    assert len(public["paper_reproduction"]["papers"]) == 5


def test_public_validator_rejects_internal_field_leak() -> None:
    public = PUBLIC.build_public_manifest(INTERNAL.build_manifest())
    public["external_claims"] = []

    with pytest.raises(ValueError, match="leaked"):
        PUBLIC.validate_public_manifest(public)


def test_public_validator_rejects_tampered_count() -> None:
    public = PUBLIC.build_public_manifest(INTERNAL.build_manifest())
    public["summary"]["tested_hypotheses"] += 1

    with pytest.raises(ValueError, match="tested_hypotheses"):
        PUBLIC.validate_public_manifest(public)


def test_public_validator_rejects_not_run_empirical_result() -> None:
    public = PUBLIC.build_public_manifest(INTERNAL.build_manifest())
    paper = next(
        item for item in public["paper_reproduction"]["papers"] if item["empirical_state"] == "NOT_RUN"
    )
    paper["empirical_verdict"] = "REPRODUCED"
    # Keep aggregate counts internally consistent so the semantic NOT_RUN guard is exercised.
    public["paper_reproduction"]["summary"]["empirically_reproduced"] += 1
    public["summary"]["papers_2021_empirically_reproduced"] += 1

    with pytest.raises(ValueError, match="NOT_RUN"):
        PUBLIC.validate_public_manifest(public)


def test_public_validator_rejects_empirical_verdict_without_evidence() -> None:
    public = PUBLIC.build_public_manifest(INTERNAL.build_manifest())
    warin = next(
        item
        for item in public["paper_reproduction"]["papers"]
        if item["empirical_state"] == "EMPIRICALLY_RUN"
    )
    warin["empirical_evidence"] = None

    with pytest.raises(ValueError, match="evidence"):
        PUBLIC.validate_public_manifest(public)
