#!/usr/bin/env node

/**
 * PreToolUseHook: Protect Critical Config Files
 *
 * Prevents agents from tampering with:
 * - Linter configs (biome.json, .eslintrc, etc.)
 * - Type checker configs (tsconfig.json, pyproject.toml)
 * - Git hooks (lefthook.yml, .git/hooks)
 * - Build configs
 *
 * Strategy: If agent tries to edit a protected file, block with clear message
 * and suggest fixing code instead of config.
 */

const PROTECTED_CONFIGS = [
  "biome.json",
  ".biomeignore",
  "biome.json.backup",
  ".eslintrc",
  ".eslintrc.json",
  ".eslintrc.js",
  "eslint.config.js",
  ".prettierrc",
  ".prettierrc.json",
  ".prettierrc.js",
  "tsconfig.json",
  "tsconfig.*.json",
  "pyproject.toml",
  ".python-version",
  "lefthook.yml",
  "lefthook-local.yml",
  ".golangci.yml",
  ".pre-commit-config.yaml",
  "Cargo.toml",
  ".swiftlint.yml",
  "Makefile",
  "Taskfile.yml",
  ".clippy.toml",
  "go.mod",
  "go.sum",
  "package.json",
  "pnpm-lock.yaml",
  "yarn.lock",
  "bun.lockb",
];

const PROTECTED_DIRS = [
  ".git/hooks",
  ".agent/hooks",
  ".husky",
  ".pre-commit-hooks.yaml",
];

function checkInput(stdin) {
  try {
    const input = JSON.parse(stdin);
    const filePath = input.tool_input?.file_path || input.tool_input?.path;

    if (!filePath) return null; // Not a file operation

    // Check protected files
    const fileName = filePath.split("/").pop();
    for (const protected of PROTECTED_CONFIGS) {
      if (fileName === protected || filePath.endsWith(`/${protected}`)) {
        return {
          blocked: true,
          file: filePath,
          type: "config",
          message: `${fileName} is a protected config file. Fix your code, not the linter configuration.`,
        };
      }
    }

    // Check protected directories
    for (const dir of PROTECTED_DIRS) {
      if (filePath.includes(`/${dir}/`) || filePath.includes(`\\${dir}\\`)) {
        return {
          blocked: true,
          file: filePath,
          type: "dir",
          message: `${dir}/ is protected. Do not modify git hooks or CI configuration.`,
        };
      }
    }

    return null; // Not protected
  } catch (e) {
    return null; // Parse error, let tool proceed
  }
}

// Read from stdin
let input = "";
process.stdin.setEncoding("utf-8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});

process.stdin.on("end", () => {
  const violation = checkInput(input);

  if (violation?.blocked) {
    console.error(`\n${"=".repeat(70)}`);
    console.error(`🚫 PROTECTED FILE: ${violation.file}`);
    console.error(`\n${violation.message}`);
    console.error(`\nWhy this file is protected:`);
    console.error(
      `  • Changes to ${violation.type === "config" ? "config files" : "git hooks"} affect the entire pipeline`,
    );
    console.error(`  • Prevents agents from silently disabling quality gates`);
    console.error(`  • Keeps linter rules consistent across the team`);
    console.error(`\nWhat to do instead:`);
    console.error(
      `  • Fix the code that triggers linter errors (usually faster)`);
    console.error(
      `  • If config change is truly needed, update CLAUDE.md for human approval`,
    );
    console.error(`${"=".repeat(70)}\n`);
    process.exit(2); // Exit code 2 = blocked by hook
  }

  process.exit(0); // Allowed
});
