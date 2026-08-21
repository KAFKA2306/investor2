from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.io.input_ledger.validators import VALIDATORS


def _source_config(registry: Mapping[str, Any], source_id: str) -> Mapping[str, Any]:
    sources = registry.get("sources")
    if not isinstance(sources, dict):
        raise AssertionError("source registry is missing sources")
    source_config = sources.get(source_id)
    if not isinstance(source_config, dict):
        raise AssertionError(f"unregistered source: {source_id}")
    return source_config


def audit_entry(entry: Mapping[str, Any], registry: Mapping[str, Any], root: Path) -> dict[str, Any]:
    source_id = str(entry.get("source") or "")
    if not source_id:
        raise AssertionError("accepted entry is missing source")

    source_config = _source_config(registry, source_id)
    if not source_config.get("enabled"):
        raise AssertionError(f"disabled source accepted: {source_id}")
    if source_config.get("failure_mode") != "fail-closed":
        raise AssertionError(f"source must fail closed: {source_id}")

    registered_adapter = str(source_config.get("adapter") or "")
    if not registered_adapter:
        raise AssertionError(f"source is missing adapter: {source_id}")
    entry_adapter = str(entry.get("adapter") or registered_adapter)
    if entry_adapter != registered_adapter:
        raise AssertionError(
            f"adapter mismatch for {source_id}: accepted={entry_adapter} registered={registered_adapter}"
        )

    artifact_rel = Path(str(entry.get("artifact_path") or ""))
    if not artifact_rel.as_posix() or artifact_rel.is_absolute() or ".." in artifact_rel.parts:
        raise AssertionError(f"invalid artifact path: {artifact_rel}")
    artifact_path = root / artifact_rel
    if not artifact_path.is_file():
        raise AssertionError(f"accepted artifact does not exist: {artifact_rel}")

    validator = VALIDATORS.get(registered_adapter)
    if validator is None:
        raise AssertionError(f"unsupported input-ledger adapter: {registered_adapter}")

    result = validator(entry, source_config, root)
    return {
        "source": source_id,
        "adapter": registered_adapter,
        **result,
    }


def audit_entries(
    entries: Sequence[Mapping[str, Any]],
    registry: Mapping[str, Any],
    root: Path,
) -> list[dict[str, Any]]:
    if not entries:
        raise AssertionError("accepted ledger must not be empty")

    paths = [str(entry.get("artifact_path") or "") for entry in entries]
    if len(paths) != len(set(paths)):
        raise AssertionError("duplicate accepted artifact path")

    return [audit_entry(entry, registry, root) for entry in entries]
