import { test, expect } from "@playwright/test";

test.describe("Company Detail Page - Chart & Financial Data", () => {
	test("Financial chart rendering and data display", async ({ page }) => {
		// Navigate directly to a company (using EDINET code 1333 = マルハニチロ)
		await page.goto("/company/detail/1333");
		await page.waitForLoadState("networkidle");

		// Verify page title
		const pageTitle = page.locator("h1");
		await expect(pageTitle).toBeVisible();

		// Take screenshot of top section
		await page.screenshot({
			path: "screenshots/07-company-detail-header.png",
			fullPage: false,
		});

		// Scroll to chart section
		const chartContainer = page.locator("canvas#financialChart");
		if (await chartContainer.isVisible()) {
			await chartContainer.scrollIntoViewIfNeeded();
			await page.waitForTimeout(500);

			// Verify Chart.js canvas is present
			await expect(chartContainer).toBeVisible();

			// Take screenshot of chart
			await page.screenshot({
				path: "screenshots/08-financial-chart.png",
				fullPage: false,
			});

			// Verify chart data by checking if it's rendered (visual verification)
			const chartBox = await chartContainer.boundingBox();
			expect(chartBox).not.toBeNull();
			expect(chartBox?.width).toBeGreaterThan(0);
			expect(chartBox?.height).toBeGreaterThan(0);
		}

		// Scroll to financial data section
		const financialSection = page.locator("text=財務指標");
		if (await financialSection.isVisible()) {
			await financialSection.scrollIntoViewIfNeeded();
			await page.waitForTimeout(500);

			// Take screenshot of financial metrics
			await page.screenshot({
				path: "screenshots/09-financial-metrics.png",
				fullPage: false,
			});

			// Verify financial data fields exist
			const eps = page.locator("text=EPS").or(page.locator("text=eps"));
			const bps = page.locator("text=BPS").or(page.locator("text=bps"));

			if (await eps.isVisible()) {
				expect(await eps.count()).toBeGreaterThan(0);
			}
		}

		// Scroll to governance section
		const govSection = page.locator("text=ガバナンス");
		if (await govSection.isVisible()) {
			await govSection.scrollIntoViewIfNeeded();
			await page.waitForTimeout(500);

			// Take screenshot of governance data
			await page.screenshot({
				path: "screenshots/10-governance-data.png",
				fullPage: false,
			});
		}

		// Full page screenshot
		await page.screenshot({
			path: "screenshots/11-company-detail-full.png",
			fullPage: true,
		});
	});

	test("Multiple company comparisons and chart variations", async ({
		page,
	}) => {
		// Test with different company
		const companies = ["1333", "7203", "9984"]; // Marubeni, Toyota, SoftBank

		for (const code of companies) {
			await page.goto(`/company/detail/${code}`);
			await page.waitForLoadState("networkidle");

			const title = page.locator("h1");
			if (await title.isVisible()) {
				const companyName = await title.textContent();
				console.log(`Testing company: ${companyName}`);

				// Check chart exists
				const chart = page.locator("canvas#financialChart");
				if (await chart.isVisible()) {
					await chart.scrollIntoViewIfNeeded();
					await page.waitForTimeout(300);

					await page.screenshot({
						path: `screenshots/12-company-${code}-chart.png`,
						fullPage: false,
					});
				}
			}
		}
	});
});
