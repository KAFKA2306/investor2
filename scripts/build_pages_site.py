#!/usr/bin/env python3
"""Build the GitHub Pages evidence browser from canonical repository content."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

CONTENT_ROOTS = ("docs", "data", "generated", "api")
SECTION_ORDER = ("results", "research", "contracts", "data", "generated", "api")
FRONTEND_FILES = ("index.html", "app.js", "styles.css")
DEFAULT_COPY_MAX_BYTES = 5_000_000

_TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".log",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".sql",
}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"}
_RESEARCH_DOC_DIRS = {"research", "paper", "ark-big-ideas"}
_CONTRACT_DOC_DIRS = {"adr", "architecture", "specs", "data-sources"}


def _viewer_for(path: Path, *, browser_renderable: bool) -> str:
    if not browser_renderable:
        return "download"
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".csv", ".tsv"}:
        return "table"
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".pdf":
        return "pdf"
    if suffix in _TEXT_SUFFIXES:
        return "text"
    return "download"


def _media_type(path: Path) -> str:
    overrides = {
        ".md": "text/markdown",
        ".json": "application/json",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
    }
    suffix = path.suffix.lower()
    if suffix in overrides:
        return overrides[suffix]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _section_for(relative_path: PurePosixPath) -> str:
    parts = relative_path.parts
    root = parts[0]
    if root == "data":
        return "data"
    if root == "generated":
        return "generated"
    if root == "api":
        return "api"
    if root != "docs":
        raise ValueError(f"unsupported Pages content root: {relative_path}")

    if len(parts) == 1:
        return "contracts"
    doc_area = parts[1]
    if doc_area == "research" and len(parts) >= 3 and parts[2] == "results":
        return "results"
    if doc_area in _RESEARCH_DOC_DIRS:
        return "research"
    if doc_area in _CONTRACT_DOC_DIRS or len(parts) == 2:
        return "contracts"
    raise ValueError(
        f"unclassified docs artifact: {relative_path}; place it under research/paper/ark-big-ideas, "
        "research/results, adr/architecture/specs/data-sources, or a documented root-level contract"
    )


def _module_for(relative_path: PurePosixPath, section: str) -> str:
    parts = relative_path.parts
    if section == "results":
        return parts[3] if len(parts) >= 5 else "research-results"
    if section == "research":
        if parts[1] == "research":
            return f"research/{parts[2]}" if len(parts) >= 4 else "research"
        return parts[1]
    if section == "contracts":
        return parts[1] if len(parts) >= 3 else "repository"
    if section == "api" and len(parts) >= 3:
        return "/".join(parts[:3])
    if section in {"data", "generated"} and len(parts) >= 2:
        return parts[1]
    return section


def _artifact_id(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]


def _source_urls(repository: str, revision: str, relative_path: str) -> tuple[str, str]:
    encoded_path = quote(relative_path, safe="/")
    source_url = f"https://github.com/{repository}/blob/{revision}/{encoded_path}"
    raw_url = f"https://raw.githubusercontent.com/{repository}/{revision}/{encoded_path}"
    return source_url, raw_url


def discover_artifacts(
    source_root: Path,
    *,
    output_root: Path,
    repository: str,
    revision: str,
    copy_max_bytes: int = DEFAULT_COPY_MAX_BYTES,
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    output_resolved = output_root.resolve()

    for root_name in CONTENT_ROOTS:
        root = source_root / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if output_resolved in path.resolve().parents:
                continue

            relative = path.relative_to(source_root)
            relative_posix = relative.as_posix()
            relative_pure = PurePosixPath(relative_posix)
            section = _section_for(relative_pure)
            size = path.stat().st_size
            local_url: str | None = None

            if size <= copy_max_bytes:
                destination = output_root / "artifacts" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                local_url = quote(
                    (PurePosixPath("artifacts") / relative_pure).as_posix(),
                    safe="/",
                )

            source_url, raw_url = _source_urls(repository, revision, relative_posix)
            artifacts.append(
                {
                    "id": _artifact_id(relative_posix),
                    "path": relative_posix,
                    "name": path.name,
                    "section": section,
                    "category": relative.parts[0],
                    "module": _module_for(relative_pure, section),
                    "extension": path.suffix.lower(),
                    "media_type": _media_type(path),
                    "viewer": _viewer_for(path, browser_renderable=local_url is not None),
                    "size_bytes": size,
                    "local_url": local_url,
                    "source_url": source_url,
                    "raw_url": raw_url,
                }
            )

    section_rank = {name: index for index, name in enumerate(SECTION_ORDER)}
    artifacts.sort(key=lambda item: (section_rank[str(item["section"])], str(item["module"]), str(item["path"])))
    return artifacts


def build_manifest(
    *,
    source_root: Path,
    output_root: Path,
    repository: str,
    revision: str,
    copy_max_bytes: int = DEFAULT_COPY_MAX_BYTES,
) -> dict[str, Any]:
    artifacts = discover_artifacts(
        source_root,
        output_root=output_root,
        repository=repository,
        revision=revision,
        copy_max_bytes=copy_max_bytes,
    )
    category_counts = Counter(str(item["category"]) for item in artifacts)
    section_counts = Counter(str(item["section"]) for item in artifacts)
    viewer_counts = Counter(str(item["viewer"]) for item in artifacts)
    local_files = sum(item["local_url"] is not None for item in artifacts)
    total_bytes = sum(int(item["size_bytes"]) for item in artifacts)

    return {
        "schema_version": 1,
        "repository": repository,
        "revision": revision,
        "content_roots": list(CONTENT_ROOTS),
        "section_order": list(SECTION_ORDER),
        "totals": {
            "artifacts": len(artifacts),
            "local_files": local_files,
            "source_only_files": len(artifacts) - local_files,
            "bytes": total_bytes,
            "categories": dict(sorted(category_counts.items())),
            "sections": {name: section_counts.get(name, 0) for name in SECTION_ORDER},
            "viewers": dict(sorted(viewer_counts.items())),
        },
        "artifacts": artifacts,
    }


def validate_manifest(manifest: dict[str, Any], *, output_root: Path, expected_revision: str) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema")
    if manifest.get("revision") != expected_revision:
        raise ValueError("manifest revision does not match the expected revision")
    if manifest.get("section_order") != list(SECTION_ORDER):
        raise ValueError("manifest section order does not match the canonical Pages taxonomy")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("manifest must contain at least one artifact")

    seen_paths: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise TypeError("manifest artifact must be an object")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("manifest artifact path is missing")
        if path in seen_paths:
            raise ValueError(f"duplicate manifest artifact: {path}")
        seen_paths.add(path)

        section = item.get("section")
        if section not in SECTION_ORDER:
            raise ValueError(f"invalid manifest section for {path}: {section}")
        module = item.get("module")
        if not isinstance(module, str) or not module:
            raise ValueError(f"manifest module is missing for {path}")

        local_url = item.get("local_url")
        if local_url is not None:
            if not isinstance(local_url, str) or not local_url.startswith("artifacts/"):
                raise ValueError(f"invalid local_url for {path}")
            local_path = output_root / local_url
            if not local_path.is_file():
                raise FileNotFoundError(f"manifest local artifact is missing: {local_url}")

    totals = manifest.get("totals")
    if not isinstance(totals, dict) or totals.get("artifacts") != len(artifacts):
        raise ValueError("manifest totals do not match artifact count")
    sections = totals.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("manifest section totals are missing")
    expected_sections = Counter(str(item["section"]) for item in artifacts)
    for name in SECTION_ORDER:
        if sections.get(name) != expected_sections.get(name, 0):
            raise ValueError(f"manifest section total does not match artifacts: {name}")


def _copy_frontend(frontend_root: Path, output_root: Path) -> None:
    for name in FRONTEND_FILES:
        source = frontend_root / name
        if not source.is_file():
            raise FileNotFoundError(f"missing Pages frontend file: {source}")
        shutil.copy2(source, output_root / name)


def build_site(
    *,
    source_root: Path,
    frontend_root: Path,
    output_root: Path,
    repository: str,
    revision: str,
    copy_max_bytes: int = DEFAULT_COPY_MAX_BYTES,
) -> dict[str, Any]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    _copy_frontend(frontend_root, output_root)
    (output_root / ".nojekyll").touch()

    manifest = build_manifest(
        source_root=source_root,
        output_root=output_root,
        repository=repository,
        revision=revision,
        copy_max_bytes=copy_max_bytes,
    )
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    revision_payload = {
        "repository": repository,
        "revision": revision,
        "artifact_count": manifest["totals"]["artifacts"],
    }
    (output_root / "revision.json").write_text(
        json.dumps(revision_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validate_manifest(manifest, output_root=output_root, expected_revision=revision)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--frontend-dir", default="pages")
    parser.add_argument("--output", default="_site")
    parser.add_argument("--repository", default="KAFKA2306/investor2")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--copy-max-bytes", type=int, default=DEFAULT_COPY_MAX_BYTES)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output).resolve()
    frontend_root = (source_root / args.frontend_dir).resolve()
    manifest = build_site(
        source_root=source_root,
        frontend_root=frontend_root,
        output_root=output_root,
        repository=args.repository,
        revision=args.revision,
        copy_max_bytes=args.copy_max_bytes,
    )
    totals = manifest["totals"]
    print(
        "built Pages evidence browser: "
        f"{totals['artifacts']} artifacts, "
        f"{totals['local_files']} locally mirrored, "
        f"{totals['source_only_files']} source-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
