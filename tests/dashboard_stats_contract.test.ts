import { describe, expect, test } from "bun:test";
import {
  CacheStatisticsSchema,
  parseCacheStatisticsJson,
  parseCacheStatisticsProcessResult,
} from "../src/shared/cache_statistics";

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
    expect(parseCacheStatisticsJson(JSON.stringify(zeroStats))).toEqual(
      zeroStats,
    );
  });

  test("rejects missing required observations instead of filling zero", () => {
    const malformed = structuredClone(zeroStats) as Record<string, unknown>;
    const marketData = malformed.marketData as Record<string, unknown>;
    delete marketData.stocks;

    expect(() => parseCacheStatisticsJson(JSON.stringify(malformed))).toThrow();
  });

  test("rejects non-JSON stats output", () => {
    expect(() => parseCacheStatisticsJson("not-json")).toThrow(
      "stats output is not valid JSON",
    );
  });

  test("propagates a failed stats subprocess", () => {
    expect(() =>
      parseCacheStatisticsProcessResult(JSON.stringify(zeroStats), 1),
    ).toThrow("stats task failed with exit code 1");
  });
});
