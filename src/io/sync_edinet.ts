import type { DatabaseRegistry } from "../schemas";
import { fetchWithCache, sleep } from "./http";

export async function syncEdinet(dbs: DatabaseRegistry) {
	const apiKey = process.env.EDINET_API_KEY!;
	const db = dbs.fundamentalEdinet;
	const dates = Array.from({ length: 1095 }, (_, i) => {
		const d = new Date();
		d.setDate(d.getDate() - i);
		return d.toISOString().split("T")[0];
	});
	for (const date of dates) {
		await fetchWithCache(
			db,
			`https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`,
		);
		await sleep(50);
	}
}

export async function syncEdinetXbrl(dbs: DatabaseRegistry) {
	const apiKey = process.env.EDINET_API_KEY!;
	const db = dbs.fundamentalEdinet;
	const dates = Array.from({ length: 365 }, (_, i) => {
		const d = new Date();
		d.setDate(d.getDate() - i);
		return d.toISOString().split("T")[0];
	});
	for (const date of dates) {
		const cacheKey = `https://api.edinet-fsa.go.jp/api/v2/documents.json?date=${date}&type=2&Subscription-Key=${apiKey}`;
		const row = db
			.query("SELECT value FROM http_cache WHERE key = ?")
			.get(cacheKey) as { value: string } | undefined;
		if (!row) continue;
		const metadata = JSON.parse(row.value);
		if (!metadata.results?.length) continue;
		for (const doc of metadata.results) {
			const xbrlUrl = `https://api.edinet-fsa.go.jp/api/v2/documents/${doc.docID}?type=1&Subscription-Key=${apiKey}`;
			const existing = db
				.query("SELECT key FROM http_cache WHERE key = ?")
				.get(xbrlUrl);
			if (existing) continue;
			const response = await fetch(xbrlUrl);
			if (!response.ok) continue;
			const content = await response.text();
			db.run(
				"INSERT OR REPLACE INTO http_cache (key, value, created_at) VALUES (?, ?, ?)",
				[xbrlUrl, JSON.stringify({ content }), Date.now()],
			);
			await sleep(300);
		}
	}
}
