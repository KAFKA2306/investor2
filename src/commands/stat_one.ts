import { Database } from "bun:sqlite";
import { config } from "./_config";

const symbol = process.argv[2];
if (!symbol) {
	console.error("Usage: stat_one.ts SYMBOL");
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT value FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
	)
	.all() as Array<{ value: string }>;

let records = 0;
let minDate = "9999-99-99";
let maxDate = "0000-00-00";
let nanCount = 0;

for (const row of rows) {
	const data = JSON.parse(row.value);
	if (!data.data) continue;
	for (const bar of data.data) {
		if (bar.Code !== symbol) continue;
		records++;
		const d = String(bar.Date);
		if (d < minDate) minDate = d;
		if (d > maxDate) maxDate = d;
		if (
			bar.AdjustmentClose === null ||
			bar.AdjustmentClose === undefined ||
			Number.isNaN(bar.AdjustmentClose)
		) {
			nanCount++;
		}
	}
}

db.close();

if (records === 0) {
	console.log(
		JSON.stringify({ symbol, records: 0, date_range: null, nan_count: 0 }),
	);
	process.exit(1);
}

console.log(
	JSON.stringify({
		symbol,
		records,
		date_range: [minDate, maxDate],
		nan_count: nanCount,
	}),
);
