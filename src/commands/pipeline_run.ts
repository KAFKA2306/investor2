import { readFileSync } from "node:fs";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";
import { PipelineOrchestrator } from "../system/pipeline_orchestrator";
import { exportPipelineResults } from "./pipeline_results_export";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

const startMs = Date.now();
const orchestrator = new PipelineOrchestrator(config);
await orchestrator.run();

// Export results for dashboard visualization
await exportPipelineResults(orchestrator, config, startMs);
