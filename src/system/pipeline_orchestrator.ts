import { randomUUID } from "node:crypto";
import {
	type AlphaCandidate,
	AlphaCandidateSchema,
	type Config,
	type CycleSummary,
	CycleSummarySchema,
	type StandardOutcome,
	StandardOutcomeSchema,
	type VerificationResult,
	VerificationResultSchema,
} from "../schemas";

/**
 * PipelineOrchestrator
 * AAARTS (Autonomous Agentic Alpha Trade System) discovery pipeline
 * Implements a self-improving agentic loop: hypothesis generation → backtesting → systematic verification
 */
export class PipelineOrchestrator {
	private config: Config;
	private consecutiveFailures = 0;
	private cycleResults: VerificationResult[] = [];
	private domainContext: string = randomUUID();

	constructor(config: Config) {
		this.config = config;
	}

	/**
	 * Get all cycle results collected during pipeline execution
	 */
	getResults(): VerificationResult[] {
		return this.cycleResults;
	}

	/**
	 * Main pipeline execution
	 * Runs maxCycles iterations of: generate → backtest → verdict → ralph loop
	 */
	async run(): Promise<void> {
		const maxCycles = this.config.pipelineBlueprint?.alphaLoop?.maxCycles ?? 1;
		const maxFailures =
			this.config.pipelineBlueprint?.alphaLoop?.maxFailures ?? 1;

		for (let cycle = 1; cycle <= maxCycles; cycle++) {
			const cycleStartMs = Date.now();
			const cycleSummary: Partial<CycleSummary> = {
				cycle,
				candidates_generated: 0,
				go_count: 0,
				hold_count: 0,
				pivot_count: 0,
			};

			// Generate alpha hypothesis
			const candidate = await this.generateAlphaHypothesis();
			cycleSummary.candidates_generated = 1;

			// Run backtest
			const outcome = await this.runBacktest(candidate);

			// Judge verdict
			const verdict = this.judgeVerdict(outcome);
			this.cycleResults.push(verdict);

			// Update cycle summary
			switch (verdict.verdict) {
				case "GO":
					cycleSummary.go_count = 1;
					this.consecutiveFailures = 0;
					break;
				case "HOLD":
					cycleSummary.hold_count = 1;
					this.consecutiveFailures = 0;
					break;
				case "PIVOT":
					cycleSummary.pivot_count = 1;
					this.consecutiveFailures += 1;
					break;
			}

			// Ralph Loop: Re-initialize domain on consecutive failures
			if (this.consecutiveFailures > maxFailures) {
				this.domainContext = randomUUID();
				this.consecutiveFailures = 0;
			}

			cycleSummary.elapsed_ms = Date.now() - cycleStartMs;

			// Output cycle summary
			const summary = CycleSummarySchema.parse(cycleSummary);
			process.stdout.write(`${JSON.stringify(summary)}\n`);
		}
	}

	/**
	 * Generate alpha hypothesis using LES agent
	 * Calls Gemini API via @google/genai
	 */
	private async generateAlphaHypothesis(): Promise<AlphaCandidate> {
		// For now, return a minimal stub hypothesis
		// In future: call LES agent with @google/genai
		const candidate: AlphaCandidate = {
			factor_id: `F_${randomUUID().slice(0, 8)}`,
			formula: "Rank(CLOSE)",
			economic_mechanism: "Mean reversion in price momentum",
		};

		return AlphaCandidateSchema.parse(candidate);
	}

	/**
	 * Run backtest via Python subprocess
	 * Executes: uv run python scripts/backtest_stub.py --factor_id --formula
	 * Expects JSON output on stdout
	 */
	private async runBacktest(
		candidate: AlphaCandidate,
	): Promise<StandardOutcome> {
		const proc = Bun.spawn(
			[
				"uv",
				"run",
				"python",
				"scripts/backtest_stub.py",
				"--factor_id",
				candidate.factor_id,
				"--formula",
				candidate.formula,
			],
			{
				stdout: "pipe",
				stderr: "pipe",
			},
		);

		const exitCode = await proc.exited;
		const stdout = await new Response(proc.stdout).text();
		const stderr = await new Response(proc.stderr).text();

		if (exitCode !== 0) {
			throw new Error(
				`Backtest failed with exit code ${exitCode}. stderr: ${stderr}`,
			);
		}

		// Parse JSON outcome from stdout
		const outcome = StandardOutcomeSchema.parse(JSON.parse(stdout));
		return outcome;
	}

	/**
	 * Judge verdict based on verification thresholds
	 * Uses config.pipelineBlueprint.verificationAcceptance
	 */
	private judgeVerdict(outcome: StandardOutcome): VerificationResult {
		const acceptance = this.config.pipelineBlueprint?.verificationAcceptance;
		const minSharpe = acceptance?.minSharpe ?? 0.25;
		const maxPValue = acceptance?.maxPValue ?? 0.2;
		const maxDrawdown = acceptance?.maxDrawdown ?? 0.45;

		const reasons: string[] = [];
		let verdict: "GO" | "HOLD" | "PIVOT" = "HOLD";

		// Check all criteria
		const sharpeOk = outcome.sharpe >= minSharpe;
		const pValueOk = outcome.p_value <= maxPValue;
		const drawdownOk = outcome.max_drawdown <= maxDrawdown;

		if (!sharpeOk) {
			reasons.push(`Sharpe ${outcome.sharpe} < ${minSharpe}`);
		}
		if (!pValueOk) {
			reasons.push(`p-value ${outcome.p_value} > ${maxPValue}`);
		}
		if (!drawdownOk) {
			reasons.push(`Max Drawdown ${outcome.max_drawdown} > ${maxDrawdown}`);
		}

		// Verdict logic
		if (sharpeOk && pValueOk && drawdownOk) {
			verdict = "GO";
			reasons.push("All criteria passed");
		} else if (reasons.length > 1) {
			verdict = "PIVOT";
			reasons.push("Multiple criteria failed");
		} else {
			verdict = "HOLD";
			reasons.push("Marginal criteria");
		}

		const result: VerificationResult = {
			verdict,
			confidence: this.computeConfidence(outcome),
			reasons,
			outcome,
		};

		return VerificationResultSchema.parse(result);
	}

	/**
	 * Compute confidence score from outcome metrics
	 * Simple Sharpe-weighted confidence
	 */
	private computeConfidence(outcome: StandardOutcome): number {
		// Sharpe-weighted: [0, 1]
		return Math.min(Math.max(outcome.sharpe / 2.0, 0), 1);
	}
}
