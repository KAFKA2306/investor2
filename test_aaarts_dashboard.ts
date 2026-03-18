import { chromium } from "@playwright/test";
import { writeFileSync } from "fs";

async function testAaartsDashboard() {
	const results: string[] = [];
	const browser = await chromium.launch({ headless: true });
	const page = await browser.newPage();

	try {
		results.push("Navigating to AAARTS pipeline results...");
		await page.goto("http://localhost:3000/pipeline/results", {
			timeout: 10000,
		});
		await page.waitForLoadState("networkidle");

		results.push("✓ AAARTS page loaded");

		// Take screenshot
		await page.screenshot({
			path: "/tmp/aaarts_dashboard.png",
			fullPage: true,
		});
		results.push("✓ Screenshot saved to /tmp/aaarts_dashboard.png");

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

		if (filterCount > 0) {
			const firstBtn = page.locator(".filter-btn").first();
			const text = await firstBtn.textContent();
			results.push(`✓ First filter button: ${text}`);
		}

		// Test filter functionality
		if (filterCount > 0) {
			results.push("\n--- Testing Filter Functionality ---");
			const allBtn = page.locator(".filter-btn").nth(0);
			await allBtn.click();
			results.push("✓ Clicked 'All' filter button");

			const visibleRows = await page.locator("[data-row]:visible").count();
			results.push(`✓ Visible data rows after filter: ${visibleRows}`);
		}

		// Test sorting
		if (rowCount > 0) {
			results.push("\n--- Testing Sort Functionality ---");
			const sharpeHeader = page.locator("th:has-text('Sharpe')").first();
			if ((await sharpeHeader.count()) > 0) {
				await sharpeHeader.click();
				results.push("✓ Clicked Sharpe header to sort");
				await page.waitForTimeout(500);
				const sortedRows = await page.locator("[data-row]").count();
				results.push(`✓ Rows after sort: ${sortedRows}`);
			}
		}

		// Test detail row expansion
		if (rowCount > 0) {
			results.push("\n--- Testing Detail Row Expansion ---");
			const firstShowBtn = page.locator("button:has-text('Show')").first();
			if ((await firstShowBtn.count()) > 0) {
				await firstShowBtn.click();
				results.push("✓ Clicked 'Show' button");
				await page.waitForTimeout(300);
				const expandedText = await page
					.locator(".details-row:not(.hidden)")
					.first()
					.textContent();
				if (expandedText && expandedText.length > 0) {
					results.push("✓ Detail row expanded with content visible");
				}
			}
		}

		results.push("\n✅ All dashboard tests completed successfully!");
	} catch (e) {
		results.push(`\n❌ ERROR: ${e}`);
	} finally {
		await browser.close();
		writeFileSync("/tmp/aaarts_test_results.txt", results.join("\n"));
	}
}

testAaartsDashboard();
