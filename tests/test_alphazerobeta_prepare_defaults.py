from __future__ import annotations

import sys

import pytest

from scripts.alphazerobeta_prepare import parse_args


def test_materialized_market_cache_defaults_to_japan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "alphazerobeta_prepare.py",
            "--market-snapshot-dir",
            "cache/snapshot",
            "--output",
            "cache/prepared.npz",
            "--universe-cutoff",
            "2023-06-30",
        ],
    )

    args = parse_args()

    assert args.market_regions == "jp"
