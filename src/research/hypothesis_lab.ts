import { z } from "zod";

const IsoTimestampSchema = z.string().min(1).refine(
	(value) => Number.isFinite(Date.parse(value)),
	"must be a parseable ISO-8601 timestamp",
);

export const MetricConditionSchema = z
	.object({
		metric: z.string().min(1),
		operator: z.enum(["gte", "lte", "gt", "lt", "eq"]),
		value: z.number().finite(),
	})
	.strict();

export const HypothesisSpecSchema = z
	.object({
		schema_version: z.literal("1.0"),
		hypothesis_id: z.string().min(1),
		thesis: z.string().min(1),
		economic_mechanism: z.string().min(1),
		stage_a: z
			.object({
				tool: z.string().min(1),
				conditions: z.array(MetricConditionSchema).min(1),
				sort_by: z.string().min(1),
			})
			.strict(),
		stage_b: z
			.object({
				required_features: z.array(z.string().min(1)).min(1),
				minimum_independent_pressure_signals: z.number().int().min(1),
			})
			.strict(),
		falsifiers: z.array(z.string().min(1)).min(1),
		decision_gate_mapping: z
			.object({
				underlying_reality: z.array(z.string().min(1)).min(1),
				price_pressure_mechanism: z.array(z.string().min(1)).min(1),
				weak_case_margin: z.array(z.string().min(1)).min(1),
			})
			.strict(),
	})
	.strict();

export type HypothesisSpec = z.infer<typeof HypothesisSpecSchema>;

export const McpCaptureSnapshotSchema = z
	.object({
		schema_version: z.literal("1.0"),
		capture_id: z.string().min(1),
		hypothesis_id: z.string().min(1),
		tool: z.string().min(1),
		params: z.record(z.string(), z.unknown()),
		captured_at: IsoTimestampSchema,
		information_cutoff: IsoTimestampSchema,
		result_count: z.number().int().nonnegative(),
		rows: z.array(z.record(z.string(), z.unknown())),
	})
	.strict()
	.superRefine((capture, ctx) => {
		if (Date.parse(capture.captured_at) < Date.parse(capture.information_cutoff)) {
			ctx.addIssue({
				code: "custom",
				path: ["captured_at"],
				message: "captured_at must be at or after information_cutoff",
			});
		}
		if (capture.rows.length > capture.result_count) {
			ctx.addIssue({
				code: "custom",
				path: ["rows"],
				message: "stored rows cannot exceed result_count",
			});
		}
	});

export type McpCaptureSnapshot = z.infer<typeof McpCaptureSnapshotSchema>;

const EvidenceRefSchema = z
	.object({
		source_type: z.enum(["edinet_filing", "mcp_capture", "corporate_event"]),
		ref: z.string().min(1),
		available_at: IsoTimestampSchema,
	})
	.strict();

const GateStatusSchema = z.enum(["pass", "fail", "unknown"]);

const GateAssessmentSchema = z
	.object({
		status: GateStatusSchema,
		reasons: z.array(z.string().min(1)).min(1),
		evidence: z.array(EvidenceRefSchema),
	})
	.strict();

export const CandidateDeepDiveSchema = z
	.object({
		schema_version: z.literal("1.0"),
		hypothesis_id: z.string().min(1),
		candidate_id: z.string().min(1),
		company: z
			.object({
				edinet_code: z.string().min(1),
				sec_code: z.string().min(1),
				name: z.string().min(1),
			})
			.strict(),
		information_cutoff: IsoTimestampSchema,
		metrics: z
			.object({
				revenue_yoy: z.number().finite().nullable(),
				operating_income_yoy: z.number().finite().nullable(),
				net_income_yoy: z.number().finite().nullable(),
				operating_cf_yoy: z.number().finite().nullable(),
				per: z.number().finite().nullable(),
				pbr: z.number().finite().nullable(),
				fcf_yield: z.number().finite().nullable(),
				net_cash_ratio: z.number().finite().nullable(),
				tsr: z.number().finite().nullable(),
				comparison_index_tsr: z.number().finite().nullable(),
				relative_tsr_ratio: z.number().finite().nullable(),
			})
			.strict(),
		pressure_signals: z.array(
			z
				.object({
					type: z.enum([
						"large_holder_reduction",
						"relative_tsr_underperformance",
						"other_observed_supply",
					]),
					description: z.string().min(1),
					evidence: EvidenceRefSchema,
				})
				.strict(),
		),
		negative_fundamental_events: z.array(z.string().min(1)),
		gate_assessment: z
			.object({
				underlying_reality: GateAssessmentSchema,
				price_pressure_mechanism: GateAssessmentSchema,
				weak_case_margin: GateAssessmentSchema,
			})
			.strict(),
		research_status: z.enum([
			"candidate",
			"eligible_for_decision_snapshot",
			"reject",
		]),
		limitations: z.array(z.string().min(1)).min(1),
	})
	.strict();

export type CandidateDeepDive = z.infer<typeof CandidateDeepDiveSchema>;

const allPositive = (values: Array<number | null>): "pass" | "fail" | "unknown" => {
	if (values.some((value) => value === null)) return "unknown";
	return values.every((value) => (value ?? 0) > 0) ? "pass" : "fail";
};

export const evaluateCandidate = (
	input: unknown,
	minimumIndependentPressureSignals = 2,
) => {
	const candidate = CandidateDeepDiveSchema.parse(input);
	const fundamentals = allPositive([
		candidate.metrics.revenue_yoy,
		candidate.metrics.operating_income_yoy,
		candidate.metrics.net_income_yoy,
		candidate.metrics.operating_cf_yoy,
	]);

	const distinctPressureTypes = new Set(
		candidate.pressure_signals.map((signal) => signal.type),
	).size;
	const pressure =
		distinctPressureTypes >= minimumIndependentPressureSignals &&
		candidate.negative_fundamental_events.length === 0
			? "pass"
			: candidate.pressure_signals.length === 0
				? "unknown"
				: "fail";

	const marginValues = [
		candidate.metrics.per,
		candidate.metrics.fcf_yield,
		candidate.metrics.net_cash_ratio,
	];
	const margin = marginValues.some((value) => value === null)
		? "unknown"
		: (candidate.metrics.per ?? Number.POSITIVE_INFINITY) <= 10 &&
			(candidate.metrics.fcf_yield ?? Number.NEGATIVE_INFINITY) >= 0.03 &&
			(candidate.metrics.net_cash_ratio ?? Number.NEGATIVE_INFINITY) >= 0
			? "pass"
			: "fail";

	return {
		underlying_reality: fundamentals,
		price_pressure_mechanism: pressure,
		weak_case_margin: margin,
		eligible_for_decision_snapshot:
			fundamentals === "pass" && pressure === "pass" && margin === "pass",
	};
};
