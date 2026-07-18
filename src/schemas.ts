import type { Database } from "bun:sqlite";
import { z } from "zod";

export interface DatabaseRegistry {
	marketsPolymarket: Database;
	marketsJquants: Database;
	marketsYahoo: Database;
	fundamentalJquants: Database;
	fundamentalEdinet: Database;
	macroEstat: Database;
	macroFred: Database;
	[key: string]: Database;
}

export const VerificationAcceptanceSchema = z.object({
	minSharpe: z.number().finite(),
	maxPValue: z.number().finite().min(0).max(1),
	maxDrawdown: z.number().finite().min(0).max(1),
	minBacktestDays: z.number().int().positive().optional(),
});

export type VerificationAcceptance = z.infer<
	typeof VerificationAcceptanceSchema
>;

export const ConfigSchema = z.object({
	project: z.object({ name: z.string() }),
	paths: z
		.object({
			data: z.string(),
			logs: z.string(),
			verification: z.string(),
			cache: z.string(),
			edinet: z.string(),
			preprocessed: z.string(),
			cacheWebSearch: z.string().optional(),
			cacheFundamentalEdinet: z.string(),
			cacheMarketsPolymarket: z.string(),
			cacheMarketsJquants: z.string(),
			cacheMarketsYahoo: z.string(),
			cacheFundamentalJquants: z.string(),
			cacheMacroEstat: z.string(),
			cacheMacroFred: z.string().optional(),
			macroFred: z.string().optional(),
			cacheMarketSqlite: z.string().optional(),
			marketdataPricesCsv: z.string().optional(),
			marketdataFinCsv: z.string().optional(),
			marketdataListCsv: z.string().optional(),
			marketdataLabelsCsv: z.string().optional(),
			cacheBacktestResults: z.string().optional(),
		})
		.passthrough(),
	polymarket: z.object({ clob_url: z.string() }),
	providers: z
		.object({
			tavily: z.object({ maxResults: z.number() }),
		})
		.optional(),
	sector_spillover: z
		.object({
			us_sectors: z.array(z.string()),
			jp_sectors: z.array(z.string()),
			pca: z.object({
				n_components: z.number(),
				regularization_alpha: z.number(),
				max_iterations: z.number(),
			}),
			signal: z.object({
				long_threshold: z.number(),
				short_threshold: z.number(),
				neutral_threshold: z.number(),
			}),
			backtest: z.object({
				initial_capital: z.number(),
				long_size: z.number(),
				short_size: z.number(),
				rebalance_frequency: z.string(),
				transaction_cost_bps: z.number(),
				data_cache_dir: z.string(),
			}),
		})
		.optional(),
	pipelineBlueprint: z
		.object({
			verificationAcceptance: VerificationAcceptanceSchema,
			alphaLoop: z.object({
				maxCycles: z.number(),
				sleepSec: z.number(),
				maxFailures: z.number(),
			}),
		})
		.optional(),
	integrations: z
		.object({
			discord: z.object({
				enabled: z.boolean(),
				tokenEnv: z.string(),
				webhookUrlEnv: z.string(),
				commandPrefix: z.string(),
				maxMessageLength: z.number(),
			}),
			slack: z
				.object({ enabled: z.boolean(), tokenEnv: z.string() })
				.optional(),
			line: z
				.object({ enabled: z.boolean(), channelAccessTokenEnv: z.string() })
				.optional(),
		})
		.optional(),
});

export type Config = z.infer<typeof ConfigSchema>;

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

export const AlphaCandidateSchema = z.object({
	factor_id: z.string(),
	formula: z.string(),
	economic_mechanism: z.string(),
});

export type AlphaCandidate = z.infer<typeof AlphaCandidateSchema>;

export const StandardOutcomeSchema = z.object({
	sharpe: z.number().finite(),
	ic: z.number().finite(),
	max_drawdown: z.number().finite().min(0).max(1),
	p_value: z.number().finite().min(0).max(1),
	factor_id: z.string().min(1),
	backtest_days: z.number().int().positive(),
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
		minBacktestDays: z.number().int().positive(),
	}),
});

export type PipelineResultsReport = z.infer<typeof PipelineResultsReportSchema>;

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
	z.literal("1000"),
	z.literal("2000"),
	z.literal("3000"),
	z.literal("4000"),
	z.literal("5000"),
	z.literal("6000"),
	z.literal("7000"),
	z.literal("8000"),
	z.literal("9000"),
	z.literal("10000"),
	z.literal("11000"),
	z.literal("12000"),
	z.literal("13000"),
	z.literal("14000"),
	z.literal("15000"),
	z.literal("16000"),
	z.literal("17000"),
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
	components: z.array(z.number()),
	variance_explained: z.array(z.number()),
	cumulative_variance: z.number(),
});

export type RegularizedPCAResult = z.infer<typeof RegularizedPCAResultSchema>;

export const SectorSpilloverSignalSchema = z.object({
	date: z.string(),
	jp_sector: JP17SectorsSchema,
	signal_score: z.number(),
	signal_type: z.union([
		z.literal("long"),
		z.literal("neutral"),
		z.literal("short"),
	]),
	confidence: z.number(),
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
	win_rate: z.number(),
	num_trades: z.number(),
	strategy_name: z.string(),
	hypothesis_id: z.string().optional(),
	net_returns_pct: z.number().optional(),
	tax_paid_pct: z.number().optional(),
	num_winning_trades: z.number().optional(),
	num_losing_trades: z.number().optional(),
	sector_performance: z
		.array(
			z.object({
				jp_sector: z.string(),
				avg_return: z.number(),
				volatility: z.number(),
				sharpe: z.number(),
				win_rate: z.number(),
			}),
		)
		.optional(),
});

export type SpilloverBacktestResult = z.infer<
	typeof SpilloverBacktestResultSchema
>;
