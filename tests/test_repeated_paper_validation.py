import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repeat_paper_validation.py"
SPEC = importlib.util.spec_from_file_location("repeat_paper_validation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_2010s_verdicts_are_repeated_and_stable() -> None:
    report = MODULE.build_repeat_report(
        ROOT / "docs/research/paper_factor_registry.json",
        repetitions=3,
        seed_start=2306,
    )

    assert report["study_count"] == 2
    assert report["repetitions"] == 3
    assert report["all_verdicts_stable"] is True
    assert set(report["studies"]) == {
        "fama_french_2015_rmw",
        "fama_french_2015_cma",
    }
    assert all(
        study["verdict_counts"] == {"not_confirmed": 3}
        for study in report["studies"].values()
    )
