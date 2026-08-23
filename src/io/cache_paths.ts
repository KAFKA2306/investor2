import { resolve } from "node:path";

export function cachePaths(cacheRoot: string) {
  return {
    marketsPolymarket: resolve(cacheRoot, "markets/polymarket.sqlite"),
    marketsJquants: resolve(cacheRoot, "markets/jquants.sqlite"),
    marketsYahoo: resolve(cacheRoot, "markets/yahoo.sqlite"),
    fundamentalJquants: resolve(cacheRoot, "fundamental/jquants_fin.sqlite"),
    fundamentalEdinet: resolve(cacheRoot, "fundamental/edinet.sqlite"),
    macroEstat: resolve(cacheRoot, "macro/estat.sqlite"),
    macroFred: resolve(cacheRoot, "macro/fred.sqlite"),
    webSearch: resolve(cacheRoot, "websearch/tavily.sqlite"),
  } as const;
}
