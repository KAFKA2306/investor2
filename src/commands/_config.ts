import { readFileSync } from "node:fs";
import yaml from "js-yaml";
import { ConfigSchema } from "../shared/schema";

export const config = ConfigSchema.parse(
	yaml.load(readFileSync("config/default.yaml", "utf-8")),
);
