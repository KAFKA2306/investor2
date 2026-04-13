import type { Database } from "bun:sqlite";
import { fetchWithCache } from "./http";

export async function fetchJPReturns(db: Database, from: string, to: string) {
	const apiKey = process.env.JQUANTS_API_KEY!;
	const baseUrl = "https://api.jquants.com/v2";
	const headers = { "x-api-key": apiKey };
	const sectors = [
		"1000",
		"2000",
		"3000",
		"4000",
		"5000",
		"6000",
		"7000",
		"8000",
		"9000",
		"10000",
		"11000",
		"12000",
		"13000",
		"14000",
		"15000",
		"16000",
		"17000",
	];
	for (const sector of sectors) {
		const url = `${baseUrl}/indices/bars/daily/${sector}?from=${from.replace(/-/g, "")}&to=${to.replace(/-/g, "")}`;
		const data = await fetchWithCache(db, url, { headers });
		if (!data?.data) continue;
		for (const bar of data.data) {
			const ret =
				(bar.AdjustmentClose - bar.AdjustmentOpen) / bar.AdjustmentOpen;
			db.run(
				"INSERT OR REPLACE INTO sector_returns (date, sector, return_pct) VALUES (?, ?, ?)",
				[bar.Date, sector, ret],
			);
		}
	}
}
