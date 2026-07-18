import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
	EvidenceStateSchema,
	GateStatusSchema,
	LifecycleDecisionSchema,
	StrategyRegistrySchema,
} from "../src/ontology";

const registryPath = resolve("docs/research/strategy_registry.json");

describe("AAARTS ontology", () => {
	test("keeps gate, evidence, and lifecycle states distinct", () => {
		expect(GateStatusSchema.parse("NOT_RUN")).toBe("NOT_RUN");
		expect(EvidenceStateSchema.parse("NOT_CONFIRMED")).toBe("NOT_CONFIRMED");
		expect(LifecycleDecisionSchema.parse("PIVOT")).toBe("PIVOT");
		expect(() => EvidenceStateSchema.parse("UNVERIFIED")).toThrow();
	});

	test("parses the committed strategy registry", () => {
		const registry = JSON.parse(readFileSync(registryPath, "utf8"));
		const parsed = StrategyRegistrySchema.parse(registry);

		expect(parsed.strategy_genomes.length).toBeGreaterThanOrEqual(7);
		expect(parsed.evidence_artifacts.length).toBe(
			parsed.strategy_genomes.length,
		);
		expect(parsed.portfolio_candidates).toHaveLength(0);
	});
});
