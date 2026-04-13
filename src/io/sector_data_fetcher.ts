import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema } from "../schemas";
import { fetchWithCache } from "./http";
import { fetchJPReturns } from "./sector_jp";
import { fetchUSReturns } from "./sector_us";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);
const cacheDir =
	config.sector_spillover?.backtest?.data_cache_dir || "cache/sector";
mkdirSync(dirname(cacheDir), { recursive: true });
const db = new Database(`${cacheDir}/sector_returns.db`);

db.run(
	"CREATE TABLE IF NOT EXISTS sector_returns (date TEXT, sector TEXT, return_pct REAL, PRIMARY KEY(date, sector))",
);

export async function fetchAllSectorData(from: string, to: string) {
	await fetchUSReturns(db, from, to);
	await fetchJPReturns(db, from, to);
}

export async function getSectorReturns(
	from: string,
	to: string,
): Promise<any[]> {
	return db
		.query("SELECT * FROM sector_returns WHERE date >= ? AND date <= ?")
		.all(from, to);
}

export function pivotToMatrix(
	returns: any[],
	_mode = "default",
): { dates: string[]; sectors: string[]; matrix: number[][] } {
	const dateMap = new Map<string, Map<string, number>>();
	const sectorSet = new Set<string>();

	for (const r of returns) {
		if (!dateMap.has(r.date)) dateMap.set(r.date, new Map());
		dateMap.get(r.date)!.set(r.sector, r.return_pct);
		sectorSet.add(r.sector);
	}

	const dates = Array.from(dateMap.keys()).sort();
	const sectors = Array.from(sectorSet).sort();

	const matrix = dates.map((date) => {
		const dayMap = dateMap.get(date)!;
		return sectors.map((s) => dayMap.get(s) ?? 0);
	});

	return { dates, sectors, matrix };
}

const args = process.argv.slice(2);
if (import.meta.main && args.length >= 4) {
	const from = args[args.indexOf("--from") + 1];
	const to = args[args.indexOf("--to") + 1];
	fetchAllSectorData(from, to);
}
