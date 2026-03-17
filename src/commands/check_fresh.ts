import { Database } from "bun:sqlite";
import { config } from "./_config";

const symbol = process.argv[2];
const hours = Number(process.argv[3]);
if (!symbol || Number.isNaN(hours)) {
	console.error("Usage: check_fresh.ts SYMBOL HOURS");
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT key, created_at FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY created_at DESC LIMIT 500",
	)
	.all() as Array<{ key: string; created_at: number }>;

let latestCreatedAt = 0;

for (const row of rows) {
	const cached = db
		.query("SELECT value FROM http_cache WHERE key = ?")
		.get(row.key) as { value: string } | undefined;
	if (!cached) continue;
	const data = JSON.parse(cached.value);
	if (!data.data) continue;
	const match = data.data.some((bar: { Code: string }) => bar.Code === symbol);
	if (match && row.created_at > latestCreatedAt) {
		latestCreatedAt = row.created_at;
	}
}

db.close();

if (latestCreatedAt === 0) {
	console.log(
		JSON.stringify({
			fresh: false,
			age_hours: null,
			threshold_hours: hours,
			symbol,
		}),
	);
	process.exit(1);
}

const ageHours = (Date.now() - latestCreatedAt) / (1000 * 60 * 60);
const fresh = ageHours <= hours;

console.log(
	JSON.stringify({
		fresh,
		age_hours: Math.round(ageHours * 10) / 10,
		threshold_hours: hours,
		symbol,
	}),
);

process.exit(fresh ? 0 : 1);
