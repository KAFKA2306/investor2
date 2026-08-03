from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.io.frozen_split import (
    build_frozen_split,
    manifest_sha256,
    validate_source_file,
)


def sample_frame() -> pd.DataFrame:
    rows = []
    for industry in ("banking", "transport", "technology"):
        for index in range(5):
            rows.append(
                {
                    "doc_id": f"{industry}-{index}",
                    "industry": industry,
                    "meta": f"sample-{index}",
                }
            )
    return pd.DataFrame(rows)


def manifest(row_count: int, source_sha256: str = "0" * 64) -> dict[str, object]:
    return {
        "schema_version": 1,
        "split_id": "test-frozen-v1",
        "source": {
            "dataset": "test/dataset",
            "config": "industry_prediction",
            "split": "train",
            "revision": "fixed-revision",
            "sha256": source_sha256,
            "row_count": row_count,
        },
        "policy": {
            "algorithm": "stratified_sha256_rank_v1",
            "seed": 20260803,
            "evaluation_fraction": 0.2,
            "id_column": "doc_id",
            "group_column": "industry",
        },
    }


def test_frozen_split_is_stable_disjoint_and_stratified() -> None:
    frame = sample_frame()
    first_development, first_evaluation, first_evidence = build_frozen_split(
        frame,
        manifest(len(frame)),
    )
    second_development, second_evaluation, second_evidence = build_frozen_split(
        frame.sample(frac=1, random_state=7),
        manifest(len(frame)),
    )

    assert first_evaluation["doc_id"].tolist() == second_evaluation["doc_id"].tolist()
    assert first_development["doc_id"].tolist() == second_development["doc_id"].tolist()
    assert set(first_development["doc_id"]).isdisjoint(first_evaluation["doc_id"])
    assert set(first_development["doc_id"]) | set(first_evaluation["doc_id"]) == set(frame["doc_id"])
    assert first_evaluation.groupby("industry").size().to_dict() == {
        "banking": 1,
        "technology": 1,
        "transport": 1,
    }
    assert first_evidence["frozen_evaluation_doc_ids"] == second_evidence["frozen_evaluation_doc_ids"]


def test_manifest_tampering_changes_hash() -> None:
    original = manifest(15)
    changed = manifest(15)
    changed["policy"]["seed"] = 7  # type: ignore[index]
    assert manifest_sha256(original) != manifest_sha256(changed)


def test_source_file_hash_is_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    source.write_bytes(b"fixed dataset bytes")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    fixed_manifest = manifest(15, expected)

    assert validate_source_file(source, fixed_manifest) == expected
    source.write_bytes(b"changed dataset bytes")
    with pytest.raises(ValueError, match="does not match the frozen manifest"):
        validate_source_file(source, fixed_manifest)


def test_duplicate_doc_ids_are_rejected() -> None:
    frame = sample_frame()
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate doc_id"):
        build_frozen_split(duplicated, manifest(len(duplicated)))


def test_row_count_change_is_rejected() -> None:
    frame = sample_frame()
    with pytest.raises(ValueError, match="row count does not match"):
        build_frozen_split(frame, manifest(len(frame) + 1))
