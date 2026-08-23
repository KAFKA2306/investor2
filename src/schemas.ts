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
}

export const ConfigSchema = z
  .object({
    paths: z
      .object({
        data: z.string(),
        logs: z.string(),
        cache: z.string(),
        edinet: z.string(),
        cacheFundamentalEdinet: z.string(),
        cacheBacktestResults: z.string(),
      })
      .strict(),
  })
  .strict();

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
