import { describe, expect, test } from "bun:test";
import {
  CacheStatisticsSchema,
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

  test("rejects non-JSON stats output", () => {
    expect(() => parseStatsJson("not-json")).toThrow(
      "stats output is not valid JSON",
    );
  });

  test("propagates a failed stats subprocess", () => {
    expect(() => parseStatsProcessResult(JSON.stringify(zeroStats), 1)).toThrow(
      "stats task failed with exit code 1",
    );
  });
});
