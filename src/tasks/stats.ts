import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";
import {
  type CacheStatistics,
  CacheStatisticsSchema,
} from "../shared/cache_statistics";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
  yaml.load(readFileSync("config/default.yaml", "utf-8")),
);
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

  const listData = readFileSync(stockListPath, "utf-8");
  const stocks = Math.max(0, listData.split("\n").length - 2);

  const priceData = readFileSync(priceCsvPath, "utf-8");
  const lines = priceData.split("\n");
  const priceRecords = Math.max(0, lines.length - 2);
  let dateRange: { start: string; end: string } | null = null;
  if (lines.length > 2) {
    const firstLine = lines[1]?.split(",")[1] || "";
    const lastLine = lines[lines.length - 2]?.split(",")[1] || "";
    if (firstLine && lastLine) {
      dateRange = { start: firstLine, end: lastLine };
    }
  }

  const finData = readFileSync(finCsvPath, "utf-8");
  const finRecords = Math.max(0, finData.split("\n").length - 2);

  const sizeBytes =
    getFileSize(priceCsvPath) +
    getFileSize(finCsvPath) +
    getFileSize(stockListPath);

  return {
    stocks,
    priceRecords,
    finRecords,
    dateRange,
    sizeGb: sizeBytes / (1024 * 1024 * 1024),
  };
}

function getEdinetStats(): CacheStatistics["edinet"] {
  const edinetDir = config.paths.edinet;
  const cacheDbPath = config.paths.cacheFundamentalEdinet;
  const cacheContent = readFileSync(cacheDbPath, "utf-8");

  const companyMatches = cacheContent.match(/"edinetCode":"[^"]+"/g) || [];
  const companyCodes = new Set(
    companyMatches.map((match) => match.match(/"([^"]+)"$/)?.[1]),
  );
  const documentMatches = cacheContent.match(/"docID":"[^"]+"/g) || [];
  const documentIds = new Set(
    documentMatches.map((match) => match.match(/"([^"]+)"$/)?.[1]),
  );

  return {
    companyCount: companyCodes.size,
    documentCount: documentIds.size,
    sizeGb: getDirectorySize(edinetDir) / (1024 * 1024 * 1024),
  };
}

function getSqliteStats(): CacheStatistics["sqlite"] {
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
    if (!existsSync(fullPath)) continue;
    stats[key] = { sizeGb: getFileSize(fullPath) / (1024 * 1024 * 1024) };
  }

  return stats;
}

function getLastUpdated(): string {
  const dirs = [config.paths.cache, config.paths.data, config.paths.edinet];
  const latestTime = Math.max(...dirs.map((dir) => statSync(dir).mtimeMs));
  return new Date(latestTime).toISOString();
}

export function collectStats(): CacheStatistics {
  const marketData = getMarketDataStats();
  const edinet = getEdinetStats();
  const sqlite = getSqliteStats();
  const totalSizeGb =
    marketData.sizeGb +
    edinet.sizeGb +
    (sqlite.market?.sizeGb || 0) +
    (sqlite.edinet?.sizeGb || 0) +
    (sqlite.yahoocache?.sizeGb || 0);

  return CacheStatisticsSchema.parse({
    marketData,
    edinet,
    sqlite,
    lastUpdated: getLastUpdated(),
    totalSizeGb,
  });
}

function renderHuman(stats: CacheStatistics): void {
  console.log(`\n${"━".repeat(70)}`);
  console.log("📊 データキャッシュ統計 — 投資家向けダッシュボード");
  console.log(`${"━".repeat(70)}\n`);

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
  console.log(
    `  📊 マーケットキャッシュ: ${stats.sqlite.market ? formatBytes(stats.sqlite.market.sizeGb * 1024 * 1024 * 1024) : "未生成"}`,
  );
  console.log(
    `  🏢 EDINET キャッシュ:    ${stats.sqlite.edinet ? formatBytes(stats.sqlite.edinet.sizeGb * 1024 * 1024 * 1024) : "未生成"}`,
  );
  console.log(
    `  🌐 Yahoo! キャッシュ:    ${stats.sqlite.yahoocache ? formatBytes(stats.sqlite.yahoocache.sizeGb * 1024 * 1024 * 1024) : "未生成"}`,
  );
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

try {
  const stats = collectStats();
  if (process.argv.includes("--json")) {
    process.stdout.write(JSON.stringify(stats));
  } else {
    renderHuman(stats);
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
