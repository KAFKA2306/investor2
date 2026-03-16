import { readFileSync, readdirSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { fetchAndParseXBRL } from "./xbrl_parser";

const CACHE_ROOT = "/mnt/d/investor_all_cached_data";
const EDINET_DIR = resolve(CACHE_ROOT, "edinet");
const JQUANTS_DIR = resolve(CACHE_ROOT, "jquants");

let intelligenceMap: Record<string, any> | null = null;
let governanceMap: Record<string, any> | null = null;
let stockListMap: Map<string, any> | null = null;
let financialDataMap: Map<string, any> | null = null;

function getIntelligenceMap(): Record<string, any> {
	if (!intelligenceMap) {
		const path = resolve(EDINET_DIR, "edinet_10k_intelligence_map.json");
		if (!existsSync(path)) {
			console.warn(`EDINET intelligence map not found at ${path}`);
			return {};
		}
		try {
			const content = readFileSync(path, "utf-8");
			intelligenceMap = JSON.parse(content);
		} catch (error) {
			console.error(`Failed to load EDINET intelligence map: ${error}`);
			intelligenceMap = {};
		}
	}
	return intelligenceMap;
}

function getGovernanceMap(): Record<string, any> {
	if (!governanceMap) {
		const path = resolve(EDINET_DIR, "edinet_governance_map.json");
		if (!existsSync(path)) {
			console.warn(`EDINET governance map not found at ${path}`);
			return {};
		}
		try {
			const content = readFileSync(path, "utf-8");
			governanceMap = JSON.parse(content);
		} catch (error) {
			console.error(`Failed to load EDINET governance map: ${error}`);
			governanceMap = {};
		}
	}
	return governanceMap;
}

function getStockListMap(): Map<string, any> {
	if (!stockListMap) {
		stockListMap = new Map();
		const path = resolve(JQUANTS_DIR, "raw_stock_list.csv");
		if (!existsSync(path)) {
			console.warn(`Stock list not found at ${path}`);
			return stockListMap;
		}
		try {
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

				stockListMap.set(code4digit, {
					name,
					sector,
					market,
					code5digit,
				});
				stockListMap.set(code5digit, {
					name,
					sector,
					market,
					code5digit,
				});
			}
		} catch (error) {
			console.error(`Failed to load stock list: ${error}`);
		}
	}
	return stockListMap;
}

function getFinancialDataMap(): Map<string, any> {
	if (!financialDataMap) {
		financialDataMap = new Map();
		const path = resolve(JQUANTS_DIR, "raw_stock_fin.csv");
		if (!existsSync(path)) {
			console.warn(`Financial data not found at ${path}`);
			return financialDataMap;
		}
		try {
			const content = readFileSync(path, "utf-8");
			const lines = content.split("\n");

			const dataByCode = new Map<string, any[]>();

			for (let i = 1; i < lines.length; i++) {
				const line = lines[i]?.trim();
				if (!line) continue;

				const parts = line.split(",");
				if (parts.length < 43) continue;

				const localCode = parts[26]?.trim();
				const docType = parts[42]?.trim();

				if (
					!localCode ||
					!docType ||
					!docType.includes("FYFinancialStatements")
				) {
					continue;
				}

				const disclosedDate = parts[1]?.trim();
				if (!disclosedDate) continue;

				const eps = parts[13] ? parseFloat(parts[13]) : null;
				const bps = parts[4] ? parseFloat(parts[4]) : null;
				const netSales = parts[28] ? parseInt(parts[28], 10) : null;
				const operatingProfit = parts[31] ? parseInt(parts[31], 10) : null;
				const profit = parts[33] ? parseInt(parts[33], 10) : null;
				const equity = parts[14] ? parseInt(parts[14], 10) : null;
				const totalAssets = parts[40] ? parseInt(parts[40], 10) : null;
				const periodEnd = parts[10]?.trim() || "";

				const record = {
					localCode,
					disclosedDate,
					eps: !isNaN(eps as number) ? eps : null,
					bps: !isNaN(bps as number) ? bps : null,
					netSales: !isNaN(netSales as number) ? netSales : null,
					operatingProfit: !isNaN(operatingProfit as number)
						? operatingProfit
						: null,
					profit: !isNaN(profit as number) ? profit : null,
					equity: !isNaN(equity as number) ? equity : null,
					totalAssets: !isNaN(totalAssets as number) ? totalAssets : null,
					periodEnd,
				};

				if (!dataByCode.has(localCode)) {
					dataByCode.set(localCode, []);
				}
				dataByCode.get(localCode)!.push(record);
			}

			for (const [code, records] of dataByCode) {
				records.sort((a, b) => a.disclosedDate.localeCompare(b.disclosedDate));
				dataByCode.set(code, records.slice(-5));
			}

			financialDataMap = dataByCode;
		} catch (error) {
			console.error(`Failed to load financial data: ${error}`);
		}
	}
	return financialDataMap;
}

function getDocumentsForCompany(edinetCode: string): string[] {
	const docsDir = resolve(EDINET_DIR, "docs");
	const docs: string[] = [];

	try {
		const files = readdirSync(docsDir);
		for (const file of files) {
			if (
				file.includes(edinetCode) ||
				file.includes(edinetCode.padStart(5, "0"))
			) {
				docs.push(file);
			}
		}
	} catch {
		// docs directory may not exist
	}

	return docs.sort().slice(0, 10);
}

export interface CompanyInfo {
	edinetCode: string;
	name: string;
	sector?: string;
	market?: string;
}

export interface CompanyGovernance {
	boardComposition?: string;
	executiveCompensation?: string;
	riskManagement?: string;
	[key: string]: any;
}

export interface FinancialData {
	eps?: number | null;
	bps?: number | null;
	netSales?: number | null;
	operatingProfit?: number | null;
	profit?: number | null;
	equity?: number | null;
	totalAssets?: number | null;
	periodEnd?: string;
}

export interface CompanyDetail extends CompanyInfo {
	governance?: CompanyGovernance;
	financial?: FinancialData[] | FinancialData;
	documentCount?: number;
	overview?: {
		businessDescription?: string;
		risks?: string;
		products?: string;
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
	includeXBRL: boolean = false,
): Promise<CompanyDetail | null> {
	const intel = getIntelligenceMap();
	const governance = getGovernanceMap();
	const stockList = getStockListMap();
	const financialData = getFinancialDataMap();

	const intelData = intel[edinetCode];
	if (!intelData) return null;

	// Try to find stock info: first try with EDINET code, then try with padded 5-digit version
	let stockInfo = stockList.get(edinetCode);
	let localCode = stockInfo?.code5digit || edinetCode;
	if (!stockInfo) {
		const paddedCode = edinetCode.padEnd(5, "0");
		stockInfo = stockList.get(paddedCode);
		localCode = stockInfo?.code5digit || paddedCode;
	}

	const name = stockInfo?.name || edinetCode;

	const detail: CompanyDetail = {
		edinetCode,
		name,
		sector: stockInfo?.sector,
		market: stockInfo?.market,
	};

	// Get governance data (get latest date)
	const govData = governance[edinetCode];
	if (govData) {
		const latestGovDate = Object.keys(govData).sort().reverse()[0];
		if (latestGovDate) {
			detail.governance = govData[latestGovDate];
		}
	}

	// Get financial data (convert from raw units to 億円)
	const finDataArray =
		financialData.get(localCode) || financialData.get(edinetCode);
	if (finDataArray && Array.isArray(finDataArray)) {
		detail.financial = finDataArray.map((d) => ({
			eps: d.eps || undefined,
			bps: d.bps || undefined,
			netSales: d.netSales ? d.netSales / 100000000 : undefined,
			operatingProfit: d.operatingProfit
				? d.operatingProfit / 100000000
				: undefined,
			profit: d.profit ? d.profit / 100000000 : undefined,
			equity: d.equity ? d.equity / 100000000 : undefined,
			totalAssets: d.totalAssets ? d.totalAssets / 100000000 : undefined,
			periodEnd: d.periodEnd,
		}));
	}

	// Fetch XBRL data if requested (primary source)
	if (includeXBRL) {
		const xbrlData = await fetchAndParseXBRL(edinetCode);
		detail.overview = {
			businessDescription: xbrlData?.businessDescription,
			risks: xbrlData?.riskFactors,
			products: xbrlData?.managementDiscussion,
		};
	}

	// Get document count
	const docs = getDocumentsForCompany(edinetCode);
	detail.documentCount = docs.length;

	return detail;
}

export async function getCompanyCount(): Promise<number> {
	const intel = getIntelligenceMap();
	return Object.keys(intel).length;
}
