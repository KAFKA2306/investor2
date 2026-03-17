import { readFileSync } from "node:fs";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const pathKey = Bun.argv[2];
if (!pathKey) {
	console.error("Usage: paths_resolve.ts PATH_KEY");
	process.exit(1);
}

const paths = config.paths as Record<string, unknown>;
const resolved = paths[pathKey];

if (resolved === undefined || resolved === null) {
	console.log(JSON.stringify({ error: `Path key not found: ${pathKey}` }));
	process.exit(1);
}

console.log(String(resolved));
