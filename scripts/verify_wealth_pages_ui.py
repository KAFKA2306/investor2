#!/usr/bin/env python3
"""Verify the actual GitHub Pages wealth watch with a browser."""

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "https://kafka2306.github.io/investor2/"
PATH = "data/wealth-consumption/observations.csv"


def run() -> None:
    revision = os.environ["EXPECTED_REVISION"]
    output = Path("production-validation")
    output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(BASE, wait_until="domcontentloaded")
        expect(page.locator("#wealth-watch-link")).to_be_visible()

        page.locator("#wealth-watch-link").click()
        expect(page.locator("#artifact-title")).to_have_text(PATH)
        rows = page.locator("#render-target table tbody tr")
        expect(rows).to_have_count(8)
        expect(page.locator("#render-target")).to_contain_text("lvmh_wj_2026q3")
        expect(page.locator("#render-target")).to_contain_text(
            "manhattan_condo_contracts_202610"
        )
        source = page.locator("#render-target a[href*='lvmh.com']")
        expect(source.first).to_be_visible()
        expect(source.first).to_have_attribute("target", "_blank")

        deployed = page.evaluate("fetch('revision.json').then(r => r.json())")
        assert deployed["revision"] == revision
        assert page.locator("#section-filter").input_value() == "data"
        assert "path=data%2Fwealth-consumption%2Fobservations.csv" in page.url
        page.screenshot(path=str(output / "wealth-desktop.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.locator("#render-target table")).to_be_visible()
        page.screenshot(path=str(output / "wealth-mobile.png"), full_page=True)
        (output / "wealth-result.txt").write_text(
            f"PASS revision={revision} rows=8\n", encoding="utf-8"
        )
        browser.close()


if __name__ == "__main__":
    run()
