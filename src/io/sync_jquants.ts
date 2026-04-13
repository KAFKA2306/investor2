import type { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import type { Config, DatabaseRegistry } from "../schemas";
import { fetchWithCache, sleep } from "./http";

export async function exportJquantsToCsv(db: Database, dataPath: string) {
	const csvPath = `${dataPath}/raw_stock_price_latest.csv`;
	const rows = db
		.query(
			"SELECT value FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%' ORDER BY key DESC LIMIT 500",
		)
		.all() as Array<{ value: string }>;
	let csvContent = "Code,Date,Close,Volume\n";
	for (const row of rows) {
		const data = JSON.parse(row.value);
		if (!data.data) continue;
		for (const bar of data.data) {
			csvContent += `${bar.Code},${bar.Date},${bar.AdjustmentClose},${bar.AdjustmentVolume}\n`;
		}
	}
	mkdirSync(dirname(csvPath), { recursive: true });
	Bun.write(csvPath, csvContent);
}

export async function syncJquants(
	mode: "markets" | "fundamental",
	dbs: DatabaseRegistry,
	config: Config,
) {
	const apiKey = process.env.JQUANTS_API_KEY?.trim();
	if (!apiKey) throw "MISSING_JQUANTS_API_KEY";
	const db = mode === "markets" ? dbs.marketsJquants : dbs.fundamentalJquants;
	const baseUrl = "https://api.jquants.com/v2";
	const headers = { "x-api-key": apiKey };
	const dates = Array.from({ length: 730 }, (_, i) => {
		const d = new Date("2023-12-26");
		d.setDate(d.getDate() + i);
		return d.toISOString().split("T")[0];
	}).filter((d) => d <= "2025-12-26");

	if (mode === "markets") {
		await fetchWithCache(db, `${baseUrl}/equities/master`, { headers });
		for (const date of dates) {
			const d = date.replace(/-/g, "");
			await fetchWithCache(db, `${baseUrl}/equities/bars/daily?date=${d}`, {
				headers,
			});
			await fetchWithCache(
				db,
				`${baseUrl}/indices/bars/daily/topix?date=${d}`,
				{ headers },
			);
			await sleep(6000);
		}
		await exportJquantsToCsv(db, config.paths.data);
	} else {
		for (const date of dates) {
			const d = date.replace(/-/g, "");
			await fetchWithCache(db, `${baseUrl}/fins/summary?date=${d}`, {
				headers,
			});
		}
	}
}
