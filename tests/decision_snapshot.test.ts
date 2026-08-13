import { describe, expect, test } from "bun:test";
import {
	DecisionReviewSchema,
	DecisionSnapshotSchema,
	evaluateEntryEligibility,
} from "../src/decision/decision_snapshot";

const evidence = (available_at = "2026-07-29T09:00:00+09:00") => ({
	assertion_type: "observed_fact" as const,
	ref: "https://example.com/evidence",
	available_at,
});

const gate = (status: "pass" | "fail" | "unknown" = "pass") => ({
	status,
	claim: "testable claim",
	evidence: [evidence()],
	falsifiers: ["a named condition would invalidate this gate"],
	unknowns: [],
});

const snapshot = () => ({
	schema_version: "1.0" as const,
	decision_id: "2026-07-29-test-entry",
	decision_kind: "entry_or_add" as const,
	recorded_at: "2026-07-29T18:00:00+09:00",
	information_cutoff: "2026-07-29T17:59:00+09:00",
	analysis_target: { name: "Analysis target", identifier: "TEST" },
	execution_target: { name: "Execution target", identifier: "TEST-ETF" },
	proposed_action: "buy" as const,
	gates: {
		underlying_reality: gate(),
		price_pressure_mechanism: gate(),
		weak_case_margin: gate(),
	},
	assumptions: ["private scenario assumption"],
	provenance: {
		research_commit: "0123456789abcdef",
		evidence_artifacts: ["docs/research/example.md"],
	},
});

describe("decision snapshot", () => {
	test("is eligible only when all three gates pass", () => {
		expect(evaluateEntryEligibility(snapshot())).toEqual({
			eligible_for_human_review: true,
			blockers: [],
		});

		const blocked = snapshot();
		blocked.gates.price_pressure_mechanism = gate("unknown");
		expect(evaluateEntryEligibility(blocked)).toEqual({
			eligible_for_human_review: false,
			blockers: ["price_pressure_mechanism:unknown"],
		});
	});

	test("rejects evidence that was unavailable at the information cutoff", () => {
		const invalid = snapshot();
		invalid.gates.weak_case_margin.evidence = [
			evidence("2026-07-30T09:00:00+09:00"),
		];

		expect(() => DecisionSnapshotSchema.parse(invalid)).toThrow();
	});

	test("rejects a snapshot recorded before its information cutoff", () => {
		const invalid = snapshot();
		invalid.recorded_at = "2026-07-29T17:00:00+09:00";
		expect(() => DecisionSnapshotSchema.parse(invalid)).toThrow();
	});

	test("keeps outcome review separate from the immutable snapshot", () => {
		const parsed = DecisionSnapshotSchema.parse(snapshot());
		expect(parsed).not.toHaveProperty("learning");

		const review = DecisionReviewSchema.parse({
			schema_version: "1.0",
			review_id: "review-2026-08-13-test-entry",
			decision_id: parsed.decision_id,
			original_snapshot_commit: "abcdef0123456789",
			reviewed_at: "2026-08-13T12:00:00+09:00",
			outcome_evidence: [evidence("2026-08-13T11:00:00+09:00")],
			gate_reassessment: {
				underlying_reality: { verdict: "supported", note: "still intact" },
				price_pressure_mechanism: {
					verdict: "unclear",
					note: "seller mechanism was not directly observable",
				},
				weak_case_margin: { verdict: "supported", note: "margin remained" },
			},
			errors_or_missed_conditions: ["one mechanism remained unverified"],
			learning: "Keep hypotheses distinct from directly observed facts.",
		});

		expect(review.decision_id).toBe(parsed.decision_id);
	});
});
