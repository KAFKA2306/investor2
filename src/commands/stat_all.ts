import { Database } from "bun:sqlite";
import { config } from "./_config";

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT key, value, created_at FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
	)
	.all() as Array<{ key: string; value: string; created_at: number }>;

const symbolStats = new Map<
	string,
	{ records: number; latestCreatedAt: number }
>();

for (const row of rows) {
	const data = JSON.parse(row.value);
	if (!data.data) continue;
	for (const bar of data.data) {
		const code = bar.Code as string;
		if (!code) continue;
		const existing = symbolStats.get(code);
		if (existing) {
			existing.records++;
			if (row.created_at > existing.latestCreatedAt)
				existing.latestCreatedAt = row.created_at;
		} else {
			symbolStats.set(code, { records: 1, latestCreatedAt: row.created_at });
		}
	}
}

db.close();

const now = Date.now();
const result = Array.from(symbolStats.entries()).map(([symbol, stat]) => ({
	symbol,
	records: stat.records,
	cache_age_hours:
		Math.round(((now - stat.latestCreatedAt) / (1000 * 60 * 60)) * 10) / 10,
}));

console.log(JSON.stringify(result));
