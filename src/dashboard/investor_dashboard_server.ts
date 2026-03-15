import { Hono } from "hono";
import { serveStatic } from "hono/bun";
import { existsSync, readdirSync, statSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import yaml from "js-yaml";

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
		const cacheDbPath = resolve(CACHE_ROOT, "cache/fundamental/edinet.sqlite");
		if (existsSync(cacheDbPath)) {
			const cacheContent = readFileSync(cacheDbPath, "utf-8");
			const matches = cacheContent.match(/"edinetCode":"[^"]+"/g) || [];
			const uniqueCodes = new Set(
				matches.map((m) => m.match(/"([^"]+)"$/)?.[1]),
			);
			companyCount = Math.max(uniqueCodes.size, 0);

			const docMatches = cacheContent.match(/"docID":"[^"]+"/g) || [];
			documentCount = new Set(docMatches.map((m) => m.match(/"([^"]+)"$/)?.[1]))
				.size;
		}
	} catch {
		// Fallback to directory scan
	}

	if (companyCount === 0) {
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

function getStats(): CacheStatistics {
	return {
		marketData: getMarketDataStats(),
		edinet: getEdinetStats(),
		sqlite: getSqliteStats(),
		lastUpdated: getLastUpdated(),
		totalSizeGb: 0,
	};
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
	const stats = getStats();
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
	const stats = getStats();
	return c.html(renderStatsCards(stats));
});

// API: Refresh cache (trigger task get:all)
app.post("/api/refresh", async (c) => {
	try {
		const proc = Bun.spawn(["bun", "run", "task", "get:all"], {
			cwd: process.cwd(),
		});
		const output = await new Response(proc.stdout).text();
		const stats = getStats();

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
	const marketData = getMarketDataStats();
	const stats = getStats();

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

        <!-- Filter Form -->
        <div class="card bg-white shadow mb-6">
          <div class="card-body">
            <h2 class="card-title">検索条件</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
              <input
                type="text"
                placeholder="銘柄コード or 企業名"
                id="search"
                hx-trigger="keyup changed delay:500ms"
                hx-get="/api/screener?q={value}"
                hx-target="#results"
                class="input input-bordered w-full"
              />
              <select class="select select-bordered">
                <option>業種: すべて</option>
                <option>電機</option>
                <option>化学</option>
                <option>自動車</option>
              </select>
              <input type="number" placeholder="時価総額(億)" class="input input-bordered" />
              <button
                hx-get="/api/screener?mode=all"
                hx-target="#results"
                class="btn btn-primary"
              >
                検索
              </button>
            </div>
          </div>
        </div>

        <!-- Results Table -->
        <div id="results" hx-trigger="load" hx-get="/api/screener">
          <div class="loading loading-spinner loading-lg"></div>
        </div>
      </div>
    </body>
    </html>
  `);
});

// Company Finder view
app.get("/company", async (c) => {
	const edinet = getEdinetStats();

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
                hx-trigger="keyup changed delay:500ms"
                hx-get="/api/company/search?q={value}"
                hx-target="#company-results"
                class="input input-bordered w-full"
              />
              <button
                hx-get="/api/company/list"
                hx-target="#company-results"
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
	const q = c.req.query("q") || "";
	const marketData = getMarketDataStats();

	// Mock data - 実装時は実際のデータを返す
	const sampleStocks = [
		{
			code: "7203",
			name: "トヨタ自動車",
			sector: "自動車",
			price: 3250,
			marketcap: 45000,
			per: 12.5,
			roe: 15.2,
		},
		{
			code: "6758",
			name: "ソニーグループ",
			sector: "電機",
			price: 13820,
			marketcap: 18000,
			per: 18.3,
			roe: 22.1,
		},
		{
			code: "9984",
			name: "ソフトバンクグループ",
			sector: "通信",
			price: 3945,
			marketcap: 22000,
			per: 11.2,
			roe: 25.4,
		},
	];

	const filtered = q
		? sampleStocks.filter(
				(s) =>
					s.code.includes(q) || s.name.toLowerCase().includes(q.toLowerCase()),
			)
		: sampleStocks;

	return c.html(`
    <div class="card bg-white shadow">
      <div class="card-body">
        <h2 class="card-title">検索結果: ${filtered.length} 件</h2>
        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>コード</th>
                <th>企業名</th>
                <th>業種</th>
                <th>株価</th>
                <th>時価総額(億)</th>
                <th>PER</th>
                <th>ROE</th>
              </tr>
            </thead>
            <tbody>
              ${filtered
								.map(
									(stock) => `
                <tr class="hover">
                  <td><code>${stock.code}</code></td>
                  <td><strong>${stock.name}</strong></td>
                  <td><span class="badge badge-secondary">${stock.sector}</span></td>
                  <td>¥${stock.price.toLocaleString()}</td>
                  <td>${stock.marketcap.toLocaleString()}</td>
                  <td>${stock.per.toFixed(1)}x</td>
                  <td class="text-green-600">${stock.roe.toFixed(1)}%</td>
                </tr>
              `,
								)
								.join("")}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `);
});

// API: Company search
app.get("/api/company/search", async (c) => {
	const q = c.req.query("q") || "";

	// Mock data
	const sampleCompanies = [
		{
			code: "E00001",
			name: "トヨタ自動車",
			docs: 45,
		},
		{
			code: "E00002",
			name: "ソニー",
			docs: 38,
		},
	];

	const filtered = q
		? sampleCompanies.filter(
				(c) =>
					c.code.includes(q) || c.name.toLowerCase().includes(q.toLowerCase()),
			)
		: sampleCompanies;

	return c.html(`
    <div class="grid gap-4">
      ${filtered
				.map(
					(comp) => `
        <div class="card bg-white shadow">
          <div class="card-body">
            <h3 class="card-title">${comp.name}</h3>
            <p class="text-sm text-gray-600">EDINET コード: <code>${comp.code}</code></p>
            <p>提出文書: <strong>${comp.docs}</strong> 件</p>
            <div class="card-actions justify-end">
              <button class="btn btn-sm btn-primary">詳細</button>
            </div>
          </div>
        </div>
      `,
				)
				.join("")}
    </div>
  `);
});

export default {
	fetch: app.fetch,
	port: 3000,
};
