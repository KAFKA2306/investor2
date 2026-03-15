import { readFileSync, writeFileSync } from "node:fs";
import yaml from "js-yaml";

const config = yaml.load(readFileSync("config/default.yaml", "utf-8")) as any;
const apiKey = process.env.JQUANTS_API_KEY?.trim();

interface JquantsBar {
	Date: string;
	Open: number;
	High: number;
	Low: number;
	Close: number;
	Volume: number;
	AdjustmentFactor: number;
	AdjustmentOpen: number;
	AdjustmentHigh: number;
	AdjustmentLow: number;
	AdjustmentClose: number;
	AdjustmentVolume: number;
}

interface JquantsResponse {
	pagination: {
		current_page: number;
		next_page: string | null;
	};
	data: JquantsBar[];
}

async function main() {
	console.log("\n" + "━".repeat(70));
	console.log("📈 J-Quants 最新マーケットデータ取得");
	console.log("━".repeat(70) + "\n");

	if (!apiKey) {
		console.error("❌ エラー: JQUANTS_API_KEY 環境変数が設定されていません");
		process.exit(1);
	}

	const baseUrl = "https://api.jquants.com/v2";
	const headers = { "x-api-key": apiKey };

	// Get master data (stock list)
	console.log("📋 ステップ 1: 銘柄マスター取得中...");
	const masterResponse = await fetch(`${baseUrl}/equities/master`, {
		headers,
	});
	if (!masterResponse.ok) {
		console.error(
			`❌ マスターデータ取得失敗: ${masterResponse.status} ${masterResponse.statusText}`,
		);
		process.exit(1);
	}
	const masterData = (await masterResponse.json()) as {
		data: Array<{ Code: string; CompanyName: string }>;
	};
	const stocks = masterData.data;

	console.log(`✅ ${stocks.length.toLocaleString()} 銘柄取得\n`);

	// Get daily bars for past 2 years
	console.log("📊 ステップ 2: 過去2年の日足データ取得中...");

	const twoYearsAgo = new Date();
	twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
	const fromDate = twoYearsAgo.toISOString().split("T")[0];
	const toDate = new Date().toISOString().split("T")[0];

	console.log(`   期間: ${fromDate} ～ ${toDate}\n`);

	const allBars: Array<{
		code: string;
		date: string;
		close: number;
		volume: number;
	}> = [];
	let processedCount = 0;

	for (const stock of stocks) {
		const code = stock.Code;

		try {
			let url = `${baseUrl}/equities/bars/daily?code=${code}&from=${fromDate}&to=${toDate}&limit=100`;
			let hasNext = true;
			let retryCount = 0;
			const maxRetries = 3;

			while (hasNext) {
				const response = await fetch(url, { headers });

				// Handle rate limit (429)
				if (response.status === 429) {
					if (retryCount < maxRetries) {
						const waitTime = Math.pow(2, retryCount) * 5000; // 5s, 10s, 20s
						console.warn(
							`⚠️  ${code}: レート制限 (429) - ${waitTime}ms 待機中...`,
						);
						retryCount++;
						await new Promise((r) => setTimeout(r, waitTime));
						continue;
					} else {
						console.warn(`❌ ${code}: 最大再試行回数に達しました`);
						break;
					}
				}

				if (!response.ok) {
					console.warn(`⚠️  ${code}: ${response.status}`);
					break;
				}

				retryCount = 0; // Reset on success

				const data = (await response.json()) as JquantsResponse;

				// Process bars
				for (const bar of data.data) {
					allBars.push({
						code,
						date: bar.Date,
						close: bar.AdjustmentClose,
						volume: bar.AdjustmentVolume,
					});
				}

				// Check for next page
				if (data.pagination.next_page) {
					url = data.pagination.next_page;
				} else {
					hasNext = false;
				}
			}

			processedCount++;
			if (processedCount % 100 === 0) {
				console.log(
					`   進捗: ${processedCount}/${stocks.length} 銘柄処理完了...`,
				);
			}

			// Rate limit: 100ms per stock, plus exponential backoff for 429
			await new Promise((r) => setTimeout(r, 500));
		} catch (error) {
			console.warn(`⚠️  ${code}: エラー発生`);
		}
	}

	console.log(
		`\n✅ ${allBars.length.toLocaleString()} 件のバーデータ取得完了\n`,
	);

	// Save to CSV
	console.log("💾 ステップ 3: CSVファイル保存中...");

	const csvPath = `${config.paths.data}/raw_stock_price_latest.csv`;
	let csvContent = "Code,Date,Close,Volume\n";
	for (const bar of allBars) {
		csvContent += `${bar.code},${bar.date},${bar.close},${bar.volume}\n`;
	}

	writeFileSync(csvPath, csvContent);
	console.log(`✅ 保存完了: ${csvPath}\n`);

	// Summary
	console.log("━".repeat(70));
	console.log("📝 詳細:");
	console.log(`  • 銘柄数: ${stocks.length.toLocaleString()}`);
	console.log(`  • バーデータ: ${allBars.length.toLocaleString()} 件`);
	console.log(`  • 期間: ${fromDate} ～ ${toDate}`);
	console.log(`  • 保存先: ${csvPath}`);
	console.log("━".repeat(70) + "\n");
}

main().catch(console.error);
