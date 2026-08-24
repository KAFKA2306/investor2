#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERDICTS = {"BEAT", "TIE", "LOSE", "BLOCKED"}
ARXIV_ID = re.compile(r"arxiv\.org/abs/([^/?#]+)", re.IGNORECASE)
REQUIRED_FAMILY_FIELDS = {
    "family_id",
    "canonical_name",
    "canonical_page",
    "primary_url",
    "historical_aliases",
    "task_class",
    "claimed_capability",
    "representative",
    "market_dataset_universe",
    "original_sample_dates",
    "native_benchmark",
    "primary_metric",
    "required_data_license_state",
    "reproduction_state",
    "head_to_head",
    "canonical_reproduction",
    "superseded_files",
    "verdict",
}


def load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "investor2.paper-family-frontier.v2":
        raise AssertionError("unsupported paper-family frontier schema")
    return payload


def identity_token(url: str) -> str:
    match = ARXIV_ID.search(url)
    if match:
        return f"arxiv:{match.group(1).lower()}"
    return url.rstrip("/").lower()


def identity_is_in_page(url: str, text: str) -> bool:
    match = ARXIV_ID.search(url)
    if match:
        return match.group(1).lower() in text.lower()
    return url.rstrip("/").lower() in text.lower()


def validate(root: Path, registry: dict[str, Any]) -> None:
    paper_dir = root / "docs" / "paper"
    active_markdown = {path.relative_to(root).as_posix() for path in paper_dir.glob("*.md")}
    families = registry["families"]
    material = registry["repository_material"]

    family_ids: set[str] = set()
    canonical_pages: set[str] = set()
    identities: dict[str, str] = {}
    mapped: set[str] = set()

    for family in families:
        missing_fields = sorted(REQUIRED_FAMILY_FIELDS - set(family))
        if missing_fields:
            raise AssertionError(f"family missing required fields: {family.get('family_id')}: {missing_fields}")

        family_id = family["family_id"]
        if family_id in family_ids:
            raise AssertionError(f"duplicate family_id: {family_id}")
        family_ids.add(family_id)

        page = family["canonical_page"]
        if page in canonical_pages:
            raise AssertionError(f"canonical page mapped twice: {page}")
        canonical_pages.add(page)
        mapped.add(page)
        page_path = root / page
        if not page_path.is_file():
            raise AssertionError(f"missing canonical page: {page}")

        primary_url = family.get("primary_url")
        if not primary_url:
            raise AssertionError(f"missing canonical primary URL: {family_id}")
        token = identity_token(primary_url)
        previous = identities.get(token)
        if previous is not None:
            raise AssertionError(f"duplicate paper identity {token}: {previous} and {family_id}")
        identities[token] = family_id
        if not identity_is_in_page(primary_url, page_path.read_text(encoding="utf-8")):
            raise AssertionError(f"filename/content identity mismatch: {page} does not contain {token}")

        if family["historical_aliases"] != family["superseded_files"]:
            raise AssertionError(f"alias/superseded mismatch: {family_id}")
        for alias in family["superseded_files"]:
            if (root / alias).exists():
                raise AssertionError(f"superseded paper alias is still active: {alias}")

        reproduction = family["canonical_reproduction"]
        if reproduction.get("benchmark_contract_issue") != 51:
            raise AssertionError(f"family does not reuse #51 benchmark authority: {family_id}")
        if reproduction.get("inspection_queue_issue") != 55:
            raise AssertionError(f"family does not reuse #55 inspection authority: {family_id}")

        verdict = family.get("verdict")
        if verdict is not None and verdict not in VERDICTS:
            raise AssertionError(f"invalid verdict for {family_id}: {verdict}")
        if verdict is not None and family["head_to_head"] == "NOT_RUN":
            raise AssertionError(f"verdict without head-to-head evidence: {family_id}")

    for item in material:
        path = item["path"]
        if path in mapped:
            raise AssertionError(f"path mapped as both family and repository material: {path}")
        mapped.add(path)
        if not (root / path).is_file():
            raise AssertionError(f"missing repository material: {path}")

    missing = sorted(active_markdown - mapped)
    stale = sorted(mapped - active_markdown)
    if missing:
        raise AssertionError(f"unmapped docs/paper markdown: {missing}")
    if stale:
        raise AssertionError(f"registry references inactive docs/paper markdown: {stale}")


def render(registry: dict[str, Any]) -> str:
    families = sorted(registry["families"], key=lambda item: item["canonical_name"].casefold())
    beat_count = sum(family.get("verdict") == "BEAT" for family in families)
    unresolved = len(families) - beat_count
    global_state = "PROVEN" if families and unresolved == 0 else "UNPROVEN"
    lines = [
        "# Paper-family frontier",
        "",
        "この表は `docs/research/paper_family_frontier.json` から生成する比較surfaceです。論文記載値とrepository実測値を混ぜず、直接head-to-headが完了するまで優越を主張しません。",
        "",
        f"**Global superiority:** {global_state} — {beat_count}/{len(families)} families are BEAT; {unresolved} remain unresolved.",
        "",
        "| Family | Claimed strength | Representative | Reproduction state | AAARTS head-to-head | Primary metric | Verdict | Evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for family in families:
        verdict = family.get("verdict") or "—"
        page = family["canonical_page"]
        label = family["canonical_name"].replace("|", "\\|")
        strength = family["claimed_capability"].replace("|", "\\|")
        representative = family["representative"].replace("|", "\\|")
        state = family["reproduction_state"].replace("|", "\\|")
        head_to_head = family["head_to_head"].replace("|", "\\|")
        metric = family["primary_metric"].replace("|", "\\|")
        relative = page.removeprefix("docs/paper/")
        lines.append(
            f"| {label} | {strength} | {representative} | {state} | {head_to_head} | {metric} | {verdict} | [{relative}](./{relative}) |"
        )
    lines.extend(
        [
            "",
            "## 判定契約",
            "",
            "- `BEAT` はfamily固有の事前固定primary capabilityで直接比較に勝ち、PIT/OOS/cost/risk hard gateも満たした場合だけ付与する。",
            "- `TIE` / `LOSE` はそのまま残す。`BLOCKED` は勝利として扱わない。未実証familyにはverdictを付けない。",
            "- 全familyが `BEAT` になるまで、AAARTSが全frontierを上回ったとは記載しない。",
            "- 比較契約は Issue #51、inspection queueは #55、日本株の共通PIT benchmarkは #184を再利用し、別authorityを作らない。",
            "",
            "生成: `python scripts/paper_family_frontier.py render --write`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and render the canonical paper-family frontier.")
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    registry_path = args.registry or root / "docs" / "research" / "paper_family_frontier.json"
    output_path = args.output or root / "docs" / "paper" / "benchmark_comparison.md"
    registry = load_registry(registry_path)
    validate(root, registry)
    if args.command == "validate":
        print(json.dumps({"families": len(registry["families"]), "status": "ok"}, sort_keys=True))
        return

    rendered = render(registry)
    if args.check:
        current = output_path.read_text(encoding="utf-8")
        if current != rendered:
            raise AssertionError(f"generated frontier is stale: run {Path(__file__).name} render --write")
    if args.write:
        output_path.write_text(rendered, encoding="utf-8")
    if not args.check and not args.write:
        print(rendered, end="")


if __name__ == "__main__":
    main()
