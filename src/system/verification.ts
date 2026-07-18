import {
	type StandardOutcome,
	StandardOutcomeSchema,
	type VerificationAcceptance,
	VerificationAcceptanceSchema,
	type VerificationResult,
} from "../schemas";

const DEFAULT_ACCEPTANCE = {
	minSharpe: 0.25,
	maxPValue: 0.2,
	maxDrawdown: 0.45,
	minBacktestDays: 60,
} satisfies VerificationAcceptance;

function clamp(value: number, lower: number, upper: number): number {
	return Math.min(Math.max(value, lower), upper);
}

function resolveAcceptance(
	acceptance?: Partial<VerificationAcceptance>,
): VerificationAcceptance {
	return VerificationAcceptanceSchema.parse({
		...DEFAULT_ACCEPTANCE,
		...acceptance,
	});
}

function computeConfidence(outcome: StandardOutcome): number {
	const sharpeScore = clamp(outcome.sharpe / 2, 0, 1);
	const significanceScore = 1 - outcome.p_value;
	const drawdownScore = 1 - clamp(outcome.max_drawdown, 0, 1);
	const sampleScore = clamp(outcome.backtest_days / 252, 0, 1);

	return clamp(
		sharpeScore * 0.4 +
			significanceScore * 0.2 +
			drawdownScore * 0.2 +
			sampleScore * 0.2,
		0,
		1,
	);
}

/**
 * Apply the promotion gate to one backtest result.
 *
 * `max_drawdown` is represented as a positive loss magnitude, e.g. 0.25
 * means a 25% drawdown. This avoids a negative drawdown accidentally passing
 * a `<=` risk threshold.
 */
export function judgeVerification(
	outcome: StandardOutcome,
	acceptance?: Partial<VerificationAcceptance>,
): VerificationResult {
	const validatedOutcome = StandardOutcomeSchema.parse(outcome);
	const thresholds = resolveAcceptance(acceptance);
	const minBacktestDays =
		thresholds.minBacktestDays ?? DEFAULT_ACCEPTANCE.minBacktestDays;
	const failures: string[] = [];

	if (validatedOutcome.sharpe < thresholds.minSharpe) {
		failures.push(
			`Sharpe ${validatedOutcome.sharpe} < ${thresholds.minSharpe}`,
		);
	}
	if (validatedOutcome.p_value > thresholds.maxPValue) {
		failures.push(
			`p-value ${validatedOutcome.p_value} > ${thresholds.maxPValue}`,
		);
	}
	if (validatedOutcome.max_drawdown > thresholds.maxDrawdown) {
		failures.push(
			`Max drawdown ${validatedOutcome.max_drawdown} > ${thresholds.maxDrawdown}`,
		);
	}
	if (validatedOutcome.backtest_days < minBacktestDays) {
		failures.push(
			`Backtest days ${validatedOutcome.backtest_days} < ${minBacktestDays}`,
		);
	}

	const verdict =
		failures.length === 0 ? "GO" : failures.length === 1 ? "HOLD" : "PIVOT";
	const reasons =
		failures.length === 0 ? ["All verification criteria passed"] : failures;

	return {
		verdict,
		confidence: computeConfidence(validatedOutcome),
		reasons,
		outcome: validatedOutcome,
	};
}
