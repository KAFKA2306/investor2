from __future__ import annotations

import json
from pathlib import Path

from scripts import verify_paper_factor_suite

ROOT = Path(__file__).resolve().parents[1]


def test_official_current_multi_paper_suite() -> None:
    registry = ROOT / "docs/research/paper_factor_registry.json"
    report = verify_paper_factor_suite.build_report(registry)
    studies = report["studies"]
    snapshot = json.loads(
        (ROOT / "docs/research/kenneth_french_current_snapshot_2026-06.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(studies) == 7
    assert snapshot["authority"] == "official_primary"
    assert snapshot["pinned_last_observation"] == "2026-06"
    assert snapshot["generation_regime"]["current_release"] == "CIZ"

    ff3 = report["datasets"]["ff3_1992_2020"]
    assert ff3["authority"] == "official_primary"
    assert ff3["rows"] == 408
    assert ff3["first_observation"] == "1992-07"
    assert ff3["last_observation"] == "2026-06"
    assert ff3["actual_sha256"] == (
        "0f7ad8a9303c54c87da2cd45df3f9fdfd36d39e74ce373f6bd84567276835fcf"
    )

    ff5 = report["datasets"]["ff5_2015_2020"]
    assert ff5["authority"] == "official_primary"
    assert ff5["rows"] == 134
    assert ff5["first_observation"] == "2015-05"
    assert ff5["last_observation"] == "2026-06"
    assert ff5["actual_sha256"] == (
        "a608eca851e909aa18c63c5e58e81160adde81df1cac7b65cb4d33d04925c4a3"
    )

    smb = studies["fama_french_1993_smb"]
    assert smb["gross_results"]["full_oos"]["months"] == 400
    assert smb["gross_results"]["full_oos"]["end"] == "2026-06"
    assert smb["verdict"] == "not_confirmed"

    hml = studies["fama_french_1993_hml"]
    assert hml["gross_results"]["full_oos"]["months"] == 400
    assert hml["verdict"] == "not_confirmed"

    rmw = studies["fama_french_2015_rmw"]
    assert rmw["gross_results"]["full_oos"]["months"] == 134
    assert rmw["gross_results"]["full_oos"]["end"] == "2026-06"
    assert rmw["verdict"] == "not_confirmed"

    cma = studies["fama_french_2015_cma"]
    assert cma["gross_results"]["full_oos"]["months"] == 134
    assert cma["verdict"] == "not_confirmed"

    assert all(
        study["verdict"] in {"not_confirmed", "proxy_not_confirmed"}
        for study in studies.values()
    )
