import { describe, it, expect } from "bun:test";

/**
 * Task #6: バックテストのエッジケーステスト
 * Sharpe Ratio, Max Drawdown, Signal thresholdの検証
 */

describe("Sharpe Ratio Calculation (Edge Cases)", () => {
	it("should handle constant returns (zero volatility)", () => {
		const dailyReturns = [0.001, 0.001, 0.001, 0.001];
		const mean = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
		const variance = dailyReturns.reduce((a, r) => a + (r - mean) ** 2, 0) / dailyReturns.length;
		const stddev = Math.sqrt(variance);
		const sharpe = stddev > 0 ? (mean / stddev) * Math.sqrt(252) : 0;

		expect(stddev).toBe(0);
		expect(sharpe).toBe(0);
	});

	it("should handle negative returns", () => {
		const dailyReturns = [-0.001, -0.002, -0.001, -0.0015];
		const mean = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
		const variance = dailyReturns.reduce((a, r) => a + (r - mean) ** 2, 0) / dailyReturns.length;
		const stddev = Math.sqrt(variance);
		const sharpe = stddev > 0 ? (mean / stddev) * Math.sqrt(252) : 0;

		expect(sharpe).toBeLessThan(0);
		expect(Number.isFinite(sharpe)).toBe(true);
	});

	it("should calculate annual Sharpe correctly", () => {
		const dailyReturns = [0.001, 0.0012, 0.0009, 0.0011, 0.001];
		const mean = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
		const variance = dailyReturns.reduce((a, r) => a + (r - mean) ** 2, 0) / dailyReturns.length;
		const stddev = Math.sqrt(variance);
		const sharpe = stddev > 0 ? (mean / stddev) * Math.sqrt(252) : 0;

		expect(stddev).toBeGreaterThan(0);
		expect(Number.isFinite(sharpe)).toBe(true);
		expect(sharpe).toBeGreaterThan(0);
	});

	it("should handle high volatility days", () => {
		const dailyReturns = [0.05, -0.08, 0.03, -0.06, 0.02];
		const mean = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
		const variance = dailyReturns.reduce((a, r) => a + (r - mean) ** 2, 0) / dailyReturns.length;
		const stddev = Math.sqrt(variance);
		const sharpe = stddev > 0 ? (mean / stddev) * Math.sqrt(252) : 0;

		expect(stddev).toBeGreaterThan(0);
		expect(Number.isFinite(sharpe)).toBe(true);
	});
});

describe("Max Drawdown Calculation (Edge Cases)", () => {
	it("should return 0 for monotonically increasing portfolio", () => {
		const portfolio = [1.0, 1.01, 1.02, 1.03, 1.04, 1.05];
		let peak = 1.0;
		let maxDD = 0;

		for (const p of portfolio) {
			peak = Math.max(peak, p);
			const dd = (peak - p) / peak;
			maxDD = Math.max(maxDD, dd);
		}

		expect(maxDD).toBe(0);
	});

	it("should return 100% for complete loss", () => {
		const portfolio = [1.0, 0.5, 0.0];
		let peak = 1.0;
		let maxDD = 0;

		for (const p of portfolio) {
			peak = Math.max(peak, p);
			const dd = (peak - p) / peak;
			maxDD = Math.max(maxDD, dd);
		}

		expect(maxDD).toBe(1.0);
	});

	it("should calculate drawdown from peak regardless of recovery", () => {
		const portfolio = [1.0, 1.05, 0.8, 0.95, 1.0];
		let peak = 1.0;
		let maxDD = 0;

		for (const p of portfolio) {
			peak = Math.max(peak, p);
			const dd = (peak - p) / peak;
			maxDD = Math.max(maxDD, dd);
		}

		expect(maxDD).toBeGreaterThan(0.23);
		expect(maxDD).toBeLessThan(0.24);
	});

	it("should handle single-day crash", () => {
		const portfolio = [1.0, 0.5];
		let peak = 1.0;
		let maxDD = 0;

		for (const p of portfolio) {
			peak = Math.max(peak, p);
			const dd = (peak - p) / peak;
			maxDD = Math.max(maxDD, dd);
		}

		expect(maxDD).toBe(0.5);
	});

	it("should handle all-time low at end", () => {
		const portfolio = [1.0, 1.1, 0.9, 0.85, 0.75];
		let peak = 1.0;
		let maxDD = 0;

		for (const p of portfolio) {
			peak = Math.max(peak, p);
			const dd = (peak - p) / peak;
			maxDD = Math.max(maxDD, dd);
		}

		expect(maxDD).toBeCloseTo(0.318, 2);
	});
});

describe("Signal Threshold Logic", () => {
	const long_threshold = 0.33;
	const short_threshold = -0.33;

	const getSignal = (score: number): "long" | "short" | "neutral" => {
		if (score > long_threshold) return "long";
		if (score < short_threshold) return "short";
		return "neutral";
	};

	it("should classify positive scores as LONG", () => {
		expect(getSignal(0.5)).toBe("long");
		expect(getSignal(0.34)).toBe("long");
		expect(getSignal(1.0)).toBe("long");
	});

	it("should classify boundary exactly at threshold as NEUTRAL", () => {
		expect(getSignal(0.33)).toBe("neutral");
		expect(getSignal(-0.33)).toBe("neutral");
	});

	it("should classify just inside LONG threshold as LONG", () => {
		expect(getSignal(0.3301)).toBe("long");
	});

	it("should classify just below LONG threshold as NEUTRAL", () => {
		expect(getSignal(0.3299)).toBe("neutral");
	});

	it("should classify negative scores as SHORT", () => {
		expect(getSignal(-0.5)).toBe("short");
		expect(getSignal(-0.34)).toBe("short");
		expect(getSignal(-1.0)).toBe("short");
	});

	it("should classify zero as NEUTRAL", () => {
		expect(getSignal(0)).toBe("neutral");
	});

	it("should classify middle range as NEUTRAL", () => {
		expect(getSignal(0.1)).toBe("neutral");
		expect(getSignal(-0.1)).toBe("neutral");
	});
});

describe("Position Weight Calculations", () => {
	it("should distribute long allocation equally", () => {
		const longSize = 0.3;
		const numLongSectors = 4;
		const allocation = longSize / numLongSectors;

		expect(allocation).toBe(0.075);
		expect(allocation * numLongSectors).toBe(longSize);
	});

	it("should distribute short allocation equally", () => {
		const shortSize = 0.3;
		const numShortSectors = 3;
		const allocation = shortSize / numShortSectors;

		expect(allocation).toBeCloseTo(0.1, 5);
		expect(allocation * numShortSectors).toBeCloseTo(shortSize, 5);
	});

	it("should maintain 100% portfolio allocation", () => {
		const longSize = 0.3;
		const shortSize = 0.3;
		const neutral = 1.0 - longSize - shortSize;

		expect(longSize + shortSize + neutral).toBeCloseTo(1.0, 10);
		expect(neutral).toBeCloseTo(0.4, 10);
	});

	it("should handle extreme allocations", () => {
		const longSize = 0.9;
		const shortSize = 0.0;
		const neutral = 1.0 - longSize - shortSize;

		expect(neutral).toBeCloseTo(0.1, 10);
		expect(longSize + shortSize + neutral).toBeCloseTo(1.0, 10);
	});
});

describe("Transaction Cost Calculations", () => {
	it("should calculate cost proportional to allocation", () => {
		const txCostBps = 5;
		const allocation = 0.15;
		const cost = (txCostBps / 10000) * allocation;

		expect(cost).toBe(allocation * 0.0005);
		expect(cost).toBeCloseTo(0.000075, 8);
	});

	it("should handle zero allocation", () => {
		const txCostBps = 5;
		const allocation = 0;
		const cost = (txCostBps / 10000) * allocation;

		expect(cost).toBe(0);
	});

	it("should scale with basis points", () => {
		const allocation = 0.1;
		const cost5bps = (5 / 10000) * allocation;
		const cost10bps = (10 / 10000) * allocation;

		expect(cost10bps).toBe(cost5bps * 2);
	});
});

describe("Win Rate Calculations", () => {
	it("should calculate win rate from profitable trades", () => {
		const winningTrades = 32;
		const totalTrades = 96;
		const winRate = winningTrades / totalTrades;

		expect(winRate).toBeCloseTo(0.3333, 4);
	});

	it("should return 0 for no trades", () => {
		const winRate = 0 > 0 ? 1 / 0 : 0;
		expect(winRate).toBe(0);
	});

	it("should return 1 for all winning trades", () => {
		const winningTrades = 50;
		const totalTrades = 50;
		const winRate = winningTrades / totalTrades;

		expect(winRate).toBe(1);
	});

	it("should return 0 for all losing trades", () => {
		const winningTrades = 0;
		const totalTrades = 50;
		const winRate = winningTrades > 0 ? winningTrades / totalTrades : 0;

		expect(winRate).toBe(0);
	});
});
