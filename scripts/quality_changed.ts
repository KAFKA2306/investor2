import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";

const args = new Set(process.argv.slice(2));
const checkTypeScript = !args.has("--python-only");
const checkPython = !args.has("--ts-only");

function gitLines(gitArgs: string[]): string[] {
  try {
    return execFileSync("git", gitArgs, { encoding: "utf8" })
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

function resolveBase(): string | null {
  for (const ref of ["origin/main", "main"]) {
    try {
      execFileSync("git", ["rev-parse", "--verify", ref], { stdio: "ignore" });
      return ref;
    } catch {
      // Try the next canonical main ref.
    }
  }
  return null;
}

const changed = new Set<string>();
const base = resolveBase();
if (base) {
  for (const path of gitLines([
    "diff",
    "--name-only",
    "--diff-filter=ACMR",
    `${base}...HEAD`,
  ])) {
    changed.add(path);
  }
}
for (const gitArgs of [
  ["diff", "--name-only", "--diff-filter=ACMR"],
  ["diff", "--cached", "--name-only", "--diff-filter=ACMR"],
  ["ls-files", "--others", "--exclude-standard"],
]) {
  for (const path of gitLines(gitArgs)) changed.add(path);
}

const maintained = [...changed].filter((path) => existsSync(path));
const tsFiles = maintained.filter((path) => /\.(?:[cm]?[jt]sx?)$/.test(path));
const pyFiles = maintained.filter((path) => path.endsWith(".py"));

let failed = false;
function run(
  label: string,
  command: string,
  commandArgs: string[],
  files: string[],
): void {
  if (files.length === 0) {
    console.log(`[quality] ${label}: no changed files`);
    return;
  }
  console.log(`[quality] ${label}: ${files.length} changed file(s)`);
  const result = spawnSync(command, [...commandArgs, ...files], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) throw result.error;
  if (result.status !== 0) failed = true;
}

if (checkTypeScript) {
  run(
    "Biome",
    "bun",
    ["x", "biome", "check", "--config-path=config/biome.json"],
    tsFiles,
  );
  run("Oxlint", "bun", ["x", "oxlint"], tsFiles);
}
if (checkPython) {
  run(
    "Ruff format",
    "uv",
    ["run", "--no-sync", "ruff", "format", "--check"],
    pyFiles,
  );
  run("Ruff lint", "uv", ["run", "--no-sync", "ruff", "check"], pyFiles);
}

if (failed) process.exit(1);
