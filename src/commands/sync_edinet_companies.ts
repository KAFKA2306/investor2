import { Database } from "bun:sqlite";
import { readFileSync } from "node:fs";
import yaml from "js-yaml";

const config = yaml.load(readFileSync("config/default.yaml", "utf-8")) as any;
const apiKey = process.env.EDINET_API_KEY;

async function main() {
	console.log("\n" + "━".repeat(70));
	console.log("🏢 EDINET全企業データ取得開始");
	console.log("━".repeat(70) + "\n");

	if (!apiKey) {
		console.error("❌ エラー: EDINET_API_KEY 環境変数が設定されていません");
		process.exit(1);
	}

	const db = new Database(config.paths.cacheFundamentalEdinet);

	// Create cache table if not exists
	db.run(`
    CREATE TABLE IF NOT EXISTS http_cache (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )
  `);

	async function fetchWithCache(url: string) {
		const row = db
			.query("SELECT value FROM http_cache WHERE key = ?")
			.get(url) as { value: string } | undefined;
		if (row) return JSON.parse(row.value);

		console.log(`[FETCH] ${url}`);
		const response = await fetch(url);
		if (!response.ok) {
			if (response.status === 404) return null;
			throw new Error(`HTTP ${response.status}: ${url}`);
		}
		const data = await response.json();

		db.run(
			"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
			[url, JSON.stringify(data), Date.now()],
		);
		return data;
	}

	function getDates(days: number) {
		const dates = [];
		for (let i = 0; i < days; i++) {
			const d = new Date();
			d.setDate(d.getDate() - i);
			dates.push(d.toISOString().split("T")[0]);
		}
		return dates;
	}

	const dates = getDates(1095); // 3 years back
	console.log(`📅 取得期間: ${dates[dates.length - 1]} ～ ${dates[0]}`);
	console.log(`⏳ ${dates.length} 日分のドキュメント情報を取得中...\n`);

	const allDocs: any[] = [];
	let fetchedCount = 0;

	for (const date of dates) {
		const url = `https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`;
		const data = await fetchWithCache(url);

		if (data?.results && Array.isArray(data.results)) {
			allDocs.push(...data.results);
			fetchedCount++;
			if (fetchedCount % 10 === 0) {
				console.log(`  📊 進捗: ${fetchedCount}/${dates.length} 日処理完了...`);
			}
		}

		// Rate limit
		await new Promise((r) => setTimeout(r, 50));
	}

	console.log(
		`\n✅ 取得完了: ${allDocs.length.toLocaleString()} 件のドキュメント\n`,
	);

	// Group by company (edinet code)
	const byCompany = new Map<string, typeof allDocs>();
	for (const doc of allDocs) {
		const code = doc.edinetCode;
		if (!byCompany.has(code)) {
			byCompany.set(code, []);
		}
		byCompany.get(code)!.push(doc);
	}

	console.log(`🏛️  対象企業: ${byCompany.size.toLocaleString()} 社\n`);

	// Show top 30 companies by document count
	const sortedCompanies = Array.from(byCompany.entries())
		.sort((a, b) => b[1].length - a[1].length)
		.slice(0, 30);

	console.log("📊 企業別ドキュメント数（上位30）:");
	console.log("─".repeat(70));

	let rank = 1;
	for (const [code, docs] of sortedCompanies) {
		if (!code) continue;
		const docTypes = [...new Set(docs.map((d) => d.docTypeCode))].join(", ");
		console.log(
			`  ${rank.toString().padStart(2)} | ${(code || "N/A").padEnd(5)} | ${docs.length.toString().padStart(3)} 件 | ${docTypes.substring(0, 35)}`,
		);
		rank++;
	}

	console.log("\n" + "━".repeat(70));
	console.log(`📝 詳細:`);
	console.log(`  • 総ドキュメント数: ${allDocs.length.toLocaleString()}`);
	console.log(`  • カバー企業数: ${byCompany.size.toLocaleString()}`);
	console.log(
		`  • 平均ドキュメント/企業: ${(allDocs.length / byCompany.size).toFixed(1)}`,
	);
	console.log(`  • キャッシュ位置: ${config.paths.cacheFundamentalEdinet}`);
	console.log("━".repeat(70) + "\n");

	db.close();
}

main().catch(console.error);
