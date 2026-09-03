import { readFileSync } from "node:fs";
import { describe, expect, test } from "bun:test";
import {
	type AssetPosition,
	buildFxOverlayDecision,
	calculateCurrentUsdExposure,
	type FxOverlayConfig,
	type FxOverlayObservation,
	optimizeIncrementalUsdExposure,
} from "../src/decision/fx_overlay";

const positions: AssetPosition[] = [
	{
		id: "QQQ",
		marketValueJpy: 600_000,
		usdExposureRatio: 1,
		sourceRef: "portfolio://qqq",
		evidenceKind: "test_fixture",
	},
	{
		id: "JPY_CASH",
		marketValueJpy: 400_000,
		usdExposureRatio: 0,
		sourceRef: "portfolio://jpy-cash",
		evidenceKind: "test_fixture",
	},
];

const config: FxOverlayConfig = {
	minIncrementalUsdExposure: 0,
	maxIncrementalUsdExposure: 1.5,
	minTotalUsdExposure: 0,
	maxTotalUsdExposure: 1.6,
	initialMarginRate: 0.04,
	maxMarginUsageFraction: 0.08,
	marginCallMarginRate: 0.04,
	liquidationMarginRate: 0.02,
	maxOverlayExpectedShortfallContribution: 0.1,
	maxCrowdingReduction: 0.8,
	riskAversion: 50,
	spreadCostRatePerUnitTurnover: 0.00001,
	trainingWindow: 4,
};

const leg = [0.01, -0.005, 0.008, -0.002, 0.006, -0.004, 0.004, -0.001];
const base = [
	0.001, -0.002, 0.0005, -0.001, 0.0015, -0.0015, 0.001, -0.0005,
];

const observation = (index: number): FxOverlayObservation => {
	const day = String(index + 1).padStart(2, "0");
	const nextDay = String(index + 2).padStart(2, "0");
	return {
		periodStart: `2026-01-${day}T00:00:00Z`,
		periodEnd: `2026-01-${day}T12:00:00Z`,
		observedAt: `2026-01-${day}T13:00:00Z`,
		basePortfolioReturn: base[index],
		usdJpySpotReturn: leg[index] - 0.0001,
		realizedSwapLongReturn: 0.0001,
		realizedSwapShortReturn: -0.0001,
		fundingCostReturn: 0,
		usdLongCrowdingPercentile: index >= 4 ? 0.9 : undefined,
		crowdingAvailableAt:
			index >= 4 ? `2026-01-${day}T00:00:00Z` : undefined,
		sourceRefs: [
			`fixture://fx/${day}`,
			`fixture://swap/${day}`,
			`fixture://${nextDay}`,
		],
		evidenceKind: "test_fixture",
	};
};

const rows = leg.map((_, index) => observation(index));

describe("FX overlay", () => {
	test("counts existing USD assets before adding an FX overlay", () => {
		expect(calculateCurrentUsdExposure(positions)).toBeCloseTo(0.6, 12);
	});

	test("optimizes a continuous incremental exposure instead of selecting a fixed leverage bucket", () => {
		const training = rows.slice(0, 4);
		const exposure = optimizeIncrementalUsdExposure(training, 0.6, config);
		expect(exposure).toBeGreaterThan(0);
		expect(exposure).toBeLessThan(1);
		expect([0, 0.5, 1, 2, 3]).not.toContain(exposure);
		expect(0.6 + exposure).toBeLessThanOrEqual(config.maxTotalUsdExposure);
	});

	test("uses CFTC crowding only to reduce the USD-long risk budget", () => {
		const training = rows.slice(0, 4);
		const normal = optimizeIncrementalUsdExposure(training, 0.6, config, 0);
		const crowded = optimizeIncrementalUsdExposure(training, 0.6, config, 1);
		expect(crowded).toBeLessThan(normal);
		expect(crowded).toBeGreaterThanOrEqual(0);
	});

	test("runs PIT walk-forward OOS and keeps fixtures out of VERIFIED output", () => {
		const result = buildFxOverlayDecision(positions, rows, config);
		expect(result.status).toBe("TEST_ONLY");
		if (result.status !== "TEST_ONLY") {
			throw new Error("expected test-only result");
		}
		expect(result.currentUsdExposure).toBeCloseTo(0.6, 12);
		expect(result.recommendedTotalUsdExposure).toBeCloseTo(
			result.currentUsdExposure + result.recommendedIncrementalUsdExposure,
			12,
		);
		expect(result).toHaveProperty("hedgeRatio");
		expect(result.oos).toHaveProperty("expectedShortfall95");
		expect(result.oos).toHaveProperty("maxDrawdown");
		expect(result.oos).toHaveProperty("carryContributionAnnualized");
		expect(result.oos).toHaveProperty("fxContributionAnnualized");
		expect(result.oos).toHaveProperty("fundingCostContributionAnnualized");
		expect(result.oos).toHaveProperty("transactionCostContributionAnnualized");
		expect(result.baselines.map((row) => row.incrementalUsdExposure)).toEqual([
			0, 0.5, 1, 2, 3,
		]);
		expect(
			result.baselines.find((row) => row.incrementalUsdExposure === 2)?.status,
		).toBe("INFEASIBLE");
	});

	test("publishes one fail-closed canonical API artifact for downstream views", () => {
		const artifact = JSON.parse(
			readFileSync(
				new URL("../api/v1/portfolio/fx-overlay.json", import.meta.url),
				"utf8",
			),
		);
		expect(artifact).toEqual({
			schema_version: "investor2.fx-overlay.v1",
			status: "UNVERIFIED",
			reason:
				"Live portfolio recommendation is unavailable: canonical realized daily swap history required by investor2#251 and the actual portfolio position snapshot required by investor2#252 are not yet materialized.",
		});
	});

	test("fails closed when the requested negative overlay has no realized short swap", () => {
		const withoutShortSwap = rows.map((row) => ({
			...row,
			realizedSwapShortReturn: undefined,
		}));
		const result = buildFxOverlayDecision(positions, withoutShortSwap, {
			...config,
			minIncrementalUsdExposure: -1,
		});
		expect(result.status).toBe("UNVERIFIED");
		if (result.status !== "UNVERIFIED") {
			throw new Error("expected unverified result");
		}
		expect(result.reason).toContain("short swap");
	});

	test("fails closed on point-in-time leakage", () => {
		const leaked = rows.map((row) => ({ ...row }));
		leaked[3].observedAt = "2026-01-06T13:00:00Z";
		const result = buildFxOverlayDecision(positions, leaked, config);
		expect(result.status).toBe("UNVERIFIED");
		if (result.status !== "UNVERIFIED") {
			throw new Error("expected unverified result");
		}
		expect(result.reason).toContain("PIT violation");
	});
});
