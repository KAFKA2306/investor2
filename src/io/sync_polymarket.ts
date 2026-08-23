import type { DatabaseRegistry } from "../schemas";
import { fetchWithCache } from "./http";

const CLOB_URL = "https://clob.polymarket.com";

export async function syncPolymarket(dbs: DatabaseRegistry) {
  const db = dbs.marketsPolymarket;
  const gammaUrl = "https://gamma-api.polymarket.com";
  for (let offset = 0; offset < 500; offset += 100) {
    await fetchWithCache(
      db,
      `${gammaUrl}/markets?active=true&closed=false&limit=100&offset=${offset}`,
    );
  }
  await fetchWithCache(db, `${CLOB_URL}/sampling-markets?active=true`);
}
