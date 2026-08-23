import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { Hono } from "hono";
import yaml from "js-yaml";
import {
	getCompanyCount,
	getCompanyDetail,
	getCompanyList,
	searchCompanies,
} from "../preprocess/edinet";
import { getScreenerData } from "../preprocess/screener";
import { ConfigSchema } from "../shared/schema";

const app = new Hono();
const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);
const CACHE_ROOT_DIR = resolve(config.paths.data, "..");

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

let cachedStats: CacheStatistics | null = null;
let lastStatsUpdate = 0;
const STATS_CACHE_TTL = 30000;
const JSON_CACHE_TTL = 3_600_000;
const JSON_CACHE_PATH = "/tmp/investor_stats_cache.json";

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

function _getMarketDataStats(): CacheStatistics["marketData"] {
	const jquantsDir = config.paths.data;
	const stockListPath = resolve(jquantsDir, "stock_list.csv");
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

function _getEdinetStats(): CacheStatistics["edinet"] {
	const edinetDir = config.paths.edinet;
	let companyCount = 0;
	let documentCount = 0;

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

	const sizeGb = getDirectorySize(edinetDir) / (1024 * 1024 * 1024);

	return { companyCount, documentCount, sizeGb };
}

function _getSqliteStats() {
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

function _getLastUpdated(): string {
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

async function getStats(): Promise<CacheStatistics> {
	const now = Date.now();

	// L1: in-memory cache (30s TTL)
	if (cachedStats && now - lastStatsUpdate < STATS_CACHE_TTL) {
		return cachedStats;
	}

	// L2: pre-computed JSON file (1h TTL)
	if (existsSync(JSON_CACHE_PATH)) {
		try {
			const fileData = JSON.parse(
				readFileSync(JSON_CACHE_PATH, "utf-8"),
			) as CacheStatistics & { generatedAt?: number };
			const fileAge = now - (fileData.generatedAt || 0);
			if (fileAge < JSON_CACHE_TTL) {
				cachedStats = fileData;
				lastStatsUpdate = now;
				return cachedStats;
			}
		} catch {
			// JSON file corrupted or unreadable, fall through to subprocess
		}
	}

	// L3: subprocess fallback (current behavior, ~5s)
	try {
		const proc = Bun.spawn(["bun", "run", "src/tasks/stats.ts"], {
			cwd: process.cwd(),
			stdio: ["inherit", "pipe", "inherit"],
		});

		const output = await new Response(proc.stdout).text();

		const parseNumber = (text: string, pattern: RegExp): number => {
			const match = text.match(pattern);
			const match1 = match?.[1];
			return match1 ? parseInt(match1.replace(/,/g, ""), 10) : 0;
		};

		const parseFloat_ = (text: string, pattern: RegExp): number => {
			const match = text.match(pattern);
			const match1 = match?.[1];
			return match1 ? parseFloat(match1) : 0;
		};

		const parseDate = (
			text: string,
			pattern: RegExp,
		): { start: string; end: string } | null => {
			const match = text.match(pattern);
			const match1 = match?.[1];
			if (!match1) return null;
			const [start, end] = match1.split(" ～ ");
			return { start: start.trim(), end: (end || "").trim() };
		};

		cachedStats = {
			marketData: {
				stocks: parseNumber(output, /📈 カバー銘柄:\s+([\d,]+)/),
				priceRecords: parseNumber(output, /📊 価格データ:\s+([\d.]+)k/),
				finRecords: parseNumber(output, /💼 財務データ:\s+([\d.]+)k/),
				dateRange: parseDate(output, /📅 カバー期間:\s+([^💾]+)/u),
				sizeGb:
					parseFloat_(
						output,
						/マーケットデータ[^容量]*容量:\s+([\d.]+)\s*[KMGT]B/,
					) || 0,
			},
			edinet: {
				companyCount: parseNumber(output, /🏛️\s+カバー企業:\s+([\d,]+)/),
				documentCount: parseNumber(output, /📄 企業文書:\s+([\d,]+)/),
				sizeGb:
					parseFloat_(
						output,
						/企業情報 \([^)]*\)[^容量]*容量:\s+([\d.]+)\s*([KMGT]B)/,
					) || 0,
			},
			sqlite: {
				market: parseFloat_(
					output,
					/📊 マーケットキャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
				)
					? {
							sizeGb:
								parseFloat_(
									output,
									/📊 マーケットキャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
								) / 1024,
						}
					: null,
				edinet: parseFloat_(
					output,
					/🏢 EDINET キャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
				)
					? {
							sizeGb:
								parseFloat_(
									output,
									/🏢 EDINET キャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
								) / 1024,
						}
					: null,
				yahoocache: parseFloat_(
					output,
					/🌐 Yahoo! キャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
				)
					? {
							sizeGb:
								parseFloat_(
									output,
									/🌐 Yahoo! キャッシュ:\s+([\d.]+)\s*([KMGT]B)/,
								) / 1024,
						}
					: null,
			},
			lastUpdated: new Date().toISOString(),
			totalSizeGb: parseFloat_(output, /🎯 総容量:\s+([\d.]+)\s*GB/),
		};
		lastStatsUpdate = now;
	} catch (error) {
		console.error("Failed to get stats:", error);
		cachedStats = {
			marketData: {
				stocks: 0,
				priceRecords: 0,
				finRecords: 0,
				dateRange: null,
				sizeGb: 0,
			},
			edinet: { companyCount: 0, documentCount: 0, sizeGb: 0 },
			sqlite: { market: null, edinet: null, yahoocache: null },
			lastUpdated: "Error",
			totalSizeGb: 0,
		};
	}

	return cachedStats;
}

// Render stats as HTML
function renderStatsCards(stats: CacheStatistics): string {
	const stats_total =
		stats.marketData.sizeGb +
		stats.edinet.sizeGb +
		(stats.sqlite.market?.sizeGb || 0) +
		(stats.sqlite.edinet?.sizeGb || 0) +
		(stats.sqlite.yahoocache?.sizeGb || 0);

	const marketReady =
		stats.marketData.stocks > 0 && stats.marketData.priceRecords > 0;
	const edinetReady = stats.edinet.companyCount > 0;
	const cacheReady = Object.values(stats.sqlite).some((v) => v !== null);

	return `
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
        <div class="text-sm font-medium text-gray-600">📈 カバー銘柄</div>
        <div class="text-3xl font-bold text-gray-900 mt-2">${stats.marketData.stocks.toLocaleString()}</div>
        <div class="text-xs text-gray-500 mt-2">Japan Exchange</div>
      </div>

      <div class="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
        <div class="text-sm font-medium text-gray-600">🏛️  EDINET企業</div>
        <div class="text-3xl font-bold text-gray-900 mt-2">${stats.edinet.companyCount.toLocaleString()}</div>
        <div class="text-xs text-gray-500 mt-2">企業情報</div>
      </div>

      <div class="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
        <div class="text-sm font-medium text-gray-600">💾 総容量</div>
        <div class="text-3xl font-bold text-gray-900 mt-2">${formatBytes(stats_total * 1024 * 1024 * 1024)}</div>
        <div class="text-xs text-gray-500 mt-2">キャッシュ総量</div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">マーケットデータ</span>
          <span class="${marketReady ? "text-green-600" : "text-gray-400"}">
            ${marketReady ? "✅" : "⏳"}
          </span>
        </div>
        <div class="mt-3 space-y-2 text-sm text-gray-600">
          <div>📊 ${(stats.marketData.priceRecords / 1000).toFixed(1)}k 行</div>
          <div>💼 ${(stats.marketData.finRecords / 1000).toFixed(1)}k 行</div>
          ${
						stats.marketData.dateRange
							? `<div>📅 ${stats.marketData.dateRange.start} ~ ${stats.marketData.dateRange.end}</div>`
							: ""
					}
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">EDINET</span>
          <span class="${edinetReady ? "text-green-600" : "text-gray-400"}">
            ${edinetReady ? "✅" : "⏳"}
          </span>
        </div>
        <div class="mt-3 space-y-2 text-sm text-gray-600">
          <div>📄 ${stats.edinet.documentCount.toLocaleString()} 件</div>
          <div>💾 ${formatBytes(stats.edinet.sizeGb * 1024 * 1024 * 1024)}</div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">実行時キャッシュ</span>
          <span class="${cacheReady ? "text-green-600" : "text-gray-400"}">
            ${cacheReady ? "✅" : "⏳"}
          </span>
        </div>
        <div class="mt-3 space-y-2 text-sm text-gray-600">
          ${
						stats.sqlite.market
							? `<div>📊 ${formatBytes(stats.sqlite.market.sizeGb * 1024 * 1024 * 1024)}</div>`
							: "<div>未生成</div>"
					}
          ${
						stats.sqlite.edinet
							? `<div>🏢 ${formatBytes(stats.sqlite.edinet.sizeGb * 1024 * 1024 * 1024)}</div>`
							: ""
					}
        </div>
      </div>
    </div>

    <div class="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
      <div>🕒 最終更新: ${stats.lastUpdated}</div>
      <div>📍 キャッシュ位置: ${CACHE_ROOT_DIR}</div>
    </div>
  `;
}

// Dashboard page
app.get("/", async (c) => {
	const stats = await getStats();
	return c.html(`
    <!DOCTYPE html>
    <html lang="ja" data-theme="light">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>📊 キャッシュダッシュボード</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
      <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    </head>
    <body>
      <!-- Navbar -->
      <div class="navbar bg-base-100 shadow">
        <div class="flex-1">
          <a class="btn btn-ghost text-2xl">📈 AAARTS ダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-primary">System Home</a>
          <a href="/screener" class="btn btn-sm btn-ghost">Screener</a>
          <a href="/company" class="btn btn-sm btn-ghost">Company Search</a>
          <a href="/links" class="btn btn-sm btn-ghost">Link Directory</a>
        </div>
      </div>

      <div class="min-h-screen">
        <!-- Main Content -->
        <div class="max-w-7xl mx-auto p-6">
          <div id="stats" hx-trigger="load" hx-get="/api/stats" hx-swap="innerHTML">
            ${renderStatsCards(stats)}
          </div>
        </div>
      </div>
    </body>
    </html>
  `);
});

// API: Get stats
app.get("/api/stats", async (c) => {
	const stats = await getStats();
	return c.html(renderStatsCards(stats));
});

// API: Refresh cache (trigger task get:all)
app.post("/api/refresh", async (c) => {
	try {
		cachedStats = null;
		lastStatsUpdate = 0;
		const proc = Bun.spawn(["bun", "run", "task", "get:all"], {
			cwd: process.cwd(),
		});
		const _output = await new Response(proc.stdout).text();
		const stats = await getStats();

		return c.html(`
      <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <div class="text-green-700 font-medium">✅ キャッシュ更新開始</div>
        <div class="text-sm text-green-600 mt-1">バックグラウンドで実行中...</div>
      </div>
      ${renderStatsCards(stats)}
    `);
	} catch (error) {
		return c.html(`
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div class="text-red-700 font-medium">❌ エラー</div>
        <div class="text-sm text-red-600 mt-1">${error instanceof Error ? error.message : "不明なエラー"}</div>
      </div>
    `);
	}
});

// Stock Screener view
app.get("/screener", async (c) => {
	const data = await getScreenerData();
	const pageSize = 50;
	const pageData = data.slice(0, pageSize);
	const totalPages = Math.ceil(data.length / pageSize);

	const resultsHtml = `
    <div class="card bg-white shadow">
      <div class="card-body">
        <h2 class="card-title">検索結果: ${data.length} 件（1/${totalPages}ページ）</h2>
        <div class="overflow-x-auto">
          <table class="table table-zebra table-sm">
            <thead>
              <tr>
                <th>コード</th>
                <th>企業名</th>
                <th>業種</th>
                <th>市場</th>
                <th>株価(¥)</th>
                <th>時価総額(億)</th>
                <th>PER</th>
                <th>PBR</th>
                <th>ROE(%)</th>
                <th>売上高(億)</th>
                <th>営業利益率(%)</th>
              </tr>
            </thead>
            <tbody>
              ${pageData
								.map(
									(stock) => `
                <tr class="hover">
                  <td><code class="text-sm">${stock.code}</code></td>
                  <td><strong class="text-sm">${stock.name}</strong></td>
                  <td><span class="badge badge-sm badge-secondary">${stock.sectorName}</span></td>
                  <td class="text-xs">${stock.market}</td>
                  <td>¥${stock.price.toLocaleString()}</td>
                  <td>${stock.marketCap.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${Number.isNaN(stock.per) ? "N/A" : stock.per.toFixed(1)}x</td>
                  <td>${Number.isNaN(stock.pbr) ? "N/A" : stock.pbr.toFixed(2)}x</td>
                  <td class="${stock.roe > 0 ? "text-green-600" : "text-red-600"}">
                    ${Number.isNaN(stock.roe) ? "N/A" : stock.roe.toFixed(1)}%
                  </td>
                  <td>${stock.netSales.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${Number.isNaN(stock.operatingMargin) ? "N/A" : stock.operatingMargin.toFixed(1)}%</td>
                </tr>
              `,
								)
								.join("")}
            </tbody>
          </table>
        </div>
        ${totalPages > 1 ? renderPagination(1, totalPages) : ""}
      </div>
    </div>
  `;

	return c.html(`
    <!DOCTYPE html>
    <html lang="ja" data-theme="light">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>銘柄スクリーニング</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
      <script src="https://unpkg.com/htmx.org@1.9.10"></script>
      <script>
        document.addEventListener('DOMContentLoaded', async () => {
          const select = document.getElementById('sector-select');
          try {
            const res = await fetch('/api/screener/sectors');
            const sectors = await res.json();
            let html = '<option value="">すべて</option>';
            for (const s of sectors) {
              html += '<option value="' + s.code + '">' + s.name + '</option>';
            }
            select.innerHTML = html;
          } catch (e) {
            console.error('Failed to load sectors:', e);
            select.innerHTML = '<option value="">エラー</option>';
          }
        });
      </script>
    </head>
    <body>
      <div class="navbar bg-base-100 shadow">
        <div class="flex-1">
          <a class="btn btn-ghost text-2xl">📈 AAARTS ダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">System Home</a>
          <a href="/screener" class="btn btn-sm btn-primary">Screener</a>
          <a href="/company" class="btn btn-sm btn-ghost">Company Search</a>
          <a href="/links" class="btn btn-sm btn-ghost">Link Directory</a>
        </div>
      </div>

      <div class="max-w-7xl mx-auto p-6">
        <h1 class="text-4xl font-bold mb-6">📊 銘柄スクリーニング</h1>

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <!-- Filter Sidebar -->
          <div class="card bg-white shadow h-fit">
            <div class="card-body">
              <h2 class="card-title text-lg">フィルター</h2>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">銘柄コード/企業名</span>
                </label>
                <input
                  type="text"
                  id="search-input"
                  name="search-input"
                  placeholder="検索..."
                  class="input input-bordered w-full"
                  hx-trigger="keyup changed delay:500ms"
                  hx-get="/api/screener"
                  hx-target="#results"
                  hx-include="#search-input,#sector-select,#market-select"
                  hx-swap="innerHTML"
                />
              </div>

              <div class="form-control mt-4">
                <label class="label">
                  <span class="label-text">業種</span>
                </label>
                <select
                  id="sector-select"
                  name="sector-select"
                  class="select select-bordered w-full"
                  hx-trigger="change"
                  hx-get="/api/screener"
                  hx-target="#results"
                  hx-include="#search-input,#sector-select,#market-select"
                  hx-swap="innerHTML"
                >
                  <option value="">読み込み中...</option>
                </select>
              </div>

              <div class="form-control mt-4">
                <label class="label">
                  <span class="label-text">市場</span>
                </label>
                <select
                  id="market-select"
                  name="market-select"
                  class="select select-bordered w-full"
                  hx-trigger="change"
                  hx-get="/api/screener"
                  hx-target="#results"
                  hx-include="#search-input,#sector-select,#market-select"
                >
                  <option value="">すべて</option>
                  <option value="プライム">プライム</option>
                  <option value="スタンダード">スタンダード</option>
                  <option value="グロース">グロース</option>
                </select>
              </div>

              <button
                hx-get="/api/screener"
                hx-target="#results"
                hx-include="#search-input,#sector-select,#market-select"
                hx-swap="innerHTML"
                class="btn btn-primary w-full mt-4"
              >
                リセット
              </button>
            </div>
          </div>

          <!-- Results Table -->
          <div class="lg:col-span-3">
            <div id="results">
              ${resultsHtml}
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
  `);
});

// Company Finder view
app.get("/company", async (c) => {
	const companyCount = await getCompanyCount();

	return c.html(`
    <!DOCTYPE html>
    <html lang="ja" data-theme="light">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>企業情報検索</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
      <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    </head>
    <body>
      <div class="navbar bg-base-100 shadow">
        <div class="flex-1">
          <a class="btn btn-ghost text-2xl">📈 AAARTS ダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">System Home</a>
          <a href="/screener" class="btn btn-sm btn-ghost">Screener</a>
          <a href="/company" class="btn btn-sm btn-primary">Company Search</a>
          <a href="/links" class="btn btn-sm btn-ghost">Link Directory</a>
        </div>
      </div>

      <div class="max-w-7xl mx-auto p-6">
        <h1 class="text-4xl font-bold mb-6">🏢 企業情報検索（EDINET）</h1>

        <!-- Search -->
        <div class="card bg-white shadow mb-6">
          <div class="card-body">
            <h2 class="card-title">企業を検索</h2>
            <div class="flex gap-2">
              <input
                type="text"
                placeholder="企業名 or EDINET コード"
                id="company-search"
                name="q"
                hx-trigger="keyup changed delay:500ms"
                hx-get="/api/company/search"
                hx-target="#company-results"
                hx-swap="innerHTML"
                class="input input-bordered w-full"
              />
              <button
                hx-get="/api/company/list"
                hx-target="#company-results"
                hx-swap="innerHTML"
                class="btn btn-primary"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        <!-- Company List -->
        <div id="company-results">
          <div class="alert alert-info">
            <span>カバー企業: <strong>${companyCount.toLocaleString()}</strong> 社</span>
          </div>
        </div>
      </div>
    </body>
    </html>
  `);
});

// API: Stock Screener results
app.get("/api/screener", async (c) => {
	const data = await getScreenerData();
	const q = c.req.query("search-input") || "";
	const sector = c.req.query("sector-select") || "";
	const market = c.req.query("market-select") || "";

	let filtered = data;

	if (q) {
		const lower = q.toLowerCase();
		filtered = filtered.filter(
			(s) =>
				s.code.includes(q) ||
				s.name.toLowerCase().includes(lower) ||
				s.sectorName.toLowerCase().includes(lower),
		);
	}

	if (sector) {
		filtered = filtered.filter((s) => s.sectorCode === sector);
	}

	if (market) {
		filtered = filtered.filter((s) => s.market === market);
	}

	const pageSize = 50;
	const page = parseInt(c.req.query("page") || "1", 10);
	const start = (page - 1) * pageSize;
	const end = start + pageSize;
	const pageData = filtered.slice(start, end);
	const totalPages = Math.ceil(filtered.length / pageSize);

	return c.html(`
    <div class="card bg-white shadow">
      <div class="card-body">
        <h2 class="card-title">検索結果: ${filtered.length} 件（${page}/${totalPages}ページ）</h2>
        <div class="overflow-x-auto">
          <table class="table table-zebra table-sm">
            <thead>
              <tr>
                <th>コード</th>
                <th>企業名</th>
                <th>業種</th>
                <th>市場</th>
                <th>株価(¥)</th>
                <th>時価総額(億)</th>
                <th>PER</th>
                <th>PBR</th>
                <th>ROE(%)</th>
                <th>売上高(億)</th>
                <th>営業利益率(%)</th>
              </tr>
            </thead>
            <tbody>
              ${pageData
								.map(
									(stock) => `
                <tr class="hover">
                  <td><code class="text-sm">${stock.code}</code></td>
                  <td><strong class="text-sm">${stock.name}</strong></td>
                  <td><span class="badge badge-sm badge-secondary">${stock.sectorName}</span></td>
                  <td class="text-xs">${stock.market}</td>
                  <td>¥${stock.price.toLocaleString()}</td>
                  <td>${stock.marketCap.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${Number.isNaN(stock.per) ? "N/A" : stock.per.toFixed(1)}x</td>
                  <td>${Number.isNaN(stock.pbr) ? "N/A" : stock.pbr.toFixed(2)}x</td>
                  <td class="${stock.roe > 0 ? "text-green-600" : "text-red-600"}">
                    ${Number.isNaN(stock.roe) ? "N/A" : stock.roe.toFixed(1)}%
                  </td>
                  <td>${stock.netSales.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${Number.isNaN(stock.operatingMargin) ? "N/A" : stock.operatingMargin.toFixed(1)}%</td>
                </tr>
              `,
								)
								.join("")}
            </tbody>
          </table>
        </div>

        ${totalPages > 1 ? renderPagination(page, totalPages) : ""}
      </div>
    </div>
  `);
});

function renderPagination(page: number, totalPages: number): string {
	const buttons = [];
	const hxAttrs =
		'hx-include="#search-input,#sector-select,#market-select" hx-swap="innerHTML"';
	if (page > 1) {
		buttons.push(
			`<button hx-get="/api/screener?page=${page - 1}" hx-target="#results" ${hxAttrs} class="btn btn-sm">← 前</button>`,
		);
	}

	for (
		let i = Math.max(1, page - 2);
		i <= Math.min(totalPages, page + 2);
		i++
	) {
		buttons.push(
			`<button hx-get="/api/screener?page=${i}" hx-target="#results" ${hxAttrs} class="btn btn-sm ${i === page ? "btn-primary" : ""}">${i}</button>`,
		);
	}

	if (page < totalPages) {
		buttons.push(
			`<button hx-get="/api/screener?page=${page + 1}" hx-target="#results" ${hxAttrs} class="btn btn-sm">次 →</button>`,
		);
	}

	return `<div class="flex justify-center gap-2 mt-4">${buttons.join("")}</div>`;
}

// API: Get all sectors
app.get("/api/screener/sectors", async (c) => {
	const data = await getScreenerData();
	const sectorsMap = new Map<string, string>(); // sectorCode -> sectorName

	for (const stock of data) {
		if (!sectorsMap.has(stock.sectorCode)) {
			sectorsMap.set(stock.sectorCode, stock.sectorName);
		}
	}

	const sectors = Array.from(sectorsMap.entries())
		.map(([code, name]) => ({ code, name }))
		.sort((a, b) => a.name.localeCompare(b.name));

	return c.json(sectors);
});

// API: Company search
// API: Company list
app.get("/api/company/list", async (c) => {
	const page = parseInt(c.req.query("page") || "0", 10);
	const limit = 20;
	const offset = page * limit;

	const companies = await getCompanyList(limit, offset);

	if (companies.length === 0) {
		return c.html(`
      <div class="alert alert-warning">
        <span>該当する企業がありません</span>
      </div>
    `);
	}

	return c.html(`
    <div class="grid gap-4">
      ${companies
				.map(
					(comp) => `
        <div class="card bg-white shadow">
          <div class="card-body">
            <h3 class="card-title">${comp.name}</h3>
            <p class="text-sm text-gray-600">EDINET コード: <code>${comp.edinetCode}</code></p>
            <p>業種: <strong>${comp.sector || "不明"}</strong> | 市場: <strong>${comp.market || "不明"}</strong></p>
            <div class="card-actions justify-end">
              <a href="/edinet/${comp.edinetCode}" class="btn btn-sm btn-primary">詳細</a>
            </div>
          </div>
        </div>
      `,
				)
				.join("")}
    </div>
  `);
});

// API: Company search
app.get("/api/company/search", async (c) => {
	const q = c.req.query("q") || "";
	const companies = await searchCompanies(q);

	if (companies.length === 0) {
		return c.html(`
      <div class="alert alert-warning">
        <span>「${q}」に該当する企業がありません</span>
      </div>
    `);
	}

	return c.html(`
    <div class="grid gap-4">
      ${companies
				.map(
					(comp) => `
        <div class="card bg-white shadow">
          <div class="card-body">
            <h3 class="card-title">${comp.name}</h3>
            <p class="text-sm text-gray-600">EDINET コード: <code>${comp.edinetCode}</code></p>
            <p>業種: <strong>${comp.sector || "不明"}</strong> | 市場: <strong>${comp.market || "不明"}</strong></p>
            <div class="card-actions justify-end">
              <a href="/edinet/${comp.edinetCode}" class="btn btn-sm btn-primary">詳細</a>
            </div>
          </div>
        </div>
      `,
				)
				.join("")}
    </div>
  `);
});

// Page: Company detail
app.get("/edinet/:code", async (c) => {
	const code = c.req.param("code");
	const company = await getCompanyDetail(code, true);

	if (!company) {
		return c.html(`
      <div class="alert alert-error">
        <span>企業が見つかりません: ${code}</span>
      </div>
    `);
	}

	return c.html(`
    <!DOCTYPE html>
    <html lang="ja" data-theme="light">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>${company.name} - EDINET</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
      <div class="navbar bg-base-100 shadow">
        <div class="flex-1">
          <a class="btn btn-ghost text-2xl">📈 AAARTS ダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">System Home</a>
          <a href="/screener" class="btn btn-sm btn-ghost">Screener</a>
          <a href="/company" class="btn btn-sm btn-primary">Company Search</a>
          <a href="/links" class="btn btn-sm btn-ghost">Link Directory</a>
        </div>
      </div>

      <div class="max-w-7xl mx-auto p-6">
        <div class="mb-6">
          <a href="/company" class="btn btn-sm btn-ghost">← 企業一覧に戻る</a>
        </div>

        <!-- Company Header -->
        <div class="card bg-white shadow mb-6">
          <div class="card-body">
            <h1 class="text-4xl font-bold">${company.name}</h1>
            <div class="grid grid-cols-2 gap-4 mt-4">
              <div>
                <p class="text-sm text-gray-600">EDINET コード</p>
                <p class="text-xl font-semibold">${company.edinetCode}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">業種</p>
                <p class="text-xl font-semibold">${company.sector || "不明"}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">市場</p>
                <p class="text-xl font-semibold">${company.market || "不明"}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">上場日</p>
                <p class="text-xl font-semibold">${company.listingDate || "不明"}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Overview Section (XBRL Text) -->
        ${
					company.overview
						? `
          <div class="card bg-white shadow mb-6">
            <div class="card-body">
              <h2 class="card-title">企業概要（テキスト情報）</h2>
              <div class="space-y-4">
                ${
									company.overview.businessDescription
										? `
                <div>
                  <h3 class="font-semibold text-gray-800 mb-2">事業内容</h3>
                  <p class="text-sm text-gray-700 whitespace-pre-wrap">${String(company.overview.businessDescription).slice(0, 500)}</p>
                </div>
                `
										: ""
								}
                ${
									company.overview.risks
										? `
                <div>
                  <h3 class="font-semibold text-gray-800 mb-2">リスク要因</h3>
                  <p class="text-sm text-gray-700 whitespace-pre-wrap">${String(company.overview.risks).slice(0, 500)}</p>
                </div>
                `
										: ""
								}
                ${
									company.overview.products
										? `
                <div>
                  <h3 class="font-semibold text-gray-800 mb-2">事業セグメント</h3>
                  <p class="text-sm text-gray-700 whitespace-pre-wrap">${String(company.overview.products).slice(0, 500)}</p>
                </div>
                `
										: ""
								}
              </div>
            </div>
          </div>
        `
						: ""
				}

        <!-- Governance Section -->
        ${
					company.governance
						? `
          <div class="card bg-white shadow mb-6">
            <div class="card-body">
              <h2 class="card-title">ガバナンス</h2>
              <div class="grid grid-cols-1 gap-4">
                ${Object.entries(company.governance)
									.slice(0, 5)
									.map(([key, value]) => {
										const displayKey = key.replace(/([A-Z])/g, " $1").trim();
										return `<div>
                  <p class="text-sm text-gray-600">${displayKey}</p>
                  <p class="font-semibold">${String(value).slice(0, 100)}</p>
                </div>`;
									})
									.join("")}
              </div>
            </div>
          </div>
        `
						: ""
				}

        <!-- Financial Section -->
        ${
					company.financial
						? (
								() => {
									const latestFin = Array.isArray(company.financial)
										? company.financial[company.financial.length - 1]
										: company.financial;
									if (!latestFin) return "";
									return `
          <div class="card bg-white shadow mb-6">
            <div class="card-body">
              <h2 class="card-title">財務概要</h2>
              <p class="text-sm text-gray-600 mb-4">期末: ${latestFin.periodEnd || "不明"}</p>
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                ${
									latestFin.eps !== null && latestFin.eps !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">EPS</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.eps === "number" ? latestFin.eps.toFixed(2) : "N/A"}</p>
                </div>`
										: ""
								}
                ${
									latestFin.bps !== null && latestFin.bps !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">BPS</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.bps === "number" ? latestFin.bps.toFixed(2) : "N/A"}</p>
                </div>`
										: ""
								}
                ${
									latestFin.netSales !== null &&
									latestFin.netSales !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">売上高</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.netSales === "number" ? latestFin.netSales.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									latestFin.profit !== null && latestFin.profit !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">純利益</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.profit === "number" ? latestFin.profit.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									latestFin.equity !== null && latestFin.equity !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">自己資本</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.equity === "number" ? latestFin.equity.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									latestFin.totalAssets !== null &&
									latestFin.totalAssets !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">総資産</p>
                  <p class="text-lg font-bold">¥${typeof latestFin.totalAssets === "number" ? latestFin.totalAssets.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
              </div>
            </div>
          </div>
        `;
								}
							)()
						: ""
				}

        <!-- Financial Chart Section -->
        ${
					company.financial && Array.isArray(company.financial)
						? `
          <div class="card bg-white shadow mb-6">
            <div class="card-body">
              <h2 class="card-title">財務指標の推移</h2>
              <div class="w-full" style="max-height: 400px;">
                <canvas id="financialChart"></canvas>
              </div>
              <script>
                const chartData = ${JSON.stringify(company.financial)};
                const periods = chartData.map(d => d.periodEnd || d.disclosedDate);
                const ctx = document.getElementById('financialChart').getContext('2d');
                new Chart(ctx, {
                  type: 'bar',
                  data: {
                    labels: periods,
                    datasets: [
                      {
                        label: 'EPS (¥)',
                        data: chartData.map(d => d.eps || null),
                        backgroundColor: '#3b82f6',
                        yAxisID: 'y1'
                      },
                      {
                        label: '売上高 (億円)',
                        data: chartData.map(d => d.netSales || null),
                        backgroundColor: '#f59e0b',
                        yAxisID: 'y2'
                      },
                      {
                        label: '純利益 (億円)',
                        data: chartData.map(d => d.profit || null),
                        backgroundColor: '#ef4444',
                        yAxisID: 'y3'
                      },
                      {
                        label: '自己資本 (億円)',
                        data: chartData.map(d => d.equity || null),
                        backgroundColor: '#8b5cf6',
                        yAxisID: 'y4'
                      }
                    ]
                  },
                  options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: true, position: 'top' }
                    },
                    scales: {
                      x: { stacked: false },
                      y1: {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'EPS (¥)' },
                        beginAtZero: true
                      },
                      y2: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: '売上高 (億円)' },
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }
                      },
                      y3: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: '純利益 (億円)' },
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }
                      },
                      y4: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: '自己資本 (億円)' },
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }
                      }
                    }
                  }
                });
              </script>
            </div>
          </div>
        `
						: ""
				}

        <!-- Documents Section -->
        ${
					company.documentCount && company.documentCount > 0
						? `
          <div class="card bg-white shadow">
            <div class="card-body">
              <h2 class="card-title">提出文書</h2>
              <p class="text-sm text-gray-600 mb-4"><strong>${company.documentCount}</strong> 件の提出文書があります</p>
              <div class="alert alert-info">
                <span>EDINET 提出文書は /edinet/docs ディレクトリに保存されています</span>
              </div>
            </div>
          </div>
        `
						: ""
				}

      </div>
    </body>
    </html>
  `);
});

interface ReferenceLink {
	title: string;
	url: string;
	category: string;
	description: string;
	features: string[];
	tags: string[];
	badge?: string;
}

const referenceLinks: ReferenceLink[] = [
	{
		title: "The社史",
		url: "https://the-shashi.com/",
		category: "企業史・歴史",
		description:
			"日本企業の歴史、創業時からの沿革や社史を集約したデータベース。過去の経営判断の変遷や長期的な企業の歩みを深掘りするために最適です。",
		features: [
			"全国各地の様々な企業の社史・記念誌を横断検索可能",
			"企業のルーツや過去のイノベーションの軌跡を追跡",
			"長期的な産業史・企業経営の文脈を理解するための一次史料",
		],
		tags: ["社史", "沿革", "企業歴史"],
		badge: "歴史データベース",
	},
	{
		title: "ザイマニ | 財務分析マニュアル",
		url: "https://zaimani.com/",
		category: "日本企業 財務・IR",
		description:
			"日系企業の財務データを非常に視覚的で分かりやすく可視化・分析できるポータル。財務分析の初心者からプロまで直感的に学べる解説も豊富です。",
		features: [
			"企業の財務諸表を直感的で美しいグラフに自動変換",
			"主要な財務指標（安全性、収益性、効率性）の自動計算とスコアリング",
			"業界平均やライバル企業との比較機能",
		],
		tags: ["財務分析", "グラフ可視化", "財務マニュアル"],
		badge: "直感ビジュアル",
	},
	{
		title: "有報キャッチャー",
		url: "https://ufocatch.com/",
		category: "日本企業 財務・IR",
		description:
			"日本の有価証券報告書や適時開示情報を素早くキャッチし、全文検索や閲覧を可能にするサービス。最新の開示情報の収集に不可欠なツールです。",
		features: [
			"EDINETおよびTDnetの開示データをリアルタイムで追跡",
			"PDFやXBRLデータの高速ダウンロードと全文検索機能",
			"RSSや通知機能によるお気に入り企業の開示ウォッチ",
		],
		tags: ["有価証券報告書", "適時開示", "XBRL"],
		badge: "開示速報",
	},
	{
		title: "IR気象台",
		url: "https://irweather.jp/",
		category: "日本企業 財務・IR",
		description:
			"企業の決算発表やIR情報の質、ネガティブ/ポジティブの度合いを、天気に例えて分かりやすく可視化する独自性の高いIR分析ツールです。",
		features: [
			"開示情報のトーンや市場の反応を「天気」マークで直感表示",
			"決算のサプライズ度やリスク要因の増減をすばやく把握",
			"企業のIRへの熱量や透明性の変化を可視化",
		],
		tags: ["IRトーン分析", "決算サプライズ", "天気マーク"],
		badge: "感情・トーン分析",
	},
	{
		title: "KabuBerry",
		url: "https://kabuberry.com/",
		category: "日本企業 財務・IR",
		description:
			"個人投資家が集まり、企業のIR説明会や決算分析を行う国内最大級 of IRコミュニティ・イベントプラットフォーム。一次情報を生の声で学べます。",
		features: [
			"企業の経営陣を招いたIR説明会の定期開催とレポート公開",
			"投資家目線でのリアルな質疑応答や企業へのフィードバック",
			"多様なセクターの個人投資家による決算・業績分析ディスカッション",
		],
		tags: ["IR説明会", "投資家コミュニティ", "一次情報"],
		badge: "投資家対話",
	},
	{
		title: "IR Searcher",
		url: "https://ir-searcher.com/",
		category: "日本企業 財務・IR",
		description:
			"大量の決算説明会資料や適時開示書類から、特定のキーワードやセグメント情報を横断的に一瞬で検索できる高機能IRデータベースです。",
		features: [
			"決算説明会スクリプトや補足資料のテキスト全文を検索対象に指定可能",
			"新事業分野や注目技術キーワードの企業露出度を定量的・定性的に比較",
			"複数のPDF書類をまとめてブラウザ上で素早く確認可能",
		],
		tags: ["IR検索", "説明会資料", "全文検索"],
		badge: "キーワード横断",
	},
	{
		title: "SEC EDGAR Advanced Search",
		url: "https://www.sec.gov/edgar/search/",
		category: "米国企業・一次情報",
		description:
			"米国証券取引委員会（SEC）の公式提出資料検索システム。米国の全上場企業の10-K、10-Q、インサイダー取引報告など、すべての一次情報源へ直接アクセスできます。",
		features: [
			"高度なクエリ構文を使用した提出書類内の全文テキスト検索",
			"提出日、企業、フォームタイプ（例：10-K, 8-K）による強力なフィルタリング",
			"企業間の財務報告書の比較とデータのCSV/XBRL形式での取得",
		],
		tags: ["SEC", "10-K/10-Q", "Edgar", "米国株"],
		badge: "米国公式一次情報",
	},
	{
		title: "OpenInsider",
		url: "http://openinsider.com/",
		category: "米国企業・一次情報",
		description:
			"米国企業の役員や大株主（インサイダー）による株式の売買取引（Form 4）情報をリアルタイムに収集・集計し、検索・フィルタリングできる極めて強力なサイトです。",
		features: [
			"CEOやCFOによる自社株買い（Insider Purchase）のリアルタイム追跡",
			"売買の規模、企業規模、取引の種類による高度なスクリーニング",
			"インサイダー取引のクラスタリング（複数役員が同時購入している企業）の検出",
		],
		tags: ["インサイダー取引", "自社株買い", "Form 4", "スマートマネー"],
		badge: "スマートマネー追跡",
	},
	{
		title: "BeatAndRaise",
		url: "https://www.beatandraise.com/",
		category: "米国企業・一次情報",
		description:
			"米国上場企業の決算発表結果（EPSや売上高が市場予想を上回ったか：Beat、または下回ったか：Miss）と業績見通し（Guidance：Raise）を素早く整理して表示する決算特化サイトです。",
		features: [
			"決算サプライズ（EPS/売上高対コンセンサス予想）の瞬時判定表示",
			"将来のガイダンス情報の上方修正・下方修正の分かりやすいビジュアル表示",
			"決算期カレンダーと重要指標のリアルタイム更新",
		],
		tags: ["決算サプライズ", "EPS/売上高", "業績見通し", "米国株決算"],
		badge: "決算サプライズ",
	},
];

app.get("/links", async (c) => {
	return c.html(`
<!DOCTYPE html>
<html lang="ja" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🔗 企業分析・情報収集リンク集</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://cdn.jsdelivr.net/npm/daisyui@4.7.2/dist/full.min.css" rel="stylesheet" type="text/css" />
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: radial-gradient(circle at 50% 0%, #0d111d 0%, #07090e 100%);
    }
    .glass-card {
      background: rgba(13, 20, 35, 0.6);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
      background: rgba(20, 30, 55, 0.8);
      border-color: rgba(99, 102, 241, 0.4);
      transform: translateY(-4px);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(99, 102, 241, 0.15);
    }
  </style>
</head>
<body class="text-gray-100 min-h-screen">
  <!-- Navbar -->
  <div class="navbar bg-slate-950/80 backdrop-blur border-b border-white/5 sticky top-0 z-50 px-6">
    <div class="flex-1">
      <a href="/" class="btn btn-ghost text-xl tracking-tight text-white hover:bg-white/5 font-semibold">
        <span class="text-indigo-400 font-bold mr-1">📈</span> AAARTS
      </a>
    </div>
    <div class="flex-none gap-2">
      <a href="/" class="btn btn-sm btn-ghost hover:bg-white/5">System Home</a>
      <a href="/screener" class="btn btn-sm btn-ghost hover:bg-white/5">Screener</a>
      <a href="/company" class="btn btn-sm btn-ghost hover:bg-white/5">Company Search</a>
      <a href="/links" class="btn btn-sm btn-primary">Link Directory</a>
    </div>
  </div>

  <!-- Hero Section -->
  <div class="relative overflow-hidden py-16 px-6 border-b border-white/5 bg-slate-950/40">
    <div class="absolute inset-0 bg-cover bg-center opacity-20 filter blur-sm" style="background-image: url('/assets/directory_banner.png');"></div>
    <div class="absolute inset-0 bg-gradient-to-t from-[#07090e] via-transparent to-transparent"></div>
    <div class="max-w-6xl mx-auto relative z-10 grid md:grid-cols-5 gap-8 items-center">
      <div class="md:col-span-3 space-y-4">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
          <span class="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span> External Resources
        </div>
        <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-white bg-clip-text bg-gradient-to-r from-white via-gray-200 to-gray-400">
          企業分析・情報収集リンク集
        </h1>
        <p class="text-gray-400 max-w-xl leading-relaxed">
          AI活用や高度な検索機能を備え、投資判断や市場調査、財務分析に多大な価値をもたらす厳選された高品質な外部データベースへのディレクトリです。
        </p>
      </div>
      <div class="md:col-span-2 hidden md:block">
        <div class="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-indigo-950/20 group">
          <img src="/assets/directory_banner.png" alt="Intelligence Dashboard" class="w-full h-auto object-cover transform group-hover:scale-105 transition-transform duration-700">
          <div class="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent"></div>
          <div class="absolute bottom-4 left-4 right-4 text-xs text-indigo-200 backdrop-blur bg-slate-900/60 p-2.5 rounded-lg border border-white/5">
            <span class="font-semibold text-white">AI-Generated Intelligence Banner</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="max-w-6xl mx-auto p-6 md:p-12 space-y-12">
    <!-- Filters & Search -->
    <div class="flex flex-col md:flex-row gap-4 items-center justify-between bg-slate-900/40 p-4 rounded-xl border border-white/5 backdrop-blur">
      <div class="flex flex-wrap gap-2 w-full md:w-auto">
        <button onclick="filterCategory('all')" id="btn-all" class="btn btn-sm btn-primary border-none text-white">すべて</button>
        <button onclick="filterCategory('企業史・歴史')" id="btn-history" class="btn btn-sm btn-ghost hover:bg-white/5 text-gray-400">企業史・歴史</button>
        <button onclick="filterCategory('日本企業 財務・IR')" id="btn-japan-ir" class="btn btn-sm btn-ghost hover:bg-white/5 text-gray-400">日本企業 財務・IR</button>
        <button onclick="filterCategory('米国企業・一次情報')" id="btn-us-ir" class="btn btn-sm btn-ghost hover:bg-white/5 text-gray-400">米国企業・一次情報</button>
      </div>
      <div class="relative w-full md:w-80">
        <input type="text" id="search-input" onkeyup="filterSearch()" placeholder="キーワードで検索..." class="input input-sm input-bordered w-full bg-slate-950/60 border-white/10 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none">
        <span class="absolute right-3 top-2.5 text-gray-500 text-xs">🔍</span>
      </div>
    </div>

    <!-- Links Grid -->
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6" id="links-grid">
      <!-- Dynamically filled link cards -->
    </div>
  </div>

  <!-- Detail Modal -->
  <dialog id="link_detail_modal" class="modal">
    <div class="modal-box bg-slate-900 border border-white/10 text-gray-100 max-w-xl">
      <form method="dialog">
        <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
      </form>
      <div id="modal-content" class="space-y-6">
        <!-- Filled dynamically -->
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>

  <script>
    const links = ${JSON.stringify(referenceLinks)};

    function getCategoryColor(category) {
      switch(category) {
        case '企業史・歴史': return 'from-amber-500/20 to-amber-600/5 text-amber-300 border-amber-500/20';
        case '日本企業 財務・IR': return 'from-emerald-500/20 to-emerald-600/5 text-emerald-300 border-emerald-500/20';
        case '米国企業・一次情報': return 'from-indigo-500/20 to-indigo-600/5 text-indigo-300 border-indigo-500/20';
        default: return 'from-gray-500/20 to-gray-600/5 text-gray-300 border-gray-500/20';
      }
    }

    function renderCards(filteredLinks) {
      const grid = document.getElementById('links-grid');
      grid.innerHTML = '';
      
      if(filteredLinks.length === 0) {
        grid.innerHTML = \`
          <div class="col-span-full py-16 text-center text-gray-500">
            <div class="text-4xl mb-4">📭</div>
            <p>条件に一致するリンクが見つかりませんでした。</p>
          </div>
        \`;
        return;
      }

      filteredLinks.forEach((link, idx) => {
        const catColor = getCategoryColor(link.category);
        const card = document.createElement('div');
        card.className = 'card glass-card rounded-2xl overflow-hidden cursor-pointer';
        card.setAttribute('onclick', 'showDetail(' + idx + ')');
        card.dataset.category = link.category;
        
        card.innerHTML = \\\`
          <div class="card-body p-6 space-y-4">
            <div class="flex items-center justify-between">
              <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-br border \\\${catColor}">
                \\\${link.badge || link.category}
              </span>
              <span class="text-xs text-gray-500">#\\\${idx + 1}</span>
            </div>
            
            <div class="space-y-1">
              <h3 class="card-title text-lg font-bold text-white tracking-tight group-hover:text-indigo-400">
                \\\${link.title}
              </h3>
              <p class="text-xs text-indigo-400/80 font-mono truncate">\\\${link.url}</p>
            </div>
            
            <p class="text-sm text-gray-400 line-clamp-3 leading-relaxed">
              \\\${link.description}
            </p>
            
            <div class="flex flex-wrap gap-1.5 pt-2">
              \\\${link.tags.map(tag => \\\`<span class="badge badge-sm bg-white/5 border-none text-gray-400 font-medium">#\\\${tag}</span>\\\`).join('')}
            </div>
            
            <div class="card-actions justify-between items-center pt-4 border-t border-white/5">
              <span class="text-xs text-indigo-400 font-semibold group-hover:text-indigo-300">詳細を表示 →</span>
              <a href="\\\${link.url}" target="_blank" onclick="event.stopPropagation();" class="btn btn-xs btn-circle btn-ghost text-gray-400 hover:text-white hover:bg-white/10">
                ↗️
              </a>
            </div>
          </div>
        \\\`;
        grid.appendChild(card);
      });
    }

    let currentCategory = 'all';
    
    function filterCategory(category) {
      currentCategory = category;
      
      const buttons = {
        'all': document.getElementById('btn-all'),
        '企業史・歴史': document.getElementById('btn-history'),
        '日本企業 財務・IR': document.getElementById('btn-japan-ir'),
        '米国企業・一次情報': document.getElementById('btn-us-ir')
      };

      Object.keys(buttons).forEach(key => {
        if(buttons[key]) {
          if(key === category) {
            buttons[key].className = 'btn btn-sm btn-primary border-none text-white';
          } else {
            buttons[key].className = 'btn btn-sm btn-ghost hover:bg-white/5 text-gray-400';
          }
        }
      });

      filterSearch();
    }

    function filterSearch() {
      const query = document.getElementById('search-input').value.toLowerCase();
      
      const filtered = links.filter(link => {
        const matchesCategory = currentCategory === 'all' || link.category === currentCategory;
        const matchesQuery = link.title.toLowerCase().includes(query) || 
                             link.description.toLowerCase().includes(query) ||
                             link.url.toLowerCase().includes(query) ||
                             link.tags.some(tag => tag.toLowerCase().includes(query));
        return matchesCategory && matchesQuery;
      });
      
      renderCards(filtered);
    }

    function showDetail(index) {
      const link = links[index];
      const catColor = getCategoryColor(link.category);
      const modal = document.getElementById('link_detail_modal');
      const content = document.getElementById('modal-content');
      
      content.innerHTML = \\\`
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-br border \\\${catColor}">
              \\\${link.category}
            </span>
            <span class="text-xs text-gray-500 font-mono">ID: \\\${index + 1}</span>
          </div>
          
          <h2 class="text-2xl font-extrabold text-white tracking-tight">\\\${link.title}</h2>
          <a href="\\\${link.url}" target="_blank" class="link link-indigo text-indigo-400 font-mono text-sm inline-flex items-center gap-1 hover:text-indigo-300">
            \\\${link.url} ↗️
          </a>
        </div>
        
        <div class="space-y-2">
          <h3 class="text-xs uppercase tracking-wider text-gray-500 font-bold">サービス概要</h3>
          <p class="text-gray-300 text-sm leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-white/5">
            \\\${link.description}
          </p>
        </div>
        
        <div class="space-y-3">
          <h3 class="text-xs uppercase tracking-wider text-gray-500 font-bold">主要機能・ユースケース</h3>
          <ul class="space-y-2 text-sm text-gray-300">
            \\\${link.features.map(feat => \\\`
              <li class="flex gap-2">
                <span class="text-indigo-400">⚡</span>
                <span>\\\${feat}</span>
              </li>
            \\\`).join('')}
          </ul>
        </div>
        
        <div class="flex flex-wrap gap-1.5 pt-2 border-t border-white/5">
          \\\${link.tags.map(tag => \\\`<span class="badge bg-white/5 border-none text-gray-400">#\\\${tag}</span>\\\`).join('')}
        </div>
        
        <div class="flex justify-end pt-4 gap-2">
          <button class="btn btn-sm btn-ghost hover:bg-white/5 text-gray-400" onclick="document.getElementById('link_detail_modal').close()">閉じる</button>
          <a href="\\\${link.url}" target="_blank" class="btn btn-sm btn-primary border-none text-white px-4">
            サイトを開く ↗️
          </a>
        </div>
      \\\`;
      
      modal.showModal();
    }

    // Initial render
    renderCards(links);
  </script>
</body>
</html>
`);
});

app.get("/assets/directory_banner.png", async (c) => {
	const imagePath = resolve("src/dashboard/directory_banner.png");
	if (existsSync(imagePath)) {
		const fileBytes = readFileSync(imagePath);
		return c.body(fileBytes, 200, {
			"Content-Type": "image/png",
		});
	}
	return c.text("Image not found", 404);
});

export default {
	fetch: app.fetch,
	port: Number(process.env.PORT) || 3000,
	idleTimeout: 120,
};
