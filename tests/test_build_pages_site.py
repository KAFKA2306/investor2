from __future__ import annotations

import json
from pathlib import Path

from scripts.build_pages_site import build_site, validate_manifest


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_site_discovers_canonical_content_without_theme_registration(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pages/index.html", "<script src='app.js'></script>")
    _write(tmp_path / "pages/app.js", "console.log('ok')")
    _write(tmp_path / "pages/styles.css", "body{}")
    _write(tmp_path / "docs/research/alpha/report.md", "# result")
    _write(tmp_path / "data/new-domain/metrics.csv", "name,value\nalpha,1\n")
    _write(tmp_path / "generated/new-domain/chart.svg", "<svg></svg>")
    _write(tmp_path / "api/v1/new-domain/result.json", '{"ok": true}')
    _write(tmp_path / "data/new-domain/large.json", "x" * 2_000)

    output = tmp_path / "_site"
    manifest = build_site(
        source_root=tmp_path,
        frontend_root=tmp_path / "pages",
        output_root=output,
        repository="KAFKA2306/investor2",
        revision="abc123",
        copy_max_bytes=1_000,
    )

    paths = {item["path"]: item for item in manifest["artifacts"]}
    assert set(paths) == {
        "api/v1/new-domain/result.json",
        "data/new-domain/large.json",
        "data/new-domain/metrics.csv",
        "docs/research/alpha/report.md",
        "generated/new-domain/chart.svg",
    }
    assert paths["api/v1/new-domain/result.json"]["module"] == "api/v1/new-domain"
    assert paths["data/new-domain/metrics.csv"]["viewer"] == "table"
    assert paths["generated/new-domain/chart.svg"]["viewer"] == "image"
    assert paths["docs/research/alpha/report.md"]["viewer"] == "text"
    assert paths["data/new-domain/large.json"]["viewer"] == "download"
    assert paths["data/new-domain/large.json"]["local_url"] is None
    assert manifest["totals"]["categories"] == {
        "api": 1,
        "data": 2,
        "docs": 1,
        "generated": 1,
    }

    payload = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    validate_manifest(payload, output_root=output, expected_revision="abc123")
    assert (output / "revision.json").is_file()


def test_new_module_appears_without_frontend_or_workflow_changes(tmp_path: Path) -> None:
    _write(tmp_path / "pages/index.html", "index")
    _write(tmp_path / "pages/app.js", "app")
    _write(tmp_path / "pages/styles.css", "css")
    _write(tmp_path / "docs/research/existing.json", "{}")

    first = build_site(
        source_root=tmp_path,
        frontend_root=tmp_path / "pages",
        output_root=tmp_path / "_site",
        repository="KAFKA2306/investor2",
        revision="r1",
    )
    assert {item["path"] for item in first["artifacts"]} == {
        "docs/research/existing.json"
    }

    _write(
        tmp_path / "generated/brand-new-study/summary.json", '{"sharpe": 1.2}'
    )
    second = build_site(
        source_root=tmp_path,
        frontend_root=tmp_path / "pages",
        output_root=tmp_path / "_site",
        repository="KAFKA2306/investor2",
        revision="r2",
    )
    assert {item["path"] for item in second["artifacts"]} == {
        "docs/research/existing.json",
        "generated/brand-new-study/summary.json",
    }
