import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";

const config = yaml.load(readFileSync("config/default.yaml", "utf-8")) as any;

const dbPaths = [
	config.paths.cacheMarketsPolymarket,
	config.paths.cacheMarketsJquants,
	config.paths.cacheMarketsYahoo,
	config.paths.cacheFundamentalJquants,
	config.paths.cacheFundamentalEdinet,
	config.paths.cacheMacroEstat,
	config.paths.cacheMacroFred,
];

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

async function fetchWithCache(db: any, url: string, options: any = {}) {
	const row = db.query("SELECT value FROM http_cache WHERE key = ?").get(url) as
		| { value: string }
		| undefined;
	if (row) return JSON.parse(row.value);

	console.log(`[FETCH] ${url}`);
	const response = await fetch(url, options);
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
	const dates = getDates(365);

	console.log(`📡 [J-Quants v2] Syncing ${mode} (${dates.length} days)...`);

	if (mode === "markets") {
		await fetchWithCache(db, `${baseUrl}/equities/master`, { headers });
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
		}
	} else {
		for (const date of dates) {
			const d = date.replace(/-/g, "");
			await fetchWithCache(db, `${baseUrl}/fins/summary?date=${d}`, {
				headers,
			});
		}
	}
}

async function syncEdinet() {
	console.log("📡 [EDINET] Syncing historical documents (3 years backfill)...");
	const apiKey = process.env.EDINET_API_KEY;
	if (!apiKey) return;

	const db = dbs.fundamentalEdinet;
	const dates = getDates(1095);

	for (const date of dates) {
		await fetchWithCache(
			db,
			`https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`,
		);
		await new Promise((r) => setTimeout(r, 50));
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

	console.log("✨ [get:all] Unified historical acquisition complete.");
}

getAll();
