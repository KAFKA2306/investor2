import { Database } from "bun:sqlite";
import { readFileSync } from "node:fs";
import yaml from "js-yaml";
import { ConfigSchema, type DatabaseRegistry } from "../schemas";
import { syncEdinet, syncEdinetXbrl } from "./sync_edinet";
import { syncJquants } from "./sync_jquants";
import { syncMacro } from "./sync_macro";
import { syncPolymarket } from "./sync_polymarket";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const dbs = Object.entries(config.paths)
	.filter(([k]) => k.startsWith("cache") || k === "macroFred")
	.reduce((acc, [k, v]) => {
		const name = k.replace(/^cache/, "").replace(/^\w/, (c) => c.toLowerCase());
		acc[name] = new Database(v as string);
		acc[name].run(
			"CREATE TABLE IF NOT EXISTS http_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at INTEGER NOT NULL)",
		);
		return acc;
	}, {} as DatabaseRegistry);

async function main() {
	const mode = process.env.GET_MODE || "all";
	if (mode === "edinet") {
		await syncEdinet(dbs);
		await syncEdinetXbrl(dbs);
		return;
	}
	if (mode === "jquants") {
		await syncJquants("markets", dbs, config);
		await syncJquants("fundamental", dbs, config);
		return;
	}
	await Promise.all([
		syncPolymarket(dbs, config),
		syncMacro(dbs),
		syncJquants("markets", dbs, config),
		syncJquants("fundamental", dbs, config),
		syncEdinet(dbs),
	]);
	if (mode !== "skip-xbrl") await syncEdinetXbrl(dbs);
}

main();
