import { getSectorReturns, pivotToMatrix } from "../io/sector_data_fetcher";
import { getStockPriceHistory } from "../io/stock_data_fetcher";
import {
	generateSpilloverSignals,
	getDefaultUSToJPMapping,
	RegularizedPCA,
} from "../preprocess/sector_spillover";
import { config } from "./_config";

async function verifyAlphaSwarm() {
	console.log(
		"🚀 [Alpha Swarm Verification] Starting Deep Empirical Research...",
	);

	const fromDate = "2024-01-03";
	const toDate = "2024-06-28";
	const TX_COST = 0.005; // 50bps
	const TAX = 0.2;

	// 1. Get Macro Signals (US -> JP Sectors)
	const sectorReturns = await getSectorReturns(fromDate, toDate);
	const { dates, sectors, matrix } = pivotToMatrix(sectorReturns, "default");
	const pca = new RegularizedPCA(3, 0.1, 100);
	const { scores } = pca.fit(matrix);
	const usSectorNames = config.sector_spillover?.us_sectors ?? [];
	const usIndices = usSectorNames
		.map((name) => sectors.indexOf(name))
		.filter((i) => i !== -1);
	const usReturnsMatrix = matrix.map((row) => usIndices.map((i) => row[i]));
	const usToJpMapping = getDefaultUSToJPMapping();
	const jpSectors = Object.keys(usToJpMapping);

	// signals[date][sector]
	const allSignalsByDate = dates.map((_d, idx) => {
		const dayUSReturns = usReturnsMatrix.slice(0, idx + 1);
		const dayPCAScores = scores.slice(0, idx + 1);
		return generateSpilloverSignals(
			dayUSReturns,
			dayPCAScores,
			jpSectors,
			usToJpMapping,
			true,
		);
	});

	// 2. Define Alpha Targets (High Swarm Score Stocks identified in parallel research)
	const targets = [
		{ code: "1333", name: "マルハニチロ", sector: "1000", expected: "LONG" },
		{ code: "4188", name: "三菱ケミカル", sector: "7000", expected: "SHORT" },
	];

	const results = [];

	for (const target of targets) {
		console.log(`\n🔍 Analyzing Target: ${target.name} (${target.code})...`);
		const history = await getStockPriceHistory(target.code, fromDate, toDate);

		if (history.length === 0) {
			console.log(`❌ No price data for ${target.code}`);
			continue;
		}

		let portfolio = 1.0;
		let totalTrades = 0;
		let winningTrades = 0;
		let currentPos = 0; // 1 for LONG, -1 for SHORT, 0 for None
		let entryPrice = 0;

		for (let i = 0; i < history.length; i++) {
			const bar = history[i];
			const daySignals = allSignalsByDate[i];
			const signal = daySignals.find((s) => s.jp_sector === target.sector);

			if (!signal) continue;

			// Signal logic: Focus ONLY on high confidence direction
			const desiredPos =
				signal.signal_type === "long"
					? 1
					: signal.signal_type === "short"
						? -1
						: 0;

			// Trade execution (at Open next day or current Close)
			if (desiredPos !== currentPos) {
				// Close previous
				if (currentPos !== 0) {
					const exitPrice = bar.open; // Exit at Open
					const tradeReturn =
						currentPos === 1
							? exitPrice / entryPrice - 1
							: entryPrice / exitPrice - 1;
					const netReturn = tradeReturn - TX_COST; // Apply 50bps
					portfolio *= 1 + netReturn;
					if (netReturn > 0) winningTrades++;
					totalTrades++;
				}

				// Open new
				if (desiredPos !== 0) {
					entryPrice = bar.open;
					currentPos = desiredPos;
				} else {
					currentPos = 0;
				}
			}
		}

		const totalReturn = (portfolio - 1) * 100;
		const taxPaid = totalReturn > 0 ? totalReturn * TAX : 0;
		const netReturn = totalReturn - taxPaid;

		results.push({
			Stock: target.name,
			Code: target.code,
			Trades: totalTrades,
			WinRate:
				totalTrades > 0
					? `${((winningTrades / totalTrades) * 100).toFixed(1)}%`
					: "0%",
			TotalReturn: `${totalReturn.toFixed(2)}%`,
			NetReturn: `${netReturn.toFixed(2)}%`,
			Status: netReturn > 0 ? "✅ ALPHA PROVEN" : "❌ NO ALPHA",
		});
	}

	console.log("\n📊 FINAL ALPHA SWARM EMPIRICAL VERIFICATION:");
	console.table(results);
}

verifyAlphaSwarm();
