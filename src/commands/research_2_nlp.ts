import { getCompanyDetail, getCompanyList } from "../preprocess/edinet";

async function runNlpResearch() {
	console.log(
		"🔍 [Research 2] Starting NLP Sentiment Analysis on Risk Factors...",
	);

	const companies = await getCompanyList(100, 0); // Check first 100 companies for speed
	const negativeKeywords = [
		"リスク",
		"悪化",
		"減少",
		"懸念",
		"不透明",
		"低下",
		"損失",
		"影響",
		"遅延",
	];
	const riskScores = [];

	for (const comp of companies) {
		const detail = await getCompanyDetail(comp.edinetCode, true); // true to include XBRL texts
		if (!detail) continue;

		const risksText = detail.overview?.risks;

		if (risksText && risksText.length > 50) {
			let negativeCount = 0;
			for (const word of negativeKeywords) {
				const regex = new RegExp(word, "g");
				const matches = risksText.match(regex);
				if (matches) {
					negativeCount += matches.length;
				}
			}

			// Normalize by text length (per 1000 characters)
			const riskScore = (negativeCount / risksText.length) * 1000;

			riskScores.push({
				code: comp.edinetCode,
				name: detail.name,
				sector: detail.sector || "Unknown",
				textLength: risksText.length,
				negativeCount,
				riskScore: riskScore.toFixed(2),
			});
		}
	}

	// Sort by highest risk score
	riskScores.sort((a, b) => parseFloat(b.riskScore) - parseFloat(a.riskScore));
	const mostRisky = riskScores.slice(0, 10);

	console.log("\n⚠️ Top 10 High-Risk Sentiment Stocks (EDINET NLP):");
	console.table(mostRisky);
	console.log("✅ [Research 2] NLP Sentiment Analysis Complete.");
}

runNlpResearch();
