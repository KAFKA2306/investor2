#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:3000', timeout=10000)
        page.wait_for_load_state('networkidle')

        # Take screenshot
        page.screenshot(path='/tmp/dashboard_screenshot.png', full_page=True)

        # Get info
        filter_count = page.locator('.filter-btn').count()
        row_count = page.locator('[data-row]').count()
        detail_count = page.locator('.details-row').count()
        chart_count = page.locator('canvas').count()
        title = page.title()

        # Write to file
        with open('/tmp/dashboard_recon.txt', 'w') as f:
            f.write(f"Title: {title}\n")
            f.write(f"Filter buttons: {filter_count}\n")
            f.write(f"Data rows: {row_count}\n")
            f.write(f"Detail rows: {detail_count}\n")
            f.write(f"Charts: {chart_count}\n")

        browser.close()

except Exception as e:
    with open('/tmp/dashboard_recon.txt', 'w') as f:
        f.write(f"ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())
