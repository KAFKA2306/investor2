import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { config } from "./_config";

const n = Number(process.argv[2]) || 20;
const filterIdx = process.argv.indexOf("--filter");
const filterPattern = filterIdx !== -1 ? process.argv[filterIdx + 1] : null;

const logDir = config.paths.logs;
const unifiedDir = resolve(logDir, "unified");

let files: string[];
files = readdirSync(unifiedDir)
	.filter((f) => f.endsWith(".json") || f.endsWith(".log"))
	.sort()
	.reverse();

const lines: string[] = [];

for (const file of files) {
	if (lines.length >= n) break;
	const content = readFileSync(resolve(unifiedDir, file), "utf-8");
	const fileLines = content.split("\n").filter((l) => l.trim().length > 0);
	for (let i = fileLines.length - 1; i >= 0; i--) {
		if (lines.length >= n) break;
		const line = fileLines[i];
		if (filterPattern && !line.includes(filterPattern)) continue;
		lines.push(line);
	}
}

lines.reverse();

for (const line of lines) {
	console.log(line);
}
