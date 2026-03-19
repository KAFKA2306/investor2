import { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { config } from "../commands/_config.ts";
import { SectorReturnsSchema } from "../schemas";
import type { SectorReturns, JP17Sectors, US11Sectors } from "../schemas";

const cacheDir = config.sector_spillover?.backtest?.data_cache_dir;
if (!cacheDir)
	throw new Error("sector_spillover.backtest.data_cache_dir not configured");
mkdirSync(dirname(cacheDir), { recursive: true });

const db = new Database(`${cacheDir}/sector_returns.db`);

// Database for J-Quants market data (from get.ts HTTP cache)
const jquantsDb = new Database(config.paths.cacheMarketsJquants);

db.exec(`
  CREATE TABLE IF NOT EXISTS sector_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sector TEXT NOT NULL,
    return_pct REAL NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(date, sector)
  )
`);

/**
 * Fetch US sector returns from Yahoo Finance
 * Maps US sector names to standard sector ETFs and computes returns
 */
export async function fetchUSReturns(
	fromDate: string,
	toDate: string,
): Promise<SectorReturns[]> {
	// US Sector to ETF mapping (11 sectors)
	const sectorETFMap: Record<string, string> = {
		energy: "XLE",
		materials: "XLB",
		industrials: "XLI",
		consumer_discretionary: "XLY",
		consumer_staples: "XLP",
		healthcare: "XLV",
		financials: "XLF",
		it: "XLK",
		communication: "XLC",
		utilities: "XLU",
		real_estate: "XLRE",
	};

	// Convert dates to Unix timestamps (seconds)
	const fromParts = fromDate.split("-");
	const toParts = toDate.split("-");
	const fromTime = Math.floor(
		new Date(Number(fromParts[0]), Number(fromParts[1]) - 1, Number(fromParts[2]))
			.getTime() / 1000,
	);
	const toTime = Math.floor(
		new Date(Number(toParts[0]), Number(toParts[1]) - 1, Number(toParts[2]))
			.getTime() / 1000,
	);

	// Build price data from Yahoo Finance
	const sectorPrices = new Map<string, Array<{ date: string; close: number }>>();

	// Initialize with empty arrays for each sector
	for (const sector of Object.keys(sectorETFMap)) {
		sectorPrices.set(sector, []);
	}

	// Fetch data for each sector ETF in parallel
	const fetchPromises = Object.entries(sectorETFMap).map(async ([sector, ticker]) => {
		const historyUrl =
			`https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?period1=${fromTime}&period2=${toTime}&interval=1d`;

		const response = await fetch(historyUrl);
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${historyUrl}`);
		}

		const data = await response.json() as {
			chart?: {
				result?: Array<{
					timestamp?: number[];
					indicators?: {
						quote?: Array<{ close?: number[] }>;
						adjclose?: Array<{ adjclose?: number[] }>;
					};
				}>;
			};
		};

		if (!data.chart?.result?.[0]?.timestamp) {
			return;
		}

		const result = data.chart.result[0];
		const timestamps = result.timestamp || [];
		const closes = result.indicators?.quote?.[0]?.close || [];
		const adjCloses = result.indicators?.adjclose?.[0]?.adjclose || closes;

		// Parse prices into array with dates
		for (let i = 0; i < timestamps.length; i++) {
			const timestamp = timestamps[i];
			const close = adjCloses?.[i];

			if (timestamp && close) {
				const date = new Date(timestamp * 1000).toISOString().split("T")[0];
				sectorPrices.get(sector)!.push({ date, close });
			}
		}
	});

	// Wait for all sector fetches to complete
	await Promise.all(fetchPromises);

	// Calculate daily returns by sector
	const results: SectorReturns[] = [];

	for (const [sector, prices] of sectorPrices) {
		if (prices.length < 2) continue;

		// Sort by date
		prices.sort((a, b) => a.date.localeCompare(b.date));

		// Calculate returns (close_t / close_t-1 - 1) * 100
		for (let i = 1; i < prices.length; i++) {
			const prevClose = prices[i - 1].close;
			const currClose = prices[i].close;
			const date = prices[i].date;

			if (prevClose && currClose) {
				const returnPct = (currClose / prevClose - 1) * 100;
				results.push({
					date,
					sector: sector as US11Sectors,
					return_pct: returnPct,
				});
			}
		}
	}

	return results;
}

/**
 * Fetch JP sector returns from J-Quants or local cache
 * Calculates sector (業種) returns by:
 * 1. Reading master data from J-Quants cache (sector code per stock)
 * 2. Reading daily bar data from J-Quants cache
 * 3. Grouping prices by sector code
 * 4. Computing sector-weighted returns per day
 */
export function fetchJPReturns(
	fromDate: string,
	toDate: string,
): SectorReturns[] {
	// Step 1: Extract master data (Code -> SectorCode mapping)
	const masterCacheRows = jquantsDb
		.query("SELECT value FROM http_cache WHERE key LIKE '%/equities/master%'")
		.all() as Array<{ value: string }>;

	if (masterCacheRows.length === 0) {
		throw new Error(
			"J-Quants master data not in cache. Run `task data:sync` first.",
		);
	}

	const masterData = JSON.parse(masterCacheRows[0].value);
	const codeToSector = new Map<string, string>();

	// Map Code -> Sector code (e.g., "1000" for 水産・農林業)
	for (const stock of masterData.data || []) {
		if (stock.Code && stock.S17) {
			const sectorCode = String(Number(stock.S17) * 1000);
			codeToSector.set(stock.Code, sectorCode);
		}
	}

	if (codeToSector.size === 0) {
		return []; // No sector mappings available
	}

	// Step 2: Extract daily bar data for date range
	const barCacheRows = jquantsDb
		.query(
			"SELECT key, value FROM http_cache WHERE key LIKE '%/equities/bars/daily%' ORDER BY key DESC LIMIT 500",
		)
		.all() as Array<{ key: string; value: string }>;

	// Group by date and parse
	const dateToStocks = new Map<
		string,
		Array<{ code: string; close: number; prev: number }>
	>();

	for (const row of barCacheRows) {
		const data = JSON.parse(row.value);
		if (!data.data) continue;

		for (const bar of data.data) {
			const code = bar.Code;
			const date = bar.Date;
			const close = bar.AdjustmentClose || bar.Close;

			if (!code || !date || !close) continue;
			if (date < fromDate || date > toDate) continue;

			if (!dateToStocks.has(date)) dateToStocks.set(date, []);
			dateToStocks.get(date)!.push({
				code,
				close: Number(close),
				prev: 0, // Will be computed from prior day
			});
		}
	}

	// Step 3: Compute daily returns by sector
	const results: SectorReturns[] = [];
	const jpSectors = (config.sector_spillover?.jp_sectors ??
		[]) as JP17Sectors[];

	// Sort dates to compute returns correctly
	const sortedDates = Array.from(dateToStocks.keys()).sort();

	for (let i = 1; i < sortedDates.length; i++) {
		const currDate = sortedDates[i];
		const prevDate = sortedDates[i - 1];

		const currStocks = dateToStocks.get(currDate)!;
		const prevStocks = dateToStocks.get(prevDate)!;

		// Create prev price map for quick lookup
		const prevPriceMap = new Map<string, number>();
		for (const stock of prevStocks) {
			prevPriceMap.set(stock.code, stock.close);
		}

		// Group current prices by sector
		const sectorToPrices = new Map<string, number[]>();
		for (const stock of currStocks) {
			const prevPrice = prevPriceMap.get(stock.code);
			if (!prevPrice) continue; // Skip stocks without prior day

			const sectorCode = codeToSector.get(stock.code);
			if (!sectorCode || !jpSectors.includes(sectorCode as JP17Sectors))
				continue;

			if (!sectorToPrices.has(sectorCode)) sectorToPrices.set(sectorCode, []);
			sectorToPrices.get(sectorCode)!.push(stock.close / prevPrice);
		}

		// Compute weighted sector returns (simple average of price ratios)
		for (const sectorCode of jpSectors) {
			const ratios = sectorToPrices.get(sectorCode);
			if (!ratios || ratios.length === 0) continue;

			const avgRatio = ratios.reduce((a, b) => a + b, 0) / ratios.length;
			const returnPct = (avgRatio - 1) * 100;

			results.push({
				date: currDate,
				sector: sectorCode,
				return_pct: returnPct,
			});
		}
	}

	return results;
}

/**
 * Cache sector returns to SQLite
 */
export function cacheSectorReturns(returns: SectorReturns[]): void {
	const stmt = db.prepare(
		`INSERT OR REPLACE INTO sector_returns (date, sector, return_pct, created_at)
     VALUES (?, ?, ?, ?)`,
	);

	const now = Math.floor(Date.now() / 1000);

	for (const ret of returns) {
		SectorReturnsSchema.parse(ret);
		stmt.run(ret.date, ret.sector, ret.return_pct, now);
	}
}

/**
 * Retrieve cached sector returns for a date range
 */
export function getCachedReturns(
	fromDate: string,
	toDate: string,
): SectorReturns[] {
	const stmt = db.prepare(
		`SELECT date, sector, return_pct FROM sector_returns
     WHERE date >= ? AND date <= ?
     ORDER BY date, sector`,
	);

	const rows = stmt.all(fromDate, toDate) as Array<{
		date: string;
		sector: string;
		return_pct: number;
	}>;

	return rows.map((row) =>
		SectorReturnsSchema.parse({
			date: row.date,
			sector: row.sector,
			return_pct: row.return_pct,
		}),
	);
}

/**
 * Fetch or get cached sector returns
 */
export async function getSectorReturns(
	fromDate: string,
	toDate: string,
): Promise<SectorReturns[]> {
	const cached = getCachedReturns(fromDate, toDate);
	if (cached.length > 0) {
		return cached;
	}

	const usReturns = await fetchUSReturns(fromDate, toDate);
	const jpReturns = fetchJPReturns(fromDate, toDate);

	const allReturns = [...usReturns, ...jpReturns];
	cacheSectorReturns(allReturns);

	return allReturns;
}

/**
 * Pivot sector returns into matrix format for PCA
 * Returns { dates: [date1, date2, ...], matrix: [[r11, r12, ...], [r21, r22, ...], ...] }
 */
export function pivotToMatrix(returns: SectorReturns[]): {
	dates: string[];
	sectors: string[];
	matrix: number[][];
} {
	const dates = Array.from(new Set(returns.map((r) => r.date))).sort();
	const sectors = Array.from(new Set(returns.map((r) => r.sector))).sort();

	const returnMap = new Map<string, number>();
	for (const ret of returns) {
		returnMap.set(`${ret.date}:${ret.sector}`, ret.return_pct);
	}

	const matrix: number[][] = dates.map((date) => {
		return sectors.map((sector) => {
			return returnMap.get(`${date}:${sector}`) ?? 0;
		});
	});

	return { dates, sectors, matrix };
}
