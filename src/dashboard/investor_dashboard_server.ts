import { Hono } from "hono";
import { serveStatic } from "hono/bun";
import { existsSync, readdirSync, statSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";
import { getScreenerData } from "./screener_data";
import {
	searchCompanies,
	getCompanyList,
	getCompanyDetail,
	getCompanyCount,
} from "./edinet_data";

const app = new Hono();
const config = yaml.load(readFileSync("config/default.yaml", "utf-8")) as any;
const CACHE_ROOT = "/mnt/d/investor_all_cached_data";

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

	try {
		if (existsSync(stockListPath)) {
			const data = readFileSync(stockListPath, "utf-8");
			stocks = data.split("\n").length - 2;
		}
	} catch {
		// continue
	}

	try {
		if (existsSync(priceCsvPath)) {
			const data = readFileSync(priceCsvPath, "utf-8");
			const lines = data.split("\n");
			priceRecords = Math.max(0, lines.length - 2);
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

	try {
		if (existsSync(finCsvPath)) {
			const data = readFileSync(finCsvPath, "utf-8");
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

	try {
		if (existsSync(edinetDir)) {
			const items = readdirSync(edinetDir);
			companyCount = items.filter((item) => !item.startsWith(".")).length;

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
			const stat = statSync(dir);
			if (stat.mtimeMs > latestTime) {
				latestTime = stat.mtimeMs;
			}
		} catch {
			// continue
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
		const proc = Bun.spawn(
			["bun", "run", "src/tasks/print_cache_statistics.ts"],
			{
				cwd: process.cwd(),
				stdio: ["inherit", "pipe", "inherit"],
			},
		);

		const output = await new Response(proc.stdout).text();

		const parseNumber = (text: string, pattern: string): number => {
			const match = text.match(pattern);
			if (!match) return 0;
			return parseInt(match[1]!.replace(/,/g, ""), 10);
		};

		const parseFloat_ = (text: string, pattern: string): number => {
			const match = text.match(pattern);
			if (!match) return 0;
			return parseFloat(match[1]!);
		};

		const parseDate = (
			text: string,
			pattern: string,
		): { start: string; end: string } | null => {
			const match = text.match(pattern);
			if (!match) return null;
			const [start, end] = match[1]!.split(" ～ ");
			return { start: start.trim(), end: end?.trim() || "" };
		};

		cachedStats = {
			marketData: {
				stocks: parseNumber(output, /📈 カバー銘柄:\s+([\d,]+)/),
				priceRecords: parseNumber(output, /📊 価格データ:\s+([\d.]+)k/),
				finRecords: parseNumber(output, /💼 財務データ:\s+([\d.]+)k/),
				dateRange: parseDate(output, /📅 カバー期間:\s+([^💾]+)/),
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
      <div>📍 キャッシュ位置: ${CACHE_ROOT}</div>
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
          <a class="btn btn-ghost text-2xl">📈 投資家向けダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-primary">ダッシュボード</a>
          <a href="/screener" class="btn btn-sm btn-ghost">銘柄検索</a>
          <a href="/company" class="btn btn-sm btn-ghost">企業情報</a>
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
		const output = await new Response(proc.stdout).text();
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
                  <td>${isNaN(stock.per) ? "N/A" : stock.per.toFixed(1)}x</td>
                  <td>${isNaN(stock.pbr) ? "N/A" : stock.pbr.toFixed(2)}x</td>
                  <td class="${stock.roe > 0 ? "text-green-600" : "text-red-600"}">
                    ${isNaN(stock.roe) ? "N/A" : stock.roe.toFixed(1)}%
                  </td>
                  <td>${stock.netSales.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${isNaN(stock.operatingMargin) ? "N/A" : stock.operatingMargin.toFixed(1)}%</td>
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
          <a class="btn btn-ghost text-2xl">📈 投資家向けダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">ダッシュボード</a>
          <a href="/screener" class="btn btn-sm btn-primary">銘柄検索</a>
          <a href="/company" class="btn btn-sm btn-ghost">企業情報</a>
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
	const stats = await getStats();
	const edinet = stats.edinet;

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
          <a class="btn btn-ghost text-2xl">📈 投資家向けダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">ダッシュボード</a>
          <a href="/screener" class="btn btn-sm btn-ghost">銘柄検索</a>
          <a href="/company" class="btn btn-sm btn-primary">企業情報</a>
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
            <span>カバー企業: <strong>${edinet.companyCount.toLocaleString()}</strong> 社</span>
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
                  <td>${isNaN(stock.per) ? "N/A" : stock.per.toFixed(1)}x</td>
                  <td>${isNaN(stock.pbr) ? "N/A" : stock.pbr.toFixed(2)}x</td>
                  <td class="${stock.roe > 0 ? "text-green-600" : "text-red-600"}">
                    ${isNaN(stock.roe) ? "N/A" : stock.roe.toFixed(1)}%
                  </td>
                  <td>${stock.netSales.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}</td>
                  <td>${isNaN(stock.operatingMargin) ? "N/A" : stock.operatingMargin.toFixed(1)}%</td>
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
          <a class="btn btn-ghost text-2xl">📈 投資家向けダッシュボード</a>
        </div>
        <div class="flex-none gap-2">
          <a href="/" class="btn btn-sm btn-ghost">ダッシュボード</a>
          <a href="/screener" class="btn btn-sm btn-ghost">銘柄検索</a>
          <a href="/company" class="btn btn-sm btn-primary">企業情報</a>
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
						? `
          <div class="card bg-white shadow mb-6">
            <div class="card-body">
              <h2 class="card-title">財務概要</h2>
              <p class="text-sm text-gray-600 mb-4">期末: ${company.financial.periodEnd || "不明"}</p>
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                ${
									company.financial.eps !== null &&
									company.financial.eps !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">EPS</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.eps === "number" ? company.financial.eps.toFixed(2) : "N/A"}</p>
                </div>`
										: ""
								}
                ${
									company.financial.bps !== null &&
									company.financial.bps !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">BPS</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.bps === "number" ? company.financial.bps.toFixed(2) : "N/A"}</p>
                </div>`
										: ""
								}
                ${
									company.financial.netSales !== null &&
									company.financial.netSales !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">売上高</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.netSales === "number" ? company.financial.netSales.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									company.financial.profit !== null &&
									company.financial.profit !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">純利益</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.profit === "number" ? company.financial.profit.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									company.financial.equity !== null &&
									company.financial.equity !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">自己資本</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.equity === "number" ? company.financial.equity.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
                ${
									company.financial.totalAssets !== null &&
									company.financial.totalAssets !== undefined
										? `<div>
                  <p class="text-xs text-gray-600">総資産</p>
                  <p class="text-lg font-bold">¥${typeof company.financial.totalAssets === "number" ? company.financial.totalAssets.toFixed(1) : "N/A"}億</p>
                </div>`
										: ""
								}
              </div>
            </div>
          </div>
        `
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

export default {
	fetch: app.fetch,
	port: 3000,
	idleTimeout: 120,
};
