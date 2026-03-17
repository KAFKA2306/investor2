import { parseArgs } from "node:util";

const { values, positionals } = parseArgs({
	args: Bun.argv.slice(2),
	options: {
		source: { type: "string", default: "jquants" },
		parallel: { type: "string", default: "3" },
	},
	allowPositionals: true,
	strict: false,
});

const symbols = positionals.filter((s) => !s.startsWith("-"));
const source = values.source as string;
const parallel = Number.parseInt(values.parallel as string, 10) || 3;

const validSources = ["jquants", "edinet", "mixseek"];
if (!validSources.includes(source)) {
	console.error(
		`Invalid source: ${source}. Must be one of: ${validSources.join(", ")}`,
	);
	process.exit(1);
}

if (symbols.length === 0) {
	console.error(
		"Usage: sync_batch.ts SYMBOL1 SYMBOL2 ... [--source jquants|edinet|mixseek] [--parallel N]",
	);
	process.exit(1);
}

async function syncSymbol(symbol: string, source: string): Promise<string> {
	const env: Record<string, string> = {
		...(process.env as Record<string, string>),
	};
	if (source === "edinet") {
		env.GET_MODE = "edinet";
	} else if (source === "jquants") {
		env.GET_MODE = "jquants";
	}

	const proc = Bun.spawn(["bun", "run", "src/commands/data_fetch.ts", symbol], {
		stdout: "pipe",
		stderr: "pipe",
		env,
	});
	const exitCode = await proc.exited;
	if (exitCode !== 0) {
		const stderr = await new Response(proc.stderr).text();
		throw new Error(stderr.trim() || `exit code ${exitCode}`);
	}
	return symbol;
}

async function runPool<T>(
	items: T[],
	concurrency: number,
	fn: (item: T) => Promise<unknown>,
): Promise<{ succeeded: T[]; failed: T[] }> {
	const succeeded: T[] = [];
	const failed: T[] = [];
	let idx = 0;

	async function worker() {
		while (idx < items.length) {
			const i = idx++;
			const item = items[i];
			const result = await fn(item).catch(() => null);
			if (result === null) {
				failed.push(item);
			} else {
				succeeded.push(item);
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

const { succeeded, failed } = await runPool(symbols, parallel, (symbol) =>
	syncSymbol(symbol, source),
);

const output = {
	source,
	synced: succeeded,
	failed,
};

console.log(JSON.stringify(output));
process.exit(failed.length > 0 ? 1 : 0);
