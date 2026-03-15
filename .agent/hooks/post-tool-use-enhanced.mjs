#!/usr/bin/env node

/**
 * PostToolUseHook: Full Quality Pipeline
 *
 * Pipeline:
 * 1. Auto-format (Biome) — fixes 40-50% of issues silently
 * 2. Lint (Biome) — detects style/logic violations
 * 3. Architecture check (ast-grep) — enforces layer boundaries
 * 4. CDD check — prevents defensive code patterns
 *
 * If issues found: block commit with clear feedback
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, existsSync } from "fs";
import path from "path";

const CHANGED_FILES = getChangedFiles();
if (CHANGED_FILES.length === 0) process.exit(0);

const TS_FILES = CHANGED_FILES.filter((f) => f.match(/\.ts$/));
const SKIP_PATTERNS = ["node_modules", ".test.", ".spec.", "dist/"];

const RESULTS = {
  formatted: [],
  linted: [],
  architectureViolations: [],
  cddViolations: [],
};

console.log(`📋 Quality Pipeline: ${CHANGED_FILES.length} file(s)\n`);

// ============================================================================
// PHASE 1: Auto-Format with Biome
// ============================================================================
console.log("🎨 Phase 1: Auto-format (Biome)...");
for (const file of TS_FILES) {
  if (shouldSkip(file)) continue;
  try {
    execSync(`biome format --write "${file}" 2>/dev/null`, { encoding: "utf-8" });
    RESULTS.formatted.push(file);
  } catch (e) {
    // biome not installed or file has errors - will be caught in lint phase
  }
}
if (RESULTS.formatted.length > 0) {
  console.log(`  ✓ Formatted ${RESULTS.formatted.length} file(s)\n`);
}

// ============================================================================
// PHASE 2: Lint with Biome
// ============================================================================
console.log("🔍 Phase 2: Lint (Biome)...");
const lintErrors = [];
for (const file of TS_FILES) {
  if (shouldSkip(file)) continue;
  try {
    execSync(`biome lint "${file}" --reporter=json 2>/dev/null`, {
      encoding: "utf-8",
    });
  } catch (e) {
    const output = e.stdout || "";
    if (output) {
      try {
        const json = JSON.parse(output);
        if (json.errors && json.errors.length > 0) {
          lintErrors.push({ file, errors: json.errors });
          RESULTS.linted.push(file);
        }
      } catch {
        lintErrors.push({ file, raw: output });
      }
    }
  }
}

// ============================================================================
// PHASE 3: Architecture Check (ast-grep)
// ============================================================================
console.log("🏛️  Phase 3: Architecture boundaries...");
const archRules = {
  // Domain layer cannot import from IO layer
  "domain-imports-io": {
    pattern: 'import { ... } from ".*/(io|providers|db)/..."',
    files: "src/domain/**/*.ts",
    message: "Domain layer cannot import from IO/providers/db",
  },
  // Business logic (agents/pipeline) cannot use try-catch
  "no-try-catch-in-logic": {
    pattern: "try { ... } catch (...) { ... }",
    files: "src/agents/**/*.ts|src/pipeline/**/*.ts",
    message: "try-catch forbidden in business logic (CDD violation)",
  },
  // Return null/undefined only at boundaries
  "no-defensive-returns": {
    pattern: "return null|return undefined",
    files: "src/agents/**/*.ts|src/domain/**/*.ts",
    message: "Defensive returns forbidden - throw errors instead",
  },
};

for (const file of TS_FILES) {
  if (shouldSkip(file)) continue;

  const content = readFileSync(file, "utf-8");

  // Check domain-imports-io
  if (file.includes("src/domain/")) {
    if (/from\s+["'](\.\.\/)*(\.\/)*(io|providers|db)\//.test(content)) {
      RESULTS.architectureViolations.push({
        file,
        rule: "domain-imports-io",
        message: "Domain cannot import from IO layer",
      });
    }
  }

  // Check try-catch in business logic
  if (
    file.includes("src/agents/") ||
    file.includes("src/pipeline/")
  ) {
    if (/try\s*\{[\s\S]*?\}\s*catch/.test(content)) {
      RESULTS.architectureViolations.push({
        file,
        rule: "no-try-catch-in-logic",
        message: "try-catch forbidden in business logic",
      });
    }
  }

  // Check defensive returns in logic layers
  if (
    file.includes("src/agents/") ||
    file.includes("src/domain/")
  ) {
    if (/return\s+(null|undefined);/.test(content)) {
      RESULTS.architectureViolations.push({
        file,
        rule: "no-defensive-returns",
        message: "Defensive returns forbidden - throw instead",
      });
    }
  }
}

if (RESULTS.architectureViolations.length > 0) {
  console.log(
    `  ⚠️  ${RESULTS.architectureViolations.length} architecture violation(s)\n`,
  );
}

// ============================================================================
// PHASE 4: CDD Check (Crash-Driven Development)
// ============================================================================
console.log("⚡ Phase 4: CDD violations...");
const cddPatterns = [
  {
    name: "Math.random",
    pattern: /Math\.random\(\)/,
    message: "Math.random() is non-deterministic",
  },
  {
    name: "mock declaration",
    pattern: /const\s+\w*mock\w*\s*=/i,
    message: "mock data forbidden in production code",
  },
  {
    name: "defensive ||",
    pattern: /return\s+\w+\s*\|\|\s*\w+/,
    message: "Defensive || pattern forbidden",
  },
];

for (const file of TS_FILES) {
  if (shouldSkip(file)) continue;
  const content = readFileSync(file, "utf-8");

  for (const pattern of cddPatterns) {
    if (pattern.pattern.test(content)) {
      RESULTS.cddViolations.push({
        file,
        pattern: pattern.name,
        message: pattern.message,
      });
    }
  }
}

if (RESULTS.cddViolations.length > 0) {
  console.log(`  🚫 ${RESULTS.cddViolations.length} CDD violation(s)\n`);
}

// ============================================================================
// FINAL VERDICT
// ============================================================================
console.log("=".repeat(70));

const hasErrors =
  lintErrors.length > 0 ||
  RESULTS.architectureViolations.length > 0 ||
  RESULTS.cddViolations.length > 0;

if (!hasErrors) {
  console.log("✅ All checks passed. Commit allowed.");
  process.exit(0);
}

console.log("❌ Quality checks failed.\n");

if (lintErrors.length > 0) {
  console.log("Lint Errors:");
  for (const { file, errors } of lintErrors) {
    console.log(`  ${file}`);
    if (errors) {
      for (const err of errors.slice(0, 3)) {
        console.log(`    Line ${err.line}: ${err.message}`);
      }
    }
  }
  console.log("");
}

if (RESULTS.architectureViolations.length > 0) {
  console.log("Architecture Violations:");
  for (const v of RESULTS.architectureViolations) {
    console.log(`  ${v.file}`);
    console.log(`    → ${v.message}`);
  }
  console.log("");
}

if (RESULTS.cddViolations.length > 0) {
  console.log("CDD Violations:");
  for (const v of RESULTS.cddViolations) {
    console.log(`  ${v.file}`);
    console.log(`    → ${v.pattern}: ${v.message}`);
  }
  console.log("");
}

console.log("=".repeat(70));
process.exit(1);

// ============================================================================
// HELPERS
// ============================================================================

function getChangedFiles() {
  try {
    const output = execSync("git diff --name-only HEAD 2>/dev/null", {
      encoding: "utf-8",
    });
    return output
      .trim()
      .split("\n")
      .filter((f) => f && f.match(/\.(ts|js)$/));
  } catch {
    return [];
  }
}

function shouldSkip(file) {
  return SKIP_PATTERNS.some((p) => file.includes(p));
}
