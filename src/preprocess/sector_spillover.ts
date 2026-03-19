import { readFileSync } from "node:fs";
import yaml from "js-yaml";
import { ConfigSchema, type SectorSpilloverSignal, type JP17Sectors } from "../schemas";

const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);

// Factor contribution constants
const FACTOR_NAMES = {
	RISK_SENTIMENT: "factor_1_risk_sentiment",
	US_DOMINANCE: "factor_2_us_dominance",
	GROWTH_VS_DEFENSIVE: "factor_3_growth_vs_defensive",
} as const;

/**
 * Regularized PCA: Extract latent factors from sector returns
 *
 * The key insight from the paper:
 * - 28 sectors (11 US + 17 JP) have return patterns that are NOT independent
 * - Instead, they are driven by a small number of common factors:
 *   1. Risk-on/off sentiment (global)
 *   2. US dominance vs Japan dominance
 *   3. Cyclical (growth) vs Defensive sectors
 *
 * Standard PCA with small sample size (time steps) vs large dim (sectors) leads to
 * noisy correlation matrix estimation. Regularized PCA stabilizes by mixing in
 * prior knowledge (Tikhonov regularization on the Gram matrix).
 */
export class RegularizedPCA {
	private nComponents: number;
	private regularizationAlpha: number;
	private maxIterations: number;

	constructor(
		nComponents: number = 3,
		regularizationAlpha: number = 0.1,
		maxIterations: number = 100,
	) {
		this.nComponents = nComponents;
		this.regularizationAlpha = regularizationAlpha;
		this.maxIterations = maxIterations;
	}

	/**
	 * Fit regularized PCA on the input matrix (T x D):
	 * T = number of time steps, D = number of sectors
	 *
	 * Returns:
	 * - components: (nComponents x D) - the principal axes
	 * - scores: (T x nComponents) - the latent factor scores per time step
	 * - varianceExplained: (nComponents,) - variance explained by each component
	 */
	fit(matrix: number[][]): {
		components: number[][];
		scores: number[][];
		varianceExplained: number[];
	} {
		const T = matrix.length; // Number of time steps
		if (T === 0) {
			return { components: [], scores: [], varianceExplained: [] };
		}
		const D = matrix[0].length; // Number of sectors

		// Step 1: Standardize the input matrix
		const mean = this.columnMean(matrix);
		const std = this.columnStd(matrix, mean);
		const X = this.standardize(matrix, mean, std);

		// Step 2: Compute Gram matrix with regularization
		// Gram = X^T X / T (empirical covariance)
		const gram = this.computeGram(X);

		// Regularization: Gram_reg = (1 - alpha) * Gram + alpha * I
		// This mixes the empirical covariance with identity (uncorrelated assumption)
		const gramReg = this.regularizeMatrix(gram, this.regularizationAlpha);

		// Step 3: Power iteration to extract top nComponents eigenvectors
		const { eigenvectors, eigenvalues } = this.powerIteration(
			gramReg,
			this.nComponents,
			this.maxIterations,
		);

		// Step 4: Compute PCA scores: X @ eigenvectors
		const scores = this.matmul(X, eigenvectors);

		// Step 5: Variance explained
		const totalVariance = eigenvalues.reduce((a, b) => a + b, 0);
		const varianceExplained = eigenvalues.map((eig) => eig / totalVariance);

		return {
			components: eigenvectors,
			scores,
			varianceExplained,
		};
	}

	private columnMean(matrix: number[][]): number[] {
		const D = matrix[0].length;
		const mean = new Array(D).fill(0);

		for (let j = 0; j < D; j++) {
			let sum = 0;
			for (let i = 0; i < matrix.length; i++) {
				sum += matrix[i][j];
			}
			mean[j] = sum / matrix.length;
		}

		return mean;
	}

	private columnStd(matrix: number[][], mean: number[]): number[] {
		const D = matrix[0].length;
		const std = new Array(D).fill(0);

		for (let j = 0; j < D; j++) {
			let sumSq = 0;
			for (let i = 0; i < matrix.length; i++) {
				const diff = matrix[i][j] - mean[j];
				sumSq += diff * diff;
			}
			std[j] = Math.sqrt(sumSq / (matrix.length - 1));
		}

		return std;
	}

	private standardize(
		matrix: number[][],
		mean: number[],
		std: number[],
	): number[][] {
		return matrix.map((row) =>
			row.map((val, j) => (val - mean[j]) / (std[j] || 1)),
		);
	}

	private computeGram(X: number[][]): number[][] {
		const T = X.length;
		const D = X[0].length;

		const gram: number[][] = Array.from({ length: D }, () =>
			new Array(D).fill(0),
		);

		for (let i = 0; i < D; i++) {
			for (let j = 0; j < D; j++) {
				let sum = 0;
				for (let t = 0; t < T; t++) {
					sum += X[t][i] * X[t][j];
				}
				gram[i][j] = sum / T;
			}
		}

		return gram;
	}

	private regularizeMatrix(gram: number[][], alpha: number): number[][] {
		const D = gram.length;
		const regulated = gram.map((row) => [...row]);

		for (let i = 0; i < D; i++) {
			for (let j = 0; j < D; j++) {
				if (i === j) {
					regulated[i][j] = (1 - alpha) * gram[i][j] + alpha * 1.0;
				} else {
					regulated[i][j] = (1 - alpha) * gram[i][j];
				}
			}
		}

		return regulated;
	}

	private powerIteration(
		matrix: number[][],
		k: number,
		maxIter: number,
	): { eigenvectors: number[][]; eigenvalues: number[] } {
		const D = matrix.length;
		const eigenvectors: number[][] = [];
		const eigenvalues: number[] = [];

		let A = matrix.map((row) => [...row]);

		for (let comp = 0; comp < k; comp++) {
			// Initialize random vector
			let v = new Array(D).fill(0).map(() => Math.random() - 0.5);
			v = this.normalize(v);

			// Power iteration
			for (let iter = 0; iter < maxIter; iter++) {
				const Av = this.matvec(A, v);
				const lambda = this.dot(v, Av);
				v = this.normalize(Av);

				const residual = this.norm(this.sub(Av, this.scale(v, lambda)));
				if (residual < 1e-6) break;
			}

			const Av = this.matvec(A, v);
			const lambda = this.dot(v, Av);

			eigenvectors.push(v);
			eigenvalues.push(Math.max(lambda, 0));

			// Deflate: A = A - lambda * v * v^T
			A = this.deflate(A, v, lambda);
		}

		return { eigenvectors, eigenvalues };
	}

	private normalize(v: number[]): number[] {
		const norm = Math.sqrt(v.reduce((a, b) => a + b * b, 0));
		return v.map((x) => x / (norm || 1));
	}

	private matvec(matrix: number[][], v: number[]): number[] {
		return matrix.map((row) =>
			row.reduce((sum, val, j) => sum + val * v[j], 0),
		);
	}

	private dot(v1: number[], v2: number[]): number {
		return v1.reduce((sum, val, i) => sum + val * v2[i], 0);
	}

	private norm(v: number[]): number {
		return Math.sqrt(v.reduce((sum, val) => sum + val * val, 0));
	}

	private scale(v: number[], scalar: number): number[] {
		return v.map((x) => x * scalar);
	}

	private sub(v1: number[], v2: number[]): number[] {
		return v1.map((x, i) => x - v2[i]);
	}

	private deflate(matrix: number[][], v: number[], lambda: number): number[][] {
		const D = matrix.length;
		const result = matrix.map((row) => [...row]);

		for (let i = 0; i < D; i++) {
			for (let j = 0; j < D; j++) {
				result[i][j] -= lambda * v[i] * v[j];
			}
		}

		return result;
	}

	private matmul(A: number[][], B: number[][]): number[][] {
		const T = A.length;
		const D = B.length;
		const K = B[0].length;

		const result: number[][] = Array.from({ length: T }, () =>
			new Array(K).fill(0),
		);

		for (let i = 0; i < T; i++) {
			for (let j = 0; j < K; j++) {
				let sum = 0;
				for (let k = 0; k < D; k++) {
					sum += A[i][k] * B[k][j];
				}
				result[i][j] = sum;
			}
		}

		return result;
	}
}

/**
 * Generate spillover signals for JP sectors based on US latent factors
 *
 * Strategy:
 * 1. Extract latent factors from US sector returns (via regularized PCA)
 * 2. Map these factors to JP sector signals
 * 3. Classify as LONG (top 30%), NEUTRAL (middle 40%), SHORT (bottom 30%)
 */
export function generateSpilloverSignals(
	usScores: number[][],
	jpSectors: string[],
	usToJpMapping: Record<string, string[]>, // Which US sectors influence which JP sectors
): SectorSpilloverSignal[] {
	if (usScores.length === 0 || usScores[0].length === 0) {
		return []; // No data available
	}

	const latestUSScores = usScores[usScores.length - 1]; // Last day's factor scores
	const date = new Date().toISOString().split("T")[0];

	const signals: SectorSpilloverSignal[] = jpSectors.map((jpSector) => {
		const sector = jpSector as JP17Sectors;
		// Aggregate US factor influence on this JP sector
		const influencingUSSectors = usToJpMapping[jpSector] || [];
		const aggregatedScore =
			influencingUSSectors.length > 0
				? influencingUSSectors.reduce(
						(sum, _, idx) => sum + (latestUSScores[idx] || 0),
						0,
					) / influencingUSSectors.length
				: 0;

		// Normalize score to [-1, 1]
		const normalizedScore = Math.tanh(aggregatedScore);

		// Classify signal
		const long_threshold = config.sector_spillover?.signal?.long_threshold ?? 0.33;
		const short_threshold = config.sector_spillover?.signal?.short_threshold ?? -0.33;
		let signalType: "long" | "neutral" | "short";
		if (normalizedScore > long_threshold) {
			signalType = "long";
		} else if (normalizedScore < short_threshold) {
			signalType = "short";
		} else {
			signalType = "neutral";
		}

		return {
			date,
			jp_sector: sector,
			signal_score: normalizedScore,
			signal_type: signalType,
			confidence: Math.abs(normalizedScore),
			us_factor_contributions: {
				[FACTOR_NAMES.RISK_SENTIMENT]: latestUSScores[0] ?? 0,
				[FACTOR_NAMES.US_DOMINANCE]: latestUSScores[1] ?? 0,
				[FACTOR_NAMES.GROWTH_VS_DEFENSIVE]: latestUSScores[2] ?? 0,
			},
		};
	});

	return signals;
}

/**
 * Default US to JP sector mapping (simplified)
 * In practice, this should be calibrated based on industry classification
 */
export function getDefaultUSToJPMapping(): Record<string, string[]> {
	// Simplified: map each JP sector to multiple US sectors based on industry correlation
	const mapping: Record<string, string[]> = {};

	const jpSectors = config.sector_spillover?.jp_sectors ?? [];
	const usSectors = config.sector_spillover?.us_sectors ?? [];

	// For each JP sector, assign influence from related US sectors
	// This is a simplified heuristic; in production, use correlation analysis
	const sectorMap: Record<string, number[]> = {
		"1000": [0, 2], // 水産・農林 <- energy, industrials
		"2000": [0, 1], // 鉱業 <- energy, materials
		"3000": [2, 7], // 建設 <- industrials, IT
		"4000": [3, 4], // 食料 <- consumer_discretionary, consumer_staples
		"5000": [3, 4], // 繊維 <- consumer_discretionary, consumer_staples
		"6000": [2], // 紙・パルプ <- industrials
		"7000": [1, 7], // 化学 <- materials, IT
		"8000": [5], // 医薬 <- healthcare
		"9000": [0], // 石油 <- energy
		"10000": [2], // ゴム <- industrials
		"11000": [1, 2], // ガラス <- materials, industrials
		"12000": [1, 2], // 鉄鋼 <- materials, industrials
		"13000": [1], // 非鉄金属 <- materials
		"14000": [2], // 金属製品 <- industrials
		"15000": [2, 7], // 機械 <- industrials, IT
		"16000": [7], // 電気機器 <- IT
		"17000": [2, 7], // 輸送用機器 <- industrials, IT
	};

	for (const [jpCode, usIndices] of Object.entries(sectorMap)) {
		mapping[jpCode] = usIndices.map((idx) => usSectors[idx]);
	}

	return mapping;
}
