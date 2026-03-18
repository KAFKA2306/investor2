import { z } from "zod";

// ============================================================
// Configuration
// ============================================================

export const ConfigSchema = z.object({
	project: z.object({
		name: z.string(),
	}),
	paths: z
		.object({
			data: z.string(),
			logs: z.string(),
			verification: z.string(),
			cache: z.string(),
			edinet: z.string(),
			preprocessed: z.string(),
			cacheFundamentalEdinet: z.string(),
			cacheMarketsPolymarket: z.string(),
			cacheMarketsJquants: z.string(),
			cacheMarketsYahoo: z.string(),
			cacheFundamentalJquants: z.string(),
			cacheMacroEstat: z.string(),
			cacheMacroFred: z.string().optional(),
			macroFred: z.string().optional(),
			cacheMarketSqlite: z.string().optional(),
		})
		.passthrough(),
	polymarket: z.object({
		clob_url: z.string(),
	}),
	pipelineBlueprint: z
		.object({
			verificationAcceptance: z
				.object({
					minSharpe: z.number(),
					maxPValue: z.number(),
					maxDrawdown: z.number(),
				})
				.optional(),
			alphaLoop: z
				.object({
					maxCycles: z.number(),
					sleepSec: z.number(),
					maxFailures: z.number(),
				})
				.optional(),
		})
		.optional(),
});

export type Config = z.infer<typeof ConfigSchema>;

// ============================================================
// EDINET Company & Financial Data
// ============================================================

export const CompanyInfoSchema = z.object({
	edinetCode: z.string(),
	name: z.string(),
	sector: z.string().optional(),
	market: z.string().optional(),
	listingDate: z.string().optional(),
});

export type CompanyInfo = z.infer<typeof CompanyInfoSchema>;

export const CompanyGovernanceSchema = z
	.object({
		boardComposition: z.string().optional(),
		executiveCompensation: z.string().optional(),
		riskManagement: z.string().optional(),
	})
	.passthrough();

export type CompanyGovernance = z.infer<typeof CompanyGovernanceSchema>;

export const FinancialDataSchema = z.object({
	eps: z.number().nullable().optional(),
	bps: z.number().nullable().optional(),
	netSales: z.number().nullable().optional(),
	operatingProfit: z.number().nullable().optional(),
	profit: z.number().nullable().optional(),
	equity: z.number().nullable().optional(),
	totalAssets: z.number().nullable().optional(),
	periodEnd: z.string().optional(),
});

export type FinancialData = z.infer<typeof FinancialDataSchema>;

export const CompanyDetailSchema = CompanyInfoSchema.extend({
	governance: CompanyGovernanceSchema.optional(),
	financial: z
		.union([z.array(FinancialDataSchema), FinancialDataSchema])
		.optional(),
	documentCount: z.number().optional(),
	overview: z
		.object({
			businessDescription: z.string().optional(),
			risks: z.string().optional(),
			products: z.string().optional(),
		})
		.optional(),
});

export type CompanyDetail = z.infer<typeof CompanyDetailSchema>;

// ============================================================
// AAARTS Alpha Discovery Pipeline
// ============================================================

export const AlphaCandidateSchema = z.object({
	factor_id: z.string(),
	formula: z.string(),
	economic_mechanism: z.string(),
});

export type AlphaCandidate = z.infer<typeof AlphaCandidateSchema>;

export const StandardOutcomeSchema = z.object({
	sharpe: z.number(),
	ic: z.number(),
	max_drawdown: z.number(),
	p_value: z.number(),
	factor_id: z.string(),
	backtest_days: z.number(),
});

export type StandardOutcome = z.infer<typeof StandardOutcomeSchema>;

export const VerificationResultSchema = z.object({
	verdict: z.enum(["GO", "HOLD", "PIVOT"]),
	confidence: z.number(),
	reasons: z.array(z.string()),
	outcome: StandardOutcomeSchema,
});

export type VerificationResult = z.infer<typeof VerificationResultSchema>;

export const CycleSummarySchema = z.object({
	cycle: z.number(),
	candidates_generated: z.number(),
	go_count: z.number(),
	hold_count: z.number(),
	pivot_count: z.number(),
	elapsed_ms: z.number(),
});

export type CycleSummary = z.infer<typeof CycleSummarySchema>;

export const PipelineResultsReportSchema = z.object({
	execution_id: z.string(),
	execution_timestamp: z.string(),
	total_cycles: z.number(),
	elapsed_seconds: z.number(),
	cycle_summaries: z.array(CycleSummarySchema),
	verdicts: z.array(VerificationResultSchema),
	config_thresholds: z.object({
		minSharpe: z.number(),
		maxPValue: z.number(),
		maxDrawdown: z.number(),
	}),
});

export type PipelineResultsReport = z.infer<typeof PipelineResultsReportSchema>;
