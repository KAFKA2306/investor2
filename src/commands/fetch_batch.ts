import { readFileSync } from "node:fs";
import { parseArgs } from "node:util";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const _config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const { values, positionals } = parseArgs({
	args: Bun.argv.slice(2),
	options: {
		parallel: { type: "string", default: "3" },
	},
	allowPositionals: true,
	strict: false,
});

const symbols = positionals.filter((s) => !s.startsWith("-"));
const parallel = Number.parseInt(values.parallel as string, 10) || 3;

if (symbols.length === 0) {
	console.error("Usage: fetch_batch.ts SYMBOL1 SYMBOL2 ... [--parallel N]");
	process.exit(1);
}

async function fetchSymbol(
	symbol: string,
): Promise<{ symbol: string; records: number }> {
	const proc = Bun.spawn(["bun", "run", "src/commands/data_fetch.ts", symbol], {
		stdout: "pipe",
		stderr: "pipe",
	});
	const exitCode = await proc.exited;
	const stdout = await new Response(proc.stdout).text();
	if (exitCode !== 0) {
		const stderr = await new Response(proc.stderr).text();
		throw new Error(stderr.trim() || `exit code ${exitCode}`);
	}
	const result = JSON.parse(stdout.trim());
	return { symbol, records: result.records ?? 0 };
}

async function runPool<T>(
	items: T[],
	concurrency: number,
	fn: (item: T) => Promise<unknown>,
): Promise<{ succeeded: unknown[]; failed: unknown[] }> {
	const succeeded: unknown[] = [];
	const failed: unknown[] = [];
	let idx = 0;

	async function worker() {
		while (idx < items.length) {
			const i = idx++;
			const item = items[i];
			const result = await fn(item).catch((e: Error) => ({
				__error: true,
				item,
				error: e.message,
			}));
			if (result && typeof result === "object" && "__error" in result) {
				failed.push(result);
			} else {
				succeeded.push(result);
			}
		}
	}

	const workers = Array.from(
		{ length: Math.min(concurrency, items.length) },
		() => worker(),
	);
	await Promise.all(workers);
	return { succeeded, failed };
}

const { succeeded, failed } = await runPool(
	symbols,
	parallel,
	async (symbol) => {
		const result = await fetchSymbol(symbol);
		return result;
	},
);

const totalRecords = (succeeded as Array<{ records: number }>).reduce(
	(sum, r) => sum + r.records,
	0,
);

const output = {
	succeeded: (succeeded as Array<{ symbol: string }>).map((r) => r.symbol),
	failed: (failed as Array<{ item: string; error: string }>).map((f) => ({
		symbol: f.item,
		error: f.error,
	})),
	total_records: totalRecords,
};

console.log(JSON.stringify(output));
process.exit(failed.length > 0 ? 1 : 0);
