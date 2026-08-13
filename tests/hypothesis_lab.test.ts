import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import {
	CandidateDeepDiveSchema,
	evaluateCandidate,
	HypothesisSpecSchema,
	McpCaptureSnapshotSchema,
} from "../src/research/hypothesis_lab";

const hypothesisPath =
	"data/hypothesis_lab/hypotheses/growth_value_dislocation_v1.json";
const capturePath =
	"data/hypothesis_lab/captures/2026-08-13-growth-value-dislocation-stage-a.json";
const rionPath = "data/hypothesis_lab/deep_dives/2026-08-13-rion-6823.json";

describe("hypothesis lab", () => {
	test("validates the pre-registered hypothesis and frozen MCP capture", () => {
		const hypothesis = HypothesisSpecSchema.parse(
			JSON.parse(readFileSync(hypothesisPath, "utf8")),
		);
		const capture = McpCaptureSnapshotSchema.parse(
			JSON.parse(readFileSync(capturePath, "utf8")),
		);

		expect(capture.hypothesis_id).toBe(hypothesis.hypothesis_id);
		expect(capture.result_count).toBe(84);
		expect(capture.rows.length).toBe(10);
	});

	test("marks the RION deep dive eligible only after all three gates pass", () => {
		const candidate = CandidateDeepDiveSchema.parse(
			JSON.parse(readFileSync(rionPath, "utf8")),
		);
		const result = evaluateCandidate(candidate, 2);

		expect(result).toEqual({
			underlying_reality: "pass",
			price_pressure_mechanism: "pass",
			weak_case_margin: "pass",
			eligible_for_decision_snapshot: true,
		});
	});

	test("fails closed when seller-flow evidence is removed", () => {
		const candidate = CandidateDeepDiveSchema.parse(
			JSON.parse(readFileSync(rionPath, "utf8")),
		);
		candidate.pressure_signals = [];

		const result = evaluateCandidate(candidate, 2);
		expect(result.price_pressure_mechanism).toBe("unknown");
		expect(result.eligible_for_decision_snapshot).toBe(false);
	});

	test("rejects the underlying-reality gate when a required growth leg turns negative", () => {
		const candidate = CandidateDeepDiveSchema.parse(
			JSON.parse(readFileSync(rionPath, "utf8")),
		);
		candidate.metrics.operating_income_yoy = -0.01;

		const result = evaluateCandidate(candidate, 2);
		expect(result.underlying_reality).toBe("fail");
		expect(result.eligible_for_decision_snapshot).toBe(false);
	});
});
