import { z } from "zod";

const IdSchema = z.string().min(1);
const IsoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}(T.*)?$/);
const HashSchema = z.string().regex(/^[a-f0-9]{64}$/);
const CommitShaSchema = z.string().regex(/^[a-f0-9]{7,40}$/);
const FingerprintSchema = z.object({
	logic: HashSchema,
	decision_trace: HashSchema,
	environment: HashSchema,
});

export const GateStatusSchema = z.enum([
	"PASS",
	"FAIL",
	"PARTIAL",
	"NOT_RUN",
	"UNVERIFIED",
]);
export type GateStatus = z.infer<typeof GateStatusSchema>;

export const EvidenceStateSchema = z.enum([
	"CONFIRMED",
	"NOT_CONFIRMED",
	"CONTRADICTED",
]);
export type EvidenceState = z.infer<typeof EvidenceStateSchema>;

export const LifecycleDecisionSchema = z.enum(["GO", "HOLD", "PIVOT"]);
export type LifecycleDecision = z.infer<typeof LifecycleDecisionSchema>;

export const EntityMetadataSchema = z.object({
	stable_id: IdSchema,
	created_at: IsoDateSchema,
	schema_version: z.literal("aaarts-ontology.v1"),
	input_hash: HashSchema,
	code_commit_sha: CommitShaSchema,
});

const entity = <T extends z.ZodRawShape>(shape: T) =>
	EntityMetadataSchema.extend(shape);

export const ExplorationRunSchema = entity({
	objective: z.string().min(1),
	strategy_version_ids: z.array(IdSchema),
	status: z.enum(["RUNNING", "COMPLETED", "FAILED"]),
});
export type ExplorationRun = z.infer<typeof ExplorationRunSchema>;

export const LearningEventSchema = entity({
	exploration_run_id: IdSchema,
	research_run_id: IdSchema,
	trigger: z.string().min(1),
	lesson: z.string().min(1),
	evidence_artifact_ids: z.array(IdSchema),
	feeds_mutation_plan_ids: z.array(IdSchema),
});
export type LearningEvent = z.infer<typeof LearningEventSchema>;

export const FailureConstraintSchema = entity({
	learning_event_id: IdSchema,
	constraint: z.string().min(1),
	scope: z.string().min(1),
});
export type FailureConstraint = z.infer<typeof FailureConstraintSchema>;

export const MutationPlanSchema = entity({
	source_strategy_version_id: IdSchema,
	next_strategy_version_id: IdSchema,
	created_at: IsoDateSchema,
	trigger: z.string().min(1),
	changes: z.array(z.string().min(1)).min(1),
	expected_test: z.string().min(1),
	status: z.enum(["PLANNED", "IN_PROGRESS", "APPLIED", "ABANDONED"]),
});
export type MutationPlan = z.infer<typeof MutationPlanSchema>;

export const EvolutionEdgeSchema = entity({
	from_strategy_version_id: IdSchema,
	to_strategy_version_id: IdSchema,
	relation: z.enum(["MUTATION", "REPLICATION", "ROLLBACK"]),
	reason: z.string().min(1),
	learning_event_id: IdSchema,
});
export type EvolutionEdge = z.infer<typeof EvolutionEdgeSchema>;

export const ContextSnapshotSchema = entity({
	environment: z.string().min(1),
	dependency_lock_hash: HashSchema,
	platform: z.string().min(1),
	notes: z.string().min(1),
});
export type ContextSnapshot = z.infer<typeof ContextSnapshotSchema>;

export const DataSourceSchema = entity({
	name: z.string().min(1),
	url: z.string().url(),
	authority: z.enum(["PRIMARY", "SECONDARY", "EXPERIMENTAL"]),
	kind: z.enum(["MARKET", "REGULATORY", "MACRO", "PAPER"]),
});
export type DataSource = z.infer<typeof DataSourceSchema>;

export const DatasetSnapshotSchema = entity({
	data_source_id: IdSchema,
	name: z.string().min(1),
	path: z.string().min(1),
	sha256: HashSchema,
	observed_at: IsoDateSchema,
	period_start: z.string().min(1),
	period_end: z.string().min(1),
});
export type DatasetSnapshot = z.infer<typeof DatasetSnapshotSchema>;

export const PITAssessmentSchema = entity({
	dataset_snapshot_id: IdSchema,
	status: GateStatusSchema,
	assessed_at: IsoDateSchema,
	note: z.string().min(1),
});
export type PITAssessment = z.infer<typeof PITAssessmentSchema>;

export const ProvenanceRecordSchema = entity({
	source_ids: z.array(IdSchema),
	dataset_snapshot_ids: z.array(IdSchema),
	pit_assessment_id: IdSchema,
	transformation: z.string().min(1),
	environment_fingerprint: HashSchema,
});
export type ProvenanceRecord = z.infer<typeof ProvenanceRecordSchema>;

export const DataQualityAssessmentSchema = entity({
	dataset_snapshot_id: IdSchema,
	status: GateStatusSchema,
	checks: z.array(z.string().min(1)),
	note: z.string().min(1),
});
export type DataQualityAssessment = z.infer<typeof DataQualityAssessmentSchema>;

export const HypothesisSchema = entity({
	title: z.string().min(1),
	claim: z.string().min(1),
	economic_mechanism: z.string().min(1),
	primary_source_ids: z.array(IdSchema).min(1),
});
export type Hypothesis = z.infer<typeof HypothesisSchema>;

export const StrategyGenomeSchema = entity({
	strategy_id: IdSchema,
	name: z.string().min(1),
	hypothesis_id: IdSchema,
	parent_genome_id: IdSchema.nullable(),
	economic_mechanism: z.string().min(1),
	signal_definition: z.string().min(1),
	universe: z.string().min(1),
	allocation: z.string().min(1),
	rebalance: z.string().min(1),
});
export type StrategyGenome = z.infer<typeof StrategyGenomeSchema>;

export const StrategyVersionSchema = entity({
	strategy_id: IdSchema,
	genome_id: IdSchema,
	version: z.string().regex(/^v\d+$/),
	parent_strategy_version_id: IdSchema.nullable(),
	status: z.enum(["ACTIVE", "PLANNED", "ARCHIVED"]),
	evidence_state: EvidenceStateSchema,
	lifecycle_decision: LifecycleDecisionSchema,
	last_verified_at: IsoDateSchema.nullable(),
});
export type StrategyVersion = z.infer<typeof StrategyVersionSchema>;

export const ImplementationVariantSchema = entity({
	strategy_version_id: IdSchema,
	name: z.string().min(1),
	implementation_type: z.enum(["DIRECT", "FACTOR", "PROXY"]),
	definition: z.string().min(1),
	limitations: z.array(z.string().min(1)),
});
export type ImplementationVariant = z.infer<typeof ImplementationVariantSchema>;

export const ProtocolSnapshotSchema = entity({
	name: z.string().min(1),
	publication_window: z.object({ start: z.string(), end: z.string() }),
	oos_rule: z.string().min(1),
	cost_rule: z.string().min(1),
	decision_rule: z.string().min(1),
	logic_fingerprint: HashSchema,
});
export type ProtocolSnapshot = z.infer<typeof ProtocolSnapshotSchema>;

export const ResearchRunSchema = entity({
	strategy_version_id: IdSchema,
	implementation_variant_id: IdSchema,
	protocol_snapshot_id: IdSchema,
	dataset_snapshot_id: IdSchema,
	provenance_record_id: IdSchema,
	context_snapshot_id: IdSchema,
	started_at: IsoDateSchema,
	ended_at: IsoDateSchema,
	status: z.enum(["COMPLETED", "FAILED", "UNVERIFIED"]),
	fingerprints: FingerprintSchema,
	reproduction_command: z.string().min(1),
});
export type ResearchRun = z.infer<typeof ResearchRunSchema>;

const MetricsSchema = z.object({
	annualized_mean: z.number(),
	sharpe: z.number(),
	cagr: z.number(),
	max_drawdown: z.number(),
	months: z.number().int().positive(),
});

export const EvidenceArtifactSchema = entity({
	research_run_id: IdSchema,
	type: z.enum(["OOS_RETURN_SERIES", "REPLICATION_REPORT", "EXECUTION_LOG"]),
	path: z.string().min(1),
	evidence_state: EvidenceStateSchema,
	verdict_label: z.string().min(1),
	gross: MetricsSchema,
	net: MetricsSchema.nullable(),
	late_half_annualized_mean: z.number(),
	summary: z.string().min(1),
});
export type EvidenceArtifact = z.infer<typeof EvidenceArtifactSchema>;

export const GateAssessmentSchema = entity({
	research_run_id: IdSchema,
	gate: z.enum(["OOS", "PIT", "COST", "FACTOR_EXPOSURE", "CAPACITY"]),
	status: GateStatusSchema,
	evidence_artifact_ids: z.array(IdSchema),
	note: z.string().min(1),
});
export type GateAssessment = z.infer<typeof GateAssessmentSchema>;

export const FactorExposureAssessmentSchema = entity({
	research_run_id: IdSchema,
	status: GateStatusSchema,
	factors: z.array(z.string()),
	note: z.string().min(1),
});
export type FactorExposureAssessment = z.infer<
	typeof FactorExposureAssessmentSchema
>;

export const TradingRealismAssessmentSchema = entity({
	research_run_id: IdSchema,
	status: GateStatusSchema,
	cost_model: z.string().min(1),
	liquidity: z.string().min(1),
	capacity: z.string().min(1),
	spread_and_slippage: z.string().min(1),
});
export type TradingRealismAssessment = z.infer<
	typeof TradingRealismAssessmentSchema
>;

export const DecisionRecordSchema = entity({
	research_run_id: IdSchema,
	strategy_version_id: IdSchema,
	evidence_state: EvidenceStateSchema,
	lifecycle_decision: LifecycleDecisionSchema,
	gate_assessment_ids: z.array(IdSchema),
	reason: z.string().min(1),
	deterministic_evaluator: z.string().min(1),
	llm_pass_authority: z.literal(false),
});
export type DecisionRecord = z.infer<typeof DecisionRecordSchema>;

export const PortfolioCandidateSchema = entity({
	strategy_version_id: IdSchema,
	eligibility: z.enum(["ELIGIBLE", "BLOCKED"]),
	block_reason: z.string().nullable(),
});
export type PortfolioCandidate = z.infer<typeof PortfolioCandidateSchema>;

export const AllocationPlanSchema = entity({
	portfolio_candidate_id: IdSchema,
	status: z.enum(["DRAFT", "APPROVED", "BLOCKED"]),
	weights: z.record(z.string(), z.number()),
});
export type AllocationPlan = z.infer<typeof AllocationPlanSchema>;

export const RiskBudgetSchema = entity({
	allocation_plan_id: IdSchema,
	max_drawdown: z.number().min(0).max(1),
	max_turnover: z.number().min(0),
	max_sector_weight: z.number().min(0).max(1),
});
export type RiskBudget = z.infer<typeof RiskBudgetSchema>;

export const OrderPlanSchema = entity({
	portfolio_candidate_id: IdSchema,
	status: z.enum(["NOT_RUN", "DRAFT", "BLOCKED"]),
	orders: z.array(
		z.object({
			symbol: z.string(),
			side: z.enum(["BUY", "SELL"]),
			weight: z.number(),
		}),
	),
});
export type OrderPlan = z.infer<typeof OrderPlanSchema>;

export const ExecutionRunSchema = entity({
	allocation_plan_id: IdSchema,
	order_plan_id: IdSchema,
	status: z.enum(["NOT_RUN", "RUNNING", "COMPLETED", "FAILED"]),
	started_at: IsoDateSchema.nullable(),
	ended_at: IsoDateSchema.nullable(),
	broker_mode: z.literal("NO_LIVE_ORDERS"),
});
export type ExecutionRun = z.infer<typeof ExecutionRunSchema>;

export const PerformanceAuditSchema = entity({
	execution_run_id: IdSchema,
	period: z.string().min(1),
	gross_return: z.number(),
	net_return: z.number(),
	fees_bps: z.number().min(0),
	spread_bps: z.number().min(0),
	slippage_bps: z.number().min(0),
	status: z.enum(["PASS", "WARN", "FAIL", "NOT_RUN"]),
});
export type PerformanceAudit = z.infer<typeof PerformanceAuditSchema>;

export const DriftEventSchema = entity({
	execution_run_id: IdSchema,
	detected_at: IsoDateSchema,
	type: z.enum(["SIGNAL", "RISK", "EXECUTION", "DATA"]),
	severity: z.enum(["LOW", "MEDIUM", "HIGH"]),
	description: z.string().min(1),
});
export type DriftEvent = z.infer<typeof DriftEventSchema>;

export const StrategyRegistrySchema = z.object({
	schema_version: z.literal(1),
	generated_at: IsoDateSchema,
	ontology_version: z.literal("aaarts-ontology.v1"),
	exploration_runs: z.array(ExplorationRunSchema),
	learning_events: z.array(LearningEventSchema),
	failure_constraints: z.array(FailureConstraintSchema),
	mutation_plans: z.array(MutationPlanSchema),
	evolution_edges: z.array(EvolutionEdgeSchema),
	context_snapshots: z.array(ContextSnapshotSchema),
	data_sources: z.array(DataSourceSchema),
	dataset_snapshots: z.array(DatasetSnapshotSchema),
	pit_assessments: z.array(PITAssessmentSchema),
	provenance_records: z.array(ProvenanceRecordSchema),
	data_quality_assessments: z.array(DataQualityAssessmentSchema),
	hypotheses: z.array(HypothesisSchema),
	strategy_genomes: z.array(StrategyGenomeSchema),
	strategy_versions: z.array(StrategyVersionSchema),
	implementation_variants: z.array(ImplementationVariantSchema),
	protocol_snapshots: z.array(ProtocolSnapshotSchema),
	research_runs: z.array(ResearchRunSchema),
	evidence_artifacts: z.array(EvidenceArtifactSchema),
	gate_assessments: z.array(GateAssessmentSchema),
	factor_exposure_assessments: z.array(FactorExposureAssessmentSchema),
	trading_realism_assessments: z.array(TradingRealismAssessmentSchema),
	decision_records: z.array(DecisionRecordSchema),
	portfolio_candidates: z.array(PortfolioCandidateSchema),
	allocation_plans: z.array(AllocationPlanSchema),
	risk_budgets: z.array(RiskBudgetSchema),
	order_plans: z.array(OrderPlanSchema),
	execution_runs: z.array(ExecutionRunSchema),
	performance_audits: z.array(PerformanceAuditSchema),
	drift_events: z.array(DriftEventSchema),
});
export type StrategyRegistry = z.infer<typeof StrategyRegistrySchema>;
