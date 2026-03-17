import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const key = Bun.argv[2];
const value = Bun.argv[3];
const ttlArg = Bun.argv[4];

if (!key || !value) {
	console.error("Usage: cache_set.ts KEY VALUE [TTL]");
	process.exit(1);
}

const ttl = ttlArg ? Number.parseInt(ttlArg, 10) : undefined;

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

const now = Date.now();
db.run(
	"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
	[key, value, now],
);

const output: Record<string, unknown> = {
	key,
	stored_at: new Date(now).toISOString(),
};
if (ttl !== undefined) {
	output.ttl = ttl;
}

console.log(JSON.stringify(output));
