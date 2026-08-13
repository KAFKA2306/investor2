import { z } from "zod";

const TimestampSchema = z.string().min(1).refine(
	(value) => Number.isFinite(Date.parse(value)),
	"must be a parseable ISO-8601 timestamp",
);

export const DecisionEvidenceRefSchema = z
	.object({
		assertion_type: z.enum([
			"observed_fact",
			"calculated_value",
			"model_estimate",
			"forecast",
			"assumption",
			"hypothesis",
		]),
		ref: z.string().min(1),
		available_at: TimestampSchema,
	})
	.strict();

export const DecisionGateSchema = z
	.object({
		status: z.enum(["pass", "fail", "unknown"]),
		claim: z.string().min(1),
		evidence: z.array(DecisionEvidenceRefSchema).min(1),
		falsifiers: z.array(z.string().min(1)).min(1),
		unknowns: z.array(z.string().min(1)).default([]),
	})
	.strict();

const DecisionTargetSchema = z
	.object({
		name: z.string().min(1),
		identifier: z.string().min(1).optional(),
	})
	.strict();

export const DecisionSnapshotSchema = z
	.object({
		schema_version: z.literal("1.0"),
		decision_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/),
		decision_kind: z.literal("entry_or_add"),
		recorded_at: TimestampSchema,
		information_cutoff: TimestampSchema,
		analysis_target: DecisionTargetSchema,
		execution_target: DecisionTargetSchema.optional(),
		proposed_action: z.enum(["buy", "add", "abstain"]),
		gates: z
			.object({
				underlying_reality: DecisionGateSchema,
				price_pressure_mechanism: DecisionGateSchema,
				weak_case_margin: DecisionGateSchema,
			})
			.strict(),
		assumptions: z.array(z.string().min(1)).default([]),
		provenance: z
			.object({
				research_commit: z.string().min(7),
				evidence_artifacts: z.array(z.string().min(1)).min(1),
			})
			.strict(),
	})
	.strict()
	.superRefine((snapshot, ctx) => {
		const recordedAt = Date.parse(snapshot.recorded_at);
		const cutoff = Date.parse(snapshot.information_cutoff);
		if (recordedAt < cutoff) {
			ctx.addIssue({
				code: "custom",
				path: ["recorded_at"],
				message: "recorded_at must be at or after information_cutoff",
			});
		}

		const gateEntries = Object.entries(snapshot.gates) as Array<
			[keyof typeof snapshot.gates, z.infer<typeof DecisionGateSchema>]
		>;
		for (const [gateName, gate] of gateEntries) {
			for (const [index, evidence] of gate.evidence.entries()) {
				if (Date.parse(evidence.available_at) > cutoff) {
					ctx.addIssue({
						code: "custom",
						path: ["gates", gateName, "evidence", index, "available_at"],
						message:
							"evidence available after information_cutoff cannot support the snapshot",
					});
				}
			}
		}
	});

export type DecisionSnapshot = z.infer<typeof DecisionSnapshotSchema>;

const ReviewAssessmentSchema = z
	.object({
		verdict: z.enum(["supported", "contradicted", "unclear"]),
		note: z.string().min(1),
	})
	.strict();

export const DecisionReviewSchema = z
	.object({
		schema_version: z.literal("1.0"),
		review_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/),
		decision_id: z.string().min(1),
		original_snapshot_commit: z.string().min(7),
		reviewed_at: TimestampSchema,
		outcome_evidence: z.array(DecisionEvidenceRefSchema).min(1),
		gate_reassessment: z
			.object({
				underlying_reality: ReviewAssessmentSchema,
				price_pressure_mechanism: ReviewAssessmentSchema,
				weak_case_margin: ReviewAssessmentSchema,
			})
			.strict(),
		errors_or_missed_conditions: z.array(z.string().min(1)).default([]),
		learning: z.string().min(1),
	})
	.strict();

export type DecisionReview = z.infer<typeof DecisionReviewSchema>;

export interface EntryEligibility {
	eligible_for_human_review: boolean;
	blockers: string[];
}

export const evaluateEntryEligibility = (
	input: unknown,
): EntryEligibility => {
	const snapshot = DecisionSnapshotSchema.parse(input);
	const blockers: string[] = [];

	for (const [gateName, gate] of Object.entries(snapshot.gates)) {
		if (gate.status !== "pass") {
			blockers.push(`${gateName}:${gate.status}`);
		}
	}

	return {
		eligible_for_human_review: blockers.length === 0,
		blockers,
	};
};
