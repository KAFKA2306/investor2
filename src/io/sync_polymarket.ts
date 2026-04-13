import type { Config, DatabaseRegistry } from "../schemas";
import { fetchWithCache } from "./http";

export async function syncPolymarket(dbs: DatabaseRegistry, config: Config) {
	const clobUrl = config.polymarket.clob_url;
	const db = dbs.marketsPolymarket;
	const gammaUrl = "https://gamma-api.polymarket.com";
	for (let offset = 0; offset < 500; offset += 100) {
		await fetchWithCache(
			db,
			`${gammaUrl}/markets?active=true&closed=false&limit=100&offset=${offset}`,
		);
	}
	await fetchWithCache(db, `${clobUrl}/sampling-markets?active=true`);
}
