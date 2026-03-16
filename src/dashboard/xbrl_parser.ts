import { fetch } from "bun";
import { parseStringPromise } from "xml2js";

interface XBRLData {
	businessDescription?: string;
	riskFactors?: string;
	managementDiscussion?: string;
}

interface EDINETDocument {
	docID: string;
	docDescription: string;
	filingDate: string;
}

export async function fetchEDINETDocuments(
	edinetCode: string,
): Promise<EDINETDocument[]> {
	const params = new URLSearchParams({
		Subscription_key: process.env.EDINET_API_KEY || "",
		type: 2,
		"Filer-FilerID": edinetCode,
		Result_StartNumber: "1",
		Result_Limit: "100",
	});

	const url = `https://disclosure2dl.edinet-fsa.go.jp/api/v3/documents.json?${params}`;

	try {
		const response = await fetch(url);
		if (!response.ok) return [];

		const data = (await response.json()) as any;
		return (
			data.results?.map((doc: any) => ({
				docID: doc.docID,
				docDescription: doc.docDescription,
				filingDate: doc.submitDateTime,
			})) || []
		);
	} catch {
		console.error(`Failed to fetch EDINET documents for ${edinetCode}`);
		return [];
	}
}

export async function downloadXBRL(docID: string): Promise<string> {
	const url = `https://disclosure2dl.edinet-fsa.go.jp/api/v3/documents/${docID}/xbrl`;

	try {
		const response = await fetch(url);
		if (!response.ok) return "";

		return await response.text();
	} catch {
		console.error(`Failed to download XBRL for ${docID}`);
		return "";
	}
}

export async function parseXBRL(xbrlContent: string): Promise<XBRLData> {
	try {
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
	} catch (error) {
		console.error("Failed to parse XBRL:", error);
		return {};
	}
}

function extractText(parsed: any, paths: string[]): string {
	for (const path of paths) {
		const value = getNestedValue(parsed, path);
		if (value) {
			return typeof value === "string" ? value : JSON.stringify(value);
		}
	}
	return "";
}

function getNestedValue(obj: any, path: string): any {
	const keys = path.split(":");
	let current = obj;

	for (const key of keys) {
		if (!current) return null;
		current = current[key] || current[key.toLowerCase()];
	}

	return current;
}

export async function fetchAndParseXBRL(
	edinetCode: string,
): Promise<XBRLData | null> {
	const docs = await fetchEDINETDocuments(edinetCode);
	if (docs.length === 0) return null;

	const latestDoc = docs[0];
	const xbrlContent = await downloadXBRL(latestDoc.docID);

	if (!xbrlContent) return null;

	return parseXBRL(xbrlContent);
}
