import { Database } from "bun:sqlite";
import { config } from "./_config";

const REQUIRED_FIELDS = ["Code", "Date", "AdjustmentClose", "AdjustmentVolume"];

const symbol = process.argv[2];
if (!symbol) {
	console.error("Usage: check_valid.ts SYMBOL");
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT value FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
	)
	.all() as Array<{ value: string }>;

const errors: string[] = [];
const warnings: string[] = [];
let recordCount = 0;

for (const row of rows) {
	const data = JSON.parse(row.value);
	if (!data.data) continue;
	for (const bar of data.data) {
		if (bar.Code !== symbol) continue;
		recordCount++;

		for (const field of REQUIRED_FIELDS) {
			if (bar[field] === undefined || bar[field] === null) {
				errors.push(`Missing field: ${field} on date ${bar.Date}`);
			}
		}

		if (
			bar.AdjustmentClose !== undefined &&
			(typeof bar.AdjustmentClose !== "number" ||
				Number.isNaN(bar.AdjustmentClose))
		) {
			errors.push(`NaN in AdjustmentClose on date ${bar.Date}`);
		}
		if (
			bar.AdjustmentVolume !== undefined &&
			(typeof bar.AdjustmentVolume !== "number" ||
				Number.isNaN(bar.AdjustmentVolume))
		) {
			warnings.push(`NaN in AdjustmentVolume on date ${bar.Date}`);
		}
	}
}

db.close();

if (recordCount === 0) {
	errors.push(`No records found for symbol ${symbol}`);
}

const valid = errors.length === 0;

console.log(
	JSON.stringify({ valid, errors, warnings, symbol, records: recordCount }),
);
process.exit(valid ? 0 : 1);
