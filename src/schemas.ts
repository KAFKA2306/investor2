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
	sector_spillover: z
		.object({
			us_sectors: z.array(z.string()).optional(),
			jp_sectors: z.array(z.string()).optional(),
			pca: z.object({
				n_components: z.number().optional(),
				regularization_alpha: z.number().optional(),
				max_iterations: z.number().optional(),
			}).optional(),
			signal: z.object({
				long_threshold: z.number().optional(),
				short_threshold: z.number().optional(),
				neutral_threshold: z.number().optional(),
			}).optional(),
			backtest: z.object({
				initial_capital: z.number().optional(),
				long_size: z.number().optional(),
				short_size: z.number().optional(),
				rebalance_frequency: z.string().optional(),
				transaction_cost_bps: z.number().optional(),
				data_cache_dir: z.string().optional(),
			}).optional(),
		})
		.optional(),
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
	verdict: z.union([z.literal("GO"), z.literal("HOLD"), z.literal("PIVOT")]),
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

// ============================================================
// Sector Spillover Strategy (US -> Japan)
// ============================================================

export const US11SectorsSchema = z.union([
	z.literal("energy"),
	z.literal("materials"),
	z.literal("industrials"),
	z.literal("consumer_discretionary"),
	z.literal("consumer_staples"),
	z.literal("healthcare"),
	z.literal("financials"),
	z.literal("it"),
	z.literal("communication"),
	z.literal("utilities"),
	z.literal("real_estate"),
]);

export type US11Sectors = z.infer<typeof US11SectorsSchema>;

export const JP17SectorsSchema = z.union([
	z.literal("1000"), // 水産・農林業
	z.literal("2000"), // 鉱業
	z.literal("3000"), // 建設業
	z.literal("4000"), // 食料品
	z.literal("5000"), // 繊維製品
	z.literal("6000"), // 紙・パルプ
	z.literal("7000"), // 化学
	z.literal("8000"), // 医薬品
	z.literal("9000"), // 石油・石炭製品
	z.literal("10000"), // ゴム製品
	z.literal("11000"), // ガラス・土石製品
	z.literal("12000"), // 鉄鋼
	z.literal("13000"), // 非鉄金属
	z.literal("14000"), // 金属製品
	z.literal("15000"), // 機械
	z.literal("16000"), // 電気機器
	z.literal("17000"), // 輸送用機器
]);

export type JP17Sectors = z.infer<typeof JP17SectorsSchema>;

export const SectorReturnsSchema = z.object({
	date: z.string(),
	sector: z.union([US11SectorsSchema, JP17SectorsSchema]),
	return_pct: z.number(),
});

export type SectorReturns = z.infer<typeof SectorReturnsSchema>;

export const RegularizedPCAResultSchema = z.object({
	date: z.string(),
	components: z.array(z.number()), // Latent factors
	variance_explained: z.array(z.number()), // Variance per component
	cumulative_variance: z.number(),
});

export type RegularizedPCAResult = z.infer<typeof RegularizedPCAResultSchema>;

export const SectorSpilloverSignalSchema = z.object({
	date: z.string(),
	jp_sector: JP17SectorsSchema,
	signal_score: z.number(), // -1.0 (strong short) to +1.0 (strong long)
	signal_type: z.union([z.literal("long"), z.literal("neutral"), z.literal("short")]),
	confidence: z.number(), // 0-1, higher = more confident
	us_factor_contributions: z.record(z.string(), z.number()),
});

export type SectorSpilloverSignal = z.infer<typeof SectorSpilloverSignalSchema>;

export const SpilloverBacktestResultSchema = z.object({
	backtest_id: z.string(),
	start_date: z.string(),
	end_date: z.string(),
	total_returns_pct: z.number(),
	sharpe_ratio: z.number(),
	max_drawdown_pct: z.number(),
	win_rate: z.number(), // % of profitable trades
	num_trades: z.number(),
	strategy_name: z.string(),
});

export type SpilloverBacktestResult = z.infer<typeof SpilloverBacktestResultSchema>;
