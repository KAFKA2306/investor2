import { getCompanyDetail, getCompanyList } from "../preprocess/edinet";

async function runSwarmResearch() {
	console.log(
		"🔍 [Research 3] Starting Alpha Swarm Integration (Macro x Micro)...",
	);

	// Mock Macro Signals from Sector Spillover (e.g., Food sector is STRONG LONG, Chemicals is STRONG SHORT)
	const macroSignals: Record<string, number> = {
		食料品: 1.5,
		化学: -2.0,
		"水産・農林業": 1.2,
		電気機器: 0.5,
	};

	const companies = await getCompanyList(300, 0);
	const swarmSignals = [];

	for (const comp of companies) {
		const detail = await getCompanyDetail(comp.edinetCode, true);
		if (!detail) continue;
		const sector = detail.sector || "Unknown";

		// 1. Get Macro Score
		const macroScore = macroSignals[sector] || 0;

		if (macroScore !== 0) {
			// 2. Get Micro Quality Score (EPS)
			let microQuality = 0;
			const fin = detail.financial;
			if (fin && Array.isArray(fin) && fin.length >= 2) {
				const sortedFin = fin.sort((a, b) =>
					(b.periodEnd || "").localeCompare(a.periodEnd || ""),
				);
				if (sortedFin[0].eps && sortedFin[1].eps) {
					microQuality =
						(sortedFin[0].eps - sortedFin[1].eps) / Math.abs(sortedFin[1].eps);
				}
			}

			// 3. Get Micro Sentiment Score (NLP)
			let nlpRisk = 0;
			const risksText = detail.overview?.risks;
			if (risksText) {
				const matches = risksText.match(/リスク|悪化|懸念/g);
				nlpRisk = matches ? (matches.length / risksText.length) * 1000 : 0;
			}

			// The Swarm Logic: If Macro says LONG, we want High Quality and Low Risk.
			// If Macro says SHORT, we want Low Quality and High Risk.
			const normalizedMicro = microQuality * 10 - nlpRisk * 0.1;
			const finalSwarmScore = macroScore * (1 + normalizedMicro);

			swarmSignals.push({
				code: comp.edinetCode,
				name: detail.name,
				sector,
				macroSignal: macroScore > 0 ? "🟢 LONG" : "🔴 SHORT",
				microQuality: `${(microQuality * 100).toFixed(1)}%`,
				nlpRiskScore: nlpRisk.toFixed(1),
				finalSwarmScore: finalSwarmScore.toFixed(3),
			});
		}
	}

	// Sort by absolute conviction (strongest longs and shorts)
	swarmSignals.sort(
		(a, b) =>
			Math.abs(parseFloat(b.finalSwarmScore)) -
			Math.abs(parseFloat(a.finalSwarmScore)),
	);
	const topSwarm = swarmSignals.slice(0, 15);

	console.log(
		"\n🌪️ Top 15 Alpha Swarm Targets (Macro Overlay + Fundamental + NLP):",
	);
	console.table(topSwarm);
	console.log("✅ [Research 3] Alpha Swarm Integration Complete.");
}

runSwarmResearch();
