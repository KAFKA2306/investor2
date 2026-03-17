import { Database } from "bun:sqlite";
import { config } from "./_config";

const EXPECTED_COLUMNS = [
	"Code",
	"Date",
	"Open",
	"High",
	"Low",
	"Close",
	"Volume",
	"TurnoverValue",
	"AdjustmentFactor",
	"AdjustmentOpen",
	"AdjustmentHigh",
	"AdjustmentLow",
	"AdjustmentClose",
	"AdjustmentVolume",
];

const symbol = process.argv[2];
if (!symbol) {
	console.error("Usage: check_schema.ts SYMBOL");
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants, { readonly: true });

const rows = db
	.query(
		"SELECT value FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
	)
	.all() as Array<{ value: string }>;

let actual: string[] = [];
let found = false;

for (const row of rows) {
	const data = JSON.parse(row.value);
	if (!data.data) continue;
	for (const bar of data.data) {
		if (bar.Code !== symbol) continue;
		actual = Object.keys(bar);
		found = true;
		break;
	}
	if (found) break;
}

db.close();

if (!found) {
	console.log(
		JSON.stringify({
			schema_ok: false,
			expected: EXPECTED_COLUMNS,
			actual: [],
			missing: EXPECTED_COLUMNS,
			symbol,
		}),
	);
	process.exit(1);
}

const missing = EXPECTED_COLUMNS.filter((col) => !actual.includes(col));
const schemaOk = missing.length === 0;

console.log(
	JSON.stringify({
		schema_ok: schemaOk,
		expected: EXPECTED_COLUMNS,
		actual,
		missing: missing.length > 0 ? missing : undefined,
		symbol,
	}),
);

process.exit(schemaOk ? 0 : 1);
