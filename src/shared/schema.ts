import { z } from "zod";

export const ConfigSchema = z.object({
	project: z.object({
		name: z.string(),
	}),
	paths: z.object({
		data: z.string(),
		logs: z.string(),
		verification: z.string(),
		cache: z.string(),
		edinet: z.string(),
		preprocessed: z.string(),
		cacheFundamentalEdinet: z.string(),
		cacheMarketsPolymarket: z.string(),
		cacheMarketsJquants: z.string(),
		cacheMarketsYahoo: z.string(),
		cacheFundamentalJquants: z.string(),
		cacheMacroEstat: z.string(),
		cacheMacroFred: z.string().optional(),
		macroFred: z.string().optional(),
	}),
	polymarket: z.object({
		clob_url: z.string(),
	}),
});

export type Config = z.infer<typeof ConfigSchema>;
