import { parseArgs } from "node:util";

const { values, positionals } = parseArgs({
	args: Bun.argv.slice(2),
	options: {
		"stop-on-error": { type: "boolean", default: false },
	},
	allowPositionals: true,
	strict: false,
});

const symbols = positionals.filter((s) => !s.startsWith("-"));
const stopOnError = values["stop-on-error"] as boolean;

if (symbols.length === 0) {
	console.error(
		"Usage: validate_batch.ts SYMBOL1 SYMBOL2 ... [--stop-on-error]",
	);
	process.exit(1);
}

async function validateSymbol(
	symbol: string,
): Promise<{ valid: boolean; errors: string[] }> {
	const proc = Bun.spawn(
		["bun", "run", "src/commands/check_valid.ts", symbol],
		{
			stdout: "pipe",
			stderr: "pipe",
		},
	);
	const exitCode = await proc.exited;
	const stdout = await new Response(proc.stdout).text();
	if (exitCode !== 0) {
		const parsed = JSON.parse(stdout.trim());
		return {
			valid: false,
			errors: parsed.errors ?? [`validation failed for ${symbol}`],
		};
	}
	return { valid: true, errors: [] };
}

const validSymbols: string[] = [];
const invalid: Array<{ symbol: string; errors: string[] }> = [];

if (stopOnError) {
	for (const symbol of symbols) {
		const result = await validateSymbol(symbol);
		if (result.valid) {
			validSymbols.push(symbol);
		} else {
			invalid.push({ symbol, errors: result.errors });
			break;
		}
	}
} else {
	const results = await Promise.all(
		symbols.map(async (symbol) => {
			const result = await validateSymbol(symbol);
			return { symbol, ...result };
		}),
	);
	for (const r of results) {
		if (r.valid) {
			validSymbols.push(r.symbol);
		} else {
			invalid.push({ symbol: r.symbol, errors: r.errors });
		}
	}
}

const output = {
	valid_symbols: validSymbols,
	invalid,
};

console.log(JSON.stringify(output));
process.exit(invalid.length > 0 ? 1 : 0);
