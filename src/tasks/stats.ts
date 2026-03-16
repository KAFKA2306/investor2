import { readdirSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

interface CacheStatistics {
	marketData: {
		stocks: number;
		priceRecords: number;
		finRecords: number;
		dateRange: { start: string; end: string } | null;
		sizeGb: number;
	};
	edinet: {
		companyCount: number;
		documentCount: number;
		sizeGb: number;
	};
	sqlite: {
		market: { sizeGb: number } | null;
		edinet: { sizeGb: number } | null;
		yahoocache: { sizeGb: number } | null;
	};
	lastUpdated: string;
	totalSizeGb: number;
}

const CACHE_ROOT_DIR = resolve(config.paths.data, "..");

function formatBytes(bytes: number): string {
	if (bytes === 0) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB", "TB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
}

function getFileSize(path: string): number {
	return statSync(path).size;
}

function getDirectorySize(dirPath: string): number {
	const files = readdirSync(dirPath, { recursive: true });
	let totalSize = 0;
	for (const file of files) {
		const filePath = resolve(dirPath, file as string);
		const stat = statSync(filePath);
		if (stat.isFile()) {
			totalSize += stat.size;
		}
	}
	return totalSize;
}

function getMarketDataStats(): CacheStatistics["marketData"] {
	const jquantsDir = config.paths.data;
	const stockListPath = resolve(jquantsDir, "raw_stock_list.csv");
	const priceCsvPath = resolve(jquantsDir, "raw_stock_price.csv");
	const finCsvPath = resolve(jquantsDir, "raw_stock_fin.csv");

	let stocks = 0;
	let priceRecords = 0;
	let finRecords = 0;
	let dateRange: { start: string; end: string } | null = null;

	const listData = readFileSync(stockListPath, "utf-8");
	stocks = listData.split("\n").length - 2;

	const priceData = readFileSync(priceCsvPath, "utf-8");
	const lines = priceData.split("\n");
	priceRecords = Math.max(0, lines.length - 2);
	if (lines.length > 2) {
		const firstLine = lines[1]?.split(",")[1] || "";
		const lastLine = lines[lines.length - 2]?.split(",")[1] || "";
		if (firstLine && lastLine) {
			dateRange = { start: firstLine, end: lastLine };
		}
	}

	const finData = readFileSync(finCsvPath, "utf-8");
	finRecords = finData.split("\n").length - 2;

	const sizeGb =
		getFileSize(priceCsvPath) +
		getFileSize(finCsvPath) +
		getFileSize(stockListPath);

	return {
		stocks,
		priceRecords,
		finRecords,
		dateRange,
		sizeGb: sizeGb / (1024 * 1024 * 1024),
	};
}

function getEdinetStats(): CacheStatistics["edinet"] {
	const edinetDir = config.paths.edinet;
	let companyCount = 0;
	let documentCount = 0;

	const cacheDbPath = config.paths.cacheFundamentalEdinet;
	const cacheContent = readFileSync(cacheDbPath, "utf-8");
	const matches = cacheContent.match(/"edinetCode":"[^"]+"/g) || [];
	const uniqueCodes = new Set(matches.map((m) => m.match(/"([^"]+)"$/)?.[1]));
	companyCount = Math.max(uniqueCodes.size, 0);

	const docMatches = cacheContent.match(/"docID":"[^"]+"/g) || [];
	documentCount = new Set(docMatches.map((m) => m.match(/"([^"]+)"$/)?.[1]))
		.size;

	if (companyCount === 0) {
		const items = readdirSync(edinetDir);
		companyCount = items.filter((item) => !item.startsWith(".")).length;

		for (const company of items) {
			const companyPath = resolve(edinetDir, company);
			const stat = statSync(companyPath);
			if (stat.isDirectory()) {
				const docs = readdirSync(companyPath);
				documentCount += docs.filter((d) => !d.startsWith(".")).length;
			}
		}
	}

	const sizeGb = getDirectorySize(edinetDir) / (1024 * 1024 * 1024);

	return { companyCount, documentCount, sizeGb };
}

function getSqliteStats() {
	const cacheDir = config.paths.cache;
	const stats: CacheStatistics["sqlite"] = {
		market: null,
		edinet: null,
		yahoocache: null,
	};

	const sqliteFiles = [
		{ key: "market", path: "market_cache.sqlite" },
		{ key: "edinet", path: "edinet_cache.sqlite" },
		{ key: "yahoocache", path: "yahoo_cache.sqlite" },
	] as const;

	for (const { key, path } of sqliteFiles) {
		const fullPath = resolve(cacheDir, path);
		const size = getFileSize(fullPath) / (1024 * 1024 * 1024);
		stats[key] = { sizeGb: size };
	}

	return stats;
}

function getLastUpdated(): string {
	const dirs = [config.paths.cache, config.paths.data, config.paths.edinet];

	let latestTime = 0;

	for (const dir of dirs) {
		const stat = statSync(dir);
		if (stat.mtimeMs > latestTime) {
			latestTime = stat.mtimeMs;
		}
	}

	return latestTime > 0 ? new Date(latestTime).toISOString() : "Never updated";
}

async function main() {
	console.log(`\n${"━".repeat(70)}`);
	console.log("📊 データキャッシュ統計 — 投資家向けダッシュボード");
	console.log(`${"━".repeat(70)}\n`);

	const stats: CacheStatistics = {
		marketData: getMarketDataStats(),
		edinet: getEdinetStats(),
		sqlite: getSqliteStats(),
		lastUpdated: getLastUpdated(),
		totalSizeGb: 0,
	};

	stats.totalSizeGb =
		stats.marketData.sizeGb +
		stats.edinet.sizeGb +
		(stats.sqlite.market?.sizeGb || 0) +
		(stats.sqlite.edinet?.sizeGb || 0) +
		(stats.sqlite.yahoocache?.sizeGb || 0);

	console.log("🏢 マーケットデータ (Japan Exchange)");
	console.log("─".repeat(70));
	console.log(
		`  📈 カバー銘柄:         ${stats.marketData.stocks.toLocaleString()} 銘柄`,
	);
	console.log(
		`  📊 価格データ:         ${(stats.marketData.priceRecords / 1000).toFixed(1)}k 行`,
	);
	console.log(
		`  💼 財務データ:         ${(stats.marketData.finRecords / 1000).toFixed(1)}k 行`,
	);
	if (stats.marketData.dateRange) {
		console.log(
			`  📅 カバー期間:         ${stats.marketData.dateRange.start} ～ ${stats.marketData.dateRange.end}`,
		);
		console.log(
			`  ⚠️  最新2年データ:     取得予定中（task jquants:fetch:latest）`,
		);
	}
	console.log(
		`  💾 容量:             ${formatBytes(stats.marketData.sizeGb * 1024 * 1024 * 1024)}`,
	);
	console.log("");

	console.log("🏢 企業情報 (EDINET)");
	console.log("─".repeat(70));
	console.log(`  🏛️  カバー企業:         ${stats.edinet.companyCount} 社`);
	console.log(`  📄 企業文書:           ${stats.edinet.documentCount} 件`);
	console.log(
		`  💾 容量:             ${formatBytes(stats.edinet.sizeGb * 1024 * 1024 * 1024)}`,
	);
	console.log("");

	console.log("⚡ キャッシュ (実行時)");
	console.log("─".repeat(70));
	if (stats.sqlite.market) {
		console.log(
			`  📊 マーケットキャッシュ: ${formatBytes(stats.sqlite.market.sizeGb * 1024 * 1024 * 1024)}`,
		);
	} else {
		console.log(`  📊 マーケットキャッシュ: 未生成`);
	}
	if (stats.sqlite.edinet) {
		console.log(
			`  🏢 EDINET キャッシュ:    ${formatBytes(stats.sqlite.edinet.sizeGb * 1024 * 1024 * 1024)}`,
		);
	} else {
		console.log(`  🏢 EDINET キャッシュ:    未生成`);
	}
	if (stats.sqlite.yahoocache) {
		console.log(
			`  🌐 Yahoo! キャッシュ:    ${formatBytes(stats.sqlite.yahoocache.sizeGb * 1024 * 1024 * 1024)}`,
		);
	} else {
		console.log(`  🌐 Yahoo! キャッシュ:    未生成`);
	}
	console.log("");

	console.log("📊 サマリー");
	console.log("─".repeat(70));
	console.log(
		`  🎯 総容量:             ${formatBytes(stats.totalSizeGb * 1024 * 1024 * 1024)}`,
	);
	console.log(`  🕒 最終更新:           ${stats.lastUpdated}`);
	console.log(`  📍 キャッシュ位置:     ${CACHE_ROOT_DIR}`);
	console.log("");
}

main().catch(console.error);
