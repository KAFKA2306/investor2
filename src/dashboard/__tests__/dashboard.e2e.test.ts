import { test, expect } from "@playwright/test";

test.describe("Dashboard E2E Tests", () => {
	test("EDINET company search and results", async ({ page }) => {
		// Navigate to company search page
		await page.goto("/company");
		await page.waitForLoadState("networkidle");

		// Take screenshot of initial state
		await page.screenshot({
			path: "screenshots/01-company-search-initial.png",
			fullPage: true,
		});

		// Fill search input
		const searchInput = page.locator('input[name="q"]');
		await searchInput.fill("マルハニチロ");

		// Wait for HTMX to trigger search and display results
		await page.waitForTimeout(1500);
		await page.waitForLoadState("networkidle");

		// Verify results are displayed
		const results = page.locator(".card");
		const count = await results.count();
		expect(count).toBeGreaterThan(0);

		// Take screenshot with search results
		await page.screenshot({
			path: "screenshots/02-company-search-results.png",
			fullPage: true,
		});

		// Click on first result to navigate to detail page
		await results.first().click();
		await page.waitForLoadState("networkidle");

		// Verify detail page loaded
		const detailTitle = page.locator("h1");
		await expect(detailTitle).toBeVisible();

		// Take screenshot of detail page
		await page.screenshot({
			path: "screenshots/03-company-detail.png",
			fullPage: true,
		});
	});

	test("Stock screener with initial results", async ({ page }) => {
		// Navigate to screener page
		await page.goto("/screener");
		await page.waitForLoadState("networkidle");

		// Verify initial data is pre-rendered (should be instant)
		const table = page.locator("table");
		await expect(table).toBeVisible();

		// Take screenshot of initial screener
		await page.screenshot({
			path: "screenshots/04-screener-initial.png",
			fullPage: true,
		});

		// Test sector filter
		const sectorSelect = page.locator('select[name="sector"]');
		if (await sectorSelect.isVisible()) {
			await sectorSelect.selectOption("1");
			await page.waitForTimeout(1000);

			// Take screenshot with filter applied
			await page.screenshot({
				path: "screenshots/05-screener-filtered.png",
				fullPage: true,
			});
		}

		// Test pagination
		const nextButton = page.locator('button:has-text("次へ")');
		if (await nextButton.isEnabled()) {
			await nextButton.click();
			await page.waitForTimeout(1000);

			// Take screenshot of paginated results
			await page.screenshot({
				path: "screenshots/06-screener-page2.png",
				fullPage: true,
			});
		}
	});
});
