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
import { judgeVerification } from "./verification";

/**
 * PipelineOrchestrator
 * AAARTS (Autonomous Agentic Alpha Trade System) discovery pipeline
 * Implements a self-improving agentic loop: hypothesis generation → backtesting → systematic verification
 */
export class PipelineOrchestrator {
	private config: Config;
	private consecutiveFailures = 0;
	private cycleResults: VerificationResult[] = [];
	private cycleSummaries: CycleSummary[] = [];
	private domainContext: string = randomUUID();

	constructor(config: Config) {
		this.config = config;
	}

	/**
	 * Get all cycle results collected during pipeline execution
	 */
	getResults(): VerificationResult[] {
		return [...this.cycleResults];
	}

	getCycleSummaries(): CycleSummary[] {
		return [...this.cycleSummaries];
	}

	/**
	 * Main pipeline execution
	 * Runs maxCycles iterations of: generate → backtest → verdict → ralph loop
	 */
	async run(): Promise<void> {
		this.cycleResults = [];
		this.cycleSummaries = [];
		this.consecutiveFailures = 0;
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
			if (this.consecutiveFailures >= maxFailures) {
				this.domainContext = randomUUID();
				this.consecutiveFailures = 0;
			}

			cycleSummary.elapsed_ms = Date.now() - cycleStartMs;

			// Output cycle summary
			const summary = CycleSummarySchema.parse(cycleSummary);
			this.cycleSummaries.push(summary);
			process.stdout.write(`${JSON.stringify(summary)}\n`);

			const sleepSec = this.config.pipelineBlueprint?.alphaLoop?.sleepSec ?? 0;
			if (cycle < maxCycles && sleepSec > 0) {
				await Bun.sleep(sleepSec * 1000);
			}
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
			factor_id: `F_${this.domainContext.slice(0, 8)}_${randomUUID().slice(0, 8)}`,
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
		return VerificationResultSchema.parse(
			judgeVerification(
				outcome,
				this.config.pipelineBlueprint?.verificationAcceptance,
			),
		);
	}
}
