import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const key = Bun.argv[2];
if (!key) {
	console.error("Usage: cache_get.ts KEY");
	process.exit(1);
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

const row = db.query("SELECT value FROM http_cache WHERE key = ?").get(key) as
	| { value: string }
	| undefined;

if (!row) {
	console.log(JSON.stringify({ error: `Key not found: ${key}` }));
	process.exit(1);
}

console.log(row.value);
