import type { Database } from "bun:sqlite";

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function fetchWithCache(
	db: Database,
	url: string,
	options: RequestInit = {},
) {
	const row = db.query("SELECT value FROM http_cache WHERE key = ?").get(url) as
		| { value: string }
		| undefined;
	if (row) return JSON.parse(row.value);
	const response = await fetch(url, options);
	if (!response.ok) {
		if ([404, 400, 403].includes(response.status)) return null;
		throw new Error(`HTTP ${response.status}: ${url}`);
	}
	const data = await response.json();
	db.run(
		"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
		[url, JSON.stringify(data), Date.now()],
	);
	return data;
}
