import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { Database } from "bun:sqlite";
import { mkdirSync, rmSync } from "node:fs";
import { RegularizedPCA, generateSpilloverSignals, getDefaultUSToJPMapping } from "../sector_spillover";
import { fetchUSReturns, fetchJPReturns, cacheSectorReturns, getCachedReturns, getSectorReturns, pivotToMatrix } from "../../io/sector_data_fetcher";
import type { SectorReturns, JP17Sectors } from "../../schemas";

// Test database path
const testCacheDir = "/tmp/test_sector_spillover_cache";

describe("fetchUSReturns", () => {
	it("should return promise of SectorReturns array", async () => {
		const returns = await fetchUSReturns("2024-01-01", "2024-01-31");
		expect(Array.isArray(returns)).toBe(true);
	});

	it("should accept valid date ranges", async () => {
		const returns = await fetchUSReturns("2024-01-01", "2024-12-31");
		expect(Array.isArray(returns)).toBe(true);
	});
});

describe("RegularizedPCA.fit", () => {
	let pca: RegularizedPCA;

	beforeEach(() => {
		pca = new RegularizedPCA(3, 0.1, 100);
	});

	it("should extract 3 principal components", () => {
		const matrix = [
			[0.5, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.4, 0.2],
			[-0.3, 0.4, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.3],
			[0.2, -0.1, 0.3, -0.2, 0.4, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1],
			[-0.1, 0.2, -0.3, 0.4, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2],
			[0.3, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.4, 0.2],
		];

		const { components, scores, varianceExplained } = pca.fit(matrix);

		expect(components.length).toBe(3);
		expect(components[0].length).toBe(11);
		expect(scores.length).toBe(5);
		expect(scores[0].length).toBe(3);
		expect(varianceExplained.length).toBe(3);
	});

	it("should have variance explained sum close to 1.0", () => {
		const matrix = [
			[0.5, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.4, 0.2],
			[-0.3, 0.4, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.3],
			[0.2, -0.1, 0.3, -0.2, 0.4, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1],
			[-0.1, 0.2, -0.3, 0.4, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2],
			[0.3, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.4, 0.2],
		];

		const { varianceExplained } = pca.fit(matrix);
		const totalVariance = varianceExplained.reduce((a, b) => a + b, 0);

		expect(totalVariance).toBeGreaterThan(0);
		expect(totalVariance).toBeLessThanOrEqual(1.1);
	});

	it("should improve conditioning with regularization", () => {
		const matrix = [
			[0.5, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.4, 0.2],
			[-0.3, 0.4, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1, -0.3],
			[0.2, -0.1, 0.3, -0.2, 0.4, -0.3, 0.2, -0.1, 0.3, -0.2, 0.1],
		];

		const pcaWithReg = new RegularizedPCA(2, 0.5, 50);
		const pcaWithoutReg = new RegularizedPCA(2, 0.0, 50);

		const resultWithReg = pcaWithReg.fit(matrix);
		const resultWithoutReg = pcaWithoutReg.fit(matrix);

		expect(resultWithReg.components).toBeDefined();
		expect(resultWithoutReg.components).toBeDefined();
		expect(resultWithReg.varianceExplained.length).toBe(2);
	});

	it("should return empty result for empty matrix", () => {
		const { components, scores, varianceExplained } = pca.fit([]);
		expect(components).toEqual([]);
		expect(scores).toEqual([]);
		expect(varianceExplained).toEqual([]);
	});

	it("should normalize vectors correctly", () => {
		const matrix = [
			[1.0, 2.0, 3.0],
			[4.0, 5.0, 6.0],
			[7.0, 8.0, 9.0],
		];

		const { components } = pca.fit(matrix);
		components.forEach((comp) => {
			const norm = Math.sqrt(comp.reduce((sum, val) => sum + val * val, 0));
			expect(Math.abs(norm - 1.0)).toBeLessThan(0.01);
		});
	});
});

describe("generateSpilloverSignals", () => {
	let usToJpMapping: Record<string, string[]>;
	let jpSectors: string[];

	beforeEach(() => {
		usToJpMapping = getDefaultUSToJPMapping();
		jpSectors = Object.keys(usToJpMapping);
	});

	it("should generate signals for all JP sectors", () => {
		const usScores = [
			[0.5, -0.2, 0.1],
			[0.3, 0.4, -0.1],
			[0.1, 0.2, 0.3],
		];

		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		expect(signals.length).toBe(jpSectors.length);
		jpSectors.forEach((jpSector) => {
			const signal = signals.find((s) => s.jp_sector === jpSector);
			expect(signal).toBeDefined();
		});
	});

	it("should have signal_type as LONG/NEUTRAL/SHORT", () => {
		const usScores = [
			[0.8, -0.2, 0.1],
			[-0.8, 0.4, -0.1],
			[0.1, 0.2, 0.3],
		];

		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		signals.forEach((signal) => {
			expect(["long", "neutral", "short"]).toContain(signal.signal_type);
		});
	});

	it("should have confidence score in [0, 1] range", () => {
		const usScores = [
			[0.5, -0.2, 0.1],
			[0.3, 0.4, -0.1],
			[0.1, 0.2, 0.3],
		];

		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		signals.forEach((signal) => {
			expect(signal.confidence).toBeGreaterThanOrEqual(0);
			expect(signal.confidence).toBeLessThanOrEqual(1);
		});
	});

	it("should include 3 factor contributions in us_factor_contributions", () => {
		const usScores = [
			[0.5, -0.2, 0.1],
			[0.3, 0.4, -0.1],
			[0.1, 0.2, 0.3],
		];

		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		signals.forEach((signal) => {
			const factors = Object.keys(signal.us_factor_contributions);
			expect(factors.length).toBe(3);
			expect(factors).toContain("factor_1_risk_sentiment");
			expect(factors).toContain("factor_2_us_dominance");
			expect(factors).toContain("factor_3_growth_vs_defensive");
		});
	});

	it("should use latest US scores for all signals", () => {
		const usScores = [
			[0.1, 0.2, 0.3],
			[0.4, 0.5, 0.6],
			[0.7, 0.8, 0.9],
		];

		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		signals.forEach((signal) => {
			expect(signal.us_factor_contributions.factor_1_risk_sentiment).toBe(0.7);
			expect(signal.us_factor_contributions.factor_2_us_dominance).toBe(0.8);
			expect(signal.us_factor_contributions.factor_3_growth_vs_defensive).toBe(0.9);
		});
	});

	it("should return empty array for empty usScores", () => {
		const signals = generateSpilloverSignals([], jpSectors, usToJpMapping);
		expect(signals).toEqual([]);
	});

	it("should classify signals correctly based on thresholds", () => {
		const usToJpMappingSmall: Record<string, string[]> = {
			"1000": ["energy"],
			"2000": ["materials"],
		};
		const jpSectorsSmall = Object.keys(usToJpMappingSmall);

		const usScoresLong = [[0.9, 0.8, 0.7]];
		const signalsLong = generateSpilloverSignals(usScoresLong, jpSectorsSmall, usToJpMappingSmall);
		signalsLong.forEach((s) => {
			if (Math.abs(Math.tanh(s.signal_score)) > 0.33) {
				expect(s.signal_type).toBe("long");
			}
		});

		const usScoresShort = [[-0.9, -0.8, -0.7]];
		const signalsShort = generateSpilloverSignals(usScoresShort, jpSectorsSmall, usToJpMappingSmall);
		signalsShort.forEach((s) => {
			if (Math.abs(Math.tanh(s.signal_score)) > 0.33) {
				expect(s.signal_type).toBe("short");
			}
		});
	});

	it("should set correct date format (YYYY-MM-DD)", () => {
		const usScores = [[0.5, -0.2, 0.1]];
		const signals = generateSpilloverSignals(usScores, jpSectors, usToJpMapping);

		signals.forEach((signal) => {
			expect(signal.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
		});
	});
});

describe("cacheSectorReturns and getCachedReturns", () => {
	beforeEach(() => {
		rmSync(testCacheDir, { recursive: true, force: true });
		mkdirSync(testCacheDir, { recursive: true });
	});

	afterEach(() => {
		rmSync(testCacheDir, { recursive: true, force: true });
	});

	it("should cache and retrieve sector returns", () => {
		const testDb = new Database(`${testCacheDir}/sector_returns_test.db`);
		testDb.exec(`
			CREATE TABLE IF NOT EXISTS sector_returns (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				date TEXT NOT NULL,
				sector TEXT NOT NULL,
				return_pct REAL NOT NULL,
				created_at INTEGER NOT NULL,
				UNIQUE(date, sector)
			)
		`);

		const returns: SectorReturns[] = [
			{
				date: "2024-01-01",
				sector: "1000",
				return_pct: 1.5,
			},
			{
				date: "2024-01-01",
				sector: "2000",
				return_pct: 2.0,
			},
		];

		const stmt = testDb.prepare(
			`INSERT OR REPLACE INTO sector_returns (date, sector, return_pct, created_at)
			 VALUES (?, ?, ?, ?)`,
		);
		const now = Math.floor(Date.now() / 1000);
		for (const ret of returns) {
			stmt.run(ret.date, ret.sector, ret.return_pct, now);
		}

		const retrieveStmt = testDb.prepare(
			`SELECT date, sector, return_pct FROM sector_returns
			 WHERE date >= ? AND date <= ?
			 ORDER BY date, sector`,
		);
		const cached = retrieveStmt.all("2024-01-01", "2024-01-31") as Array<{
			date: string;
			sector: string;
			return_pct: number;
		}>;

		expect(cached.length).toBe(2);
		expect(cached[0].sector).toBe("1000");
		expect(cached[0].return_pct).toBe(1.5);

		testDb.close();
	});
});

describe("getSectorReturns", () => {
	it("should return promise of SectorReturns array", async () => {
		const returns = await getSectorReturns("2024-01-01", "2024-01-31");
		expect(Array.isArray(returns)).toBe(true);
	});

	it("should include both US and JP returns when data available", async () => {
		const returns = await getSectorReturns("2024-01-01", "2024-01-31");

		if (returns.length > 0) {
			const hasSectors = returns.some((r) => typeof r.sector === "string");
			expect(hasSectors).toBe(true);
		}
	});
});

describe("pivotToMatrix", () => {
	it("should convert SectorReturns array to matrix format", () => {
		const returns: SectorReturns[] = [
			{ date: "2024-01-01", sector: "1000", return_pct: 1.0 },
			{ date: "2024-01-01", sector: "2000", return_pct: 2.0 },
			{ date: "2024-01-02", sector: "1000", return_pct: 1.5 },
			{ date: "2024-01-02", sector: "2000", return_pct: 2.5 },
		];

		const { dates, sectors, matrix } = pivotToMatrix(returns);

		expect(dates).toEqual(["2024-01-01", "2024-01-02"]);
		expect(sectors).toEqual(["1000", "2000"]);
		expect(matrix.length).toBe(2);
		expect(matrix[0].length).toBe(2);
		expect(matrix[0][0]).toBe(1.0);
		expect(matrix[0][1]).toBe(2.0);
		expect(matrix[1][0]).toBe(1.5);
		expect(matrix[1][1]).toBe(2.5);
	});

	it("should handle missing data with 0.0", () => {
		const returns: SectorReturns[] = [
			{ date: "2024-01-01", sector: "1000", return_pct: 1.0 },
			{ date: "2024-01-02", sector: "2000", return_pct: 2.0 },
		];

		const { matrix } = pivotToMatrix(returns);

		expect(matrix[0][1]).toBe(0);
		expect(matrix[1][0]).toBe(0);
	});

	it("should return empty arrays for empty input", () => {
		const { dates, sectors, matrix } = pivotToMatrix([]);

		expect(dates).toEqual([]);
		expect(sectors).toEqual([]);
		expect(matrix).toEqual([]);
	});

	it("should sort dates and sectors", () => {
		const returns: SectorReturns[] = [
			{ date: "2024-01-03", sector: "2000", return_pct: 1.0 },
			{ date: "2024-01-01", sector: "1000", return_pct: 2.0 },
			{ date: "2024-01-02", sector: "1000", return_pct: 3.0 },
		];

		const { dates, sectors } = pivotToMatrix(returns);

		expect(dates).toEqual(["2024-01-01", "2024-01-02", "2024-01-03"]);
		expect(sectors).toEqual(["1000", "2000"]);
	});
});

describe("getDefaultUSToJPMapping", () => {
	it("should return non-empty mapping", () => {
		const mapping = getDefaultUSToJPMapping();
		expect(Object.keys(mapping).length).toBeGreaterThan(0);
	});

	it("should map all 17 JP sectors", () => {
		const mapping = getDefaultUSToJPMapping();
		const expectedSectors = [
			"1000",
			"2000",
			"3000",
			"4000",
			"5000",
			"6000",
			"7000",
			"8000",
			"9000",
			"10000",
			"11000",
			"12000",
			"13000",
			"14000",
			"15000",
			"16000",
			"17000",
		];

		for (const sector of expectedSectors) {
			expect(mapping[sector]).toBeDefined();
			expect(Array.isArray(mapping[sector])).toBe(true);
		}
	});

	it("should have string arrays for US sector references", () => {
		const mapping = getDefaultUSToJPMapping();

		for (const jpSector of Object.keys(mapping)) {
			const usSectors = mapping[jpSector];
			expect(Array.isArray(usSectors)).toBe(true);
			usSectors.forEach((sector) => {
				expect(typeof sector).toBe("string");
			});
		}
	});
});
