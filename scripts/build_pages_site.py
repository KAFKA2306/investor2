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


def _module_for(relative_path: PurePosixPath) -> str:
    parts = relative_path.parts
    if len(parts) == 1:
        return parts[0]
    if parts[0] == "api" and len(parts) >= 3:
        return "/".join(parts[:3])
    return "/".join(parts[:2])


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
            size = path.stat().st_size
            local_url: str | None = None

            if size <= copy_max_bytes:
                destination = output_root / "artifacts" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                local_url = quote(
                    (
                        PurePosixPath("artifacts") / PurePosixPath(relative_posix)
                    ).as_posix(),
                    safe="/",
                )

            source_url, raw_url = _source_urls(repository, revision, relative_posix)
            artifacts.append(
                {
                    "id": _artifact_id(relative_posix),
                    "path": relative_posix,
                    "name": path.name,
                    "category": relative.parts[0],
                    "module": _module_for(PurePosixPath(relative_posix)),
                    "extension": path.suffix.lower(),
                    "media_type": _media_type(path),
                    "viewer": _viewer_for(
                        path, browser_renderable=local_url is not None
                    ),
                    "size_bytes": size,
                    "local_url": local_url,
                    "source_url": source_url,
                    "raw_url": raw_url,
                }
            )

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
    viewer_counts = Counter(str(item["viewer"]) for item in artifacts)
    local_files = sum(item["local_url"] is not None for item in artifacts)
    total_bytes = sum(int(item["size_bytes"]) for item in artifacts)

    return {
        "schema_version": 1,
        "repository": repository,
        "revision": revision,
        "content_roots": list(CONTENT_ROOTS),
        "totals": {
            "artifacts": len(artifacts),
            "local_files": local_files,
            "source_only_files": len(artifacts) - local_files,
            "bytes": total_bytes,
            "categories": dict(sorted(category_counts.items())),
            "viewers": dict(sorted(viewer_counts.items())),
        },
        "artifacts": artifacts,
    }


def validate_manifest(
    manifest: dict[str, Any], *, output_root: Path, expected_revision: str
) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema")
    if manifest.get("revision") != expected_revision:
        raise ValueError("manifest revision does not match the expected revision")

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

        local_url = item.get("local_url")
        if local_url is not None:
            if not isinstance(local_url, str) or not local_url.startswith("artifacts/"):
                raise ValueError(f"invalid local_url for {path}")
            local_path = output_root / local_url
            if not local_path.is_file():
                raise FileNotFoundError(
                    f"manifest local artifact is missing: {local_url}"
                )

    totals = manifest.get("totals")
    if not isinstance(totals, dict) or totals.get("artifacts") != len(artifacts):
        raise ValueError("manifest totals do not match artifact count")


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
