import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_dashboard_registry_covers_committed_research_artifacts() -> None:
    registry = json.loads(
        (ROOT / "docs/research/dashboard_registry.json").read_text(encoding="utf-8")
    )
    artifacts = registry["artifacts"]

    assert len(artifacts) == 2
    assert {artifact["file"] for artifact in artifacts} == {
        "post_publication_momentum_oos.json",
        "multi_paper_oos_results.json",
    }
    assert sum(artifact["record_count"] for artifact in artifacts) == 8

    momentum = json.loads(
        (ROOT / "docs/research/post_publication_momentum_oos.json").read_text(
            encoding="utf-8"
        )
    )
    multi = json.loads(
        (ROOT / "docs/research/multi_paper_oos_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert momentum["verdict"].startswith("not_confirmed")
    assert len(multi["studies"]) == 7
    assert sum(
        1 for study in multi["studies"].values() if study["verdict"] == "not_confirmed"
    ) + 1 == 5
    assert sum(
        1
        for study in multi["studies"].values()
        if study["verdict"] == "proxy_not_confirmed"
    ) == 3
