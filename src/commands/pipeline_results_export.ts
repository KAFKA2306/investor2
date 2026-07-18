import { randomUUID } from "node:crypto";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import {
	type Config,
	type PipelineResultsReport,
	PipelineResultsReportSchema,
} from "../schemas";
import type { PipelineOrchestrator } from "../system/pipeline_orchestrator";

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

	const cycleSummaries = orchestrator.getCycleSummaries();

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
			minBacktestDays: thresholds?.minBacktestDays ?? 60,
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
