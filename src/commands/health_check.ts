import { existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { config } from "./_config";

interface Check {
	name: string;
	status: boolean;
}

const checks: Check[] = [];

const pathsOk = existsSync(config.paths.data) && existsSync(config.paths.cache);
checks.push({ name: "PathRegistry", status: pathsOk });

const sqlitePath = config.paths.cacheMarketsJquants;
const sqliteOk = existsSync(sqlitePath) && statSync(sqlitePath).size > 0;
checks.push({ name: "CacheSqlite", status: sqliteOk });

const logDir = resolve(config.paths.logs, "unified");
const logDirOk = existsSync(logDir);
checks.push({ name: "LogDir", status: logDirOk });

const healthy = checks.every((c) => c.status);

console.log(JSON.stringify({ healthy, checks }));

process.exit(healthy ? 0 : 1);
