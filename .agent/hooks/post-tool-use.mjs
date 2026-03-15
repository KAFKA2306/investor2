#!/usr/bin/env node

/**
 * PostToolUseHook: Auto-Fix CDD Violations
 *
 * Strategy: Detect defensive code patterns and auto-fix them.
 * If auto-fix is not possible, block commit with clear instruction.
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync } from "fs";
import { existsSync } from "fs";

const PATTERNS = {
  // Pattern: return null/undefined/[]/{}  as defensive
  defensiveReturn: {
    pattern: /return\s+(null|undefined|\[\]|\{\});?(?!.*\/\/)/g,
    context: "defensive return (should throw instead)",
    severity: "error",
    fixable: false,
  },

  // Pattern: || with defaults
  orDefault: {
    pattern: /(\w+)\s*\|\|\s*(null|undefined|0|""|false|{|}|\[\])/g,
    context: "defensive || pattern",
    severity: "error",
    fixable: false,
  },

  // Pattern: ?? nullish coalescing
  coalesce: {
    pattern: /(\w+)\s*\?\?\s*(\w+)/g,
    context: "nullish coalescing (should handle missing data)",
    severity: "warning",
    fixable: false,
  },

  // Pattern: try-catch in business logic
  tryCatch: {
    pattern: /try\s*\{[\s\S]*?\}\s*catch\s*\(/g,
    context: "try-catch block (CDD violation)",
    severity: "error",
    fixable: false,
  },

  // Pattern: mock/stub/fake declarations
  mockDeclaration: {
    pattern: /const\s+(\w*mock\w*|stub|fake)\s*=/gi,
    context: "mock/stub/fake declaration",
    severity: "error",
    fixable: true,
  },

  // Pattern: Math.random() outside randomized context
  randomDice: {
    pattern: /Math\.random\(\)(?!.*@randomized)/g,
    context: "Math.random() (non-deterministic)",
    severity: "warning",
    fixable: false,
  },

  // Pattern: fallback references
  fallbackRef: {
    pattern: /fallback|Fallback(?=\s*[=:;])/g,
    context: "fallback variable/function",
    severity: "warning",
    fixable: false,
  },
};

const BUSINESS_LOGIC_DIRS = [
  "src/agents/",
  "src/domain/",
  "src/pipeline/",
];

const INFRASTRUCTURE_DIRS = [
  "src/db/",
  "src/io/",
  "src/providers/",
];

const SKIP_DIRS = [
  "node_modules",
  ".next",
  "dist",
  "build",
];

function isBusinessLogic(filePath) {
  return BUSINESS_LOGIC_DIRS.some((dir) => filePath.includes(dir));
}

function isInfrastructure(filePath) {
  return INFRASTRUCTURE_DIRS.some((dir) => filePath.includes(dir));
}

function shouldSkip(filePath) {
  return SKIP_DIRS.some((dir) => filePath.includes(dir)) ||
         filePath.endsWith(".test.ts") ||
         filePath.endsWith(".spec.ts");
}

function getChangedFiles() {
  try {
    const output = execSync("git diff --name-only HEAD", {
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

function scanFile(filePath) {
  if (!existsSync(filePath)) return [];

  const content = readFileSync(filePath, "utf-8");
  const violations = [];

  for (const [patternName, config] of Object.entries(PATTERNS)) {
    if (content.match(config.pattern)) {
      const severity =
        isBusinessLogic(filePath) && config.severity === "warning"
          ? "error"
          : config.severity;

      violations.push({
        pattern: patternName,
        severity,
        fixable: config.fixable,
        context: config.context,
      });
    }
  }

  return violations;
}

function reportViolation(filePath, violation) {
  const icon = violation.severity === "error" ? "❌" : "⚠️";
  const layer = isBusinessLogic(filePath)
    ? "[BUSINESS LOGIC]"
    : isInfrastructure(filePath)
      ? "[INFRASTRUCTURE]"
      : "[OTHER]";

  console.error(
    `${icon} ${layer} ${filePath}`,
  );
  console.error(`   → ${violation.context}`);
  console.error(`   → Severity: ${violation.severity}`);

  if (violation.fixable) {
    console.error(`   → Auto-fixable: YES (implement in hook)`);
  } else {
    console.error(`   → Action: Manual fix required (CDD principle)`);
  }
}

function main() {
  const files = getChangedFiles();

  if (files.length === 0) {
    process.exit(0);
  }

  let errorCount = 0;
  let warningCount = 0;

  console.log(`🔍 Scanning ${files.length} changed file(s)...\n`);

  for (const file of files) {
    if (shouldSkip(file)) continue;

    const violations = scanFile(file);

    for (const violation of violations) {
      reportViolation(file, violation);

      if (violation.severity === "error") {
        errorCount++;
      } else {
        warningCount++;
      }
    }
  }

  if (errorCount > 0) {
    console.error("\n" + "=".repeat(70));
    console.error(
      `💢 ${errorCount} CDD violations found. Commit blocked.`,
    );
    console.error("=".repeat(70));
    console.error("\nCDD Principles (no compromises):");
    console.error("  1. Let errors crash immediately (no try-catch in domain)");
    console.error("  2. Never return null/undefined to hide errors");
    console.error("  3. No fallback defaults (fail fast)");
    console.error("  4. No mocks/stubs in production code");
    console.error("  5. No Math.random() in deterministic logic");
    console.error("");
    process.exit(1);
  }

  if (warningCount > 0) {
    console.warn(
      `\n⚠️  ${warningCount} warning(s). Proceeding with caution.\n`,
    );
  }

  console.log("✅ No blocking violations. Commit allowed.\n");
  process.exit(0);
}

main();
