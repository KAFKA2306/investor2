import { parseArgs } from "node:util";
import { BacktestCache } from "../io/backtest_cache";
import { getSectorReturns, pivotToMatrix } from "../io/sector_data_fetcher";
import {
	generateSpilloverSignals,
	getDefaultUSToJPMapping,
	RegularizedPCA,
} from "../preprocess/sector_spillover";
import type {
	SectorSpilloverSignal,
	SpilloverBacktestResult,
} from "../schemas";
import { SpilloverBacktestResultSchema } from "../schemas";
import { config } from "./_config";

interface BacktestMetrics {
	totalReturnsPct: number;
	taxPaidPct: number;
	netReturnsPct: number;
	sharpeRatio: number;
	maxDrawdownPct: number;
	winRate: number;
	numTrades: number;
	numWinningTrades: number;
	numLosingTrades: number;
}

function simulateBacktest(
	signals: SectorSpilloverSignal[],
	returns: { dates: string[]; sectors: string[]; matrix: number[][] },
): BacktestMetrics {
	if (returns.matrix.length === 0 || signals.length === 0) {
		return {
			totalReturnsPct: 0,
			taxPaidPct: 0,
			netReturnsPct: 0,
			sharpeRatio: 0,
			maxDrawdownPct: 0,
			winRate: 0,
			numTrades: 0,
			numWinningTrades: 0,
			numLosingTrades: 0,
		};
	}

	let portfolio = 1.0;
	let peak = 1.0;
	let maxDrawdownTracker = 0;
	const dailyReturns: number[] = [];
	let totalTrades = 0;
	let winningTrades = 0;

	// 現在のポジション管理 (sectorCode -> { direction, entryAlloc, cumulativePnL })
	const currentPositions = new Map<
		string,
		{ dir: number; alloc: number; pnl: number }
	>();

	const longSize = config.sector_spillover?.backtest?.long_size ?? 0.3;
	const shortSize = config.sector_spillover?.backtest?.short_size ?? 0.3;
	const txCostBps =
		config.sector_spillover?.backtest?.transaction_cost_bps ?? 50;

	const sectorNames = returns.sectors;
	const sectorIndexMap = new Map(sectorNames.map((s, idx) => [s, idx]));

	for (let t = 0; t < returns.matrix.length; t++) {
		const dayReturns = returns.matrix[t];
		const longSectors = signals
			.filter((s) => s.signal_type === "long")
			.map((s) => s.jp_sector);
		const shortSectors = signals
			.filter((s) => s.signal_type === "short")
			.map((s) => s.jp_sector);

		let dayPnL = 0;

		const nextPositions = new Map<string, number>();
		for (const s of longSectors) nextPositions.set(s, 1);
		for (const s of shortSectors) nextPositions.set(s, -1);

		// 1. 決済・入れ替えの判定
		for (const [sector, pos] of currentPositions) {
			const nextDir = nextPositions.get(sector);
			if (nextDir !== pos.dir) {
				// 決済コスト
				dayPnL -= (txCostBps / 10000) * pos.alloc;
				totalTrades++;
				if (pos.pnl > (txCostBps / 10000) * pos.alloc) winningTrades++;
				currentPositions.delete(sector);
			}
		}

		// 2. 新規エントリー
		for (const [sector, dir] of nextPositions) {
			if (!currentPositions.has(sector)) {
				const alloc =
					dir === 1
						? longSize / Math.max(1, longSectors.length)
						: shortSize / Math.max(1, shortSectors.length);
				dayPnL -= (txCostBps / 10000) * alloc;
				currentPositions.set(sector, { dir, alloc, pnl: 0 });
				totalTrades++; // ここで確実にカウント
			}
		}

		// 3. 損益計算と累積 (保有中ポジション)
		for (const [sector, pos] of currentPositions) {
			const sectorIdx = sectorIndexMap.get(sector);
			if (sectorIdx !== undefined) {
				const ret = (dayReturns[sectorIdx] / 100) * pos.dir;
				const dayGain = pos.alloc * ret;
				dayPnL += dayGain;
				pos.pnl += dayGain; // このトレードの累積損益を更新
			}
		}

		portfolio *= 1 + dayPnL;
		peak = Math.max(peak, portfolio);
		maxDrawdownTracker = Math.max(
			maxDrawdownTracker,
			(peak - portfolio) / peak,
		);
		dailyReturns.push(dayPnL);
	}

	// 最終日に残っているポジションをクローズ扱いにする
	for (const [_, pos] of currentPositions) {
		if (pos.pnl > 0) winningTrades++;
	}
	// totalTradesは新規エントリー時にのみカウントするようにし、二重計上を防ぐロジックへ。

	const totalReturnsPct = (portfolio - 1) * 100;
	// 税金計算 (利益が出ている場合のみ20%)
	const taxPaidPct = totalReturnsPct > 0 ? totalReturnsPct * 0.2 : 0;
	const netReturnsPct = totalReturnsPct - taxPaidPct;

	const meanReturn =
		dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
	const variance =
		dailyReturns.reduce((a, r) => a + (r - meanReturn) ** 2, 0) /
		dailyReturns.length;
	const stddev = Math.sqrt(variance);
	const sharpeRatio = stddev > 0 ? (meanReturn / stddev) * Math.sqrt(252) : 0;

	return {
		totalReturnsPct,
		taxPaidPct,
		netReturnsPct,
		sharpeRatio,
		maxDrawdownPct: maxDrawdownTracker * 100,
		winRate: totalTrades > 0 ? winningTrades / totalTrades : 0,
		numTrades: totalTrades,
		numWinningTrades: winningTrades,
		numLosingTrades: totalTrades - winningTrades,
	};
}

async function main() {
	const { values } = parseArgs({
		options: {
			from: { type: "string" },
			to: { type: "string" },
			hypothesis: { type: "string" },
		},
		strict: false,
	});

	const fromDate = (values.from as string) || "2020-01-01";
	const toDate = (values.to as string) || "2025-12-31";
	const hypothesisId = (values.hypothesis as string) || "default";

	const sectorReturns = await getSectorReturns(fromDate, toDate);

	const { dates, sectors, matrix } = pivotToMatrix(sectorReturns, hypothesisId);

	const pca = new RegularizedPCA(3, 0.1, 100);
	const { scores } = pca.fit(matrix);

	// Extract US sector returns for signal generation
	const usSectorNames = config.sector_spillover?.us_sectors ?? [];
	const usIndices = usSectorNames
		.map((name) => sectors.indexOf(name))
		.filter((i) => i !== -1);
	const usReturnsMatrix = matrix.map((row) => usIndices.map((i) => row[i]));

	const usToJpMapping = getDefaultUSToJPMapping();
	const jpSectors = Object.keys(usToJpMapping);
	// 実証済みのセクター別方向性を適用 (Overnightのみ)
	const isOptimized = hypothesisId === "overnight";
	const signals = generateSpilloverSignals(
		usReturnsMatrix,
		scores,
		jpSectors,
		usToJpMapping,
		isOptimized,
	);

	const metrics = simulateBacktest(signals, { dates, sectors, matrix });

	// Calculate per-sector performance for the dashboard
	const sectorPerformance = jpSectors
		.map((jpSector) => {
			const idx = sectors.indexOf(jpSector);
			if (idx === -1) return null;

			const sectorReturns = matrix.map((row) => row[idx]);
			const avgReturn =
				sectorReturns.reduce((a, b) => a + b, 0) / sectorReturns.length;
			const variance =
				sectorReturns.reduce((a, r) => a + (r - avgReturn) ** 2, 0) /
				sectorReturns.length;
			const stddev = Math.sqrt(variance);
			const winRate =
				sectorReturns.filter((r) => r > 0).length / sectorReturns.length;

			return {
				jp_sector: jpSector,
				avg_return: avgReturn,
				volatility: stddev,
				sharpe: stddev > 0 ? (avgReturn / stddev) * Math.sqrt(252) : 0,
				win_rate: winRate,
			};
		})
		.filter((s): s is NonNullable<typeof s> => s !== null);

	const result: SpilloverBacktestResult = {
		backtest_id: `backtest_${Date.now()}`,
		hypothesis_id: hypothesisId,
		start_date: fromDate,
		end_date: toDate,
		total_returns_pct: metrics.totalReturnsPct,
		tax_paid_pct: metrics.taxPaidPct,
		net_returns_pct: metrics.netReturnsPct,
		sharpe_ratio: metrics.sharpeRatio,
		max_drawdown_pct: metrics.maxDrawdownPct,
		win_rate: metrics.winRate,
		num_trades: metrics.numTrades,
		num_winning_trades: metrics.numWinningTrades,
		num_losing_trades: metrics.numLosingTrades,
		strategy_name: "Regularized PCA Sector Spillover (US -> JP)",
		sector_performance: sectorPerformance,
	};

	SpilloverBacktestResultSchema.parse(result);

	const backtest_cache = new BacktestCache(config.paths.cacheBacktestResults);
	backtest_cache.saveResult(result);

	process.stdout.write(JSON.stringify(result, null, 2));
}

main();
