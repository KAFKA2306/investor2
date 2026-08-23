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
        cache: z.string(),
        edinet: z.string(),
        cacheFundamentalEdinet: z.string(),
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
