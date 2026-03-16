import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import AdmZip from "adm-zip";
import yaml from "js-yaml";
import { parseStringPromise } from "xml2js";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const EDINET_DB_PATH = config.paths.cacheFundamentalEdinet;
const OUTPUT_PATH = resolve(config.paths.edinet, "edinet_xbrl_text_map.json");

interface XBRLText {
	businessDescription?: string;
	riskFactors?: string;
	managementDiscussion?: string;
}

async function parseXBRL(xbrlContent: string): Promise<XBRLText> {
	const parsed = await parseStringPromise(xbrlContent);

	const businessDesc = extractText(parsed, [
		"jpfr-asr:BusinessOverviewTextBlock",
		"BusinessDescriptionTextBlock",
	]);

	const risks = extractText(parsed, [
		"jpfr-asr:RisksTextBlock",
		"RiskFactorsTextBlock",
	]);

	const md_a = extractText(parsed, [
		"jpfr-asr:OperatingResultsTextBlock",
		"ManagementDiscussionAndAnalysisTextBlock",
	]);

	return {
		businessDescription: businessDesc || undefined,
		riskFactors: risks || undefined,
		managementDiscussion: md_a || undefined,
	};
}

function extractText(parsed: unknown, paths: string[]): string {
	for (const path of paths) {
		const value = getNestedValue(parsed, path);
		if (value) {
			return typeof value === "string" ? value : JSON.stringify(value);
		}
	}
	return "";
}

function getNestedValue(obj: unknown, path: string): unknown {
	const keys = path.split(":");
	let current = obj as Record<string, unknown> | null;

	for (const key of keys) {
		if (!current || typeof current !== "object") return null;
		const next = current[key] || current[key.toLowerCase()];
		current = next as Record<string, unknown> | null;
	}

	return current;
}

async function extractEdinetXbrlText() {
	console.log("🔄 [XBRL TEXT] Starting XBRL text extraction...");

	const db = new Database(EDINET_DB_PATH);
	const rows = db
		.query("SELECT key, value FROM http_cache WHERE key LIKE ?")
		.all("%/api/v2/documents/%?type=1%") as {
		key: string;
		value: string;
	}[];

	console.log(`📊 Found ${rows.length} XBRL cache entries`);

	const textMap: Record<string, Record<string, XBRLText>> = {};
	let processed = 0;
	let extracted = 0;

	for (const row of rows) {
		try {
			const cached = JSON.parse(row.value);
			let xbrlContent = cached.content;
			if (!xbrlContent) continue;

			// Handle ZIP format
			if (xbrlContent.startsWith("PK")) {
				const zip = new AdmZip(Buffer.from(xbrlContent, "binary"));
				const xbrlEntry = zip
					.getEntries()
					.find((e) => e.entryName.endsWith(".xbrl"));
				if (xbrlEntry) {
					xbrlContent = xbrlEntry.getData().toString("utf8");
				}
			}

			const textData = await parseXBRL(xbrlContent);

			// Extract EDINET code from URL: /api/v2/documents/{docID}?...
			const docIdMatch = row.key.match(/\/documents\/(\d+)\?/);
			if (!docIdMatch) continue;

			const docID = docIdMatch[1];

			// Fetch document metadata to get EDINET code
			const metadataRows = db
				.query("SELECT value FROM http_cache WHERE key LIKE ? LIMIT 1000")
				.all(`%/api/v2/documents.json?%`) as { value: string }[];

			let edinetCode = null;
			for (const metaRow of metadataRows) {
				const metadata = JSON.parse(metaRow.value);
				if (metadata.results && Array.isArray(metadata.results)) {
					const doc = metadata.results.find(
						(d: { docID: string; filerID?: string }) => d.docID === docID,
					);
					if (doc?.filerID) {
						edinetCode = doc.filerID;
						break;
					}
				}
			}

			if (!edinetCode) continue;

			if (!textMap[edinetCode]) {
				textMap[edinetCode] = {};
			}

			textMap[edinetCode][docID] = textData;
			processed++;

			if (
				textData.businessDescription ||
				textData.riskFactors ||
				textData.managementDiscussion
			) {
				extracted++;
			}

			if (processed % 100 === 0) {
				console.log(`✓ Processed ${processed} documents...`);
			}
		} catch (error) {
			console.error(`❌ Error processing document ${row.key}:`, error);
		}
	}

	// Save to JSON
	mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
	writeFileSync(OUTPUT_PATH, JSON.stringify(textMap, null, 2));

	console.log(
		`✨ [XBRL TEXT] Extraction complete: ${extracted}/${processed} documents with text`,
	);
	console.log(`📁 Saved to ${OUTPUT_PATH}`);

	db.close();
}

extractEdinetXbrlText().catch((error) => {
	console.error("❌ Extraction failed:", error);
	process.exit(1);
});
