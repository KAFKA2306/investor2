#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_warin_2101_02044_table9_constraints.py"

spec = importlib.util.spec_from_file_location("warin_table9", RUNNER)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--model-id", type=int, choices=[1, 4], required=True)
    parser.add_argument("--restart", type=int, choices=[0, 1, 2, 3], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    protocol_path = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    report = mod.run_one(protocol, args.model_id, args.restart, output_dir)
    print(
        json.dumps(
            {
                "model": args.model_id,
                "restart": args.restart,
                "score": report["evaluation"]["unpenalized_score"],
                "opposite_penalized_objective": report["evaluation"]["opposite_penalized_objective"],
                "within": report["comparison"]["within_predeclared_tolerance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
