import { Database } from "bun:sqlite";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import yaml from "js-yaml";
import { ConfigSchema, type DatabaseRegistry } from "../schemas";
import { cachePaths } from "./cache_paths";
import { syncEdinet, syncEdinetXbrl } from "./sync_edinet";
import { syncJquants } from "./sync_jquants";
import { syncMacro } from "./sync_macro";
import { syncPolymarket } from "./sync_polymarket";

const config = ConfigSchema.parse(
  yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

function openCache(path: string): Database {
  mkdirSync(dirname(path), { recursive: true });
  const db = new Database(path);
  db.run(
    "CREATE TABLE IF NOT EXISTS http_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at INTEGER NOT NULL)",
  );
  return db;
}

const paths = cachePaths(config.paths.cache);
const dbs: DatabaseRegistry = {
  marketsPolymarket: openCache(paths.marketsPolymarket),
  marketsJquants: openCache(paths.marketsJquants),
  marketsYahoo: openCache(paths.marketsYahoo),
  fundamentalJquants: openCache(paths.fundamentalJquants),
  fundamentalEdinet: openCache(paths.fundamentalEdinet),
  macroEstat: openCache(paths.macroEstat),
  macroFred: openCache(paths.macroFred),
};

async function main() {
  const mode = process.env.GET_MODE || "all";
  if (mode === "edinet") {
    await syncEdinet(dbs);
    await syncEdinetXbrl(dbs);
    return;
  }
  if (mode === "jquants") {
    await syncJquants("markets", dbs, config);
    await syncJquants("fundamental", dbs, config);
    return;
  }
  await Promise.all([
    syncPolymarket(dbs),
    syncMacro(dbs),
    syncJquants("markets", dbs, config),
    syncJquants("fundamental", dbs, config),
    syncEdinet(dbs),
  ]);
  if (mode !== "skip-xbrl") await syncEdinetXbrl(dbs);
}

main();
