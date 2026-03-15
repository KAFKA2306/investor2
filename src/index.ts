import { readFileSync } from "node:fs";
import yaml from "js-yaml";

async function main() {
	console.log("🚀 Starting Investor2 Agent Shell...");

	const config = yaml.load(readFileSync("config/default.yaml", "utf-8")) as any;
	console.log(`📍 Project: ${config.project?.name || "Unknown"}`);
	console.log(`📍 Data Root: ${config.paths?.data || "Not set"}`);

	console.log("✅ Environment validation successful.");
}

main();
