import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../schemas";

interface TavilyResponse {
	results: Array<{
		title: string;
		url: string;
		content: string;
		source: string;
		score: number;
	}>;
	query: string;
}

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

async function initWebSearchDb(dbPath: string): Promise<Database> {
	mkdirSync(dirname(dbPath), { recursive: true });
	const db = new Database(dbPath);
	db.run(
		"CREATE TABLE IF NOT EXISTS websearch_cache (key TEXT PRIMARY KEY, query TEXT NOT NULL, results TEXT NOT NULL, created_at INTEGER NOT NULL, source TEXT DEFAULT 'tavily')",
	);
	return db;
}

async function searchWithTavily(query: string): Promise<TavilyResponse> {
	const apiKey = process.env.TAVILY_API_KEY?.trim();
	const maxResults = config.providers?.tavily?.maxResults || 5;
	const response = await fetch("https://api.tavily.com/search", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			api_key: apiKey,
			query,
			max_results: maxResults,
			include_domains: ["edinet-fsa.go.jp", "jquants.com", "nikkei.com"],
		}),
	});
	if (!response.ok) throw new Error(`Tavily API error: ${response.status}`);
	return (await response.json()) as TavilyResponse;
}

async function cacheWebSearch(
	db: Database,
	query: string,
	results: TavilyResponse,
): Promise<void> {
	db.run(
		"INSERT OR REPLACE INTO websearch_cache (key, query, results, created_at, source) VALUES (?, ?, ?, ?, ?)",
		[
			query.toLowerCase().replace(/\s+/g, "_"),
			query,
			JSON.stringify(results),
			Date.now(),
			"tavily",
		],
	);
}

async function getCachedSearch(
	db: Database,
	query: string,
): Promise<TavilyResponse | null> {
	const row = db
		.query(
			"SELECT results FROM websearch_cache WHERE query = ? ORDER BY created_at DESC LIMIT 1",
		)
		.get(query) as { results: string } | undefined;
	return row ? JSON.parse(row.results) : null;
}

async function syncWebSearch(queries: string[]): Promise<void> {
	const dbPath = config.paths.cacheWebSearch;
	if (!dbPath) throw "MISSING_WEBSEARCH_CACHE_PATH";
	const db = await initWebSearchDb(dbPath);
	for (const query of queries) {
		const cached = await getCachedSearch(db, query);
		if (cached) continue;
		const results = await searchWithTavily(query);
		await cacheWebSearch(db, query, results);
		await new Promise((r) => setTimeout(r, 1000));
	}
	db.close();
}

async function main() {
	const mode = process.env.WEBSEARCH_MODE || "default";
	if (mode === "query") {
		const q = process.env.WEBSEARCH_QUERY;
		if (!q) throw "MISSING_QUERY";
		await syncWebSearch([q]);
		return;
	}
	await syncWebSearch([
		"日本株 最新ニュース",
		"日経平均 見通し",
		"TOPIX パフォーマンス",
		"JPX 新規上場銘柄",
		"日本株 決算サマリー",
	]);
}

main();
export { searchWithTavily, syncWebSearch, getCachedSearch };
