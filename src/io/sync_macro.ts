import type { DatabaseRegistry } from "../schemas";
import { fetchWithCache } from "./http";

export async function syncMacro(dbs: DatabaseRegistry) {
	const yahooSymbols = [
		"^N225",
		"^TOPX",
		"^GSPC",
		"^VIX",
		"USDJPY=X",
		"EURUSD=X",
		"CL=F",
		"GC=F",
	];
	for (const s of yahooSymbols) {
		await fetchWithCache(
			dbs.marketsYahoo,
			`https://query1.finance.yahoo.com/v8/finance/chart/${s}?interval=1d&range=max`,
		);
	}
	const estatAppId = process.env.ESTAT_APP_ID;
	if (estatAppId) {
		for (const id of ["0003411475", "0003103532", "0003060843"]) {
			await fetchWithCache(
				dbs.macroEstat,
				`https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?appId=${estatAppId}&statsDataId=${id}`,
			);
		}
	}
	const fredKey = process.env.FRED_API_KEY;
	if (fredKey) {
		for (const id of ["FEDFUNDS", "DGS10", "CPIAUCSL", "UNRATE", "T10YIE"]) {
			await fetchWithCache(
				dbs.macroFred,
				`https://api.stlouisfed.org/fred/series/observations?series_id=${id}&api_key=${fredKey}&file_type=json`,
			);
		}
	}
}
