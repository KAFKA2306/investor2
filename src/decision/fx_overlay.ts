export const FX_OVERLAY_SCHEMA_VERSION = "investor2.fx-overlay.v1" as const;

export type EvidenceKind = "real" | "test_fixture";

export interface AssetPosition {
  id: string;
  marketValueJpy: number;
  usdExposureRatio: number;
  sourceRef: string;
  evidenceKind: EvidenceKind;
}

export interface FxOverlayObservation {
  periodStart: string;
  periodEnd: string;
  observedAt: string;
  basePortfolioReturn: number;
  usdJpySpotReturn: number;
  realizedSwapLongReturn: number;
  realizedSwapShortReturn?: number;
  fundingCostReturn: number;
  usdLongCrowdingPercentile?: number;
  crowdingAvailableAt?: string;
  sourceRefs: string[];
  evidenceKind: EvidenceKind;
}

export interface FxOverlayConfig {
  minIncrementalUsdExposure: number;
  maxIncrementalUsdExposure: number;
  minTotalUsdExposure: number;
  maxTotalUsdExposure: number;
  initialMarginRate: number;
  maxMarginUsageFraction: number;
  marginCallMarginRate: number;
  liquidationMarginRate: number;
  maxOverlayExpectedShortfallContribution: number;
  maxCrowdingReduction: number;
  riskAversion: number;
  spreadCostRatePerUnitTurnover: number;
  trainingWindow: number;
}

export interface PerformanceMetrics {
  cagr: number;
  annualizedVolatility: number;
  sharpe: number;
  sortino: number;
  maxDrawdown: number;
  expectedShortfall95: number;
  worstPeriodReturn: number;
}

export interface OverlayPathMetrics extends PerformanceMetrics {
  fxContributionAnnualized: number;
  carryContributionAnnualized: number;
  fundingCostContributionAnnualized: number;
  transactionCostContributionAnnualized: number;
  marginCallCount: number;
  forcedLiquidationCount: number;
  turnover: number;
}

export interface BaselineResult {
  incrementalUsdExposure: number;
  status: "EVALUATED" | "INFEASIBLE";
  reason?: string;
  metrics?: OverlayPathMetrics;
}

export interface FxOverlayVerifiedResult {
  schema_version: typeof FX_OVERLAY_SCHEMA_VERSION;
  status: "VERIFIED" | "TEST_ONLY";
  currentUsdExposure: number;
  recommendedIncrementalUsdExposure: number;
  recommendedTotalUsdExposure: number;
  hedgeRatio: number;
  overhedged: boolean;
  marginRequirementFraction: number;
  liquidationHeadroomFraction: number;
  oos: OverlayPathMetrics;
  baselines: BaselineResult[];
  provenance: {
    positionSourceRefs: string[];
    observationSourceRefs: string[];
  };
}

export interface FxOverlayUnverifiedResult {
  schema_version: typeof FX_OVERLAY_SCHEMA_VERSION;
  status: "UNVERIFIED";
  reason: string;
}

export type FxOverlayDecisionResult =
  | FxOverlayVerifiedResult
  | FxOverlayUnverifiedResult;

export class UnverifiedDataError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnverifiedDataError";
  }
}

type Bounds = { min: number; max: number };
type Direction = "long" | "short";

const finite = (value: number, name: string): void => {
  if (!Number.isFinite(value)) {
    throw new UnverifiedDataError(`${name} must be finite`);
  }
};

const time = (value: string, name: string): number => {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    throw new UnverifiedDataError(`${name} must be a parseable timestamp`);
  }
  return parsed;
};

const average = (values: number[]): number =>
  values.reduce((sum, value) => sum + value, 0) / values.length;

const sampleVariance = (values: number[]): number => {
  if (values.length < 2) return 0;
  const center = average(values);
  return (
    values.reduce((sum, value) => sum + (value - center) ** 2, 0) /
    (values.length - 1)
  );
};

const sampleCovariance = (left: number[], right: number[]): number => {
  if (left.length !== right.length || left.length < 2) return 0;
  const leftMean = average(left);
  const rightMean = average(right);
  return (
    left.reduce(
      (sum, value, index) =>
        sum + (value - leftMean) * (right[index] - rightMean),
      0,
    ) /
    (left.length - 1)
  );
};

const expectedShortfallLoss = (returns: number[]): number => {
  const sorted = [...returns].sort((a, b) => a - b);
  const tailCount = Math.max(1, Math.ceil(sorted.length * 0.05));
  return Math.max(0, -average(sorted.slice(0, tailCount)));
};

const validatePosition = (position: AssetPosition): void => {
  if (!position.id || !position.sourceRef) {
    throw new UnverifiedDataError("positions require id and sourceRef");
  }
  finite(position.marketValueJpy, `${position.id}.marketValueJpy`);
  finite(position.usdExposureRatio, `${position.id}.usdExposureRatio`);
  if (position.marketValueJpy < 0) {
    throw new UnverifiedDataError("negative market value is unsupported");
  }
};

const validateObservation = (row: FxOverlayObservation): void => {
  const start = time(row.periodStart, "periodStart");
  const end = time(row.periodEnd, "periodEnd");
  const observed = time(row.observedAt, "observedAt");
  if (!(start < end && end <= observed)) {
    throw new UnverifiedDataError(
      "observation timing must satisfy periodStart < periodEnd <= observedAt",
    );
  }
  if (row.sourceRefs.length === 0 || row.sourceRefs.some((ref) => !ref)) {
    throw new UnverifiedDataError("observations require explicit sourceRefs");
  }
  finite(row.basePortfolioReturn, "basePortfolioReturn");
  finite(row.usdJpySpotReturn, "usdJpySpotReturn");
  finite(row.realizedSwapLongReturn, "realizedSwapLongReturn");
  finite(row.fundingCostReturn, "fundingCostReturn");
  if (row.realizedSwapShortReturn !== undefined) {
    finite(row.realizedSwapShortReturn, "realizedSwapShortReturn");
  }
  if (row.usdLongCrowdingPercentile !== undefined) {
    finite(row.usdLongCrowdingPercentile, "usdLongCrowdingPercentile");
    if (
      row.usdLongCrowdingPercentile < 0 ||
      row.usdLongCrowdingPercentile > 1 ||
      !row.crowdingAvailableAt
    ) {
      throw new UnverifiedDataError(
        "crowding requires percentile in [0,1] and crowdingAvailableAt",
      );
    }
  }
};

const validateConfig = (config: FxOverlayConfig): void => {
  for (const [name, value] of Object.entries(config)) finite(value, name);
  if (!Number.isInteger(config.trainingWindow) || config.trainingWindow < 2) {
    throw new UnverifiedDataError("trainingWindow must be an integer >= 2");
  }
  if (config.minIncrementalUsdExposure > config.maxIncrementalUsdExposure) {
    throw new UnverifiedDataError("invalid incremental exposure bounds");
  }
  if (config.minTotalUsdExposure > config.maxTotalUsdExposure) {
    throw new UnverifiedDataError("invalid total exposure bounds");
  }
  if (
    config.initialMarginRate <= 0 ||
    config.maxMarginUsageFraction <= 0 ||
    config.marginCallMarginRate <= 0 ||
    config.liquidationMarginRate <= 0 ||
    config.maxOverlayExpectedShortfallContribution <= 0 ||
    config.maxCrowdingReduction < 0 ||
    config.maxCrowdingReduction > 1 ||
    config.riskAversion < 0 ||
    config.spreadCostRatePerUnitTurnover < 0
  ) {
    throw new UnverifiedDataError("invalid risk, margin, or cost configuration");
  }
};

export const calculateCurrentUsdExposure = (
  positions: AssetPosition[],
): number => {
  if (positions.length === 0) {
    throw new UnverifiedDataError("positions are required");
  }
  positions.forEach(validatePosition);
  const nav = positions.reduce((sum, row) => sum + row.marketValueJpy, 0);
  if (nav <= 0) throw new UnverifiedDataError("portfolio NAV must be positive");
  return (
    positions.reduce(
      (sum, row) => sum + row.marketValueJpy * row.usdExposureRatio,
      0,
    ) / nav
  );
};

const overlayUnitReturn = (
  row: FxOverlayObservation,
  direction: Direction,
): number => {
  if (direction === "long") {
    return (
      row.usdJpySpotReturn +
      row.realizedSwapLongReturn -
      row.fundingCostReturn
    );
  }
  if (row.realizedSwapShortReturn === undefined) {
    throw new UnverifiedDataError(
      "negative USD exposure requires realized short swap; no policy-rate fallback is allowed",
    );
  }
  return (
    -row.usdJpySpotReturn +
    row.realizedSwapShortReturn -
    row.fundingCostReturn
  );
};

const exposureBounds = (
  training: FxOverlayObservation[],
  currentUsdExposure: number,
  config: FxOverlayConfig,
  crowding?: number,
): Bounds => {
  const marginLimit =
    config.maxMarginUsageFraction / config.initialMarginRate;
  let min = Math.max(
    config.minIncrementalUsdExposure,
    config.minTotalUsdExposure - currentUsdExposure,
    -marginLimit,
  );
  let max = Math.min(
    config.maxIncrementalUsdExposure,
    config.maxTotalUsdExposure - currentUsdExposure,
    marginLimit,
  );

  const longLoss = expectedShortfallLoss(
    training.map((row) => overlayUnitReturn(row, "long")),
  );
  if (longLoss > 0) {
    max = Math.min(
      max,
      config.maxOverlayExpectedShortfallContribution / longLoss,
    );
  }
  if (crowding !== undefined) {
    max *= 1 - config.maxCrowdingReduction * crowding;
  }

  if (min < 0) {
    const shortLoss = expectedShortfallLoss(
      training.map((row) => overlayUnitReturn(row, "short")),
    );
    if (shortLoss > 0) {
      min = Math.max(
        min,
        -config.maxOverlayExpectedShortfallContribution / shortLoss,
      );
    }
  }
  if (min > max) {
    throw new UnverifiedDataError(
      "risk and exposure constraints have no feasible range",
    );
  }
  return { min, max };
};

const utility = (
  base: number[],
  leg: number[],
  magnitude: number,
  riskAversion: number,
): number => {
  const combined = base.map(
    (value, index) => value + magnitude * leg[index],
  );
  return (
    average(combined) * 252 -
    riskAversion * sampleVariance(combined) * 252
  );
};

const bestMagnitude = (
  base: number[],
  leg: number[],
  lower: number,
  upper: number,
  riskAversion: number,
): number => {
  if (lower > upper) {
    throw new UnverifiedDataError("invalid optimization segment");
  }
  const legVariance = sampleVariance(leg);
  const legMean = average(leg);
  if (riskAversion === 0 || legVariance === 0) {
    return legMean > 0 ? upper : lower;
  }
  const unconstrained =
    (legMean / (2 * riskAversion) - sampleCovariance(base, leg)) /
    legVariance;
  return Math.min(upper, Math.max(lower, unconstrained));
};

export const optimizeIncrementalUsdExposure = (
  training: FxOverlayObservation[],
  currentUsdExposure: number,
  config: FxOverlayConfig,
  crowding?: number,
): number => {
  validateConfig(config);
  if (training.length < 2) {
    throw new UnverifiedDataError(
      "at least two training observations are required",
    );
  }
  training.forEach(validateObservation);
  const bounds = exposureBounds(
    training,
    currentUsdExposure,
    config,
    crowding,
  );
  const base = training.map((row) => row.basePortfolioReturn);
  const candidates: Array<{ exposure: number; score: number }> = [];

  if (bounds.min <= 0 && bounds.max >= 0) {
    candidates.push({
      exposure: 0,
      score:
        average(base) * 252 -
        config.riskAversion * sampleVariance(base) * 252,
    });
  }
  if (bounds.max > 0) {
    const lower = Math.max(0, bounds.min);
    const upper = bounds.max;
    const leg = training.map((row) => overlayUnitReturn(row, "long"));
    const magnitude = bestMagnitude(
      base,
      leg,
      lower,
      upper,
      config.riskAversion,
    );
    candidates.push({
      exposure: magnitude,
      score: utility(base, leg, magnitude, config.riskAversion),
    });
  }
  if (bounds.min < 0) {
    const lower = Math.max(0, -bounds.max);
    const upper = -bounds.min;
    const leg = training.map((row) => overlayUnitReturn(row, "short"));
    const magnitude = bestMagnitude(
      base,
      leg,
      lower,
      upper,
      config.riskAversion,
    );
    candidates.push({
      exposure: -magnitude,
      score: utility(base, leg, magnitude, config.riskAversion),
    });
  }
  return candidates.sort((a, b) => b.score - a.score)[0].exposure;
};

const performanceMetrics = (returns: number[]): PerformanceMetrics => {
  if (returns.length === 0) {
    throw new UnverifiedDataError("cannot evaluate an empty return path");
  }
  let wealth = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    finite(value, "return");
    if (value <= -1) {
      throw new UnverifiedDataError("return <= -100% invalidates the path");
    }
    wealth *= 1 + value;
    peak = Math.max(peak, wealth);
    maxDrawdown = Math.max(maxDrawdown, 1 - wealth / peak);
  }
  const dailyMean = average(returns);
  const dailyVol = Math.sqrt(sampleVariance(returns));
  const downside = returns.filter((value) => value < 0);
  const downsideVol =
    downside.length > 1 ? Math.sqrt(sampleVariance(downside)) : 0;
  return {
    cagr: wealth ** (252 / returns.length) - 1,
    annualizedVolatility: dailyVol * Math.sqrt(252),
    sharpe: dailyVol === 0 ? 0 : (dailyMean / dailyVol) * Math.sqrt(252),
    sortino:
      downsideVol === 0 ? 0 : (dailyMean / downsideVol) * Math.sqrt(252),
    maxDrawdown,
    expectedShortfall95: expectedShortfallLoss(returns),
    worstPeriodReturn: Math.min(...returns),
  };
};

const evaluatePath = (
  rows: FxOverlayObservation[],
  exposures: number[],
  config: FxOverlayConfig,
): OverlayPathMetrics => {
  if (rows.length === 0 || rows.length !== exposures.length) {
    throw new UnverifiedDataError(
      "rows and exposures must have equal non-zero length",
    );
  }
  const returns: number[] = [];
  let equity = 1;
  let previousExposure = 0;
  let liquidated = false;
  let marginCallCount = 0;
  let forcedLiquidationCount = 0;
  let turnover = 0;
  let fxContribution = 0;
  let carryContribution = 0;
  let fundingContribution = 0;
  let transactionContribution = 0;

  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    validateObservation(row);
    const exposure = liquidated ? 0 : exposures[index];
    finite(exposure, "exposure");
    const change = Math.abs(exposure - previousExposure);
    const fx = exposure * row.usdJpySpotReturn;
    const carry =
      exposure >= 0
        ? exposure * row.realizedSwapLongReturn
        : Math.abs(exposure) *
          overlayUnitReturn(
            { ...row, usdJpySpotReturn: 0, fundingCostReturn: 0 },
            "short",
          );
    const funding = Math.abs(exposure) * row.fundingCostReturn;
    const transaction = change * config.spreadCostRatePerUnitTurnover;
    const periodReturn =
      row.basePortfolioReturn + fx + carry - funding - transaction;

    returns.push(periodReturn);
    equity *= 1 + periodReturn;
    turnover += change;
    fxContribution += fx;
    carryContribution += carry;
    fundingContribution += funding;
    transactionContribution += transaction;

    if (equity < Math.abs(exposure) * config.marginCallMarginRate) {
      marginCallCount += 1;
    }
    if (
      !liquidated &&
      equity < Math.abs(exposure) * config.liquidationMarginRate
    ) {
      forcedLiquidationCount += 1;
      liquidated = true;
    }
    previousExposure = exposure;
  }

  const annualizer = 252 / rows.length;
  return {
    ...performanceMetrics(returns),
    fxContributionAnnualized: fxContribution * annualizer,
    carryContributionAnnualized: carryContribution * annualizer,
    fundingCostContributionAnnualized: fundingContribution * annualizer,
    transactionCostContributionAnnualized:
      transactionContribution * annualizer,
    marginCallCount,
    forcedLiquidationCount,
    turnover,
  };
};

const baselineBlocker = (
  exposure: number,
  currentUsdExposure: number,
  config: FxOverlayConfig,
): string | undefined => {
  if (
    exposure < config.minIncrementalUsdExposure ||
    exposure > config.maxIncrementalUsdExposure
  ) {
    return "outside incremental exposure bounds";
  }
  const total = currentUsdExposure + exposure;
  if (total < config.minTotalUsdExposure || total > config.maxTotalUsdExposure) {
    return "outside total USD exposure bounds";
  }
  if (
    Math.abs(exposure) * config.initialMarginRate >
    config.maxMarginUsageFraction
  ) {
    return "margin usage exceeds configured maximum";
  }
  return undefined;
};

const allRealEvidence = (
  positions: AssetPosition[],
  rows: FxOverlayObservation[],
): boolean =>
  positions.every((row) => row.evidenceKind === "real") &&
  rows.every((row) => row.evidenceKind === "real");

export const walkForwardFxOverlay = (
  positions: AssetPosition[],
  observations: FxOverlayObservation[],
  config: FxOverlayConfig,
): FxOverlayVerifiedResult => {
  validateConfig(config);
  positions.forEach(validatePosition);
  observations.forEach(validateObservation);
  if (observations.length <= config.trainingWindow) {
    throw new UnverifiedDataError(
      "insufficient observations for walk-forward OOS",
    );
  }

  const sorted = [...observations].sort(
    (a, b) =>
      time(a.periodStart, "periodStart") - time(b.periodStart, "periodStart"),
  );
  const currentUsdExposure = calculateCurrentUsdExposure(positions);
  const oosRows: FxOverlayObservation[] = [];
  const exposures: number[] = [];

  for (let index = config.trainingWindow; index < sorted.length; index += 1) {
    const target = sorted[index];
    const decisionTime = time(target.periodStart, "periodStart");
    const training = sorted.slice(index - config.trainingWindow, index);
    if (training.some((row) => time(row.observedAt, "observedAt") > decisionTime)) {
      throw new UnverifiedDataError(
        "PIT violation: a training observation was unavailable at decision time",
      );
    }

    let crowding: number | undefined;
    if (target.usdLongCrowdingPercentile !== undefined) {
      if (
        !target.crowdingAvailableAt ||
        time(target.crowdingAvailableAt, "crowdingAvailableAt") > decisionTime
      ) {
        throw new UnverifiedDataError(
          "PIT violation: crowding data was unavailable at decision time",
        );
      }
      crowding = target.usdLongCrowdingPercentile;
    }

    exposures.push(
      optimizeIncrementalUsdExposure(
        training,
        currentUsdExposure,
        config,
        crowding,
      ),
    );
    oosRows.push(target);
  }

  const recommendedIncrementalUsdExposure = exposures.at(-1) ?? 0;
  const recommendedTotalUsdExposure =
    currentUsdExposure + recommendedIncrementalUsdExposure;
  const hedgeRatio =
    currentUsdExposure > 0 && recommendedIncrementalUsdExposure < 0
      ? -recommendedIncrementalUsdExposure / currentUsdExposure
      : 0;
  const baselines = [0, 0.5, 1, 2, 3].map<BaselineResult>((exposure) => {
    const reason = baselineBlocker(exposure, currentUsdExposure, config);
    if (reason) {
      return {
        incrementalUsdExposure: exposure,
        status: "INFEASIBLE",
        reason,
      };
    }
    return {
      incrementalUsdExposure: exposure,
      status: "EVALUATED",
      metrics: evaluatePath(
        oosRows,
        Array.from({ length: oosRows.length }, () => exposure),
        config,
      ),
    };
  });

  return {
    schema_version: FX_OVERLAY_SCHEMA_VERSION,
    status: allRealEvidence(positions, observations) ? "VERIFIED" : "TEST_ONLY",
    currentUsdExposure,
    recommendedIncrementalUsdExposure,
    recommendedTotalUsdExposure,
    hedgeRatio,
    overhedged: hedgeRatio > 1,
    marginRequirementFraction:
      Math.abs(recommendedIncrementalUsdExposure) * config.initialMarginRate,
    liquidationHeadroomFraction:
      config.maxMarginUsageFraction -
      Math.abs(recommendedIncrementalUsdExposure) * config.initialMarginRate,
    oos: evaluatePath(oosRows, exposures, config),
    baselines,
    provenance: {
      positionSourceRefs: [...new Set(positions.map((row) => row.sourceRef))],
      observationSourceRefs: [
        ...new Set(observations.flatMap((row) => row.sourceRefs)),
      ],
    },
  };
};

export const buildFxOverlayDecision = (
  positions: AssetPosition[],
  observations: FxOverlayObservation[],
  config: FxOverlayConfig,
): FxOverlayDecisionResult => {
  try {
    return walkForwardFxOverlay(positions, observations, config);
  } catch (error) {
    if (error instanceof UnverifiedDataError) {
      return {
        schema_version: FX_OVERLAY_SCHEMA_VERSION,
        status: "UNVERIFIED",
        reason: error.message,
      };
    }
    throw error;
  }
};
