import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const symbol = Bun.argv[2];
if (!symbol) {
	console.error("Usage: data_fetch.ts SYMBOL");
	process.exit(1);
}

const apiKey = process.env.JQUANTS_API_KEY?.trim();
if (!apiKey) {
	throw new Error("JQUANTS_API_KEY is not set");
}

const dbPath = config.paths.cacheMarketsJquants;
mkdirSync(dirname(dbPath), { recursive: true });
const db = new Database(dbPath);
db.run(`
	CREATE TABLE IF NOT EXISTS http_cache (
		key TEXT PRIMARY KEY,
		value TEXT NOT NULL,
		created_at INTEGER NOT NULL
	)
`);

const baseUrl = "https://api.jquants.com/v2";
const headers = { "x-api-key": apiKey };

const now = new Date();
const to = now.toISOString().split("T")[0];
const from = new Date(now.getTime() - 730 * 24 * 60 * 60 * 1000)
	.toISOString()
	.split("T")[0];

const url = `${baseUrl}/equities/bars/daily?code=${symbol}&from=${from}&to=${to}`;

const cached = db
	.query("SELECT value FROM http_cache WHERE key = ?")
	.get(url) as { value: string } | undefined;

let data: { data?: unknown[] };
if (cached) {
	data = JSON.parse(cached.value);
} else {
	const response = await fetch(url, { headers });
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${url}`);
	}
	data = (await response.json()) as { data?: unknown[] };
	db.run(
		"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
		[url, JSON.stringify(data), Date.now()],
	);
}

const records = Array.isArray(data.data) ? data.data.length : 0;

const output = {
	success: true,
	symbol,
	records,
	timestamp: new Date().toISOString(),
};

console.log(JSON.stringify(output));
