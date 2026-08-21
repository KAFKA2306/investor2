#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io.input_ledger import audit_entries  # noqa: E402

LEDGER = ROOT / "data/input_ledger/accepted.ndjson"
REGISTRY = ROOT / "data/input_ledger/source_registry.json"


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = audit_entries(entries, registry, ROOT)
    print(
        json.dumps(
            {
                "schema_version": "investor2.input-ledger-audit.v2",
                "status": "PASS",
                "artifacts": results,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
