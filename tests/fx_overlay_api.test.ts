import { readFileSync } from "node:fs";
import { expect, test } from "bun:test";

test("publishes one fail-closed canonical FX overlay API artifact", () => {
  const artifact = JSON.parse(
    readFileSync(
      new URL("../api/v1/portfolio/fx-overlay.json", import.meta.url),
      "utf8",
    ),
  );

  expect(artifact).toEqual({
    schema_version: "investor2.fx-overlay.v1",
    status: "UNVERIFIED",
    reason:
      "Live portfolio recommendation is unavailable: canonical realized daily swap history required by investor2#251 and the actual portfolio position snapshot required by investor2#252 are not yet materialized.",
  });
});
