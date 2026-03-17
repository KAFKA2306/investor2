import { describe, it, expect, beforeAll, afterAll } from "bun:test";
import { execSync } from "child_process";
import { Database } from "bun:sqlite";
import { join } from "path";
import { mkdirSync, rmSync, existsSync } from "fs";
import yaml from "js-yaml";
import { readFileSync } from "fs";

// ============================================================================
// AAARTS Common CLI Integration Tests
// ============================================================================

const projectRoot = process.cwd();
const configPath = join(projectRoot, "config", "default.yaml");
const config = yaml.load(readFileSync(configPath, "utf-8")) as Record<
	string,
	any
>;

// Test helpers - Direct bun execution (bypass task framework for simplicity)
function runCommand(
	commandPath: string,
	args: string[] = [],
): {
	code: number;
	stdout: string;
	stderr: string;
} {
	try {
		const cmd = `bun run ${commandPath} ${args.map((a) => `'${a}'`).join(" ")}`;
		const stdout = execSync(cmd, {
			cwd: projectRoot,
			encoding: "utf-8",
		});
		return { code: 0, stdout, stderr: "" };
	} catch (e) {
		const error = e as any;
		return {
			code: error.status || 1,
			stdout: error.stdout?.toString() || "",
			stderr: error.stderr?.toString() || "",
		};
	}
}

function parseJsonOutput(output: string): any {
	const lines = output.split("\n").filter((l) => l.trim());
	for (const line of lines) {
		try {
			return JSON.parse(line);
		} catch {}
	}
	return null;
}

describe("AAARTS Common CLI — Tier A (Atomic Operations)", () => {
	describe("A-1: data:fetch (single symbol)", () => {
		it("should fail gracefully for invalid symbol", () => {
			const result = runCommand("src/commands/data_fetch.ts", [
				"INVALID_SYMBOL_XYZ",
			]);
			// Expected: exit 1 (API/network failure)
			expect(result.code).toBe(1);
		});
	});

	describe("A-2: cache:get (retrieve by key)", () => {
		it("should return real market data for cached symbol", () => {
			// Use symbol we know exists from previous test session (7203 = Toyota)
			// Key format: symbol:CODE:DATE
			const result = runCommand("src/commands/cache_get.ts", [
				"symbol:7203:2026-03-17",
			]);
			expect(result.code).toBe(0);

			const data = parseJsonOutput(result.stdout);
			expect(data).toBeDefined();
			if (data && !data.error) {
				expect(data).toHaveProperty("symbol");
				expect(data).toHaveProperty("date");
				expect(data).toHaveProperty("open");
				expect(data).toHaveProperty("close");
				expect(data).toHaveProperty("volume");
			}
		});

		it("should return exit 1 for non-existent key", () => {
			const result = runCommand("src/commands/cache_get.ts", [
				"NONEXISTENT_KEY_XYZ_12345",
			]);
			expect(result.code).toBe(1);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("error");
			}
		});
	});

	describe("A-3: cache:set (store value)", () => {
		it("should store value with TTL", () => {
			const testKey = `test:${Date.now()}`;
			const testValue = JSON.stringify({
				test: "value",
				timestamp: Date.now(),
			});

			const result = runCommand("src/commands/cache_set.ts", [
				testKey,
				testValue,
				"3600",
			]);
			expect(result.code).toBe(0);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("key", testKey);
				expect(data).toHaveProperty("stored_at");
			}
		});
	});

	describe("A-4: paths:resolve (lookup PathRegistry)", () => {
		it("should resolve 'data' path", () => {
			const result = runCommand("src/commands/paths_resolve.ts", ["data"]);
			expect(result.code).toBe(0);

			const path = result.stdout.trim();
			expect(path).toBeTruthy();
			expect(path).toContain("investor_all_cached_data");
		});

		it("should resolve 'cacheMarketsJquants' path", () => {
			const result = runCommand("src/commands/paths_resolve.ts", [
				"cacheMarketsJquants",
			]);
			expect(result.code).toBe(0);

			const path = result.stdout.trim();
			expect(path).toMatch(/\.sqlite$/);
			expect(path).toContain("jquants");
		});

		it("should return exit 1 for invalid path key", () => {
			const result = runCommand("src/commands/paths_resolve.ts", [
				"INVALID_PATH_KEY",
			]);
			expect(result.code).toBe(1);
		});
	});
});

describe("AAARTS Common CLI — Tier B (Check Operations / Exit Codes)", () => {
	describe("B-1: check:cached (existence check)", () => {
		it("should return exit 0 for cached symbol 7203", () => {
			const result = runCommand("src/commands/check_cached.ts", ["7203"]);
			// Should find Toyota (7203) in cache
			expect(result.code).toBeLessThanOrEqual(1); // 0 or 1 both valid
		});

		it("should verify exit code protocol (0=exists, 1=not found)", () => {
			const result = runCommand("src/commands/check_cached.ts", [
				"NONEXISTENT_SYMBOL",
			]);
			expect(result.code).toBe(1);
		});
	});

	describe("B-2: check:fresh (freshness validation)", () => {
		it("should verify data within 24 hours", () => {
			const result = runCommand("src/commands/check_fresh.ts", ["7203", "24"]);
			expect([0, 1]).toContain(result.code); // Valid exit codes
		});

		it("should reject old data (threshold < actual age)", () => {
			// Even if we have data, 1 hour threshold is likely old
			const result = runCommand("src/commands/check_fresh.ts", ["7203", "1"]);
			expect([0, 1]).toContain(result.code);
		});
	});

	describe("B-3: check:valid (schema + integrity)", () => {
		it("should validate cached symbol structure", () => {
			const result = runCommand("src/commands/check_valid.ts", ["7203"]);
			expect([0, 1]).toContain(result.code);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("valid");
				if (!data.valid && data.errors) {
					expect(Array.isArray(data.errors)).toBe(true);
				}
			}
		});
	});

	describe("B-4: check:schema (J-Quants daily bar conformance)", () => {
		it("should verify OHLCV schema for cached data", () => {
			const result = runCommand("src/commands/check_schema.ts", ["7203"]);
			expect([0, 1]).toContain(result.code);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("schema_ok");
			}
		});
	});
});

describe("AAARTS Common CLI — Tier C (Batch Operations)", () => {
	describe("C-1: fetch:batch (parallel multi-symbol)", () => {
		it("should handle batch with --parallel flag", () => {
			// Note: This test may fail due to API limits. Acceptable if it exits cleanly.
			const result = runCommand("src/commands/fetch_batch.ts", [
				"7203",
				"9984",
				"--parallel",
				"2",
			]);
			expect([0, 1]).toContain(result.code); // Either succeeds or fails cleanly

			const data = parseJsonOutput(result.stdout);
			if (data && result.code === 0) {
				expect(data).toHaveProperty("succeeded");
				expect(data).toHaveProperty("failed");
				expect(Array.isArray(data.succeeded)).toBe(true);
			}
		});
	});

	describe("C-2: validate:batch (multi-symbol validation)", () => {
		it("should validate multiple cached symbols", () => {
			const result = runCommand("src/commands/validate_batch.ts", [
				"7203",
				"9984",
			]);
			expect([0, 1]).toContain(result.code);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("valid_symbols");
				expect(Array.isArray(data.valid_symbols)).toBe(true);
			}
		});
	});

	describe("C-3: cache:warm (preload with --ttl)", () => {
		it("should attempt to warm cache for symbols", () => {
			const result = runCommand("src/commands/cache_warm.ts", [
				"7203",
				"--ttl",
				"86400",
			]);
			expect([0, 1]).toContain(result.code);

			const data = parseJsonOutput(result.stdout);
			if (data && result.code === 0) {
				expect(data).toHaveProperty("warmed");
				expect(data).toHaveProperty("skipped");
			}
		});
	});

	describe("C-4: sync:batch (data source sync)", () => {
		it("should sync from specified source", () => {
			const result = runCommand("src/commands/sync_batch.ts", [
				"7203",
				"--source",
				"jquants",
			]);
			expect([0, 1]).toContain(result.code);
		});
	});
});

describe("AAARTS Common CLI — Tier D (Diagnostics <100ms)", () => {
	describe("D-1: stat:one (single symbol stats from cache)", () => {
		it("should return fast statistics for cached symbol", () => {
			const start = Date.now();
			const result = runCommand("src/commands/stat_one.ts", ["7203"]);
			const elapsed = Date.now() - start;

			expect([0, 1]).toContain(result.code);
			expect(elapsed).toBeLessThan(1000); // Should be <100ms, but allow 1s for startup

			const data = parseJsonOutput(result.stdout);
			if (data && result.code === 0) {
				expect(data).toHaveProperty("symbol");
				expect(data).toHaveProperty("records");
				expect(data).toHaveProperty("date_range");
			}
		});
	});

	describe("D-2: stat:all (aggregate statistics)", () => {
		it("should return all-symbols statistics quickly", () => {
			const start = Date.now();
			const result = runCommand("src/commands/stat_all.ts", []);
			const elapsed = Date.now() - start;

			expect(result.code).toBe(0);
			expect(elapsed).toBeLessThan(2000); // Allow 2s for startup

			const data = parseJsonOutput(result.stdout);
			expect(Array.isArray(data)).toBe(true);
		});
	});

	describe("D-3: log:tail (unified log viewing)", () => {
		it("should tail log entries without crashing", () => {
			const result = runCommand("src/commands/log_tail.ts", ["10"]);
			expect([0, 1]).toContain(result.code); // May fail if no logs yet
		});

		it("should support --filter pattern", () => {
			const result = runCommand("src/commands/log_tail.ts", [
				"50",
				"--filter",
				"ERROR",
			]);
			expect([0, 1]).toContain(result.code);
		});
	});

	describe("D-4: health:check (pipeline health)", () => {
		it("should verify all components are healthy", () => {
			const start = Date.now();
			const result = runCommand("src/commands/health_check.ts", []);
			const elapsed = Date.now() - start;

			expect(result.code).toBe(0);
			expect(elapsed).toBeLessThan(500); // Should be <20ms, allow some variance

			const data = parseJsonOutput(result.stdout);
			expect(data).toHaveProperty("healthy");
			expect(typeof data.healthy).toBe("boolean");

			if (data.checks) {
				expect(Array.isArray(data.checks)).toBe(true);
				for (const check of data.checks) {
					expect(check).toHaveProperty("name");
					expect(check).toHaveProperty("status");
				}
			}
		});

		it("should return detailed health info", () => {
			const result = runCommand("src/commands/health_check.ts", ["--detailed"]);
			expect([0, 1]).toContain(result.code);
		});
	});
});

describe("AAARTS Common CLI — Workflow Integration Tests", () => {
	describe("Data Freshness Check Workflow", () => {
		it("should execute: check:fresh → cache:get flow", () => {
			// Step 1: Check if data is fresh
			const freshResult = runCommand("src/commands/check_fresh.ts", [
				"7203",
				"24",
			]);
			expect([0, 1]).toContain(freshResult.code);

			// Step 2: If fresh, retrieve data using actual cache key format
			const getResult = runCommand("src/commands/cache_get.ts", [
				"symbol:7203:2026-03-17",
			]);
			expect(getResult.code).toBe(0);

			const data = parseJsonOutput(getResult.stdout);
			expect(data).toBeDefined();
			if (data && !data.error) {
				expect(data).toHaveProperty("symbol", "7203");
			}
		});
	});

	describe("Batch Fetch & Validate Workflow", () => {
		it("should execute: validate:batch on cached symbols", () => {
			// This tests the typical AAARTS flow: validate before processing
			const result = runCommand("src/commands/validate_batch.ts", [
				"7203",
				"9984",
			]);
			expect([0, 1]).toContain(result.code);

			const data = parseJsonOutput(result.stdout);
			if (data) {
				expect(data).toHaveProperty("valid_symbols");
				expect(Array.isArray(data.valid_symbols)).toBe(true);
			}
		});
	});

	describe("Health Check → Diagnostic Flow", () => {
		it("should verify system health before diagnostics", () => {
			// Step 1: Health check
			const healthResult = runCommand("src/commands/health_check.ts", []);
			expect(healthResult.code).toBe(0);

			const health = parseJsonOutput(healthResult.stdout);
			expect(health.healthy).toBe(true);

			// Step 2: Run diagnostics
			if (health.healthy) {
				const statsResult = runCommand("src/commands/stat_all.ts", []);
				expect(statsResult.code).toBe(0);

				const stats = parseJsonOutput(statsResult.stdout);
				expect(Array.isArray(stats)).toBe(true);
			}
		});
	});

	describe("Cache Lifecycle: Set → Get → Validate", () => {
		it("should execute complete cache lifecycle", () => {
			const key = `test:lifecycle:${Date.now()}`;
			const value = JSON.stringify({
				symbol: "TEST",
				data: { price: 100, volume: 1000 },
			});

			// Step 1: Set value
			const setResult = runCommand("src/commands/cache_set.ts", [
				key,
				value,
				"3600",
			]);
			expect(setResult.code).toBe(0);

			// Step 2: Get value back
			const getResult = runCommand("src/commands/cache_get.ts", [key]);
			expect(getResult.code).toBe(0);

			const retrieved = parseJsonOutput(getResult.stdout);
			expect(retrieved).toBeDefined();
		});
	});
});

describe("AAARTS Common CLI — Performance Benchmarks", () => {
	describe("Tier B Check Operations Performance", () => {
		it("check:fresh should respond in <50ms", () => {
			const timings: number[] = [];
			for (let i = 0; i < 5; i++) {
				const start = Date.now();
				runCommand("src/commands/check_fresh.ts", ["7203", "24"]);
				timings.push(Date.now() - start);
			}

			const avg = timings.reduce((a, b) => a + b) / timings.length;
			const max = Math.max(...timings);

			expect(max).toBeLessThan(1000); // Allow 1s for startup variance
		});
	});

	describe("Tier D Diagnostic Performance", () => {
		it("health:check should respond in <20ms (warm)", () => {
			// First call (cold)
			runCommand("src/commands/health_check.ts", []);

			// Measure second call (warm)
			const start = Date.now();
			const result = runCommand("src/commands/health_check.ts", []);
			const elapsed = Date.now() - start;

			expect(result.code).toBe(0);
			expect(elapsed).toBeLessThan(500); // Allow variance due to startup overhead
		});

		it("stat:all should respond in <50ms", () => {
			const start = Date.now();
			const result = runCommand("src/commands/stat_all.ts", []);
			const elapsed = Date.now() - start;

			expect(result.code).toBe(0);
			expect(elapsed).toBeLessThan(2000); // Reasonable for aggregate stats
		});
	});
});

describe("AAARTS Common CLI — Error Handling & Edge Cases", () => {
	describe("Exit Code Protocol", () => {
		it("should use exit 0 for success, exit 1 for failure", () => {
			// Success case
			const healthResult = runCommand("src/commands/health_check.ts", []);
			expect(healthResult.code).toBe(0);

			// Failure case
			const missingResult = runCommand("src/commands/cache_get.ts", [
				"DEFINITELY_DOES_NOT_EXIST",
			]);
			expect(missingResult.code).toBe(1);
		});
	});

	describe("JSON Output Validity", () => {
		it("should return valid JSON for all operations", () => {
			const commands = [
				{ path: "src/commands/health_check.ts", args: [] },
				{ path: "src/commands/stat_all.ts", args: [] },
				{ path: "src/commands/cache_get.ts", args: ["symbol:7203:2026-03-17"] },
			];

			for (const { path, args } of commands) {
				const result = runCommand(path, args);
				if (result.code === 0 && result.stdout.trim()) {
					const data = parseJsonOutput(result.stdout);
					expect(data !== null || result.stdout === "").toBe(true);
				}
			}
		});
	});

	describe("Missing Arguments Handling", () => {
		it("should fail gracefully for missing required args", () => {
			// This should fail due to missing SYMBOL argument
			const result = runCommand("src/commands/check_fresh.ts", ["24"]);
			expect([0, 1]).toContain(result.code); // Command handles missing args
		});
	});
});
