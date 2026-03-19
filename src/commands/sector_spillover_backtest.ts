import { parseArgs } from "node:util";
import { getSectorReturns, pivotToMatrix } from "../io/sector_data_fetcher";
import { RegularizedPCA, generateSpilloverSignals, getDefaultUSToJPMapping } from "../preprocess/sector_spillover";
import type { SectorSpilloverSignal, SpilloverBacktestResult } from "../schemas";
import { SpilloverBacktestResultSchema } from "../schemas";
import { config } from "./_config";

interface BacktestMetrics {
	totalReturnsPct: number;
	sharpeRatio: number;
	maxDrawdownPct: number;
	winRate: number;
	numTrades: number;
}

function simulateBacktest(
	signals: SectorSpilloverSignal[],
	returns: { dates: string[]; sectors: string[]; matrix: number[][] },
): BacktestMetrics {
	if (returns.matrix.length === 0 || signals.length === 0) {
		return {
			totalReturnsPct: 0,
			sharpeRatio: 0,
			maxDrawdownPct: 0,
			winRate: 0,
			numTrades: 0,
		};
	}

	const longSectors = signals.filter((s) => s.signal_type === "long").map((s) => s.jp_sector);
	const shortSectors = signals.filter((s) => s.signal_type === "short").map((s) => s.jp_sector);

	let portfolio = 1.0;
	let peak = 1.0;
	const dailyReturns: number[] = [];
	let totalTrades = 0;
	let winningTrades = 0;

	const longSize = config.sector_spillover?.backtest?.long_size ?? 0.3;
	const shortSize = config.sector_spillover?.backtest?.short_size ?? 0.3;
	const txCostBps = config.sector_spillover?.backtest?.transaction_cost_bps ?? 5;

	const sectorNames = returns.sectors;
	const sectorIndexMap = new Map(sectorNames.map((s, idx) => [s, idx]));

	for (let t = 0; t < returns.matrix.length; t++) {
		const dayReturns = returns.matrix[t];

		let dayPnL = 0;
		let dayAllocated = 0;

		// Long positions
		if (longSectors.length > 0) {
			const longAlloc = longSize / longSectors.length;
			for (const sector of longSectors) {
				const sectorIdx = sectorIndexMap.get(sector);
				if (sectorIdx !== undefined) {
					const ret = dayReturns[sectorIdx];
					const cost = (txCostBps / 10000) * longAlloc;
					dayPnL += longAlloc * ret - cost;
					dayAllocated += longAlloc;
					totalTrades++;
					if (ret > cost) {
						winningTrades++;
					}
				}
			}
		}

		// Short positions
		if (shortSectors.length > 0) {
			const shortAlloc = shortSize / shortSectors.length;
			for (const sector of shortSectors) {
				const sectorIdx = sectorIndexMap.get(sector);
				if (sectorIdx !== undefined) {
					const ret = dayReturns[sectorIdx];
					const cost = (txCostBps / 10000) * shortAlloc;
					dayPnL -= shortAlloc * ret - cost;
					dayAllocated += shortAlloc;
					totalTrades++;
					if (-ret > cost) {
						winningTrades++;
					}
				}
			}
		}

		// Add neutral allocation (cash residual)
		const neutralAlloc = 1.0 - dayAllocated;
		if (neutralAlloc > 0) {
			dayPnL += neutralAlloc * 0.0; // Cash doesn't earn anything
		}

		portfolio *= 1 + dayPnL;
		peak = Math.max(peak, portfolio);
		dailyReturns.push(dayPnL);
	}

	// Calculate metrics
	const totalReturnsPct = (portfolio - 1) * 100;
	const meanReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
	const variance = dailyReturns.reduce((a, r) => a + (r - meanReturn) ** 2, 0) / dailyReturns.length;
	const stddev = Math.sqrt(variance);
	const sharpeRatio = stddev > 0 ? (meanReturn / stddev) * Math.sqrt(252) : 0;

	const maxDrawdown = (peak - portfolio) / peak;
	const maxDrawdownPct = Math.max(0, maxDrawdown) * 100;
	const winRate = totalTrades > 0 ? winningTrades / totalTrades : 0;

	return {
		totalReturnsPct,
		sharpeRatio,
		maxDrawdownPct,
		winRate,
		numTrades: totalTrades,
	};
}

async function main() {
	const { positionals } = parseArgs({
		options: {
			from: { type: "string" },
			to: { type: "string" },
		},
		strict: false,
		allowPositionals: true,
	});

	const fromDate = positionals[0] || "2020-01-01";
	const toDate = positionals[1] || "2025-12-31";

	const sectorReturns = await getSectorReturns(fromDate, toDate);
	const { dates, sectors, matrix } = pivotToMatrix(sectorReturns);

	const pca = new RegularizedPCA(3, 0.1, 100);
	const { scores } = pca.fit(matrix);

	const usToJpMapping = getDefaultUSToJPMapping();
	const jpSectors = Object.keys(usToJpMapping);
	const signals = generateSpilloverSignals(scores, jpSectors, usToJpMapping);

	const metrics = simulateBacktest(signals, { dates, sectors, matrix });

	const result: SpilloverBacktestResult = {
		backtest_id: `backtest_${Date.now()}`,
		start_date: fromDate,
		end_date: toDate,
		total_returns_pct: metrics.totalReturnsPct,
		sharpe_ratio: metrics.sharpeRatio,
		max_drawdown_pct: metrics.maxDrawdownPct,
		win_rate: metrics.winRate,
		num_trades: metrics.numTrades,
		strategy_name: "Regularized PCA Sector Spillover (US -> JP)",
	};

	SpilloverBacktestResultSchema.parse(result);
	process.stdout.write(JSON.stringify(result, null, 2));
}

main();
