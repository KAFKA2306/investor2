import { z } from "zod";

const CountSchema = z.number().int().nonnegative();
const SizeGbSchema = z.number().finite().nonnegative();

export const CacheStatisticsSchema = z
  .object({
    marketData: z
      .object({
        stocks: CountSchema,
        priceRecords: CountSchema,
        finRecords: CountSchema,
        dateRange: z
          .object({
            start: z.string().min(1),
            end: z.string().min(1),
          })
          .strict()
          .nullable(),
        sizeGb: SizeGbSchema,
      })
      .strict(),
    edinet: z
      .object({
        companyCount: CountSchema,
        documentCount: CountSchema,
        sizeGb: SizeGbSchema,
      })
      .strict(),
    sqlite: z
      .object({
        market: z.object({ sizeGb: SizeGbSchema }).strict().nullable(),
        edinet: z.object({ sizeGb: SizeGbSchema }).strict().nullable(),
        yahoocache: z.object({ sizeGb: SizeGbSchema }).strict().nullable(),
      })
      .strict(),
    lastUpdated: z.string().min(1),
    totalSizeGb: SizeGbSchema,
  })
  .strict();

const CachedStatisticsSchema = CacheStatisticsSchema.extend({
  generatedAt: z.number().finite().nonnegative(),
}).strict();

export type CacheStatistics = z.infer<typeof CacheStatisticsSchema>;

function decodeJson(text: string, source: string): unknown {
  if (!text.trim()) {
    throw new Error(`${source} is empty`);
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${source} is not valid JSON`, { cause: error });
  }
}

export function parseStatsJson(text: string): CacheStatistics {
  return CacheStatisticsSchema.parse(decodeJson(text, "stats output"));
}

export function parseStatsProcessResult(
  output: string,
  exitCode: number,
): CacheStatistics {
  if (exitCode !== 0) {
    throw new Error(`stats task failed with exit code ${exitCode}`);
  }
  return parseStatsJson(output);
}

export function parseFreshStatsCache(
  text: string,
  nowMs: number,
  ttlMs: number,
): CacheStatistics | null {
  const payload = CachedStatisticsSchema.parse(
    decodeJson(text, "stats cache"),
  );
  const ageMs = nowMs - payload.generatedAt;
  if (ageMs < 0) {
    throw new Error("stats cache generatedAt is in the future");
  }
  if (ageMs >= ttlMs) {
    return null;
  }

  const { generatedAt: _generatedAt, ...stats } = payload;
  return CacheStatisticsSchema.parse(stats);
}
