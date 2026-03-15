import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const CACHE_ROOT = "/mnt/d/investor_all_cached_data";
const EDINET_DIR = resolve(CACHE_ROOT, "edinet");
const JQUANTS_DIR = resolve(CACHE_ROOT, "jquants");

let intelligenceMap: Record<string, any> | null = null;
let stockListMap: Map<string, any> | null = null;

function getIntelligenceMap(): Record<string, any> {
	if (!intelligenceMap) {
		const path = resolve(EDINET_DIR, "edinet_10k_intelligence_map.json");
		const content = readFileSync(path, "utf-8");
		intelligenceMap = JSON.parse(content);
	}
	return intelligenceMap;
}

function getStockListMap(): Map<string, any> {
	if (!stockListMap) {
		stockListMap = new Map();
		const path = resolve(JQUANTS_DIR, "raw_stock_list.csv");
		const content = readFileSync(path, "utf-8");
		const lines = content.split("\n");

		for (let i = 1; i < lines.length; i++) {
			const line = lines[i]?.trim();
			if (!line) continue;

			const parts = line.split(",");
			if (parts.length < 2) continue;

			const code5digit = parts[0]!.trim();
			const code4digit = code5digit.slice(0, 4);
			const name = parts[1]!.trim();
			const sector = parts[7]?.trim();
			const market = parts[8]?.trim();

			stockListMap.set(code4digit, { name, sector, market });
		}
	}
	return stockListMap;
}

export interface CompanyInfo {
	edinetCode: string;
	name: string;
	sector?: string;
	market?: string;
}

export interface CompanyDetail extends CompanyInfo {
	intelligence?: {
		sentiment?: number;
		aiExposure?: number;
		kgCentrality?: number;
	};
}

export async function searchCompanies(query: string): Promise<CompanyInfo[]> {
	const intel = getIntelligenceMap();
	const stockList = getStockListMap();
	const companies: CompanyInfo[] = [];

	if (!query || query.trim().length === 0) {
		return getCompanyList();
	}

	const q = query.toLowerCase();

	for (const code of Object.keys(intel)) {
		const stockInfo = stockList.get(code);
		const name = stockInfo?.name || code;

		if (code.toLowerCase().includes(q) || name.toLowerCase().includes(q)) {
			companies.push({
				edinetCode: code,
				name,
				sector: stockInfo?.sector,
				market: stockInfo?.market,
			});
			if (companies.length >= 100) break;
		}
	}

	return companies;
}

export async function getCompanyList(
	limit: number = 50,
	offset: number = 0,
): Promise<CompanyInfo[]> {
	const intel = getIntelligenceMap();
	const stockList = getStockListMap();
	const companies: CompanyInfo[] = [];

	let idx = 0;
	for (const code of Object.keys(intel)) {
		if (idx < offset) {
			idx++;
			continue;
		}
		if (companies.length >= limit) break;

		const stockInfo = stockList.get(code);
		const name = stockInfo?.name || code;

		companies.push({
			edinetCode: code,
			name,
			sector: stockInfo?.sector,
			market: stockInfo?.market,
		});
		idx++;
	}

	return companies;
}

export async function getCompanyDetail(
	edinetCode: string,
): Promise<CompanyDetail | null> {
	const intel = getIntelligenceMap();
	const stockList = getStockListMap();
	const intelData = intel[edinetCode];

	if (!intelData) return null;

	const stockInfo = stockList.get(edinetCode);
	const name = stockInfo?.name || edinetCode;

	// Get latest intelligence data
	const latestDate = Object.keys(intelData).sort().reverse()[0];
	const latestIntel = latestDate ? intelData[latestDate] : null;

	return {
		edinetCode,
		name,
		sector: stockInfo?.sector,
		market: stockInfo?.market,
		intelligence: latestIntel
			? {
					sentiment: latestIntel.sentiment,
					aiExposure: latestIntel.aiExposure,
					kgCentrality: latestIntel.kgCentrality,
				}
			: undefined,
	};
}

export async function getCompanyCount(): Promise<number> {
	const intel = getIntelligenceMap();
	return Object.keys(intel).length;
}
