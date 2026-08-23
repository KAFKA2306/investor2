from __future__ import annotations

import json
from importlib.machinery import ModuleSpec

import pytest

import scripts.alphazerobeta_build_market_snapshot as market_snapshot_builder


def test_repair_runtime_fails_fast_with_structured_scipy_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_find_spec(name: str) -> ModuleSpec | None:
        if name == "scipy":
            return None
        return ModuleSpec(name, loader=None)

    monkeypatch.setattr(market_snapshot_builder.importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(
        market_snapshot_builder,
        "package_version",
        lambda name: None if name == "scipy" else "test-version",
    )

    with pytest.raises(RuntimeError, match="scipy is required"):
        market_snapshot_builder.require_repair_runtime()

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["event"] for event in events] == ["dependency_preflight", "dependency_preflight_failed"]
    assert events[0]["scipy_available"] is False
    assert events[0]["yfinance_repair"] is True
    assert events[1]["missing_dependency"] == "scipy"


def test_log_event_is_machine_parseable(capsys: pytest.CaptureFixture[str]) -> None:
    market_snapshot_builder.log_event("unit_test", stage="download", batch=3)

    payload = json.loads(capsys.readouterr().out)
    assert payload["component"] == "alphazerobeta_yahoo_market_snapshot"
    assert payload["event"] == "unit_test"
    assert payload["stage"] == "download"
    assert payload["batch"] == 3
    assert payload["ts_utc"].endswith("+00:00")
