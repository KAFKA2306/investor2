import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const CACHE_ROOT = "/mnt/d/investor_all_cached_data";
const JQUANTS_DIR = resolve(CACHE_ROOT, "jquants");

interface StockRecord {
	code: string; // 4-digit (padded)
	name: string;
	sectorCode: string;
	sectorName: string;
	market: string;
	price: number; // yen, latest close
	marketCap: number; // 億円
	per: number; // Price / EPS
	pbr: number; // Price / BPS
	roe: number; // %
	roa: number; // %
	operatingMargin: number; // %
	netSales: number; // 億円
	operatingProfit: number; // 億円
	netIncome: number; // 億円
	equity: number; // 億円
	fiscalPeriodEnd: string;
}

interface StockListRow {
	code: string;
	name: string;
	sectorCode: string;
	sectorName: string;
	market: string;
}

interface FinRow {
	localCode: string;
	eps: number;
	bps: number;
	shares: number;
	netSales: number;
	operatingProfit: number;
	ordinaryProfit: number;
	profit: number;
	equity: number;
	totalAssets: number;
	periodEnd: string;
	docType: string;
	disclosedDate: string;
}

// Module-level cache
let screenerCache: StockRecord[] | null = null;

function parseFloat_(val: string): number {
	if (!val || val === "－" || val === "") return NaN;
	const parsed = parseFloat(val);
	return isNaN(parsed) ? NaN : parsed;
}

function parseInt_(val: string): number {
	if (!val || val === "－" || val === "") return NaN;
	const parsed = parseInt(val, 10);
	return isNaN(parsed) ? NaN : parsed;
}

function parseCSVLine(line: string): string[] {
	const result: string[] = [];
	let current = "";
	let inQuotes = false;

	for (let i = 0; i < line.length; i++) {
		const char = line[i];

		if (char === '"') {
			inQuotes = !inQuotes;
		} else if (char === "," && !inQuotes) {
			result.push(current);
			current = "";
		} else {
			current += char;
		}
	}

	result.push(current);
	return result;
}

function loadStockList(): Map<string, StockListRow> {
	const path = resolve(JQUANTS_DIR, "raw_stock_list.csv");
	const content = readFileSync(path, "utf-8");
	const lines = content.split("\n");
	const map = new Map<string, StockListRow>();

	for (let i = 1; i < lines.length; i++) {
		const line = lines[i]?.trim();
		if (!line) continue;

		const parts = parseCSVLine(line);
		if (parts.length < 9) continue;

		const code = parts[0]!.trim(); // 5-digit
		const name = parts[1]!.trim();
		const sectorCode = parts[4]!.trim();
		const sectorName = parts[7]!.trim();
		const market = parts[8]!.trim() || "不明";

		// Skip if parsing failed (empty fields)
		if (!code || !name || !sectorCode || !sectorName) continue;

		map.set(code, { code, name, sectorCode, sectorName, market });
	}

	console.log(`✅ Loaded ${map.size} stocks from raw_stock_list.csv`);
	return map;
}

function loadFinData(): Map<string, FinRow> {
	const path = resolve(JQUANTS_DIR, "raw_stock_fin.csv");
	const content = readFileSync(path, "utf-8");
	const lines = content.split("\n");
	const map = new Map<string, FinRow>();

	// Track latest DisclosedDate per LocalCode to pick the most recent full-year statement
	const latestDisclosedDate = new Map<string, string>();

	for (let i = 1; i < lines.length; i++) {
		const line = lines[i]?.trim();
		if (!line) continue;

		const parts = parseCSVLine(line);
		if (parts.length < 43) continue;

		const localCode = parts[26]!.trim(); // 5-digit
		const disclosedDate = parts[1]!.trim();
		const docType = parts[42]!.trim();

		// Filter: only "FYFinancialStatements" (full-year), not quarters or other statements
		if (!docType.includes("FYFinancialStatements")) continue;

		// Keep only latest DisclosedDate per localCode
		const prevDate = latestDisclosedDate.get(localCode);
		if (prevDate && prevDate >= disclosedDate) continue;

		latestDisclosedDate.set(localCode, disclosedDate);

		const eps = parseFloat_(parts[13]!);
		const bps = parseFloat_(parts[4]!);
		const shares = parseInt_(parts[29]!); // NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock
		const netSales = parseInt_(parts[28]!); // NetSales
		const operatingProfit = parseInt_(parts[31]!);
		const ordinaryProfit = parseInt_(parts[32]!);
		const profit = parseInt_(parts[33]!);
		const equity = parseInt_(parts[14]!);
		const totalAssets = parseInt_(parts[40]!);
		const periodEnd = parts[10]!.trim(); // CurrentPeriodEndDate

		map.set(localCode, {
			localCode,
			eps,
			bps,
			shares,
			netSales,
			operatingProfit,
			ordinaryProfit,
			profit,
			equity,
			totalAssets,
			periodEnd,
			docType,
			disclosedDate,
		});
	}

	console.log(`✅ Loaded ${map.size} fin records from raw_stock_fin.csv`);
	return map;
}

function loadLatestPrices(): Map<string, number> {
	const path = resolve(JQUANTS_DIR, "raw_stock_price.csv");
	const content = readFileSync(path, "utf-8");
	const lines = content.split("\n");
	const map = new Map<string, number>();

	// Reverse scan: iterate from end, collect first-seen close per code
	for (let i = lines.length - 2; i >= 1; i--) {
		const line = lines[i]?.trim();
		if (!line) continue;

		const parts = parseCSVLine(line);
		if (parts.length < 6) continue;

		const code = parts[0]!.trim(); // 5-digit
		if (map.has(code)) continue; // Already have latest for this code

		const close = parseFloat_(parts[5]!);
		if (!isNaN(close) && close > 0) {
			map.set(code, close);
		}

		// Early exit when all 4233 codes collected
		if (map.size >= 4233) break;
	}

	console.log(
		`✅ Loaded ${map.size} latest price records from raw_stock_price.csv`,
	);
	return map;
}

function buildRecords(
	listMap: Map<string, StockListRow>,
	finMap: Map<string, FinRow>,
	priceMap: Map<string, number>,
): StockRecord[] {
	const records: StockRecord[] = [];

	for (const [code, stock] of listMap) {
		// code is already 5-digit, use directly
		const finData = finMap.get(code);
		const price = priceMap.get(code);

		// Skip if missing critical data
		if (!finData || !price || price <= 0) continue;
		if (isNaN(finData.eps) || isNaN(finData.bps)) continue;
		if (isNaN(finData.equity) || isNaN(finData.totalAssets)) continue;

		const shares = isNaN(finData.shares) ? 0 : finData.shares;
		const marketCap = shares > 0 ? (price * shares) / 100000000 : 0; // price(yen) * shares / 1e8

		const per = finData.eps > 0 ? price / finData.eps : NaN;
		const pbr = finData.bps > 0 ? price / finData.bps : NaN;

		const profit = isNaN(finData.profit) ? 0 : finData.profit;
		const roe = finData.equity > 0 ? (profit / finData.equity) * 100 : NaN;
		const roa =
			finData.totalAssets > 0 ? (profit / finData.totalAssets) * 100 : NaN;

		const opProfit = isNaN(finData.operatingProfit)
			? 0
			: finData.operatingProfit;
		const netSales = isNaN(finData.netSales) ? 0 : finData.netSales;
		const operatingMargin = netSales > 0 ? (opProfit / netSales) * 100 : NaN;

		records.push({
			code: stock.code,
			name: stock.name,
			sectorCode: stock.sectorCode,
			sectorName: stock.sectorName,
			market: stock.market,
			price,
			marketCap,
			per,
			pbr,
			roe,
			roa,
			operatingMargin,
			netSales: netSales / 100000000,
			operatingProfit: opProfit / 100000000,
			netIncome: profit / 100000000,
			equity: finData.equity / 100000000,
			fiscalPeriodEnd: finData.periodEnd,
		});
	}

	console.log(`✅ Built ${records.length} stock records`);
	return records;
}

export async function getScreenerData(): Promise<StockRecord[]> {
	if (screenerCache) return screenerCache;

	console.log("📊 Loading screener data...");
	const startTime = Date.now();

	const listMap = loadStockList();
	const finMap = loadFinData();
	const priceMap = loadLatestPrices();

	screenerCache = buildRecords(listMap, finMap, priceMap);

	const elapsed = Date.now() - startTime;
	console.log(`⏱️ Screener data loaded in ${(elapsed / 1000).toFixed(2)}s`);

	return screenerCache;
}

export function clearCache() {
	screenerCache = null;
}
