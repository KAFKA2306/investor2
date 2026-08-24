import { describe, expect, test } from "bun:test";
import {
  CacheStatisticsSchema,
  parseFreshStatsCache,
  parseStatsJson,
  parseStatsProcessResult,
} from "../src/dashboard/stats_contract";

const zeroStats = {
  marketData: {
    stocks: 0,
    priceRecords: 0,
    finRecords: 0,
    dateRange: null,
    sizeGb: 0,
  },
  edinet: {
    companyCount: 0,
    documentCount: 0,
    sizeGb: 0,
  },
  sqlite: {
    market: null,
    edinet: null,
    yahoocache: null,
  },
  lastUpdated: "2026-08-25T00:00:00.000Z",
  totalSizeGb: 0,
};

describe("dashboard stats contract", () => {
  test("accepts legitimate zero observations", () => {
    expect(CacheStatisticsSchema.parse(zeroStats)).toEqual(zeroStats);
    expect(parseStatsJson(JSON.stringify(zeroStats))).toEqual(zeroStats);
  });

  test("rejects missing required observations instead of filling zero", () => {
    const malformed = structuredClone(zeroStats) as Record<string, unknown>;
    const marketData = malformed.marketData as Record<string, unknown>;
    delete marketData.stocks;

    expect(() => parseStatsJson(JSON.stringify(malformed))).toThrow();
  });

  test("propagates a failed stats subprocess", () => {
    expect(() => parseStatsProcessResult(JSON.stringify(zeroStats), 1)).toThrow(
      "stats task failed with exit code 1",
    );
  });

  test("rejects corrupted cache rather than treating it as valid stats", () => {
    expect(() => parseFreshStatsCache("not-json", 2_000, 1_000)).toThrow(
      "stats cache is not valid JSON",
    );
  });

  test("distinguishes fresh, stale, and future cache state", () => {
    const payload = JSON.stringify({ ...zeroStats, generatedAt: 1_000 });
    expect(parseFreshStatsCache(payload, 1_500, 1_000)).toEqual(zeroStats);
    expect(parseFreshStatsCache(payload, 2_000, 1_000)).toBeNull();
    expect(() => parseFreshStatsCache(payload, 500, 1_000)).toThrow(
      "stats cache generatedAt is in the future",
    );
  });
});
