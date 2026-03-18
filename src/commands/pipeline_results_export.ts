import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { randomUUID } from "crypto";
import {
	Config,
	PipelineResultsReport,
	PipelineResultsReportSchema,
	VerificationResult,
} from "../schemas";
import { PipelineOrchestrator } from "../system/pipeline_orchestrator";

/**
 * Export pipeline results to JSON file for dashboard visualization
 * Persists PipelineResultsReport with all cycle data and thresholds
 */
export async function exportPipelineResults(
	orchestrator: PipelineOrchestrator,
	config: Config,
	executionStartMs: number,
): Promise<PipelineResultsReport> {
	const executionEndMs = Date.now();
	const verdicts = orchestrator.getResults();
	const thresholds = config.pipelineBlueprint?.verificationAcceptance;

	// Build cycle summaries from verdicts
	const cycleSummaries = verdicts.map((verdict, idx) => ({
		cycle: idx + 1,
		candidates_generated: 1,
		go_count: verdict.verdict === "GO" ? 1 : 0,
		hold_count: verdict.verdict === "HOLD" ? 1 : 0,
		pivot_count: verdict.verdict === "PIVOT" ? 1 : 0,
		elapsed_ms: verdict.outcome.backtest_days * 10, // Approximate from backtest days
	}));

	const report: PipelineResultsReport = {
		execution_id: randomUUID(),
		execution_timestamp: new Date().toISOString(),
		total_cycles: verdicts.length,
		elapsed_seconds: Math.round((executionEndMs - executionStartMs) / 1000),
		cycle_summaries: cycleSummaries,
		verdicts,
		config_thresholds: {
			minSharpe: thresholds?.minSharpe ?? 0.25,
			maxPValue: thresholds?.maxPValue ?? 0.2,
			maxDrawdown: thresholds?.maxDrawdown ?? 0.45,
		},
	};

	// Validate report
	const validated = PipelineResultsReportSchema.parse(report);

	// Persist to file using config paths
	const outputDir = resolve(config.paths.logs, "..");
	const outputPath = resolve(outputDir, "pipeline_results.json");

	writeFileSync(outputPath, JSON.stringify(validated, null, 2));

	return validated;
}
