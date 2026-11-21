#!/usr/bin/env python3
"""Exercise the deployed GitHub Pages wealth watch with a real browser."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

BASE = "https://kafka2306.github.io/investor2/"
OBSERVATION_PATH = "data/wealth-consumption/observations.csv"
SRC = "https://www.lvmh.com/en/publications/continued-growth-in-the-third-quarter-of-2026"


def run() -> None:
    expected = os.environ["EXPECTED_REVISION"]
    evidence = Path("production-validation")
    evidence.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        # Open the same entry point that users will open, not a build artifact.
        response = page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        assert response is not None and response.status == 200
        expect(page.locator("#wealth-watch-link")).to_be_visible(timeout=20000)

        # Follow the user-visible navigation path; the browser renders the CSV.
        page.locator("#wealth-watch-link").click()
        expect(page.locator("#artifact-title")).to_have_text(
            OBSERVATION_PATH, timeout=25000
        )
        table = page.locator("#render-target")
        expect(table.locator("table tbody tr")).to_have_count(8, timeout=25000)
        expect(table).to_contain_text("lvmh_wj_2026q3")
        expect(table).to_contain_text("manhattan_condo_contracts_202610")

        # The primary URL must be usable, not plain text inside a table.
        source = page.locator('#render-target a[href="' + SRC + '"]')
        assert source.count() >= 1
        expect(source.first).to_have_attribute("target", "_blank")
        expect(source.first).to_have_attribute("rel", "noopener noreferrer")
        assert page.locator("#section-filter").input_value() == "data"
        assert parse_qs(urlsplit(page.url).query).get("path") == [OBSERVATION_PATH]

        manifest = page.evaluate(
            "async () => (await fetch('manifest.json', { cache: 'no-store' })).json()"
        )
        assert manifest["revision"] == expected, (expected, manifest["revision"])
        assert any(
            item["path"] == OBSERVATION_PATH and item["local_url"]
            for item in manifest["artifacts"]
        )

        page.screenshot(path=str(evidence / "wealth-watch-desktop.png"), full_page=True)

        # Small screens must keep the main content inside the viewport.
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator("#render-target table")).to_be_visible()
        page.screenshot(path=str(evidence / "wealth-watch-mobile.png"), full_page=True)

        assert not errors, errors
        (evidence / "wealth-watch-browser.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "revision": expected,
                    "path": OBSERVATION_PATH,
                    "rows": 8,
                    "source_link": SRC,
                    "page_errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        browser.close()


if __name__ == "__main__":
    run()
