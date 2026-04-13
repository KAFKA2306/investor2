import type { Database } from "bun:sqlite";

export async function fetchUSReturns(db: Database, from: string, to: string) {
	const sectors = [
		"XLK",
		"XLF",
		"XLV",
		"XLP",
		"XLY",
		"XLE",
		"XLI",
		"XLB",
		"XLU",
		"XLRE",
		"XLC",
	];
	for (const sector of sectors) {
		const url = `https://query1.finance.yahoo.com/v8/finance/chart/${sector}?period1=${Math.floor(new Date(from).getTime() / 1000)}&period2=${Math.floor(new Date(to).getTime() / 1000)}&interval=1d`;
		const res = await fetch(url);
		if (!res.ok) continue;
		const json = (await res.json()) as any;
		const timestamps = json.chart.result[0].timestamp;
		const closes = json.chart.result[0].indicators.quote[0].close;
		for (let i = 1; i < timestamps.length; i++) {
			if (!closes[i] || !closes[i - 1]) continue;
			const ret = (closes[i] - closes[i - 1]) / closes[i - 1];
			const date = new Date(timestamps[i] * 1000).toISOString().split("T")[0];
			db.run(
				"INSERT OR REPLACE INTO sector_returns (date, sector, return_pct) VALUES (?, ?, ?)",
				[date, sector.toLowerCase(), ret],
			);
		}
	}
}
