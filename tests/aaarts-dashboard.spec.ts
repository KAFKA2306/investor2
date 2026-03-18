import { test, expect } from "@playwright/test";

test.describe("AAARTS Pipeline Dashboard", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("http://localhost:3000/pipeline/results");
		await page.waitForLoadState("networkidle");
	});

	test("should display page title and summary", async ({ page }) => {
		expect(page).toHaveTitle("AAARTS Pipeline Results");

		const heading = page.locator("text=AAARTS Pipeline Results");
		await expect(heading).toBeVisible();

		const subtitle = page.locator("text=Alpha Research and Trading System");
		await expect(subtitle).toBeVisible();
	});

	test("should display execution summary", async ({ page }) => {
		const executionIdLabel = page.locator("text=Execution ID");
		await expect(executionIdLabel).toBeVisible();

		const totalCyclesLabel = page.locator("text=Total Cycles");
		await expect(totalCyclesLabel).toBeVisible();
	});

	test("should render verdict distribution chart", async ({ page }) => {
		const chartTitle = page.locator("text=Verdict Distribution");
		await expect(chartTitle).toBeVisible();

		const canvas = page.locator("canvas").first();
		await expect(canvas).toBeVisible();
	});

	test("should render verdict timeline chart", async ({ page }) => {
		const chartTitle = page.locator("text=Verdict Timeline");
		await expect(chartTitle).toBeVisible();

		const canvas = page.locator("canvas").nth(1);
		await expect(canvas).toBeVisible();
	});

	test("should display performance metrics", async ({ page }) => {
		const metrics = [
			"Average Confidence",
			"Success Rate",
			"Avg Sharpe (GO)",
			"Avg Sharpe (HOLD)",
		];

		for (const metric of metrics) {
			const element = page.locator(`text=${metric}`);
			await expect(element).toBeVisible();
		}
	});

	test("should have filter buttons with verdict counts", async ({ page }) => {
		const allBtn = page.locator('button:has-text("All")');
		await expect(allBtn).toBeVisible();
		await expect(allBtn).toContainText(/All \(\d+\)/);

		const goBtn = page.locator('button:has-text("GO")');
		await expect(goBtn).toBeVisible();

		const holdBtn = page.locator('button:has-text("HOLD")');
		await expect(holdBtn).toBeVisible();

		const pivotBtn = page.locator('button:has-text("PIVOT")');
		await expect(pivotBtn).toBeVisible();
	});

	test("should display detailed results table", async ({ page }) => {
		const tableHeading = page.locator("text=Detailed Results");
		await expect(tableHeading).toBeVisible();

		const headers = [
			"Cycle",
			"Factor ID",
			"Verdict",
			"Sharpe",
			"IC",
			"Drawdown",
			"p-value",
		];
		for (const header of headers) {
			const headerEl = page.locator(`th:has-text("${header}")`);
			await expect(headerEl).toBeVisible();
		}
	});

	test("should display data rows in table", async ({ page }) => {
		const rows = page.locator("table tbody tr");
		const rowCount = await rows.count();
		expect(rowCount).toBeGreaterThan(0);
	});

	test("should have show/hide buttons for detail rows", async ({ page }) => {
		const showBtn = page.locator('button:has-text("Show")').first();
		await expect(showBtn).toBeVisible();
	});

	test("should filter results when clicking verdict buttons", async ({
		page,
	}) => {
		const allBtn = page.locator('button:has-text("All")').first();
		await expect(allBtn).toBeVisible();
		await allBtn.click();

		const holdBtn = page.locator('button:has-text("HOLD")').first();
		await expect(holdBtn).toBeVisible();
		await holdBtn.click();

		await page.waitForTimeout(300);
		expect(holdBtn).toHaveClass(/ring-2/);
	});

	test("should expand detail rows when clicking show", async ({ page }) => {
		const showBtn = page.locator('button:has-text("Show")').first();
		if ((await showBtn.count()) > 0) {
			await showBtn.click();
			await page.waitForTimeout(300);

			const detailContent = page.locator(".details-row").first();
			const text = await detailContent.textContent();
			expect(text).toBeTruthy();
			expect(text).toContain(/Performance Analysis|Verdict|Reasoning/);
		}
	});

	test("should display configuration thresholds", async ({ page }) => {
		const thresholdHeading = page.locator("text=Configuration Thresholds");
		await expect(thresholdHeading).toBeVisible();

		const thresholds = ["MIN SHARPE RATIO", "MAX P-VALUE", "MAX DRAWDOWN"];

		for (const threshold of thresholds) {
			const element = page.locator(`text=${threshold}`);
			await expect(element).toBeVisible();
		}
	});

	test("should display threshold validation indicators in table", async ({
		page,
	}) => {
		const checkmarks = page.locator("text=/✓|✗/");
		const count = await checkmarks.count();
		expect(count).toBeGreaterThan(0);
	});
});
