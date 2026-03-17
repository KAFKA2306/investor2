import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";
import {
	type CompanyDetail,
	type CompanyGovernance,
	type CompanyInfo,
	ConfigSchema,
	type FinancialData,
} from "../schemas";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const EDINET_DIR = config.paths.edinet;
const JQUANTS_DIR = config.paths.data;

let intelligenceMap: Record<string, unknown> | null = null;
let governanceMap: Record<string, Record<string, CompanyGovernance>> | null =
	null;
let xbrlTextMap: Record<
	string,
	Record<
		string,
		{
			businessDescription?: string;
			riskFactors?: string;
			managementDiscussion?: string;
		}
	>
> | null = null;

interface StockListEntry {
	name: string;
	sector: string;
	market: string;
	code5digit: string;
}
let stockListMap: Map<string, StockListEntry> | null = null;

interface RawFinancialRecord {
	localCode: string;
	disclosedDate: string;
	eps: number | null;
	bps: number | null;
	netSales: number | null;
	operatingProfit: number | null;
	profit: number | null;
	equity: number | null;
	totalAssets: number | null;
	periodEnd: string;
}
let financialDataMap: Map<string, RawFinancialRecord[]> | null = null;

function getIntelligenceMap(): Record<string, unknown> {
	if (!intelligenceMap) {
		const path = resolve(EDINET_DIR, "edinet_10k_intelligence_map.json");
		const content = readFileSync(path, "utf-8");
		intelligenceMap = JSON.parse(content);
	}
	return intelligenceMap || {};
}

function getGovernanceMap(): Record<string, Record<string, CompanyGovernance>> {
	if (!governanceMap) {
		const path = resolve(EDINET_DIR, "edinet_governance_map.json");
		const content = readFileSync(path, "utf-8");
		governanceMap = JSON.parse(content);
	}
	return governanceMap || {};
}

function getXbrlTextMap(): Record<
	string,
	Record<
		string,
		{
			businessDescription?: string;
			riskFactors?: string;
			managementDiscussion?: string;
		}
	>
> {
	if (!xbrlTextMap) {
		const path = resolve(EDINET_DIR, "edinet_xbrl_text_map.json");
		const content = readFileSync(path, "utf-8");
		xbrlTextMap = JSON.parse(content);
	}
	return xbrlTextMap || {};
}

function getStockListMap(): Map<string, StockListEntry> {
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

			const code5digit = parts[0]?.trim();
			const code4digit = code5digit.slice(0, 4);
			const name = parts[1]?.trim();
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
	}
	return stockListMap;
}

function getFinancialDataMap(): Map<string, RawFinancialRecord[]> {
	if (!financialDataMap) {
		financialDataMap = new Map();
		const path = resolve(JQUANTS_DIR, "raw_stock_fin.csv");
		const content = readFileSync(path, "utf-8");
		const lines = content.split("\n");

		const dataByCode = new Map<string, RawFinancialRecord[]>();

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
				eps: !Number.isNaN(eps as number) ? eps : null,
				bps: !Number.isNaN(bps as number) ? bps : null,
				netSales: !Number.isNaN(netSales as number) ? netSales : null,
				operatingProfit: !Number.isNaN(operatingProfit as number)
					? operatingProfit
					: null,
				profit: !Number.isNaN(profit as number) ? profit : null,
				equity: !Number.isNaN(equity as number) ? equity : null,
				totalAssets: !Number.isNaN(totalAssets as number) ? totalAssets : null,
				periodEnd,
			};

			if (!dataByCode.has(localCode)) {
				dataByCode.set(localCode, []);
			}
			dataByCode.get(localCode)?.push(record);
		}

		for (const [code, records] of dataByCode) {
			records.sort((a, b) => a.disclosedDate.localeCompare(b.disclosedDate));
			dataByCode.set(code, records.slice(-5));
		}

		financialDataMap = dataByCode;
	}
	return financialDataMap;
}

function getDocumentsForCompany(edinetCode: string): string[] {
	const docsDir = resolve(EDINET_DIR, "docs");
	const docs: string[] = [];

	const files = readdirSync(docsDir);
	for (const file of files) {
		if (
			file.includes(edinetCode) ||
			file.includes(edinetCode.padStart(5, "0"))
		) {
			docs.push(file);
		}
	}

	return docs.sort().slice(0, 10);
}

export type { CompanyInfo, CompanyGovernance, FinancialData, CompanyDetail };

export async function searchCompanies(query: string): Promise<CompanyInfo[]> {
	const intel = getIntelligenceMap();
	const stockList = getStockListMap();
	const companies: CompanyInfo[] = [];

	if (!query || query.trim().length === 0) {
		return getCompanyList();
	}

	const q = query.toLowerCase();

	const codes =
		Object.keys(intel).length > 0
			? Object.keys(intel)
			: Array.from(stockList.keys());

	for (const code of codes) {
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

	const codes =
		Object.keys(intel).length > 0
			? Object.keys(intel)
			: Array.from(stockList.keys());

	let idx = 0;
	for (const code of codes) {
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

	// Use cached XBRL text if available
	if (includeXBRL) {
		const textMap = getXbrlTextMap();
		const companyTexts = textMap[edinetCode];
		if (companyTexts) {
			const latestDocId = Object.keys(companyTexts).sort().reverse()[0];
			if (latestDocId) {
				const textData = companyTexts[latestDocId];
				detail.overview = {
					businessDescription: textData.businessDescription,
					risks: textData.riskFactors,
					products: textData.managementDiscussion,
				};
			}
		}
	}

	// Get document count
	const docs = getDocumentsForCompany(edinetCode);
	detail.documentCount = docs.length;

	return detail;
}

export async function getCompanyCount(): Promise<number> {
	const intel = getIntelligenceMap();
	const stockList = getStockListMap();

	if (Object.keys(intel).length > 0) {
		return Object.keys(intel).length;
	}

	return stockList.size;
}
