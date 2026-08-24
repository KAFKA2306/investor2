#!/usr/bin/env python3
"""Validate the paper-family frontier registry and generate the README matrix."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/research/paper_family_frontier.json"
README = ROOT / "README.md"
PAPER_DIR = ROOT / "docs/paper"
START = "<!-- frontier:start -->"
END = "<!-- frontier:end -->"
VERDICTS = ("BEAT", "TIE", "LOSE", "BLOCKED")
VERDICT_ORDER = {"LOSE": 0, "TIE": 1, "BEAT": 2, "BLOCKED": 3}
ARXIV_RE = re.compile(
    r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/([A-Za-z0-9._/-]+)"
)


def _load_registry() -> dict[str, Any]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("schema_version") != "investor2.paper-family-frontier.v1":
        raise ValueError("unsupported paper-family frontier schema")
    return data


def _arxiv_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for match in ARXIV_RE.finditer(text):
        paper_id = match.group(1).removesuffix(".pdf").rstrip("/")
        ids.add(re.sub(r"v\d+$", "", paper_id))
    return ids


def _registry_arxiv_id(url: str | None) -> str | None:
    if not url:
        return None
    match = ARXIV_RE.search(url)
    if not match:
        return None
    return re.sub(r"v\d+$", "", match.group(1).removesuffix(".pdf").rstrip("/"))


def validate(data: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = data.get("defaults", {})
    families = data.get("families")
    if not isinstance(families, list) or not families:
        raise ValueError("families must be a non-empty list")

    resolved: list[dict[str, Any]] = []
    ids: set[str] = set()
    pages: set[str] = set()
    alias_paths: set[str] = set()

    for raw in families:
        if not isinstance(raw, dict):
            raise ValueError("each family must be an object")
        family = {**defaults, **raw}
        family_id = str(family.get("id", ""))
        page = str(family.get("page", ""))
        verdict = str(family.get("verdict", ""))

        if not family_id or family_id in ids:
            raise ValueError(f"duplicate or missing family id: {family_id!r}")
        if not page or page in pages:
            raise ValueError(f"duplicate or missing canonical page: {page!r}")
        if verdict not in VERDICTS:
            raise ValueError(f"invalid verdict for {family_id}: {verdict}")

        canonical_path = ROOT / page
        if not canonical_path.is_file():
            raise ValueError(f"canonical page does not exist: {page}")

        if verdict != "BLOCKED":
            benchmark = str(family.get("benchmark", ""))
            aaarts_result = str(family.get("aaarts_result", ""))
            evidence = str(family.get("evidence", ""))
            if not benchmark or benchmark == defaults.get("benchmark"):
                raise ValueError(f"measured family lacks frozen benchmark: {family_id}")
            if not aaarts_result:
                raise ValueError(f"measured family lacks AAARTS result: {family_id}")
            if not evidence or not (ROOT / evidence).is_file():
                raise ValueError(f"measured family lacks readable evidence: {family_id}")

        expected_arxiv = _registry_arxiv_id(family.get("url"))
        if expected_arxiv and page.startswith("docs/paper/"):
            actual_ids = _arxiv_ids(canonical_path.read_text(encoding="utf-8"))
            if expected_arxiv not in actual_ids:
                raise ValueError(
                    f"canonical page identity mismatch for {family_id}: "
                    f"expected arXiv {expected_arxiv}, found {sorted(actual_ids)}"
                )

        aliases = family.get("aliases", [])
        if not isinstance(aliases, list):
            raise ValueError(f"aliases must be a list: {family_id}")
        alias_paths.update(str(alias) for alias in aliases)

        ids.add(family_id)
        pages.add(page)
        resolved.append(family)

    non_paper = {str(path) for path in data.get("non_paper_documents", [])}
    superseded = {str(path) for path in data.get("superseded_files", [])}
    if alias_paths != superseded:
        raise ValueError(
            "superseded_files must exactly match aliases: "
            f"aliases_only={sorted(alias_paths - superseded)}, "
            f"superseded_only={sorted(superseded - alias_paths)}"
        )
    lingering = sorted(path for path in superseded if (ROOT / path).exists())
    if lingering:
        raise ValueError(f"superseded paper aliases still exist: {lingering}")

    actual_paper_pages = {
        str(path.relative_to(ROOT)) for path in PAPER_DIR.glob("*.md") if path.is_file()
    }
    canonical_paper_pages = {page for page in pages if page.startswith("docs/paper/")}
    expected_paper_pages = canonical_paper_pages | non_paper
    missing = sorted(actual_paper_pages - expected_paper_pages)
    stale = sorted(expected_paper_pages - actual_paper_pages)
    if missing or stale:
        raise ValueError(
            "docs/paper coverage mismatch: "
            f"unclassified={missing}, registered_but_missing={stale}"
        )

    identity_pages: dict[str, list[str]] = defaultdict(list)
    for page in sorted(canonical_paper_pages):
        text = (ROOT / page).read_text(encoding="utf-8")
        for paper_id in _arxiv_ids(text):
            identity_pages[paper_id].append(page)
    duplicates = {
        paper_id: paths for paper_id, paths in identity_pages.items() if len(paths) > 1
    }
    if duplicates:
        raise ValueError(f"duplicate active arXiv identities: {duplicates}")

    return resolved


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _link(label: object, path: str | None) -> str:
    text = _escape(label)
    return f"[{text}]({path})" if path else text


def render(data: dict[str, Any], families: list[dict[str, Any]]) -> str:
    counts = Counter(str(family["verdict"]) for family in families)
    ordered = sorted(
        families,
        key=lambda family: (
            VERDICT_ORDER[str(family["verdict"])],
            str(family["name"]).casefold(),
        ),
    )

    lines = [
        START,
        "## Empirical frontier",
        "",
        (
            f"**BEAT {counts['BEAT']} / TIE {counts['TIE']} / "
            f"LOSE {counts['LOSE']} / BLOCKED {counts['BLOCKED']}**"
        ),
        "",
        (
            "この表は `data/research/paper_family_frontier.json` から生成します。"
            " `BLOCKED`、CI成功、実装完了は勝利として扱いません。"
            " 論文側の代表結果とrepositoryの再現・head-to-head結果は混ぜません。"
        ),
        "",
        "| Family | 強み | Benchmark | Paper / 代表結果 | AAARTS | Verdict | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for family in ordered:
        page = str(family["page"])
        evidence = family.get("evidence")
        evidence_cell = _link("result", str(evidence)) if evidence else "—"
        paper_result = family.get("paper_result") or "—"
        aaarts_result = family.get("aaarts_result") or "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    _link(family["name"], page),
                    _escape(family["strength"]),
                    _escape(family["benchmark"]),
                    _escape(paper_result),
                    _escape(aaarts_result),
                    f"**{_escape(family['verdict'])}**",
                    evidence_cell,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            (
                "`LOSE` は完了した否定的比較です。`BLOCKED` は未勝利です。"
                " 次の研究対象は、まず `LOSE`、次に価値の高い `BLOCKED` を解消します。"
            ),
            END,
        ]
    )
    return "\n".join(lines)


def _with_generated_block(readme: str, block: str) -> str:
    if START in readme or END in readme:
        if readme.count(START) != 1 or readme.count(END) != 1:
            raise ValueError("README frontier markers are malformed")
        start = readme.index(START)
        end = readme.index(END, start) + len(END)
        return readme[:start] + block + readme[end:]

    lines = readme.splitlines()
    insert_at = 1
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("[!["):
            insert_at = index + 1
    lines[insert_at:insert_at] = ["", block, ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data = _load_registry()
    families = validate(data)
    block = render(data, families)
    current = README.read_text(encoding="utf-8")
    expected = _with_generated_block(current, block)

    if args.write:
        README.write_text(expected, encoding="utf-8")
        return 0

    if current != expected:
        raise SystemExit(
            "README frontier table is stale; run "
            "python3 scripts/frontier_readme.py --write"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
