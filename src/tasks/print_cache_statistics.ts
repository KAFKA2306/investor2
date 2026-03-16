import { existsSync, readdirSync, statSync } from "fs";
import { resolve } from "path";

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

const CACHE_ROOT = "/mnt/d/investor_all_cached_data";

function formatBytes(bytes: number): string {
	if (bytes === 0) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB", "TB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getFileSize(path: string): number {
	try {
		return statSync(path).size;
	} catch {
		return 0;
	}
}

function getDirectorySize(dirPath: string): number {
	if (!existsSync(dirPath)) return 0;
	try {
		const files = readdirSync(dirPath, { recursive: true });
		let totalSize = 0;
		for (const file of files) {
			const filePath = resolve(dirPath, file as string);
			try {
				const stat = statSync(filePath);
				if (stat.isFile()) {
					totalSize += stat.size;
				}
			} catch {
				// skip
			}
		}
		return totalSize;
	} catch {
		return 0;
	}
}

function getMarketDataStats(): CacheStatistics["marketData"] {
	const jquantsDir = resolve(CACHE_ROOT, "jquants");
	const stockListPath = resolve(jquantsDir, "stock_list.csv");
	const priceCsvPath = resolve(jquantsDir, "raw_stock_price.csv");
	const finCsvPath = resolve(jquantsDir, "raw_stock_fin.csv");

	let stocks = 0;
	let priceRecords = 0;
	let finRecords = 0;
	let dateRange: { start: string; end: string } | null = null;

	// Count stocks from stock_list.csv
	try {
		const fs = require("fs");
		if (existsSync(stockListPath)) {
			const data = fs.readFileSync(stockListPath, "utf-8");
			stocks = data.split("\n").length - 2; // -1 for header, -1 for last empty line
		}
	} catch {
		// continue
	}

	// Count price records
	try {
		const fs = require("fs");
		if (existsSync(priceCsvPath)) {
			const data = fs.readFileSync(priceCsvPath, "utf-8");
			const lines = data.split("\n");
			priceRecords = Math.max(0, lines.length - 2);
			// Extract date range from first and last lines
			if (lines.length > 2) {
				const firstLine = lines[1]?.split(",")[1] || "";
				const lastLine = lines[lines.length - 2]?.split(",")[1] || "";
				if (firstLine && lastLine) {
					dateRange = { start: firstLine, end: lastLine };
				}
			}
		}
	} catch {
		// continue
	}

	// Count fin records
	try {
		const fs = require("fs");
		if (existsSync(finCsvPath)) {
			const data = fs.readFileSync(finCsvPath, "utf-8");
			finRecords = data.split("\n").length - 2;
		}
	} catch {
		// continue
	}

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
	const edinetDir = resolve(CACHE_ROOT, "edinet");
	let companyCount = 0;
	let documentCount = 0;

	// Try to read from SQLite cache first
	try {
		const cacheDbPath = resolve(CACHE_ROOT, "cache/fundamental/edinet.sqlite");
		if (existsSync(cacheDbPath)) {
			const fs = require("fs");
			const cacheContent = fs.readFileSync(cacheDbPath, "utf-8");
			// Count unique edinetCode values in cache (heuristic)
			const matches = cacheContent.match(/"edinetCode":"[^"]+"/g) || [];
			const uniqueCodes = new Set(
				matches.map((m) => m.match(/"([^"]+)"$/)?.[1]),
			);
			companyCount = Math.max(uniqueCodes.size, 0);

			// Try to count documents from JSON content
			const docMatches = cacheContent.match(/"docID":"[^"]+"/g) || [];
			documentCount = new Set(docMatches.map((m) => m.match(/"([^"]+)"$/)?.[1]))
				.size;
		}
	} catch {
		// Fallback to directory scan
	}

	// Fallback: count from directory if SQLite fails
	if (companyCount === 0) {
		try {
			if (existsSync(edinetDir)) {
				const items = readdirSync(edinetDir);
				companyCount = items.filter((item) => !item.startsWith(".")).length;

				// Count documents
				for (const company of items) {
					const companyPath = resolve(edinetDir, company);
					try {
						const stat = statSync(companyPath);
						if (stat.isDirectory()) {
							const docs = readdirSync(companyPath);
							documentCount += docs.filter((d) => !d.startsWith(".")).length;
						}
					} catch {
						// continue
					}
				}
			}
		} catch {
			// continue
		}
	}

	const sizeGb = getDirectorySize(edinetDir) / (1024 * 1024 * 1024);

	return { companyCount, documentCount, sizeGb };
}

function getSqliteStats() {
	const cacheDir = resolve(CACHE_ROOT, "cache");
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
		if (existsSync(fullPath)) {
			const size = getFileSize(fullPath) / (1024 * 1024 * 1024);
			stats[key] = { sizeGb: size };
		}
	}

	return stats;
}

function getLastUpdated(): string {
	const dirs = [
		resolve(CACHE_ROOT, "cache"),
		resolve(CACHE_ROOT, "jquants"),
		resolve(CACHE_ROOT, "edinet"),
	];

	let latestTime = 0;

	for (const dir of dirs) {
		try {
			if (existsSync(dir)) {
				const stat = statSync(dir);
				if (stat.mtimeMs > latestTime) {
					latestTime = stat.mtimeMs;
				}
			}
		} catch {
			// continue
		}
	}

	return latestTime > 0 ? new Date(latestTime).toISOString() : "Never updated";
}

async function main() {
	console.log("\n" + "━".repeat(70));
	console.log("📊 データキャッシュ統計 — 投資家向けダッシュボード");
	console.log("━".repeat(70) + "\n");

	const stats: CacheStatistics = {
		marketData: getMarketDataStats(),
		edinet: getEdinetStats(),
		sqlite: getSqliteStats(),
		lastUpdated: getLastUpdated(),
		totalSizeGb: 0,
	};

	// Calculate total size
	stats.totalSizeGb =
		stats.marketData.sizeGb +
		stats.edinet.sizeGb +
		(stats.sqlite.market?.sizeGb || 0) +
		(stats.sqlite.edinet?.sizeGb || 0) +
		(stats.sqlite.yahoocache?.sizeGb || 0);

	// Display market data section
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

	// Display EDINET section
	console.log("🏢 企業情報 (EDINET)");
	console.log("─".repeat(70));
	console.log(`  🏛️  カバー企業:         ${stats.edinet.companyCount} 社`);
	console.log(`  📄 企業文書:           ${stats.edinet.documentCount} 件`);
	console.log(
		`  💾 容量:             ${formatBytes(stats.edinet.sizeGb * 1024 * 1024 * 1024)}`,
	);
	console.log("");

	// Display SQLite caches section
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

	// Display summary
	console.log("📊 サマリー");
	console.log("─".repeat(70));
	console.log(
		`  🎯 総容量:             ${formatBytes(stats.totalSizeGb * 1024 * 1024 * 1024)}`,
	);
	console.log(`  🕒 最終更新:           ${stats.lastUpdated}`);
	console.log(`  📍 キャッシュ位置:     ${CACHE_ROOT}`);
	console.log("");

	// Display health indicators
	console.log("✅ ステータス指標");
	console.log("─".repeat(70));
	const indicators = [
		{
			name: "マーケットデータ",
			ready: stats.marketData.stocks > 0 && stats.marketData.priceRecords > 0,
		},
		{
			name: "EDINET",
			ready: stats.edinet.companyCount > 0,
		},
		{
			name: "実行時キャッシュ",
			ready: Object.values(stats.sqlite).some((v) => v !== null),
		},
	];

	for (const { name, ready } of indicators) {
		console.log(`  ${ready ? "✓" : "✗"} ${name}`);
	}

	console.log("\n" + "━".repeat(70) + "\n");
}

main().catch(console.error);
