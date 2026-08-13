import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
	CandidateDeepDiveSchema,
	evaluateCandidate,
	HypothesisSpecSchema,
	McpCaptureSnapshotSchema,
} from "../research/hypothesis_lab";

const hypothesisPath =
	Bun.env.HYPOTHESIS_PATH ??
	"data/hypothesis_lab/hypotheses/growth_value_dislocation_v1.json";
const capturePath =
	Bun.env.CAPTURE_PATH ??
	"data/hypothesis_lab/captures/2026-08-13-growth-value-dislocation-stage-a.json";
const deepDiveDir = Bun.env.DEEP_DIVE_DIR ?? "data/hypothesis_lab/deep_dives";

const hypothesis = HypothesisSpecSchema.parse(
	JSON.parse(readFileSync(hypothesisPath, "utf8")),
);
const capture = McpCaptureSnapshotSchema.parse(
	JSON.parse(readFileSync(capturePath, "utf8")),
);

if (capture.hypothesis_id !== hypothesis.hypothesis_id) {
	throw new Error(
		`capture hypothesis ${capture.hypothesis_id} does not match ${hypothesis.hypothesis_id}`,
	);
}

const deepDives = readdirSync(deepDiveDir)
	.filter((name) => name.endsWith(".json"))
	.map((name) => {
		const parsed = CandidateDeepDiveSchema.parse(
			JSON.parse(readFileSync(join(deepDiveDir, name), "utf8")),
		);
		if (parsed.hypothesis_id !== hypothesis.hypothesis_id) return null;
		return {
			candidate_id: parsed.candidate_id,
			company: parsed.company,
			declared_status: parsed.research_status,
			evaluation: evaluateCandidate(
				parsed,
				hypothesis.stage_b.minimum_independent_pressure_signals,
			),
			limitations: parsed.limitations,
		};
	})
	.filter((row) => row !== null);

const eligible = deepDives.filter(
	(row) => row.evaluation.eligible_for_decision_snapshot,
);

process.stdout.write(
	`${JSON.stringify(
		{
			hypothesis_id: hypothesis.hypothesis_id,
			capture_id: capture.capture_id,
			information_cutoff: capture.information_cutoff,
			stage_a_total_matches: capture.result_count,
			stage_a_rows_stored: capture.rows.length,
			deep_dives: deepDives,
			eligible_for_decision_snapshot: eligible.map((row) => row.candidate_id),
			note: "Eligibility is a research gate only. It does not authorize or execute a trade.",
		},
		null,
		2,
	)}\n`,
);
