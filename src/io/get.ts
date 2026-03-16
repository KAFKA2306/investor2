import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const dbPaths = [
	config.paths.cacheMarketsPolymarket,
	config.paths.cacheMarketsJquants,
	config.paths.cacheMarketsYahoo,
	config.paths.cacheFundamentalJquants,
	config.paths.cacheFundamentalEdinet,
	config.paths.cacheMacroEstat,
	config.paths.cacheMacroFred,
].filter((p): p is string => !!p);

for (const path of dbPaths) {
	mkdirSync(dirname(path), { recursive: true });
}

const dbs = {
	marketsPolymarket: new Database(config.paths.cacheMarketsPolymarket),
	marketsJquants: new Database(config.paths.cacheMarketsJquants),
	marketsYahoo: new Database(config.paths.cacheMarketsYahoo),
	fundamentalJquants: new Database(config.paths.cacheFundamentalJquants),
	fundamentalEdinet: new Database(config.paths.cacheFundamentalEdinet),
	macroEstat: new Database(config.paths.cacheMacroEstat),
	macroFred: new Database(
		config.paths.macroFred || config.paths.cacheMacroFred,
	),
};

Object.values(dbs).forEach((db) => {
	db.run(`
    CREATE TABLE IF NOT EXISTS http_cache (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )
  `);
});

async function fetchWithCache(
	db: Database,
	url: string,
	options: RequestInit = {},
) {
	const row = db.query("SELECT value FROM http_cache WHERE key = ?").get(url) as
		| { value: string }
		| undefined;
	if (row) return JSON.parse(row.value);

	console.log(`[FETCH] ${url}`);
	const response = await fetch(url, options);
	if (!response.ok) {
		if (
			response.status === 404 ||
			response.status === 400 ||
			response.status === 403
		)
			return null;
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

async function syncPolymarket() {
	console.log("📡 [Polymarket] Syncing all active markets (Backfill)...");
	const clobUrl = config.polymarket.clob_url;
	const db = dbs.marketsPolymarket;
	const gammaUrl = "https://gamma-api.polymarket.com";

	for (let offset = 0; offset < 500; offset += 100) {
		await fetchWithCache(
			db,
			`${gammaUrl}/markets?active=true&closed=false&limit=100&offset=${offset}`,
		);
	}
	await fetchWithCache(db, `${clobUrl}/sampling-markets?active=true`);
}

async function syncJquants(mode: "markets" | "fundamental") {
	const apiKey = process.env.JQUANTS_API_KEY?.trim();
	if (!apiKey) {
		console.warn("⚠️  [J-Quants] JQUANTS_API_KEY not set. Skipping.");
		return;
	}

	const db = mode === "markets" ? dbs.marketsJquants : dbs.fundamentalJquants;
	const baseUrl = "https://api.jquants.com/v2";
	const headers = { "x-api-key": apiKey };

	const now = new Date();
	const to = now.toISOString().split("T")[0];
	const backfillDays = mode === "markets" ? 730 : 365; // Markets: 2y, Fundamental: 1y
	const from = new Date(now.getTime() - backfillDays * 24 * 60 * 60 * 1000)
		.toISOString()
		.split("T")[0];

	console.log(`📡 [J-Quants v2] Syncing ${mode} Bulk (${from} ～ ${to})...`);

	if (mode === "markets") {
		// Master
		await fetchWithCache(db, `${baseUrl}/equities/master`, { headers });

		// Bulk Prices: Group by code if necessary, or fetch daily for topix?
		// Note: J-Quants v2 daily is more efficient for all symbols.
		const dates = getDates(backfillDays);
		for (const date of dates) {
			const d = date.replace(/-/g, "");
			await fetchWithCache(db, `${baseUrl}/equities/bars/daily?date=${d}`, {
				headers,
			});
			await fetchWithCache(
				db,
				`${baseUrl}/indices/bars/daily/topix?date=${d}`,
				{ headers },
			);
			// Rate limit: ~2 requests per second to avoid 429
			await new Promise((r) => setTimeout(r, 500));
		}

		// Export CSV for the "latest" consumers
		await exportJquantsToCsv(db);
	} else {
		const dates = getDates(365);
		for (const date of dates) {
			const d = date.replace(/-/g, "");
			await fetchWithCache(db, `${baseUrl}/fins/summary?date=${d}`, {
				headers,
			});
		}
	}
}

async function exportJquantsToCsv(db: Database) {
	console.log("💾 [J-Quants] Exporting latest prices to CSV...");
	const csvPath = `${config.paths.data}/raw_stock_price_latest.csv`;

	// We gather all bars from recent daily bar JSONs in cache
	// 500 dates should cover ~2 years of trading days
	const rows = db
		.query(
			"SELECT key, value FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
		)
		.all() as Array<{ key: string; value: string }>;

	let csvContent = "Code,Date,Close,Volume\n";
	for (const row of rows) {
		const data = JSON.parse(row.value);
		if (!data.data) continue;
		for (const bar of data.data) {
			csvContent += `${bar.Code},${bar.Date},${bar.AdjustmentClose},${bar.AdjustmentVolume}\n`;
		}
	}

	mkdirSync(dirname(csvPath), { recursive: true });
	writeFileSync(csvPath, csvContent);
	console.log(`✅ [J-Quants] CSV Exported: ${csvPath}`);
}

async function syncEdinet() {
	console.log("📡 [EDINET] Syncing historical documents (3 years backfill)...");
	const apiKey = process.env.EDINET_API_KEY;
	if (!apiKey) return;

	const db = dbs.fundamentalEdinet;
	const dates = getDates(1095);

	let _allDocsFoundCount = 0;
	const byCompany = new Map<string, unknown[]>();

	for (const date of dates) {
		const url = `https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`;
		const data = await fetchWithCache(db, url);

		if (data?.results) {
			_allDocsFoundCount += data.results.length;
			for (const doc of data.results) {
				const code = doc.edinetCode;
				if (code) {
					if (!byCompany.has(code)) byCompany.set(code, []);
					byCompany.get(code)?.push(doc);
				}
			}
		}
		await new Promise((r) => setTimeout(r, 50));
	}

	// Ranking Output
	console.log(`\n🏢 [EDINET] Unified Ranking (Top 10):`);
	const sorted = Array.from(byCompany.entries())
		.sort((a, b) => b[1].length - a[1].length)
		.slice(0, 10);
	sorted.forEach(([code, docs], i) => {
		console.log(`  ${i + 1}. ${code}: ${docs.length} docs`);
	});
}

async function syncEdinetXbrl() {
	console.log(
		"📡 [EDINET XBRL] Downloading XBRL files for recent documents...",
	);
	const apiKey = process.env.EDINET_API_KEY;
	if (!apiKey) return;

	const db = dbs.fundamentalEdinet;
	const dates = getDates(365);

	for (const date of dates) {
		const cacheKey = `https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`;
		const row = db
			.query("SELECT value FROM http_cache WHERE key = ?")
			.get(cacheKey) as { value: string } | undefined;

		if (!row) continue;

		const metadata = JSON.parse(row.value);
		if (!metadata.results?.length) continue;

		for (const doc of metadata.results) {
			const docID = doc.docID;
			const xbrlUrl = `https://api.edinet-fsa.go.jp/api/v2/documents/${docID}?type=1&Subscription-Key=${apiKey}`;

			const existingRow = db
				.query("SELECT value FROM http_cache WHERE key = ?")
				.get(xbrlUrl) as { value: string } | undefined;

			if (existingRow) continue;

			try {
				const response = await fetch(xbrlUrl);
				if (!response.ok) {
					if (response.status === 404) continue;
					throw new Error(`HTTP ${response.status}: ${xbrlUrl}`);
				}

				const xbrlContent = await response.text();
				db.run(
					"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
					[xbrlUrl, JSON.stringify({ content: xbrlContent }), Date.now()],
				);

				console.log(`✓ [XBRL] ${docID}`);
				await new Promise((r) => setTimeout(r, 300));
			} catch (error) {
				console.warn(`⚠️  [XBRL] Failed for ${docID}: ${error}`);
			}
		}
	}
}

async function syncYahoo() {
	console.log("📡 [Yahoo Finance] Syncing full history (Max Range)...");
	const db = dbs.marketsYahoo;
	const symbols = [
		"^N225",
		"^TOPX",
		"^GSPC",
		"^VIX",
		"USDJPY=X",
		"EURUSD=X",
		"CL=F",
		"GC=F",
	];

	for (const symbol of symbols) {
		await fetchWithCache(
			db,
			`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=max`,
		);
	}
}

async function syncEstat() {
	console.log("📡 [e-Stat] Syncing macro statistics...");
	const appId = process.env.ESTAT_APP_ID;
	if (!appId) return;
	const db = dbs.macroEstat;
	const ids = ["0003411475", "0003103532", "0003060843"];
	for (const id of ids) {
		await fetchWithCache(
			db,
			`https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?appId=${appId}&statsDataId=${id}`,
		);
	}
}

async function syncFred() {
	const apiKey = process.env.FRED_API_KEY;
	if (!apiKey) return;
	console.log("📡 [FRED] Syncing historical US macro data...");
	const db = dbs.macroFred;
	const seriesIds = ["FEDFUNDS", "DGS10", "CPIAUCSL", "UNRATE", "T10YIE"];
	for (const seriesId of seriesIds) {
		await fetchWithCache(
			db,
			`https://api.stlouisfed.org/fred/series/observations?series_id=${seriesId}&api_key=${apiKey}&file_type=json`,
		);
	}
}

async function getAll() {
	const mode = process.env.GET_MODE || "all";

	if (mode === "edinet") {
		console.log("🚀 [get:edinet] Starting EDINET Sync...");
		await syncEdinet();
		await syncEdinetXbrl();
		return;
	}

	if (mode === "jquants") {
		console.log("🚀 [get:jquants] Starting J-Quants Sync...");
		await syncJquants("markets");
		await syncJquants("fundamental");
		return;
	}

	if (mode === "xbrl-only") {
		console.log("🚀 [get:xbrl] Starting EDINET XBRL-Only Acquisition...");
		await syncEdinet();
		await syncEdinetXbrl();
		console.log("✨ [get:xbrl] EDINET XBRL acquisition complete.");
		return;
	}

	console.log(
		"🚀 [get:all] Starting Unified Historical Acquisition (v2 Ready)...",
	);

	await Promise.allSettled([
		syncPolymarket(),
		syncYahoo(),
		syncEstat(),
		syncFred(),
	]);

	await syncJquants("markets");
	await syncJquants("fundamental");
	await syncEdinet();

	if (mode !== "skip-xbrl") {
		await syncEdinetXbrl();
	}

	console.log("✨ [get:all] Unified historical acquisition complete.");
}

getAll();
