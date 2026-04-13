import { getCompanyDetail, getCompanyList } from "../preprocess/edinet";

async function runQualityResearch() {
	console.log("🔍 [Research 1] Starting Financial Quality Filter Analysis...");

	const companies = await getCompanyList(500, 0); // Check first 500 companies
	const validCompanies = [];

	for (const comp of companies) {
		const detail = await getCompanyDetail(comp.edinetCode, false);
		if (!detail) continue;

		const fin = detail.financial;

		if (fin && Array.isArray(fin) && fin.length >= 2) {
			// Sort by date descending
			const sortedFin = fin.sort((a, b) =>
				(b.periodEnd || "").localeCompare(a.periodEnd || ""),
			);
			const latest = sortedFin[0];
			const previous = sortedFin[1];

			if (latest.eps && previous.eps && latest.bps) {
				const epsGrowth = (latest.eps - previous.eps) / Math.abs(previous.eps);
				const _pbr = 1.0; // Assume PBR proxy if market price is missing, or just use BPS as value indicator
				// Simplified quality score: EPS Growth * BPS
				const qualityScore = epsGrowth * latest.bps;

				validCompanies.push({
					code: comp.edinetCode,
					name: detail.name,
					sector: detail.sector || "Unknown",
					epsGrowth: `${(epsGrowth * 100).toFixed(2)}%`,
					bps: latest.bps,
					qualityScore,
				});
			}
		}
	}

	validCompanies.sort((a, b) => b.qualityScore - a.qualityScore);
	const top10 = validCompanies.slice(0, 10);

	console.log("\n🏆 Top 10 High-Quality Stocks (EPS Growth + Value):");
	console.table(top10);
	console.log("✅ [Research 1] Financial Quality Filter Analysis Complete.");
}

runQualityResearch();
