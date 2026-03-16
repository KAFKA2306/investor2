import { writeFileSync } from "node:fs";

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

const proc = Bun.spawn(["bun", "run", "src/tasks/print_cache_statistics.ts"], {
	cwd: process.cwd(),
	stdio: ["inherit", "pipe", "inherit"],
});

const output = await new Response(proc.stdout).text();

const parseNumber = (pattern: RegExp): number => {
	const m = output.match(pattern);
	const match1 = m?.[1];
	return match1 ? parseInt(match1.replace(/,/g, ""), 10) : 0;
};

const parseFloat_ = (pattern: RegExp): number => {
	const m = output.match(pattern);
	const match1 = m?.[1];
	return match1 ? parseFloat(match1) : 0;
};

const parseDate = (pattern: RegExp): { start: string; end: string } | null => {
	const m = output.match(pattern);
	const match1 = m?.[1];
	if (!match1) return null;
	const [start, end] = match1.split(" ～ ");
	return { start: start.trim(), end: (end || "").trim() };
};

const stats: CacheStatistics = {
	marketData: {
		stocks: parseNumber(/📈 カバー銘柄:\s+([\d,]+)/),
		priceRecords: parseNumber(/📊 価格データ:\s+([\d.]+)k/),
		finRecords: parseNumber(/💼 財務データ:\s+([\d.]+)k/),
		dateRange: parseDate(/📅 カバー期間:\s+([^\n]+)/),
		sizeGb:
			parseFloat_(/マーケットデータ[^容量]*容量:\s+([\d.]+)\s*[KMGT]B/) || 0,
	},
	edinet: {
		companyCount: parseNumber(/🏛️\s+カバー企業:\s+([\d,]+)/),
		documentCount: parseNumber(/📄 企業文書:\s+([\d,]+)/),
		sizeGb:
			parseFloat_(/企業情報 \([^)]*\)[^容量]*容量:\s+([\d.]+)\s*([KMGT]B)/) ||
			0,
	},
	sqlite: {
		market: parseFloat_(/📊 マーケットキャッシュ:\s+([\d.]+)\s*([KMGT]B)/)
			? {
					sizeGb:
						parseFloat_(/📊 マーケットキャッシュ:\s+([\d.]+)\s*([KMGT]B)/) /
						1024,
				}
			: null,
		edinet: parseFloat_(/🏢 EDINET キャッシュ:\s+([\d.]+)\s*([KMGT]B)/)
			? {
					sizeGb:
						parseFloat_(/🏢 EDINET キャッシュ:\s+([\d.]+)\s*([KMGT]B)/) / 1024,
				}
			: null,
		yahoocache: parseFloat_(/🌐 Yahoo! キャッシュ:\s+([\d.]+)\s*([KMGT]B)/)
			? {
					sizeGb:
						parseFloat_(/🌐 Yahoo! キャッシュ:\s+([\d.]+)\s*([KMGT]B)/) / 1024,
				}
			: null,
	},
	lastUpdated: new Date().toISOString(),
	totalSizeGb: parseFloat_(/🎯 総容量:\s+([\d.]+)\s*GB/),
};

writeFileSync("/tmp/investor_stats_cache.json", JSON.stringify(stats, null, 2));
console.log(
	`Stats cached at /tmp/investor_stats_cache.json (${stats.marketData.stocks} stocks, ${stats.edinet.companyCount} companies)`,
);
