#!/usr/bin/env python3
import sys
print("Starting reconnaissance...", file=sys.stderr)

try:
    from playwright.sync_api import sync_playwright

    print("Launching browser...", file=sys.stderr)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to dashboard...", file=sys.stderr)
        page.goto('http://localhost:3000', timeout=10000)
        print("Waiting for page load...", file=sys.stderr)
        page.wait_for_load_state('networkidle')

        # Take screenshot
        page.screenshot(path='/tmp/dashboard_screenshot.png', full_page=True)
        print("✓ Screenshot saved to /tmp/dashboard_screenshot.png", file=sys.stdout)

        # Check for filter buttons
        filter_buttons = page.locator('.filter-btn')
        count = filter_buttons.count()
        print(f"✓ Found {count} filter buttons", file=sys.stdout)

        # Check for table rows
        data_rows = page.locator('[data-row]')
        count = data_rows.count()
        print(f"✓ Found {count} data rows", file=sys.stdout)

        # Check for detail rows
        detail_rows = page.locator('.details-row')
        count = detail_rows.count()
        print(f"✓ Found {count} detail rows", file=sys.stdout)

        # Check for chart
        charts = page.locator('canvas')
        count = charts.count()
        print(f"✓ Found {count} charts", file=sys.stdout)

        # Get page title
        title = page.title()
        print(f"✓ Page title: {title}", file=sys.stdout)

        browser.close()
        print("Done!", file=sys.stderr)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
