import { Database } from "bun:sqlite";
import { readFileSync, statSync } from "node:fs";
import { parseArgs } from "node:util";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const { values, positionals } = parseArgs({
	args: Bun.argv.slice(2),
	options: {
		ttl: { type: "string", default: "86400" },
		parallel: { type: "string", default: "3" },
	},
	allowPositionals: true,
	strict: false,
});

const symbols = positionals.filter((s) => !s.startsWith("-"));
const ttl = Number.parseInt(values.ttl as string, 10) || 86400;
const parallel = Number.parseInt(values.parallel as string, 10) || 3;

if (symbols.length === 0) {
	console.error(
		"Usage: cache_warm.ts SYMBOL1 SYMBOL2 ... [--ttl SECONDS] [--parallel N]",
	);
	process.exit(1);
}

const db = new Database(config.paths.cacheMarketsJquants);

function isCacheFresh(symbol: string, ttlSeconds: number): boolean {
	const row = db
		.query(
			"SELECT created_at FROM http_cache WHERE key LIKE ? ORDER BY created_at DESC LIMIT 1",
		)
		.get(`%${symbol}%`) as { created_at: number } | undefined;
	if (!row) return false;
	const ageSeconds = (Date.now() - row.created_at) / 1000;
	return ageSeconds < ttlSeconds;
}

async function warmSymbol(symbol: string): Promise<"warmed" | "skipped"> {
	if (isCacheFresh(symbol, ttl)) return "skipped";

	const proc = Bun.spawn(["bun", "run", "src/commands/data_fetch.ts", symbol], {
		stdout: "pipe",
		stderr: "pipe",
	});
	const exitCode = await proc.exited;
	if (exitCode !== 0) {
		const stderr = await new Response(proc.stderr).text();
		throw new Error(stderr.trim() || `exit code ${exitCode}`);
	}
	return "warmed";
}

async function runPool<T, R>(
	items: T[],
	concurrency: number,
	fn: (item: T) => Promise<R>,
): Promise<Array<{ item: T; result?: R; error?: string }>> {
	const results: Array<{ item: T; result?: R; error?: string }> = [];
	let idx = 0;

	async function worker() {
		while (idx < items.length) {
			const i = idx++;
			const item = items[i];
			const r = await fn(item).catch((e: Error) => ({ __error: e.message }));
			if (r && typeof r === "object" && "__error" in r) {
				results.push({ item, error: (r as { __error: string }).__error });
			} else {
				results.push({ item, result: r as R });
			}
		}
	}

	const workers = Array.from(
		{ length: Math.min(concurrency, items.length) },
		() => worker(),
	);
	await Promise.all(workers);
	return results;
}

const results = await runPool(symbols, parallel, warmSymbol);

const warmed: string[] = [];
const skipped: string[] = [];
let hasError = false;

for (const r of results) {
	if (r.error) {
		hasError = true;
	} else if (r.result === "skipped") {
		skipped.push(r.item);
	} else {
		warmed.push(r.item);
	}
}

let cacheSizeMb = 0;
const dbPath = config.paths.cacheMarketsJquants;
const stat = statSync(dbPath, { throwIfNoEntry: false });
if (stat) cacheSizeMb = Math.round((stat.size / 1024 / 1024) * 100) / 100;

const output = {
	warmed,
	skipped,
	cache_size_mb: cacheSizeMb,
};

console.log(JSON.stringify(output));
process.exit(hasError ? 1 : 0);
