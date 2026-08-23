import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";

const args = new Set(process.argv.slice(2));
const checkTypeScript = !args.has("--python-only");
const checkPython = !args.has("--ts-only");

const gitLines = (...gitArgs: string[]): string[] =>
  execFileSync("git", gitArgs, { encoding: "utf8" })
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

const hasRef = (ref: string): boolean => {
  const result = spawnSync("git", ["rev-parse", "--verify", "--quiet", ref]);
  if (result.error) throw result.error;
  return result.status === 0;
};

const base = hasRef("origin/main") ? "origin/main" : "main";
const changed = new Set([
  ...gitLines("diff", "--name-only", "--diff-filter=ACMR", `${base}...HEAD`),
  ...gitLines("diff", "--name-only", "--diff-filter=ACMR"),
  ...gitLines("diff", "--cached", "--name-only", "--diff-filter=ACMR"),
  ...gitLines("ls-files", "--others", "--exclude-standard"),
]);
const maintained = [...changed].filter(existsSync);
const tsFiles = maintained.filter((path) => /\.(?:[cm]?[jt]sx?)$/.test(path));
const pyFiles = maintained.filter((path) => path.endsWith(".py"));

type Check = [boolean, string, string, string[], string[]];
const checks: Check[] = [
  [
    checkTypeScript,
    "Biome",
    "bun",
    ["x", "biome", "check", "--config-path=config/biome.json"],
    tsFiles,
  ],
  [checkTypeScript, "Oxlint", "bun", ["x", "oxlint"], tsFiles],
  [
    checkPython,
    "Ruff format",
    "uv",
    ["run", "--no-sync", "ruff", "format", "--diff"],
    pyFiles,
  ],
  [
    checkPython,
    "Ruff lint",
    "uv",
    ["run", "--no-sync", "ruff", "check"],
    pyFiles,
  ],
];

let failed = false;
for (const [enabled, label, command, commandArgs, files] of checks) {
  if (!enabled) continue;
  if (files.length === 0) {
    console.log(`[quality] ${label}: no changed files`);
    continue;
  }
  console.log(`[quality] ${label}: ${files.length} changed file(s)`);
  const result = spawnSync(command, [...commandArgs, ...files], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) throw result.error;
  failed ||= result.status !== 0;
}

process.exitCode = failed ? 1 : 0;
