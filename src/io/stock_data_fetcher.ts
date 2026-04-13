import { readFileSync } from "node:fs";
import { config } from "../commands/_config.ts";

export interface StockBar {
	date: string;
	open: number;
	close: number;
	adjClose: number;
}

/**
 * Fetch daily bars for a specific stock code from the raw J-Quants CSV.
 * Optimized for verification of specific alpha targets.
 */
export async function getStockPriceHistory(
	code: string,
	fromDate: string,
	toDate: string,
): Promise<StockBar[]> {
	const csvPath = config.paths.marketdataPricesCsv;
	if (!csvPath) throw new Error("marketdataPricesCsv not configured");

	// For massive CSVs, we use a simple line-by-line scan (optimized for this environment)
	const content = readFileSync(csvPath, "utf-8");
	const lines = content.split("\n");
	const results: StockBar[] = [];

	// Target code can be 4 or 5 digits in CSV (e.g., 13330 or 1333)
	const targetCode1 = code;
	const targetCode2 = code.length === 4 ? `${code}0` : code;

	for (let i = 1; i < lines.length; i++) {
		const line = lines[i];
		if (
			!line ||
			(!line.startsWith(targetCode1) && !line.startsWith(targetCode2))
		)
			continue;

		const parts = line.split(",");
		if (parts.length < 13) continue;

		const rowCode = parts[0];
		if (rowCode !== targetCode1 && rowCode !== targetCode2) continue;

		const date = parts[1];
		if (date < fromDate || date > toDate) continue;

		results.push({
			date,
			open: Number(parts[2]),
			close: Number(parts[5]),
			adjClose: Number(parts[12]),
		});
	}

	return results.sort((a, b) => a.date.localeCompare(b.date));
}
