import { Database } from "bun:sqlite";
import { config } from "./_config";

const symbol = process.argv[2];
if (!symbol) {
	console.error("Usage: check_cached.ts SYMBOL");
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT key, created_at FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY created_at DESC LIMIT 500",
	)
	.all() as Array<{ key: string; created_at: number }>;

let found = false;
let latestCreatedAt = 0;

for (const row of rows) {
	const cached = db
		.query("SELECT value FROM http_cache WHERE key = ?")
		.get(row.key) as { value: string } | undefined;
	if (!cached) continue;
	const data = JSON.parse(cached.value);
	if (!data.data) continue;
	const match = data.data.some((bar: { Code: string }) => bar.Code === symbol);
	if (match) {
		found = true;
		if (row.created_at > latestCreatedAt) latestCreatedAt = row.created_at;
	}
}

db.close();

if (found) {
	const ageHours = (Date.now() - latestCreatedAt) / (1000 * 60 * 60);
	console.log(
		JSON.stringify({
			exists: true,
			age_hours: Math.round(ageHours * 10) / 10,
			symbol,
		}),
	);
	process.exit(0);
}

console.log(JSON.stringify({ exists: false, symbol }));
process.exit(1);
