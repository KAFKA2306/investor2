import { readFileSync } from "node:fs";
import {
	DecisionSnapshotSchema,
	evaluateEntryEligibility,
} from "../decision/decision_snapshot";

const path = Bun.argv[2];

if (!path) {
	console.error("usage: bun src/commands/decision_check.ts <snapshot.json>");
	process.exit(1);
}

try {
	const parsed = JSON.parse(readFileSync(path, "utf8"));
	const snapshot = DecisionSnapshotSchema.parse(parsed);
	const result = evaluateEntryEligibility(snapshot);

	console.log(
		JSON.stringify(
			{
				decision_id: snapshot.decision_id,
				proposed_action: snapshot.proposed_action,
				...result,
			},
			null,
			2,
		),
	);

	if (
		(snapshot.proposed_action === "buy" || snapshot.proposed_action === "add") &&
		!result.eligible_for_human_review
	) {
		process.exitCode = 2;
	}
} catch (error) {
	console.error(error instanceof Error ? error.message : String(error));
	process.exitCode = 1;
}
