import { z } from "zod";
import {
	DecisionReviewSchema,
	DecisionSnapshotSchema,
	type DecisionReview,
	type DecisionSnapshot,
} from "./decision_snapshot";

const TimestampSchema = z.string().min(1).refine(
	(value) => Number.isFinite(Date.parse(value)),
	"must be a parseable ISO-8601 timestamp",
);

const CommitShaSchema = z
	.string()
	.regex(/^[0-9a-f]{40}$/i, "must be an exact 40-character commit SHA");

export const DecisionSnapshotRefSchema = z
	.object({
		decision_id: z.string().min(1),
		commit: CommitShaSchema,
	})
	.strict();

export const HumanDecisionRecordSchema = z
	.object({
		schema_version: z.literal("1.0"),
		record_kind: z.enum(["actual", "synthetic"]),
		decision_id: z.string().min(1),
		snapshot_ref: DecisionSnapshotRefSchema,
		decided_at: TimestampSchema,
		action: z.enum(["buy", "add", "abstain"]),
		proposal_disposition: z.enum(["accepted", "overridden"]),
		execution_target_identifier: z.string().min(1).optional(),
		human_reason: z.string().min(1).optional(),
		outcome_evaluation_plan_ref: z.string().min(1),
	})
	.strict()
	.superRefine((record, ctx) => {
		if (record.snapshot_ref.decision_id !== record.decision_id) {
			ctx.addIssue({
				code: "custom",
				path: ["snapshot_ref", "decision_id"],
				message: "snapshot reference must point to the same decision_id",
			});
		}
	});

export type HumanDecisionRecord = z.infer<typeof HumanDecisionRecordSchema>;

const ReviewConditionSchema = z.union([
	z.object({ type: z.literal("elapsed_days"), days: z.number().int().positive() }).strict(),
	z.object({ type: z.literal("named_condition"), condition: z.string().min(1) }).strict(),
]);

const AggregatePolicySchema = z
	.object({
		policy_id: z.string().min(1),
		weight: z.number().positive(),
		minimum_resolved_decisions: z.number().int().positive(),
		positive_value_threshold: z.number().finite(),
		negative_value_threshold: z.number().finite(),
		overlap_handling: z.enum(["reject_same_target", "allow_distinct_decisions"]),
	})
	.strict()
	.superRefine((policy, ctx) => {
		if (policy.negative_value_threshold > policy.positive_value_threshold) {
			ctx.addIssue({
				code: "custom",
				path: ["negative_value_threshold"],
				message: "negative threshold must not exceed positive threshold",
			});
		}
	});

export const OutcomeEvaluationPlanSchema = z
	.object({
		schema_version: z.literal("1.0"),
		plan_id: z.string().min(1),
		decision_id: z.string().min(1),
		snapshot_ref: DecisionSnapshotRefSchema,
		fixed_at: TimestampSchema,
		review_condition: ReviewConditionSchema,
		benchmark: z.string().min(1),
		transaction_cost_assumption: z.string().min(1),
		primary_outcome_metric: z.string().min(1),
		downside_metric: z.string().min(1),
		missing_policy: z.enum(["unresolved", "fail_closed"]),
		aggregate: AggregatePolicySchema,
	})
	.strict()
	.superRefine((plan, ctx) => {
		if (plan.snapshot_ref.decision_id !== plan.decision_id) {
			ctx.addIssue({
				code: "custom",
				path: ["snapshot_ref", "decision_id"],
				message: "snapshot reference must point to the same decision_id",
			});
		}
	});

export type OutcomeEvaluationPlan = z.infer<typeof OutcomeEvaluationPlanSchema>;

export const DecisionOutcomeSchema = z
	.object({
		observed_at: TimestampSchema,
		primary_outcome: z.number().finite(),
		benchmark_outcome: z.number().finite(),
		transaction_cost: z.number().finite().nonnegative(),
		delta: z.number().finite(),
		downside: z.number().finite(),
	})
	.strict()
	.superRefine((outcome, ctx) => {
		const expected =
			outcome.primary_outcome - outcome.benchmark_outcome - outcome.transaction_cost;
		if (Math.abs(expected - outcome.delta) > 1e-9) {
			ctx.addIssue({
				code: "custom",
				path: ["delta"],
				message: "delta must equal primary_outcome - benchmark_outcome - transaction_cost",
			});
		}
	});

export const DecisionLedgerReviewSchema = DecisionReviewSchema.extend({
	outcome_evaluation_plan_ref: z.string().min(1),
	outcome: DecisionOutcomeSchema,
}).strict();

export type DecisionLedgerReview = z.infer<typeof DecisionLedgerReviewSchema>;

export const DecisionLedgerEntrySchema = z
	.object({
		snapshot_commit: CommitShaSchema,
		snapshot: DecisionSnapshotSchema,
		decision: HumanDecisionRecordSchema,
		plan: OutcomeEvaluationPlanSchema,
		review: DecisionLedgerReviewSchema.optional(),
	})
	.strict()
	.superRefine((entry, ctx) => {
		const { snapshot, snapshot_commit: snapshotCommit, decision, plan, review } = entry;
		const decisionTime = Date.parse(decision.decided_at);

		if (decision.decision_id !== snapshot.decision_id) {
			ctx.addIssue({ code: "custom", path: ["decision", "decision_id"], message: "decision must reference snapshot decision_id" });
		}
		if (decision.snapshot_ref.commit !== snapshotCommit) {
			ctx.addIssue({ code: "custom", path: ["decision", "snapshot_ref", "commit"], message: "decision must reference the exact snapshot commit" });
		}
		if (plan.decision_id !== snapshot.decision_id || plan.snapshot_ref.commit !== snapshotCommit) {
			ctx.addIssue({ code: "custom", path: ["plan", "snapshot_ref"], message: "plan must reference the exact snapshot identity" });
		}
		if (decision.outcome_evaluation_plan_ref !== plan.plan_id) {
			ctx.addIssue({ code: "custom", path: ["decision", "outcome_evaluation_plan_ref"], message: "decision must reference the attached outcome plan" });
		}
		if (Date.parse(plan.fixed_at) > decisionTime) {
			ctx.addIssue({ code: "custom", path: ["plan", "fixed_at"], message: "outcome plan must be fixed no later than the human decision" });
		}
		if (decisionTime < Date.parse(snapshot.recorded_at)) {
			ctx.addIssue({ code: "custom", path: ["decision", "decided_at"], message: "human decision cannot predate its snapshot" });
		}

		if (!review) return;
		if (review.decision_id !== decision.decision_id) {
			ctx.addIssue({ code: "custom", path: ["review", "decision_id"], message: "review must reference the human decision" });
		}
		if (review.original_snapshot_commit !== snapshotCommit) {
			ctx.addIssue({ code: "custom", path: ["review", "original_snapshot_commit"], message: "review must preserve the exact snapshot commit" });
		}
		if (review.outcome_evaluation_plan_ref !== plan.plan_id) {
			ctx.addIssue({ code: "custom", path: ["review", "outcome_evaluation_plan_ref"], message: "review must use the decision-time outcome plan" });
		}
		if (Date.parse(review.outcome.observed_at) < decisionTime) {
			ctx.addIssue({ code: "custom", path: ["review", "outcome", "observed_at"], message: "outcome cannot predate the human decision" });
		}
		const reviewedAt = Date.parse(review.reviewed_at);
		if (reviewedAt < Date.parse(review.outcome.observed_at)) {
			ctx.addIssue({ code: "custom", path: ["review", "reviewed_at"], message: "review cannot predate the outcome observation" });
		}
		for (const [index, evidence] of review.outcome_evidence.entries()) {
			const availableAt = Date.parse(evidence.available_at);
			if (availableAt < decisionTime) {
				ctx.addIssue({ code: "custom", path: ["review", "outcome_evidence", index, "available_at"], message: "outcome evidence cannot predate the human decision" });
			}
			if (availableAt > reviewedAt) {
				ctx.addIssue({ code: "custom", path: ["review", "outcome_evidence", index, "available_at"], message: "review cannot use evidence that was not yet available" });
			}
		}
	});

export type DecisionLedgerEntry = z.infer<typeof DecisionLedgerEntrySchema>;

export const appendHumanDecisionRecord = (
	records: readonly HumanDecisionRecord[],
	candidate: unknown,
): HumanDecisionRecord[] => {
	const parsed = HumanDecisionRecordSchema.parse(candidate);
	const existing = records.find((record) => record.decision_id === parsed.decision_id);
	if (!existing) return [...records, parsed];
	if (JSON.stringify(existing) !== JSON.stringify(parsed)) {
		throw new Error(`decision record ${parsed.decision_id} is immutable`);
	}
	return [...records];
};

export interface DecisionProjection {
	decision_id: string;
	record_kind: "actual" | "synthetic";
	action: "buy" | "add" | "abstain";
	proposal_disposition: "accepted" | "overridden";
	status: "resolved" | "unresolved";
	primary_outcome: number | null;
	benchmark_outcome: number | null;
	delta: number | null;
	downside: number | null;
}

export const projectDecision = (input: unknown): DecisionProjection => {
	const entry = DecisionLedgerEntrySchema.parse(input);
	return {
		decision_id: entry.decision.decision_id,
		record_kind: entry.decision.record_kind,
		action: entry.decision.action,
		proposal_disposition: entry.decision.proposal_disposition,
		status: entry.review ? "resolved" : "unresolved",
		primary_outcome: entry.review?.outcome.primary_outcome ?? null,
		benchmark_outcome: entry.review?.outcome.benchmark_outcome ?? null,
		delta: entry.review?.outcome.delta ?? null,
		downside: entry.review?.outcome.downside ?? null,
	};
};

export interface DecisionScorecard {
	metric_layer: "investment_outcome";
	actual_decision_count: number;
	synthetic_excluded_count: number;
	resolved_count: number;
	unresolved_count: number;
	action_distribution: Record<"buy" | "add" | "abstain", number>;
	proposal_distribution: Record<"accepted" | "overridden", number>;
	weighted_delta: number | null;
	weighted_downside: number | null;
	verdict: "INSUFFICIENT_EVIDENCE" | "POSITIVE_VALUE" | "NO_DEMONSTRATED_VALUE" | "NEGATIVE_VALUE";
}

const sameAggregatePolicy = (left: OutcomeEvaluationPlan, right: OutcomeEvaluationPlan): boolean => {
	const a = left.aggregate;
	const b = right.aggregate;
	return (
		a.policy_id === b.policy_id &&
		a.minimum_resolved_decisions === b.minimum_resolved_decisions &&
		a.positive_value_threshold === b.positive_value_threshold &&
		a.negative_value_threshold === b.negative_value_threshold &&
		a.overlap_handling === b.overlap_handling
	);
};

export const projectDecisionScorecard = (inputs: readonly unknown[]): DecisionScorecard => {
	const entries = inputs.map((input) => DecisionLedgerEntrySchema.parse(input));
	const actual = entries.filter((entry) => entry.decision.record_kind === "actual");
	const syntheticExcluded = entries.length - actual.length;
	const actionDistribution = { buy: 0, add: 0, abstain: 0 };
	const proposalDistribution = { accepted: 0, overridden: 0 };

	for (const entry of actual) {
		actionDistribution[entry.decision.action] += 1;
		proposalDistribution[entry.decision.proposal_disposition] += 1;
	}

	if (actual.length === 0) {
		return {
			metric_layer: "investment_outcome",
			actual_decision_count: 0,
			synthetic_excluded_count: syntheticExcluded,
			resolved_count: 0,
			unresolved_count: 0,
			action_distribution: actionDistribution,
			proposal_distribution: proposalDistribution,
			weighted_delta: null,
			weighted_downside: null,
			verdict: "INSUFFICIENT_EVIDENCE",
		};
	}

	const policyOwner = actual[0].plan;
	for (const entry of actual.slice(1)) {
		if (!sameAggregatePolicy(policyOwner, entry.plan)) {
			throw new Error("actual decisions use incompatible aggregate policies");
		}
	}

	if (policyOwner.aggregate.overlap_handling === "reject_same_target") {
		const targets = new Set<string>();
		for (const entry of actual) {
			const target = entry.decision.execution_target_identifier;
			if (!target) continue;
			if (targets.has(target)) throw new Error(`overlapping execution target: ${target}`);
			targets.add(target);
		}
	}

	const resolved = actual.filter((entry) => entry.review !== undefined);
	const totalWeight = resolved.reduce((sum, entry) => sum + entry.plan.aggregate.weight, 0);
	const weightedDelta = totalWeight === 0
		? null
		: resolved.reduce((sum, entry) => sum + (entry.review?.outcome.delta ?? 0) * entry.plan.aggregate.weight, 0) / totalWeight;
	const weightedDownside = totalWeight === 0
		? null
		: resolved.reduce((sum, entry) => sum + (entry.review?.outcome.downside ?? 0) * entry.plan.aggregate.weight, 0) / totalWeight;

	let verdict: DecisionScorecard["verdict"] = "INSUFFICIENT_EVIDENCE";
	if (resolved.length >= policyOwner.aggregate.minimum_resolved_decisions && weightedDelta !== null) {
		if (weightedDelta >= policyOwner.aggregate.positive_value_threshold) verdict = "POSITIVE_VALUE";
		else if (weightedDelta <= policyOwner.aggregate.negative_value_threshold) verdict = "NEGATIVE_VALUE";
		else verdict = "NO_DEMONSTRATED_VALUE";
	}

	return {
		metric_layer: "investment_outcome",
		actual_decision_count: actual.length,
		synthetic_excluded_count: syntheticExcluded,
		resolved_count: resolved.length,
		unresolved_count: actual.length - resolved.length,
		action_distribution: actionDistribution,
		proposal_distribution: proposalDistribution,
		weighted_delta: weightedDelta,
		weighted_downside: weightedDownside,
		verdict,
	};
};

export type { DecisionReview, DecisionSnapshot };
