import { describe, expect, test } from "bun:test";
import type { StandardOutcome } from "../src/schemas";
import { judgeVerification } from "../src/system/verification";

const outcome = (
	overrides: Partial<StandardOutcome> = {},
): StandardOutcome => ({
	sharpe: 0.8,
	ic: 0.04,
	max_drawdown: 0.2,
	p_value: 0.05,
	factor_id: "F_TEST",
	backtest_days: 252,
	...overrides,
});

describe("verification gate", () => {
	test("promotes only when every criterion passes", () => {
		const result = judgeVerification(outcome());

		expect(result.verdict).toBe("GO");
		expect(result.reasons).toEqual(["All verification criteria passed"]);
	});

	test("treats drawdown as a positive loss magnitude", () => {
		expect(() => judgeVerification(outcome({ max_drawdown: -0.2 }))).toThrow();
	});

	test("keeps one failed criterion on HOLD and multiple failures on PIVOT", () => {
		expect(judgeVerification(outcome({ p_value: 0.3 })).verdict).toBe("HOLD");
		expect(
			judgeVerification(outcome({ p_value: 0.3, max_drawdown: 0.6 })).verdict,
		).toBe("PIVOT");
	});

	test("rejects short backtests before promotion", () => {
		const result = judgeVerification(outcome({ backtest_days: 30 }));

		expect(result.verdict).toBe("HOLD");
		expect(result.reasons[0]).toContain("Backtest days 30 < 60");
	});
});
