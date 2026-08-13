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
        "materialized": 0,
        "empirically_reproduced": 0,
    }
    assert all(
        paper["empirical_state"] == "NOT_RUN"
        and "実証再現は未実施" in paper["stage_label"]
        for paper in public["paper_reproduction"]["papers"]
    )

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


def test_public_projection_scales_when_a_2021_paper_is_added() -> None:
    internal = INTERNAL.build_manifest()
    extra = copy.deepcopy(internal["paper_reproduction_2021"]["papers"][0])
    extra["id"] = "future_2021_paper_fixture"
    extra["arxiv_id"] = "2101.99999"
    extra["title"] = "Future 2021 paper fixture"
    internal["paper_reproduction_2021"]["papers"].append(extra)
    internal["paper_reproduction_2021"]["summary"]["indexed"] += 1
    internal["paper_reproduction_2021"]["summary"]["method_contract_pass"] += 1
    internal["summary"]["papers_2021_indexed"] += 1
    internal["summary"]["papers_2021_method_contract_pass"] += 1

    public = PUBLIC.build_public_manifest(internal)
    PUBLIC.validate_public_manifest(public)

    assert public["paper_reproduction"]["summary"]["indexed"] == 5
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


def test_public_validator_rejects_false_empirical_label() -> None:
    public = PUBLIC.build_public_manifest(INTERNAL.build_manifest())
    public["paper_reproduction"]["papers"][0]["stage_label"] = "実証再現済み"

    with pytest.raises(ValueError, match="clearly labeled"):
        PUBLIC.validate_public_manifest(public)
