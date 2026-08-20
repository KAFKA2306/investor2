#!/usr/bin/env python3
"""Build the ARK Big Ideas 2026 repository-coverage matrix."""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ark-big-ideas"
API = ROOT / "api" / "v1" / "ark-big-ideas"
DEFAULT_CATALOG = DATA / "repository-coverage-catalog.json"
DEFAULT_SOURCE_CATALOG = DATA / "source-catalog.json"
DEFAULT_EVIDENCE_MATRIX = API / "evidence-matrix.json"
DEFAULT_CLAIM_EVIDENCE = API / "claim-evidence.json"
DEFAULT_DATA_OUTPUT = DATA / "repository-coverage.json"
DEFAULT_API_OUTPUT = API / "repository-coverage.json"
DEFAULT_CSV_OUTPUT = API / "repository-coverage.csv"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "ark-big-ideas" / "repository-coverage.md"
UA = "investor2-ark-repository-coverage/1.0"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_catalog(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    themes = catalog.get("themes")
    if not isinstance(themes, list) or len(themes) != 13:
        raise ValueError("coverage catalog must contain exactly 13 themes")
    names = [row.get("theme") for row in themes]
    if len(set(names)) != 13 or any(not name for name in names):
        raise ValueError("theme names must be unique")
    for theme in themes:
        components = theme.get("components")
        if not isinstance(components, list) or not components:
            raise ValueError(f"theme requires components: {theme['theme']}")
        for component in components:
            if not str(component.get("current_repo", "")).startswith("KAFKA2306/"):
                raise ValueError(f"invalid current_repo: {component}")
            if not component.get("target_repo"):
                raise ValueError(f"target_repo missing: {component}")
    return themes


def request(url: str, *, json_response: bool = True) -> Any:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        raw = response.read()
    return json.loads(raw) if json_response else raw.decode("utf-8", errors="replace")


def blob_path(url: str | None, repository: str) -> str | None:
    prefix = f"https://github.com/{repository}/blob/"
    if not url or not url.startswith(prefix):
        return None
    rest = url[len(prefix) :]
    return rest.split("/", 1)[1] if "/" in rest else None


def probe_repository(repository: str, evidence_url: str | None) -> dict[str, Any]:
    encoded = urllib.parse.quote(repository, safe="/")
    try:
        repo = request(f"https://api.github.com/repos/{encoded}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {
                "exists": False,
                "scheduled": False,
                "latest_passed": False,
                "evidence_commit": None,
            }
        raise
    branch = repo["default_branch"]
    workflows = request(f"https://api.github.com/repos/{encoded}/actions/workflows?per_page=100")
    scheduled = False
    for workflow in workflows.get("workflows", []):
        path = workflow.get("path")
        if not isinstance(path, str) or not path.startswith(".github/workflows/"):
            continue
        raw_url = f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"
        try:
            text = request(raw_url, json_response=False)
        except urllib.error.HTTPError:
            continue
        if "schedule:" in text and "cron:" in text:
            scheduled = True
            break
    runs = request(
        f"https://api.github.com/repos/{encoded}/actions/runs"
        f"?branch={urllib.parse.quote(str(branch))}&status=completed&per_page=1"
    ).get("workflow_runs", [])
    evidence_commit = None
    path = blob_path(evidence_url, repository)
    if path:
        commits = request(
            f"https://api.github.com/repos/{encoded}/commits?path={urllib.parse.quote(path, safe='/')}&per_page=1"
        )
        if commits:
            evidence_commit = commits[0].get("sha")
    return {
        "exists": True,
        "scheduled": scheduled,
        "latest_passed": bool(runs and runs[0].get("conclusion") == "success"),
        "evidence_commit": evidence_commit,
    }


def probe_output(url: str | None) -> dict[str, bool]:
    if not url:
        return {"available": False, "primary": False, "raw": False}
    try:
        payload = request(url)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return {"available": False, "primary": False, "raw": False}
    urls: list[str] = []
    raw_hash = False

    def walk(value: Any, key: str = "") -> None:
        nonlocal raw_hash
        if isinstance(value, dict):
            for child_key, child in value.items():
                lowered = str(child_key).lower()
                if child and (
                    ("raw" in lowered and "hash" in lowered)
                    or lowered in {"source_hash", "response_hash", "raw_sha256", "source_sha256"}
                ):
                    raw_hash = True
                walk(child, lowered)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and value.startswith("http") and ("source" in key or "url" in key):
            urls.append(value)

    walk(payload)
    primary = any(
        "github.com/KAFKA2306/" not in url and "raw.githubusercontent.com/KAFKA2306/" not in url for url in urls
    )
    return {"available": True, "primary": primary, "raw": raw_hash}


def all_components(components: list[dict[str, Any]], field: str) -> bool:
    return all(bool(component[field]) for component in components)


def build(
    catalog: dict[str, Any],
    source_catalog: dict[str, Any],
    evidence_matrix: dict[str, Any],
    claim_evidence: dict[str, Any],
    *,
    live: bool,
    repo_probe: Callable[[str, str | None], dict[str, Any]] = probe_repository,
    output_probe: Callable[[str | None], dict[str, bool]] = probe_output,
    checked_at: str | None = None,
) -> dict[str, Any]:
    sources = {row["logical_repo"]: row for row in source_catalog["sources"]}
    projections = {row["logical_repo"]: row for row in evidence_matrix["sources"]}
    claims = {row["claim_id"]: row for row in claim_evidence["records"]}
    records = []

    for theme in validate_catalog(catalog):
        components = []
        for spec in theme["components"]:
            logical = spec.get("logical_repo")
            source = sources.get(logical) if logical else None
            projection = projections.get(logical) if logical else None
            expected_repo = spec["current_repo"]
            source_repo = source.get("current_repo") if source else expected_repo
            aligned = source_repo == expected_repo
            p = projection.get("projection", {}) if projection else {}
            row_count = p.get("row_count", 0)
            projected = bool(
                aligned
                and source
                and source.get("status") == "ready"
                and not p.get("excluded")
                and isinstance(row_count, int)
                and row_count > 0
            )
            canonical_url = source.get("canonical_url") if source and aligned else None
            repo_state = {
                "exists": False,
                "scheduled": False,
                "latest_passed": False,
                "evidence_commit": None,
            }
            output_state = {"available": False, "primary": False, "raw": False}
            if live:
                repo_state = repo_probe(expected_repo, canonical_url)
                if source and aligned and source.get("raw_url"):
                    output_state = output_probe(source["raw_url"])
            verified = projected and output_state["available"]
            components.append(
                {
                    "logical_repo": logical,
                    "current_repo": expected_repo,
                    "current_repository_url": f"https://github.com/{expected_repo}",
                    "source_catalog_repo": source_repo if source else None,
                    "target_repo": spec["target_repo"],
                    "implementation_issue_url": spec["implementation_issue_url"],
                    "canonical_alignment": aligned,
                    "source_status": source.get("status") if source else None,
                    "repository_exists": bool(repo_state["exists"]),
                    "real_data_exists": bool(verified),
                    "primary_source_provenance_exists": bool(verified and output_state["primary"]),
                    "raw_evidence_exists": bool(verified and output_state["raw"]),
                    "derived_output_exists": bool(verified),
                    "reproducible_from_raw": bool(verified and output_state["raw"] and p.get("adapter")),
                    "scheduled_workflow_exists": bool(repo_state["scheduled"]),
                    "latest_workflow_passed": bool(repo_state["latest_passed"]),
                    "public_view_exists": False,
                    "investor2_integration_exists": bool(projection and not p.get("excluded") and row_count),
                    "canonical_output_url": canonical_url,
                    "mirror_artifact_path": p.get("artifact_path") if aligned else None,
                    "mirror_sha256": p.get("mirror_sha256") if aligned else None,
                    "latest_evidence_commit": repo_state["evidence_commit"],
                }
            )

        if not theme["dedicated_repository_required"]:
            claim = claims.get(theme["claim_id"], {})
            evidence_rows = claim.get("evidence_row_count", 0)
            if live:
                state = repo_probe("KAFKA2306/investor2", None)
            else:
                state = {
                    "exists": False,
                    "scheduled": False,
                    "latest_passed": False,
                    "evidence_commit": None,
                }
            has_evidence = isinstance(evidence_rows, int) and evidence_rows > 0
            components[0].update(
                repository_exists=bool(state["exists"]),
                real_data_exists=has_evidence,
                primary_source_provenance_exists=has_evidence,
                raw_evidence_exists=has_evidence,
                derived_output_exists=has_evidence,
                reproducible_from_raw=has_evidence,
                scheduled_workflow_exists=bool(state["scheduled"]),
                latest_workflow_passed=bool(state["latest_passed"]),
                investor2_integration_exists=has_evidence,
                latest_evidence_commit=state["evidence_commit"],
                canonical_output_url=(
                    "https://github.com/KAFKA2306/investor2/blob/main/api/v1/ark-big-ideas/claim-evidence.json"
                ),
            )

        commits = [
            component["latest_evidence_commit"] for component in components if component["latest_evidence_commit"]
        ]
        record = {
            "theme": theme["theme"],
            "claim_id": theme["claim_id"],
            "dedicated_repository_required": bool(theme["dedicated_repository_required"]),
            "canonical_repositories": [component["current_repo"] for component in components],
            "current_repository_urls": [component["current_repository_url"] for component in components],
            "target_repository_names": [component["target_repo"] for component in components],
            "implementation_issue_urls": [component["implementation_issue_url"] for component in components],
            "components": components,
            "latest_evidence_commit": commits[0] if len(commits) == 1 else (commits or None),
        }
        for field in (
            "repository_exists",
            "real_data_exists",
            "primary_source_provenance_exists",
            "raw_evidence_exists",
            "derived_output_exists",
            "reproducible_from_raw",
            "scheduled_workflow_exists",
            "latest_workflow_passed",
            "public_view_exists",
            "investor2_integration_exists",
        ):
            record[field] = all_components(components, field)
        records.append(record)

    return {
        "schema_version": 1,
        "ark_source_url": catalog["ark_source_url"],
        "mapping_source_url": catalog["mapping_source_url"],
        "coverage_rule": (
            "Theme booleans are true only when every required component is verified; "
            "repository or Issue existence alone is insufficient."
        ),
        "checked_at": checked_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "live_github_checks": live,
        "theme_count": len(records),
        "records": records,
    }


def write_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "theme",
        "canonical_repo",
        "real_data",
        "primary_source_provenance",
        "reproducible",
        "scheduled_workflow",
        "latest_workflow_passed",
        "public_view",
        "investor2_integration",
        "evidence_commit",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result["records"]:
            writer.writerow(
                {
                    "theme": row["theme"],
                    "canonical_repo": " + ".join(row["canonical_repositories"]),
                    "real_data": str(row["real_data_exists"]).lower(),
                    "primary_source_provenance": str(row["primary_source_provenance_exists"]).lower(),
                    "reproducible": str(row["reproducible_from_raw"]).lower(),
                    "scheduled_workflow": str(row["scheduled_workflow_exists"]).lower(),
                    "latest_workflow_passed": str(row["latest_workflow_passed"]).lower(),
                    "public_view": str(row["public_view_exists"]).lower(),
                    "investor2_integration": str(row["investor2_integration_exists"]).lower(),
                    "evidence_commit": json.dumps(row["latest_evidence_commit"])
                    if row["latest_evidence_commit"]
                    else "",
                }
            )


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    def yes(value: object) -> str:
        return "yes" if value else "no"

    lines = [
        "# ARK Big Ideas 2026 × KAFKA2306 repository coverage",
        "",
        (
            "13テーマを、repository名やIssueの存在ではなく、実データ、一次情報provenance、"
            "再生成可能性、GitHub Actions、investor2統合で比較する。"
        ),
        "",
        f"- ARK official source: {result['ark_source_url']}",
        f"- canonical mapping: {result['mapping_source_url']}",
        f"- checked_at: `{result['checked_at']}`",
        "",
        (
            "| Theme | Canonical repository | Real data | Primary-source provenance | Reproducible | "
            "Scheduled workflow | Latest workflow passed | Public domain view | investor2 integration |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["records"]:
        repos = "<br>".join(f"[{repo}](https://github.com/{repo})" for repo in row["canonical_repositories"])
        lines.append(
            f"| {row['theme']} | {repos} | {yes(row['real_data_exists'])} | "
            f"{yes(row['primary_source_provenance_exists'])} | {yes(row['reproducible_from_raw'])} | "
            f"{yes(row['scheduled_workflow_exists'])} | {yes(row['latest_workflow_passed'])} | "
            f"{yes(row['public_view_exists'])} | {yes(row['investor2_integration_exists'])} |"
        )
    lines += [
        "",
        "## Boundaries",
        "",
        "- The Great Acceleration は横断統合であり専用repositoryを要求しない。",
        "- Bitcoin は network / treasury / derivatives を別componentとして判定する。",
        "- Distributed Energy は electricity / nuclear を別componentとして判定する。",
        ("- Multiomics は canonical `KAFKA2306/multiomics` と legacy `KAFKA2306/kafin3` を同一視しない。"),
        ("- non-canonical `KAFKA2306/robot` / `KAFKA2306/space` はcoverageへ加算しない。"),
        "",
        ("ARK forecastとの比較は [#119](https://github.com/KAFKA2306/investor2/issues/119) の責務とする。"),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--source-catalog", type=Path, default=DEFAULT_SOURCE_CATALOG)
    parser.add_argument("--evidence-matrix", type=Path, default=DEFAULT_EVIDENCE_MATRIX)
    parser.add_argument("--claim-evidence", type=Path, default=DEFAULT_CLAIM_EVIDENCE)
    parser.add_argument("--data-output", type=Path, default=DEFAULT_DATA_OUTPUT)
    parser.add_argument("--api-output", type=Path, default=DEFAULT_API_OUTPUT)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    result = build(
        load(args.catalog),
        load(args.source_catalog),
        load(args.evidence_matrix),
        load(args.claim_evidence),
        live=args.live,
    )
    write_json(args.data_output, result)
    write_json(args.api_output, result)
    write_csv(args.csv_output, result)
    write_markdown(args.markdown_output, result)
    print(
        json.dumps(
            {
                "themes": result["theme_count"],
                "real_data": sum(row["real_data_exists"] for row in result["records"]),
                "integrated": sum(row["investor2_integration_exists"] for row in result["records"]),
            }
        )
    )


if __name__ == "__main__":
    main()
