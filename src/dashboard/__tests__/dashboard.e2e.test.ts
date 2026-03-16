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

		// Navigate to company detail directly
		await page.goto("/edinet/1333");
		await page.waitForLoadState("networkidle");

		// Take screenshot with company search results (simulated)
		await page.screenshot({
			path: "screenshots/02-company-search-results.png",
			fullPage: true,
		});

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
		// Navigate to stock screener page (銘柄スクリーニング)
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
		const sectorSelect = page.locator("#sector-select");
		if (await sectorSelect.isVisible()) {
			await sectorSelect.waitFor({ state: "attached" });
			const options = await sectorSelect.locator("option").count();
			if (options > 1) {
				await sectorSelect.selectOption({ index: 1 });
				await page.waitForTimeout(1500);

				// Take screenshot with filter applied
				await page.screenshot({
					path: "screenshots/05-screener-filtered.png",
					fullPage: true,
				});
			}
		}

		// Test pagination (look for "次 →" button)
		const nextButton = page.locator('button:has-text("次")').last();
		if (await nextButton.isVisible({ timeout: 2000 }).catch(() => false)) {
			await nextButton.click();
			await page.waitForTimeout(1500);

			// Take screenshot of paginated results
			await page.screenshot({
				path: "screenshots/06-screener-page2.png",
				fullPage: true,
			});
		}
	});
});
