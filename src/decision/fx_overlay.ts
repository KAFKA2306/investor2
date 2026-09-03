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
	hegeRatio: number;
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

const assertFinite = (value: number, name: string): void => {
	if (!Number.isFinite(value)) {
		throw new UnverifiedDataError(`${name} must be finite`);
	}
};

const timestamp = (value: string, name: string): number => {
	const parsed = Date.parse(value);
	if (!Number.isFinite(parsed)) {
		throw new UnverifiedDataError(`${name} must be a parseable timestamp`);
	}
	return parsed;
};

const mean = (values: number[]): number =>
	values.reduce((total, value) => total + value, 0) / values.length;

const variance = (values: number[]): number => {
	if (values.length < 2) return 0;
	const center = mean(values);
	return (
		values.reduce((total, value) => total + (value - center) ** 2, 0) /
		(values.length - 1)
	);
};

const covariance = (left: number[], right: number[]): number => {
	if (left.length !== right.length || left.length < 2) return 0;
	const leftMean = mean(left);
	const rightMean = mean(right);
	return (
		left.reduce(
			(total, value, index) =>
				total + (value - leftMean) * (right[index] - rightMean),
			0,
		) /
		(left.length - 1)
	);
};

const expectedShortfallLoss = (returns: number[]): number => {
	const sorted = [...returns].sort((a, b) => a - b);
	const count = Math.max(1, Math.ceil(sorted.length * 0.05));
	return Math.max(0, -mean(sorted.slice(0, count)));
};

const performanceMetrics = (returns: number[]): PerformanceMetrics => {
	if (returns.length === 0) {
		throw new UnverifiedDataError("cannot evaluate an empty return path");
	}
	let wealth = 1;
	let peak = 1;
	let maxDrawdown = 0;
	for (const value of returns) {
		assertFinite(value, "return");
		if (value <= -1) {
			throw new UnverifiedDataError("return <= -100% invalidates the path");
		}
		wealth *= 1 + value;
		peak = Math.max(peak, wealth);
		maxDrawdown = Math.max(maxDrawdown, 1 - wealth / peak);
	}
	const dailyMean = mean(returns);
	const dailyVol = Math.sqrt(variance(returns));
	const downside = returns.filter((value) => value < 0);
	const downsideVol = downside.length > 1 ? Math.sqrt(variance(downside)) : 0;
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

const validatePosition = (position: AssetPosition): void => {
	if (!position.id || !position.sourceRef) {
		throw new UnverifiedDataError("positions require id and sourceRef");
	}
	assertFinite(position.marketValueJpy, `${position.id}.marketValueJpy`);
	assertFinite(position.usdExposureRatio, `${position.id}.usdExposureRatio`);
	if (position.marketValueJpy < 0) {
		throw new UnverifiedDataError("negative market value is unsupported");
	}
};

const validateObservation = (row: FxOverlayObservation): void => {
	const start = timestamp(row.periodStart, "periodStart");
	const end = timestamp(row.periodEnd, "periodEnd");
	const observed = timestamp(row.observedAt, "observedAt");
	if (!(start < end && end <= observed)) {
		throw new UnverifiedDataError(
			"observation timing must satisfy periodStart < periodEnd <= observedAt",
		);
	}
	if (row.sourceRefs.length === 0 || row.sourceRefs.some((ref) => !ref)) {
		throw new UnverifiedDataError("observations require explicit sourceRefs");
	}
	for (const [name, value] of Object.entries({
		basePortfolioReturn: row.basePortfolioReturn,
		usdJpySpotReturn: row.usdJpySpotReturn,
		realizedSwapLongReturn: row.realizedSwapLongReturn,
		fundingCostReturn: row.fundingCostReturn,
	})) {
		assertFinite(value, name);
	}
	if (row.realizedSwapShortReturn !== undefined) {
		assertFinite(row.realizedSwapShortReturn, "realizedSwapShortReturn");
	}
	if (row.usdLongCrowdingPercentile !== undefined) {
		assertFinite(row.usdLongCrowdingPercentile, "usdLongCrowdingPercentile");
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
	for (const [name, value] of Object.entries(config)) assertFinite(value, name);
	if (config.trainingWindow < 2 || !Number.isInteger(config.trainingWindow)) {
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
		config.riskAversion < 0 ||
		config.spreadCostRatePerUnitTurnover < 0 ||
		config.maxCrowdingReduction < 0 ||
		config.maxCrowdingReduction > 1
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
	const nav = positions.reduce((total, row) => total + row.marketValueJpy, 0);
	if (nav <= 0) throw new UnverifiedDataError("portfolio NAV must be positive");
	return (
		positions.reduce(
			(total, row) => total + row.marketValueJpy * row.usdExposureRatio,
			0,
		) / nav
	);
};

const overlayLeg = (
	row: FxOverlayObservation,
	direction: "long" | "short",
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

const continuousMagnitudeOptimum = (
	base: number[],
	leg: number[],
	upperBound: number,
	riskAversion: number,
): number => {
	if (upperBound <= 0) return 0;
	const legVariance = variance(leg);
	const legMean = mean(leg);
	if (riskAversion === 0 || legVariance === 0) {
		return legMean > 0 ? upperBound : 0;
	}
	const optimum =
		(legMean / (2 * riskAversion) - covariance(base, leg)) / legVariance;
	return Math.min(upperBound, Math.max(0, optimum));
};

const utility = (
	base: number[],
	leg: number[],
	magnitude: number,
	riskAversion: number,
): number => {
	const combined = base.map((value, index) => value + magnitude * leg[index]);
	return mean(combined) * 252 - riskAversion * variance(combined) * 252;
};

const exposureBounds = (
	training: FxOverlayObservation[],
	currentUsdExposure: number,
	config: FxOverlayConfig,
	usdLongCrowdingPercentile?: number,
): { min: number; max: number } => {
	const marginLimit = config.maxMarginUsageFraction / config.initialMarginRate;
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

	const longLeg = training.map((row) => overlayLeg(row, "long"));
	const longEs = expectedShortfallLoss(longLeg);
	if (longEs > 0) {
		max = Math.min(
			max,
			config.maxOverlayExpectedShortfallContribution / longEs,
		);
	}
	if (usdLongCrowdingPercentile !== undefined) {
		max *= 1 - config.maxCrowdingReduction * usdLongCrowdingPercentile;
	}

	if (min < 0) {
		const shortLeg = training.map((row) => overlayLeg(row, "short"));
		const shortEs = expectedShortfallLoss(shortLeg);
		if (shortEs > 0) {
			min = Math.max(
				min,
				-config.maxOverlayExpectedShortfallContribution / shortEs,
			);
		}
	}
	if (min > max) {
		throw new UnverifiedDataError("risk and exposure constraints have no feasible range");
	}
	return { min, max };
};

export const optimizeIncrementalUsdExposure = (
	training: FxOverlayObservation[],
	currentUsdExposure: number,
	config: FxOverlayConfig,
	usdLongCrowdingPercentile?: number,
): number => {
	validateConfig(config);
	if (training.length < 2) {
		throw new UnverifiedDataError("at least two training observations are required");
	}
	training.forEach(validateObservation);
	const bounds = exposureBounds(
		training,
		currentUsdExposure,
		config,
		usdLongCrowdingPercentile,
	);
	const base = training.map((row) => row.basePortfolioReturn);
	const candidates: Array<{ exposure: number; score: number }> = [
		{ exposure: 0, score: mean(base) * 252 - config.riskAversion * variance(base) * 252 },
	];

	if (bounds.max > 0) {
		const leg = training.map((row) => overlayLeg(row, "long"));
		const magnitude = continuousMagnitudeOptimum(
			base,
			leg,
			bounds.max,
			config.riskAversion,
		);
		candidates.push({
			exposure: magnitude,
			score: utility(base, leg, magnitude, config.riskAversion),
		});
	}
	if (bounds.min < 0) {
		const leg = training.map((row) => overlayLeg(row, "short"));
		const magnitude = continuousMagnitudeOptimum(
			base,
			leg,
			-bounds.min,
			config.riskAversion,
		);
		candidates.push({
			exposure: -magnitude,
			score: utility(base, leg, magnitude, config.riskAversion),
		});
	}
	return candidates.sort((a, b) => b.score - a.score)[0].exposure;
};

const evaluatePath = (
	rows: FxOverlayObservation[],
	exposures: number[],
	config: FxOverlayConfig,
): OverlayPathMetrics => {
	if (rows.length !== exposures.length || rows.length === 0) {
		throw new UnverifiedDataError("rows and exposures must have equal non-zero length");
	}
	const returns: number[] = [];
	let equity = 1;
	let previousExposure = 0;
	let disabledByLiquidation = false;
	let marginCallCount = 0;
	let forcedLiquidationCount = 0;
	let turnover = 0;
	let fxContribution = 0;
	let carryContribution = 0;
	let fundingCostContribution = 0;
	let transactionCostContribution = 0;

	for (let index = 0; index < rows.length; index += 1) {
		const row = rows[index];
		validateObservation(row);
		const requested = exposures[index];
		assertFinite(requested, "exposure");
		const exposure = disabledByLiquidation ? 0 : requested;
		const change = Math.abs(exposure - previousExposure);
		const fx = exposure * row.usdJpySpotReturn;
		const carry =
			exposure >= 0
				? exposure * row.realizedSwapLongReturn
				: Math.abs(exposure) * (row.realizedSwapShortReturn ?? (() => {
					throw new UnverifiedDataError("short swap is required for negative exposure");
				})());
		const funding = Math.abs(exposure) * row.fundingCostReturn;
		const transaction = change * config.spreadCostRatePerUnitTurnover;
		const periodReturn =
			row.basePortfolioReturn + fx + carry - funding - transaction;
		returns.push(periodReturn);
		equity *= 1 + periodReturn;
		turnover += change;
		fxContribution += fx;
		carryContribution += carry;
		fundingCostContribution += funding;
		transactionCostContribution += transaction;

		if (equity < Math.abs(exposure) * config.marginCallMarginRate) {
			marginCallCount += 1;
		}
		if (
			!disabledByLiquidation &&
			equity < Math.abs(exposure) * config.liquidationMarginRate
		) {
			forcedLiquidationCount += 1;
			disabledByLiquidation = true;
		}
		previousExposure = exposure;
	}
	const annualizer = 252 / rows.length;
	return {
		...performanceMetrics(returns),
		fxContributionAnnualized: fxContribution * annualizer,
		carryContributionAnnualized: carryContribution * annualizer,
		fundingCostContributionAnnualized: fundingCostContribution * annualizer,
		transactionCostContributionAnnualized: transactionCostContribution * annualizer,
		marginCallCount,
		forcedLiquidationCount,
		turnover,
	};
};

const baselineFeasibility = (
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
	if (Math.abs(exposure) * config.initialMarginRate > config.maxMarginUsageFraction) {
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
	if (observations.length <= config.trainingWindow) {
		throw new UnverifiedDataError("insufficient observations for walk-forward OOS");
	}
	positions.forEach(validatePosition);
	observations.forEach(validateObservation);
	const sorted = [...observations].sort(
		(a, b) => timestamp(a.periodStart, "periodStart") - timestamp(b.periodStart, "periodStart"),
	);
	const currentUsdExposure = calculateCurrentUsdExposure(positions);
	const oosRows: FxOverlayObservation[] = [];
	const exposures: number[] = [];

	for (let index = config.trainingWindow; index < sorted.length; index += 1) {
		const target = sorted[index];
		const decisionTime = timestamp(target.periodStart, "periodStart");
		const training = sorted.slice(index - config.trainingWindow, index);
		if (training.some((row) => timestamp(row.observedAt, "observedAt") > decisionTime)) {
			throw new UnverifiedDataError(
				"PIT violation: a training observation was unavailable at decision time",
			);
		}
		let crowding: number | undefined;
		if (target.usdLongCrowdingPercentile !== undefined) {
			if (
				!target.crowdingAvailableAt ||
				timestamp(target.crowdingAvailableAt, "crowdingAvailableAt") > decisionTime
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
	const baselines: BaselineResult[] = [0, 0.5, 1, 2, 3].map((exposure) => {
		const reason = baselineFeasibility(exposure, currentUsdExposure, config);
		if (reason) return { incrementalUsdExposure: exposure, status: "INFEASIBLE", reason };
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
		hegeRatio: hedgeRatio,
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
