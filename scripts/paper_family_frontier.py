#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

VERDICTS = {"BEAT", "TIE", "LOSE", "BLOCKED"}
VERDICT_ORDER = {"LOSE": 0, "TIE": 1, "BEAT": 2, "BLOCKED": 3}
ARXIV_ID = re.compile(r"arxiv\.org/abs/([^/?#]+)", re.IGNORECASE)
README_START = "<!-- paper-family-frontier:start -->"
README_END = "<!-- paper-family-frontier:end -->"
ALPHAZERO_HYPOTHESIS = Path("data/hypothesis_lab/hypotheses/alphazerobeta_market_neutral_v1.json")
ALPHAZERO_RESULT_64 = Path("docs/research/results/alphazerobeta_jquants_free/summary.json")
ALPHAZERO_RESULT_256 = Path("docs/research/results/alphazerobeta_jquants_free_256/summary.json")


def load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "investor2.paper-family-frontier.v1":
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
        if primary_url:
            token = identity_token(primary_url)
            previous = identities.get(token)
            if previous is not None:
                raise AssertionError(f"duplicate paper identity {token}: {previous} and {family_id}")
            identities[token] = family_id
            if not identity_is_in_page(primary_url, page_path.read_text(encoding="utf-8")):
                raise AssertionError(f"filename/content identity mismatch: {page} does not contain {token}")

        verdict = family.get("verdict")
        if verdict is not None and verdict not in VERDICTS:
            raise AssertionError(f"invalid verdict for {family_id}: {verdict}")

        for alias in family.get("historical_aliases", []):
            if (root / alias).exists():
                raise AssertionError(f"superseded paper alias is still active: {alias}")

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
    lines = [
        "# Paper-family frontier",
        "",
        "この表は `docs/research/paper_family_frontier.json` から生成する比較surfaceです。論文記載値とrepository実測値を混ぜず、直接head-to-headが完了するまで優越を主張しません。",
        "",
        f"**Global superiority:** UNPROVEN — {beat_count}/{len(families)} families are BEAT; {unresolved} remain unresolved.",
        "",
        "| Family | Claimed strength | Representative | Reproduction state | Primary metric | Verdict | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for family in families:
        verdict = family.get("verdict") or "BLOCKED"
        page = family["canonical_page"]
        label = family["canonical_name"].replace("|", "\\|")
        strength = family["claimed_capability"].replace("|", "\\|")
        representative = family["representative"].replace("|", "\\|")
        state = family["reproduction_state"].replace("|", "\\|")
        metric = family["primary_metric"].replace("|", "\\|")
        relative = page.removeprefix("docs/paper/")
        lines.append(
            f"| {label} | {strength} | {representative} | {state} | {metric} | {verdict} | [{relative}](./{relative}) |"
        )
    lines.extend(
        [
            "",
            "## 判定契約",
            "",
            "- `BEAT` はfamily固有の事前固定primary capabilityで直接比較に勝ち、PIT/OOS/cost/risk hard gateも満たした場合だけ付与する。",
            "- `TIE` / `LOSE` はそのまま残す。未実証またはcontract未凍結のfamilyは公開surfaceで `BLOCKED` とし、勝利として扱わない。",
            "- 全familyが `BEAT` になるまで、AAARTSが全frontierを上回ったとは記載しない。",
            "- 比較契約は Issue #51、inspection queueは #55、日本株の共通PIT benchmarkは #184を再利用し、別authorityを作らない。",
            "",
            "生成: `python scripts/paper_family_frontier.py render --write`",
            "",
        ]
    )
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _alphazerobeta_row(root: Path) -> dict[str, str]:
    hypothesis = json.loads((root / ALPHAZERO_HYPOTHESIS).read_text(encoding="utf-8"))
    result_path = ALPHAZERO_RESULT_256 if (root / ALPHAZERO_RESULT_256).is_file() else ALPHAZERO_RESULT_64
    result = json.loads((root / result_path).read_text(encoding="utf-8"))
    trained_assets = int(result["trained_asset_count"])
    folds = int(result["walk_forward"]["folds"])
    primary = result["primary_lambda_corr_0_5"]
    verdict = "LOSE" if result.get("verdict") == "reject" else "BLOCKED"
    reason = hypothesis["replication_boundary"]["reason"]
    aaarts = (
        f"return {primary['cumulative_return']:.4%}; "
        f"Sharpe {primary['annualized_sharpe']:.4f}; "
        f"corr {primary['benchmark_correlation']:.5f}; "
        f"max DD {primary['max_drawdown']:.4%}"
    )
    return {
        "name": "AlphaZeroBeta",
        "page": "docs/research/alphazerobeta_validation.md",
        "strength": "market-neutral portfolio construction",
        "benchmark": f"J-Quants Free, {trained_assets} assets, {folds} OOS folds",
        "paper_result": f"Exact paper reproduction BLOCKED: {reason}",
        "aaarts_result": aaarts,
        "verdict": verdict,
        "evidence": result_path.as_posix(),
    }


def public_rows(root: Path, registry: dict[str, Any]) -> list[dict[str, str]]:
    rows = [_alphazerobeta_row(root)]
    for family in registry["families"]:
        rows.append(
            {
                "name": family["canonical_name"],
                "page": family["canonical_page"],
                "strength": family["claimed_capability"],
                "benchmark": family["primary_metric"],
                "paper_result": family["representative"],
                "aaarts_result": family["reproduction_state"],
                "verdict": family.get("verdict") or "BLOCKED",
                "evidence": family["canonical_page"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            VERDICT_ORDER[row["verdict"]],
            row["name"].casefold(),
        ),
    )


def render_readme_block(root: Path, registry: dict[str, Any]) -> str:
    rows = public_rows(root, registry)
    counts = Counter(row["verdict"] for row in rows)
    lines = [
        README_START,
        "## Empirical frontier",
        "",
        (f"**BEAT {counts['BEAT']} / TIE {counts['TIE']} / LOSE {counts['LOSE']} / BLOCKED {counts['BLOCKED']}**"),
        "",
        "この表はcanonical family registryとrepository実測結果から生成します。`BLOCKED`、CI成功、実装完了は勝利ではありません。論文側とrepository側の結果は分離して表示します。",
        "",
        "| Family | 強み | Benchmark | Paper / 代表結果 | AAARTS | Verdict | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        family = f"[{_escape(row['name'])}]({_escape(row['page'])})"
        evidence = f"[evidence]({_escape(row['evidence'])})"
        lines.append(
            "| "
            + " | ".join(
                [
                    family,
                    _escape(row["strength"]),
                    _escape(row["benchmark"]),
                    _escape(row["paper_result"]),
                    _escape(row["aaarts_result"]),
                    f"**{row['verdict']}**",
                    evidence,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "`LOSE` は隠さず次の改善frontierにします。`BLOCKED` は直接head-to-headが未完了、または再現条件が未確定な状態であり、勝利として扱いません。",
            README_END,
        ]
    )
    return "\n".join(lines)


def merge_readme(readme: str, block: str) -> str:
    if README_START in readme or README_END in readme:
        if readme.count(README_START) != 1 or readme.count(README_END) != 1:
            raise AssertionError("README frontier markers are malformed")
        start = readme.index(README_START)
        end = readme.index(README_END, start) + len(README_END)
        return readme[:start] + block + readme[end:]

    lines = readme.splitlines()
    insert_at = 1
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("[!["):
            insert_at = index + 1
    lines[insert_at:insert_at] = ["", block, ""]
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and render the canonical paper-family frontier.")
    parser.add_argument("command", choices=("validate", "render", "readme"))
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
    registry = load_registry(registry_path)
    validate(root, registry)
    if args.command == "validate":
        print(
            json.dumps(
                {"families": len(registry["families"]), "status": "ok"},
                sort_keys=True,
            )
        )
        return

    if args.command == "readme":
        output_path = args.output or root / "README.md"
        current = output_path.read_text(encoding="utf-8")
        expected = merge_readme(current, render_readme_block(root, registry))
        if args.check and current != expected:
            raise AssertionError(f"generated README frontier is stale: run {Path(__file__).name} readme --write")
        if args.write:
            output_path.write_text(expected, encoding="utf-8")
        if not args.check and not args.write:
            print(render_readme_block(root, registry), end="\n")
        return

    output_path = args.output or root / "docs" / "paper" / "benchmark_comparison.md"
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
