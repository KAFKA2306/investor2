import { describe, expect, test } from "bun:test";
import {
	DecisionLedgerEntrySchema,
	HumanDecisionRecordSchema,
	appendHumanDecisionRecord,
	projectDecision,
	projectDecisionScorecard,
} from "../src/decision/decision_ledger";

const SNAPSHOT_COMMIT = "1111111111111111111111111111111111111111";

const evidence = (available_at: string) => ({
	assertion_type: "observed_fact" as const,
	ref: "https://example.com/evidence",
	available_at,
});

const gate = () => ({
	status: "pass" as const,
	claim: "testable claim",
	evidence: [evidence("2026-07-29T09:00:00+09:00")],
	falsifiers: ["named falsifier"],
	unknowns: [],
});

const snapshot = (decision_id = "decision-1") => ({
	schema_version: "1.0" as const,
	decision_id,
	decision_kind: "entry_or_add" as const,
	recorded_at: "2026-07-29T18:00:00+09:00",
	information_cutoff: "2026-07-29T17:59:00+09:00",
	analysis_target: { name: "Target", identifier: "TEST" },
	execution_target: { name: "Execution", identifier: `${decision_id}-ETF` },
	proposed_action: "buy" as const,
	gates: {
		underlying_reality: gate(),
		price_pressure_mechanism: gate(),
		weak_case_margin: gate(),
	},
	assumptions: [],
	provenance: {
		research_commit: "0123456789abcdef",
		evidence_artifacts: ["docs/research/example.md"],
	},
});

const plan = (decision_id = "decision-1", policy_id = "policy-v1") => ({
	schema_version: "1.0" as const,
	plan_id: `plan-${decision_id}`,
	decision_id,
	snapshot_ref: { decision_id, commit: SNAPSHOT_COMMIT },
	fixed_at: "2026-07-29T18:05:00+09:00",
	review_condition: { type: "elapsed_days" as const, days: 30 },
	benchmark: "benchmark total return over the same horizon",
	transaction_cost_assumption: "10 bps round trip",
	primary_outcome_metric: "benchmark-relative total return",
	downside_metric: "maximum drawdown",
	missing_policy: "unresolved" as const,
	aggregate: {
		policy_id,
		weight: 1,
		minimum_resolved_decisions: 2,
		positive_value_threshold: 0.01,
		negative_value_threshold: -0.01,
		overlap_handling: "reject_same_target" as const,
	},
});

const decision = (
	decision_id = "decision-1",
	record_kind: "actual" | "synthetic" = "actual",
	action: "buy" | "add" | "abstain" = "buy",
) => ({
	schema_version: "1.0" as const,
	record_kind,
	decision_id,
	snapshot_ref: { decision_id, commit: SNAPSHOT_COMMIT },
	decided_at: "2026-07-29T18:10:00+09:00",
	action,
	proposal_disposition: "accepted" as const,
	execution_target_identifier: `${decision_id}-ETF`,
	human_reason: "Decision recorded before outcome observation.",
	outcome_evaluation_plan_ref: `plan-${decision_id}`,
});

const review = (decision_id = "decision-1", delta = 0.02) => ({
	schema_version: "1.0" as const,
	review_id: `review-${decision_id}`,
	decision_id,
	original_snapshot_commit: SNAPSHOT_COMMIT,
	reviewed_at: "2026-08-30T12:00:00+09:00",
	outcome_evidence: [evidence("2026-08-30T11:00:00+09:00")],
	gate_reassessment: {
		underlying_reality: { verdict: "supported" as const, note: "supported" },
		price_pressure_mechanism: { verdict: "supported" as const, note: "supported" },
		weak_case_margin: { verdict: "supported" as const, note: "supported" },
	},
	errors_or_missed_conditions: [],
	learning: "Keep the decision-time record immutable.",
	outcome_evaluation_plan_ref: `plan-${decision_id}`,
	outcome: {
		observed_at: "2026-08-30T11:00:00+09:00",
		primary_outcome: delta + 0.031,
		benchmark_outcome: 0.03,
		transaction_cost: 0.001,
		delta,
		downside: -0.04,
	},
});

const entry = (
	decision_id = "decision-1",
	options: {
		record_kind?: "actual" | "synthetic";
		action?: "buy" | "add" | "abstain";
		delta?: number;
		resolved?: boolean;
		policy_id?: string;
	} = {},
) => ({
	snapshot_commit: SNAPSHOT_COMMIT,
	snapshot: snapshot(decision_id),
	decision: decision(
		decision_id,
		options.record_kind ?? "actual",
		options.action ?? "buy",
	),
	plan: plan(decision_id, options.policy_id ?? "policy-v1"),
	...(options.resolved === false
		? {}
		: { review: review(decision_id, options.delta ?? 0.02) }),
});

describe("canonical decision ledger", () => {
	test("binds snapshot, human decision, plan, and review to exact identities", () => {
		const parsed = DecisionLedgerEntrySchema.parse(entry());
		expect(parsed.decision.snapshot_ref.commit).toBe(SNAPSHOT_COMMIT);
		expect(parsed.review?.outcome_evaluation_plan_ref).toBe(parsed.plan.plan_id);
		expect(projectDecision(parsed)).toMatchObject({
			decision_id: "decision-1",
			status: "resolved",
			delta: 0.02,
		});
	});

	test("supports buy, add, and abstain through one human-decision contract", () => {
		for (const action of ["buy", "add", "abstain"] as const) {
			expect(HumanDecisionRecordSchema.parse(decision(`decision-${action}`, "actual", action)).action).toBe(action);
		}
	});

	test("fails closed on stale snapshot and outcome evidence that predates the decision", () => {
		const stale = entry();
		stale.decision.snapshot_ref.commit = "2222222222222222222222222222222222222222";
		expect(() => DecisionLedgerEntrySchema.parse(stale)).toThrow();

		const futureRewrite = entry();
		futureRewrite.review!.outcome_evidence[0].available_at = "2026-07-29T18:09:00+09:00";
		expect(() => DecisionLedgerEntrySchema.parse(futureRewrite)).toThrow();
	});

	test("keeps the human decision append-only and idempotent", () => {
		const original = HumanDecisionRecordSchema.parse(decision());
		const once = appendHumanDecisionRecord([], original);
		const twice = appendHumanDecisionRecord(once, original);
		expect(twice).toEqual(once);

		const rewritten = { ...original, action: "abstain" as const };
		expect(() => appendHumanDecisionRecord(once, rewritten)).toThrow("immutable");
	});

	test("counts unresolved actual decisions and excludes synthetic fixtures from outcome value", () => {
		const scorecard = projectDecisionScorecard([
			entry("actual-1", { delta: 0.03 }),
			entry("actual-2", { action: "add", resolved: false }),
			entry("fixture-1", { record_kind: "synthetic", delta: 10 }),
		]);

		expect(scorecard).toEqual({
			metric_layer: "investment_outcome",
			actual_decision_count: 2,
			synthetic_excluded_count: 1,
			resolved_count: 1,
			unresolved_count: 1,
			action_distribution: { buy: 1, add: 1, abstain: 0 },
			proposal_distribution: { accepted: 2, overridden: 0 },
			weighted_delta: 0.03,
			weighted_downside: -0.04,
			verdict: "INSUFFICIENT_EVIDENCE",
		});
	});

	test("produces a deterministic aggregate verdict only after minimum evidence", () => {
		const inputs = [entry("actual-1", { delta: 0.03 }), entry("actual-2", { delta: 0.02 })];
		const first = projectDecisionScorecard(inputs);
		const second = projectDecisionScorecard(inputs);
		expect(first).toEqual(second);
		expect(first.weighted_delta).toBeCloseTo(0.025);
		expect(first.verdict).toBe("POSITIVE_VALUE");
	});

	test("represents zero real decisions as insufficient evidence instead of implementation failure", () => {
		const scorecard = projectDecisionScorecard([
			entry("fixture-only", { record_kind: "synthetic", delta: 0.5 }),
		]);
		expect(scorecard.actual_decision_count).toBe(0);
		expect(scorecard.synthetic_excluded_count).toBe(1);
		expect(scorecard.weighted_delta).toBeNull();
		expect(scorecard.verdict).toBe("INSUFFICIENT_EVIDENCE");
	});

	test("rejects incompatible aggregate policies instead of silently mixing metrics", () => {
		expect(() =>
			projectDecisionScorecard([
				entry("actual-1", { delta: 0.03, policy_id: "policy-v1" }),
				entry("actual-2", { delta: 0.02, policy_id: "policy-v2" }),
			]),
		).toThrow("incompatible aggregate policies");
	});
});
