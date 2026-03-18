import { chromium } from "@playwright/test";
import { writeFileSync } from "fs";

async function testDashboard() {
	const results: string[] = [];
	const browser = await chromium.launch({ headless: true });
	const page = await browser.newPage();

	try {
		results.push("Navigating to dashboard...");
		await page.goto("http://localhost:3000", { timeout: 10000 });
		await page.waitForLoadState("networkidle");

		results.push("✓ Page loaded");

		// Take screenshot
		await page.screenshot({ path: "/tmp/dashboard.png", fullPage: true });
		results.push("✓ Screenshot saved to /tmp/dashboard.png");

		// Get page info
		const title = await page.title();
		results.push(`✓ Title: ${title}`);

		// Check for filter buttons
		const filterCount = await page.locator(".filter-btn").count();
		results.push(`✓ Filter buttons: ${filterCount}`);

		// Check for data rows
		const rowCount = await page.locator("[data-row]").count();
		results.push(`✓ Data rows: ${rowCount}`);

		// Check for detail rows
		const detailCount = await page.locator(".details-row").count();
		results.push(`✓ Detail rows: ${detailCount}`);

		// Get chart count
		const chartCount = await page.locator("canvas").count();
		results.push(`✓ Charts: ${chartCount}`);

		// Get first filter button text
		const firstBtn = page.locator(".filter-btn").first();
		const text = await firstBtn.textContent();
		results.push(`✓ First filter button: ${text}`);
	} catch (e) {
		results.push(`ERROR: ${e}`);
	} finally {
		await browser.close();
		writeFileSync("/tmp/test_results.txt", results.join("\n"));
	}
}

testDashboard();
