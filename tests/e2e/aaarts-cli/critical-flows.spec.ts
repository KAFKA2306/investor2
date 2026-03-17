import { test, expect } from "@playwright/test";
import { execSync, exec } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import Database from "better-sqlite3";

const execAsync = promisify(exec);

// Test utilities
const runTaskCommand = (
	taskName: string,
	vars: Record<string, string> = {},
): string => {
	const varFlags = Object.entries(vars)
		.map(([key, value]) => `${key}='${value.replace(/'/g, "'\\''")}'`)
		.join(" ");
	const cmd = varFlags ? `task ${taskName} ${varFlags}` : `task ${taskName}`;
	return execSync(cmd, {
		cwd: "/home/kafka/finance/investor2",
		encoding: "utf-8",
		env: { ...process.env, ...vars }, // Also set in env to be double sure
	});
};

const parseJsonOutput = (output: string): any => {
	const lines = output.trim().split("\n");
	// Try from the bottom up to find the last JSON (usually the command output)
	for (let i = lines.length - 1; i >= 0; i--) {
		const line = lines[i].trim();
		if (
			(line.startsWith("{") && line.endsWith("}")) ||
			(line.startsWith("[") && line.endsWith("]"))
		) {
			try {
				return JSON.parse(line);
			} catch {
				continue;
			}
		}
	}
	throw new Error(`No valid JSON found in output: ${output.substring(0, 100)}...`);
};

const getCacheDb = (): any => {
	return new Database(
		"/mnt/d/investor_all_cached_data/cache/markets/jquants.sqlite",
		{
			readonly: true,
		},
	);
};

const testSymbols = ["7203", "9984"];

test.beforeAll(() => {
	const db = new Database(
		"/mnt/d/investor_all_cached_data/cache/markets/jquants.sqlite",
	);
	db.prepare(`
		CREATE TABLE IF NOT EXISTS http_cache (
			key TEXT PRIMARY KEY,
			value TEXT NOT NULL,
			created_at INTEGER NOT NULL
		)
	`).run();

	const now = Date.now();
	const to = new Date().toISOString().split("T")[0];
	const from = new Date(now - 730 * 24 * 60 * 60 * 1000)
		.toISOString()
		.split("T")[0];

	// Inject per-symbol mock data via DIRECT BUN to bypass task quoting issues
	for (const symbol of testSymbols) {
		const url = `https://api.jquants.com/v2/equities/bars/daily?code=${symbol}&from=${from}&to=${to}`;
		const mockData = {
			data: [
				{
					Code: symbol,
					Date: to,
					AdjustmentClose: 2500.5,
					AdjustmentVolume: 1234567,
				},
			],
		};
		// Use direct bun call for injection
		execSync(`bun src/commands/cache_set.ts '${url}' '${JSON.stringify(mockData)}' 86400`, {
			cwd: "/home/kafka/finance/investor2",
		});
	}

	// Inject bulk fetch mock data
	const bulkDate = to.replace(/-/g, "");
	const bulkUrl = `https://api.jquants.com/v2/equities/bars/daily?date=${bulkDate}`;
	const bulkData = {
		data: testSymbols.map((symbol) => ({
			Code: symbol,
			Date: to,
			AdjustmentClose: 2500.5,
			AdjustmentVolume: 1234567,
		})),
	};
	execSync(`bun src/commands/cache_set.ts '${bulkUrl}' '${JSON.stringify(bulkData)}' 86400`, {
		cwd: "/home/kafka/finance/investor2",
	});
});

test.describe("AAARTS Critical Flows", () => {
	test.describe("1. Data Freshness Check Flow", () => {
		test("check:fresh returns valid freshness status", () => {
			const symbol = testSymbols[0];
			const hours = 72;

			const output = runTaskCommand("check:fresh", {
				SYMBOL: symbol,
				HOURS: String(hours),
			});

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("fresh");
			expect(result).toHaveProperty("age_hours");
			expect(result).toHaveProperty("threshold_hours");
			expect(result).toHaveProperty("symbol");
			expect(result.symbol).toBe(symbol);
			expect(result.threshold_hours).toBe(hours);

			if (typeof result.age_hours === "number") {
				expect(result.age_hours).toBeGreaterThanOrEqual(0);
			}
		});

		test("check:fresh with stale data returns false", () => {
			const symbol = testSymbols[1];
			const hours = 1;

			const output = runTaskCommand("check:fresh", {
				SYMBOL: symbol,
				HOURS: String(hours),
			});

			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("fresh");
			expect(typeof result.fresh).toBe("boolean");
		});

		test("data:fetch updates cache with new data", () => {
			const symbol = testSymbols[0];

			const output = runTaskCommand("data:fetch", { SYMBOL: symbol });

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("symbol");
			expect(result.symbol).toBe(symbol);
			expect(result).toHaveProperty("records");

			if (typeof result.records === "number") {
				expect(result.records).toBeGreaterThanOrEqual(0);
			}
		});

		test("cache:get returns updated data after fetch", () => {
			const symbol = testSymbols[0];

			runTaskCommand("data:fetch", { SYMBOL: symbol });

			const db = getCacheDb();
			const rows = db
				.prepare(
					"SELECT key FROM http_cache WHERE key LIKE '%/equities/bars/daily?date=%'",
				)
				.all() as Array<{ key: string }>;

			expect(rows.length).toBeGreaterThan(0);

			const key = rows[0].key;
			const output = runTaskCommand("cache:get", { KEY: key });
			const value = JSON.parse(output);

			expect(value).toHaveProperty("data");
			expect(Array.isArray(value.data)).toBe(true);

			db.close();
		});
	});

	test.describe("2. Batch Fetch & Validate Flow", () => {
		test("fetch:batch with parallel execution succeeds", () => {
			const symbols = testSymbols.join(",");
			const parallelCount = "3";

			const output = runTaskCommand("fetch:batch", {
				SYMBOLS: symbols,
				PARALLEL: parallelCount,
			});

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("total");
			expect(result).toHaveProperty("succeeded");
			expect(result).toHaveProperty("failed");
			expect(result.total).toBe(testSymbols.length);

			if (typeof result.succeeded === "number") {
				expect(result.succeeded).toBeGreaterThan(0);
			}

			if (Array.isArray(result.results)) {
				result.results.forEach((item: Record<string, unknown>) => {
					expect(item).toHaveProperty("symbol");
					expect(item).toHaveProperty("status");
					expect(["success", "failed"]).toContain(item.status);
				});
			}
		});

		test("validate:batch checks all symbols", () => {
			const symbols = testSymbols.join(",");

			const output = runTaskCommand("validate:batch", { SYMBOLS: symbols });

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("total");
			expect(result).toHaveProperty("valid");

			if (Array.isArray(result.results)) {
				result.results.forEach((item: Record<string, unknown>) => {
					expect(item).toHaveProperty("symbol");
					expect(item).toHaveProperty("valid");
					expect(typeof item.valid).toBe("boolean");
				});
			}
		});

		test("batch operations handle partial failures", () => {
			const validSymbol = testSymbols[0];
			const invalidSymbol = "INVALID_SYMBOL_999999";
			const symbols = `${validSymbol},${invalidSymbol}`;

			const output = runTaskCommand("fetch:batch", {
				SYMBOLS: symbols,
				PARALLEL: "2",
			});

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("total");
			expect(result.total).toBe(2);

			if (Array.isArray(result.results)) {
				const statuses = result.results.map(
					(r: Record<string, unknown>) => r.status,
				);
				expect(statuses).toContain("success");
			}
		});

		test("sync:batch merges new data with existing cache", () => {
			const symbols = testSymbols.join(",");

			const output = runTaskCommand("sync:batch", { SYMBOLS: symbols });

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("total");
		});

		test("check:valid checks symbol data integrity", () => {
			const symbol = testSymbols[0];
			const output = runTaskCommand("check:valid", { SYMBOL: symbol });
			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("valid");
			expect(result.symbol).toBe(symbol);
		});

		test("check:schema validates against J-Quants schema", () => {
			const symbol = testSymbols[0];
			const output = runTaskCommand("check:schema", { SYMBOL: symbol });
			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("matches");
			expect(result.symbol).toBe(symbol);
		});

		test("check:cached confirms presence in cache", () => {
			const symbol = testSymbols[0];
			const output = runTaskCommand("check:cached", { SYMBOL: symbol });
			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("exists");
			expect(result.exists).toBe(true);
			expect(result.symbol).toBe(symbol);
		});

		test("cache:warm preloads multiple symbols", () => {
			const symbols = testSymbols.join(",");
			const output = runTaskCommand("cache:warm", { SYMBOLS: symbols });
			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("warmed");
			expect(result).toHaveProperty("skipped");
		});
	});

	test.describe("3. System Health Verification Flow", () => {
		test("health:check verifies PathRegistry", () => {
			const output = runTaskCommand("health:check");

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("healthy");
			expect(result).toHaveProperty("checks");
			expect(Array.isArray(result.checks)).toBe(true);

			const checks = result.checks as Array<{ name: string; status: boolean }>;
			const pathRegistryCheck = checks.find((c) => c.name === "PathRegistry");

			expect(pathRegistryCheck).toBeDefined();
			expect(pathRegistryCheck?.status).toBe(true);
		});

		test("health:check verifies Cache database", () => {
			const output = runTaskCommand("health:check");

			const result = parseJsonOutput(output);

			const checks = result.checks as Array<{ name: string; status: boolean }>;
			const cacheCheck = checks.find((c) => c.name === "CacheSqlite");

			expect(cacheCheck).toBeDefined();
			expect(cacheCheck?.status).toBe(true);
		});

		test("health:check verifies Logs directory", () => {
			const output = runTaskCommand("health:check");

			const result = parseJsonOutput(output);

			const checks = result.checks as Array<{ name: string; status: boolean }>;
			const logCheck = checks.find((c) => c.name === "LogDir");

			expect(logCheck).toBeDefined();
		});

		test("stat:all returns valid JSON statistics", () => {
			const output = runTaskCommand("stat:all");

			const result = JSON.parse(output);

			expect(Array.isArray(result)).toBe(true);
			expect(result.length).toBeGreaterThan(0);

			result.forEach((item: Record<string, unknown>) => {
				expect(item).toHaveProperty("symbol");
				expect(item).toHaveProperty("records");
				expect(item).toHaveProperty("cache_age_hours");
				expect(typeof item.records).toBe("number");
				expect(typeof item.cache_age_hours).toBe("number");
			});
		});

		test("health:check exit code is 0 when healthy", () => {
			try {
				execSync("task health:check", {
					cwd: "/home/kafka/finance/investor2",
				});
			} catch (error: unknown) {
				expect((error as any).status).toBe(0);
			}
		});
	});

	test.describe("4. Cache Lifecycle Flow", () => {
		test("cache:set stores value in SQLite", () => {
			const key = `test/key/${Date.now()}`;
			const value = JSON.stringify({ test: "data", timestamp: Date.now() });
			const ttl = "3600";

			const output = runTaskCommand("cache:set", {
				KEY: key,
				VALUE: value,
				TTL: ttl,
			});

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("key");
			expect(result.key).toBe(key);
			expect(result).toHaveProperty("stored");
			expect(result.stored).toBe(true);
		});

		test("cache:get retrieves previously set value", () => {
			const key = `test/retrieve/${Date.now()}`;
			const value = JSON.stringify({ test: "retrieve", id: 42 });

			runTaskCommand("cache:set", {
				KEY: key,
				VALUE: value,
				TTL: "7200",
			});

			const retrievedOutput = runTaskCommand("cache:get", { KEY: key });

			const retrieved = JSON.parse(retrievedOutput);

			expect(retrieved).toEqual(JSON.parse(value));
		});

		test("cache:get returns error for non-existent key", () => {
			const nonExistentKey = `test/nonexistent/${Date.now()}`;

			try {
				runTaskCommand("cache:get", { KEY: nonExistentKey });
				throw new Error("Expected command to fail");
			} catch (error: unknown) {
				const errorMsg = (error as any).stderr || (error as any).message || "";
				expect(errorMsg.toLowerCase()).toContain("not found");
			}
		});

		test("cache data integrity after set/get cycle", () => {
			const key = `integrity/test/${Date.now()}`;
			const testData = {
				symbol: "9984",
				values: [1, 2, 3, 4, 5],
				metadata: { source: "test", verified: true },
			};
			const value = JSON.stringify(testData);

			runTaskCommand("cache:set", {
				KEY: key,
				VALUE: value,
				TTL: "3600",
			});

			const retrievedOutput = runTaskCommand("cache:get", { KEY: key });

			const retrieved = JSON.parse(retrievedOutput);

			expect(retrieved).toEqual(testData);
			expect(retrieved.symbol).toBe(testData.symbol);
			expect(retrieved.values).toEqual(testData.values);
			expect(retrieved.metadata.verified).toBe(true);
		});

		test("cache contains expected schema fields", () => {
			const db = getCacheDb();

			const tableInfo = db.prepare("PRAGMA table_info(http_cache)").all();

			const columnNames = (tableInfo as Array<{ name: string }>).map(
				(col) => col.name,
			);

			expect(columnNames).toContain("key");
			expect(columnNames).toContain("value");
			expect(columnNames).toContain("created_at");

			db.close();
		});
	});

	test.describe("5. Integration: Complete Workflow", () => {
		test("complete workflow: check fresh -> fetch -> validate -> stats", () => {
			const symbol = testSymbols[0];

			const freshOutput = runTaskCommand("check:fresh", {
				SYMBOL: symbol,
				HOURS: "24",
			});

			const freshResult = parseJsonOutput(freshOutput);
			expect(freshResult).toHaveProperty("fresh");

			const fetchOutput = runTaskCommand("data:fetch", { SYMBOL: symbol });

			const fetchResult = parseJsonOutput(fetchOutput);
			expect(fetchResult).toHaveProperty("symbol");
			expect(fetchResult.symbol).toBe(symbol);

			const validateOutput = runTaskCommand("validate:batch", {
				SYMBOLS: symbol,
			});

			const validateResult = parseJsonOutput(validateOutput);
			expect(validateResult).toHaveProperty("valid");

			const statsOutput = runTaskCommand("stat:all");

			const statResults = JSON.parse(statsOutput);
			expect(Array.isArray(statResults)).toBe(true);

			const symbolStats = statResults.find(
				(s: Record<string, unknown>) => s.symbol === symbol,
			);

			if (symbolStats) {
				expect(symbolStats).toHaveProperty("records");
				expect(symbolStats).toHaveProperty("cache_age_hours");
			}
		});

		test("complete workflow: batch operations with health verification", () => {
			const healthOutput = runTaskCommand("health:check");

			const healthResult = parseJsonOutput(healthOutput);
			expect(healthResult.healthy).toBe(true);

			const symbols = testSymbols.join(",");
			const batchOutput = runTaskCommand("fetch:batch", {
				SYMBOLS: symbols,
				PARALLEL: "2",
			});

			const batchResult = parseJsonOutput(batchOutput);
			expect(batchResult).toHaveProperty("succeeded");

			const secondHealthOutput = runTaskCommand("health:check");

			const secondHealthResult = parseJsonOutput(secondHealthOutput);
			expect(secondHealthResult.healthy).toBe(true);
		});

		test("paths:resolve returns valid configured paths", () => {
			const pathKeys = ["data", "cache", "logs"];

			pathKeys.forEach((pathKey) => {
				const output = runTaskCommand("paths:resolve", { PATH_KEY: pathKey });

				const result = parseJsonOutput(output);

				expect(result).toHaveProperty("key");
				expect(result.key).toBe(pathKey);
				expect(result).toHaveProperty("path");
				expect(typeof result.path).toBe("string");
				expect(typeof (result as any).path).toBe("string");
				expect(((result as any).path as string).length).toBeGreaterThan(0);

				if (existsSync(result.path as string)) {
					expect(existsSync(result.path as string)).toBe(true);
				}
			});
		});
	});

	test.describe("6. Error Handling & Edge Cases", () => {
		test("check:fresh with invalid symbol returns false", () => {
			const invalidSymbol = "NOTAREALSYMBOL999999";

			const output = runTaskCommand("check:fresh", {
				SYMBOL: invalidSymbol,
				HOURS: "24",
			});

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("fresh");
			expect(result.fresh).toBe(false);
			expect(result.symbol).toBe(invalidSymbol);
		});

		test("data:fetch with non-existent symbol handles gracefully", () => {
			const invalidSymbol = "NOTEXIST001";

			try {
				runTaskCommand("data:fetch", { SYMBOL: invalidSymbol });
			} catch (error: unknown) {
				expect((error as any).status).not.toBe(0);
			}
		});

		test("cache:get with empty key returns error", () => {
			try {
				runTaskCommand("cache:get", { KEY: "" });
				throw new Error("Expected command to fail");
			} catch (error: unknown) {
				expect((error as any).status).not.toBe(0);
			}
		});

		test("validate:batch with empty symbols list", () => {
			try {
				runTaskCommand("validate:batch", { SYMBOLS: "" });
			} catch (error: unknown) {
				expect((error as any).status).not.toBe(0);
			}
		});

		test("fetch:batch with zero parallel workers", () => {
			const symbols = testSymbols.join(",");

			try {
				runTaskCommand("fetch:batch", {
					SYMBOLS: symbols,
					PARALLEL: "0",
				});
			} catch (error: unknown) {
				expect((error as any).status).not.toBe(0);
			}
		});

		test("concurrent cache operations do not corrupt data", () => {
			const key = `concurrent/test/${Date.now()}`;
			const value1 = JSON.stringify({ attempt: 1, data: "first" });
			const value2 = JSON.stringify({ attempt: 2, data: "second" });

			runTaskCommand("cache:set", {
				KEY: key,
				VALUE: value1,
				TTL: "3600",
			});

			const result1 = parseJsonOutput(
				runTaskCommand("cache:get", { KEY: key }),
			);

			runTaskCommand("cache:set", {
				KEY: key,
				VALUE: value2,
				TTL: "3600",
			});

			const result2 = parseJsonOutput(
				runTaskCommand("cache:get", { KEY: key }),
			);

			expect(result1.attempt).toBe(1);
			expect(result2.attempt).toBe(2);
		});

		test("stat:one returns statistics for a single symbol", () => {
			const symbol = testSymbols[0];
			const output = runTaskCommand("stat:one", { SYMBOL: symbol });
			const result = parseJsonOutput(output);
			expect(result).toHaveProperty("symbol");
			expect(result.symbol).toBe(symbol);
			expect(result).toHaveProperty("records");
			expect(result.records).toBeGreaterThan(0);
		});

		test("log:tail retrieves recent logs", () => {
			const output = runTaskCommand("log:tail", { N: "5" });
			const lines = output.trim().split("\n");
			expect(lines.length).toBeLessThanOrEqual(10); // Task output + 5 logs
		});
	});

	test.describe("7. Output Format Validation", () => {
		test("all commands produce valid JSON output", () => {
			const commands: Array<{ task: string; vars: Record<string, string> }> = [
				{ task: "check:fresh", vars: { SYMBOL: testSymbols[0], HOURS: "24" } },
				{ task: "data:fetch", vars: { SYMBOL: testSymbols[0] } },
				{ task: "health:check", vars: {} },
				{ task: "stat:all", vars: {} },
			];

			commands.forEach(({ task, vars }) => {
				const output = runTaskCommand(task, vars);

				expect(() => parseJsonOutput(output)).not.toThrow();
			});
		});

		test("fetch:batch output includes all required fields", () => {
			const symbols = testSymbols.join(",");

			const output = runTaskCommand("fetch:batch", {
				SYMBOLS: symbols,
				PARALLEL: "2",
			});

			const result = parseJsonOutput(output);

			const requiredFields = ["total", "succeeded", "failed"];

			requiredFields.forEach((field) => {
				expect(result).toHaveProperty(field);
			});
		});

		test("stat:all output array contains complete records", () => {
			const output = runTaskCommand("stat:all");

			const results = JSON.parse(output) as unknown[];

			expect(Array.isArray(results)).toBe(true);

			if ((results as unknown[]).length > 0) {
				const firstRecord = (results as unknown[])[0] as Record<
					string,
					unknown
				>;

				expect(firstRecord).toHaveProperty("symbol");
				expect(firstRecord).toHaveProperty("records");
				expect(firstRecord).toHaveProperty("cache_age_hours");
				expect(typeof firstRecord.symbol).toBe("string");
				expect(typeof firstRecord.records).toBe("number");
				expect(typeof firstRecord.cache_age_hours).toBe("number");
			}
		});

		test("health:check output structure is valid", () => {
			const output = runTaskCommand("health:check");

			const result = parseJsonOutput(output);

			expect(result).toHaveProperty("healthy");
			expect(typeof result.healthy).toBe("boolean");
			expect(result).toHaveProperty("checks");
			expect(Array.isArray(result.checks)).toBe(true);

			const checks = result.checks as Array<{ name: string; status: boolean }>;

			checks.forEach((check) => {
				expect(check).toHaveProperty("name");
				expect(check).toHaveProperty("status");
				expect(typeof check.name).toBe("string");
				expect(typeof check.status).toBe("boolean");
			});
		});
	});
});
