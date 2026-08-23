from pathlib import Path

SERVER = Path("src/dashboard/server.ts")
SCHEMAS = Path("src/schemas.ts")
CONFIG = Path("config/default.yaml")
SELF = Path("scripts/remove_historical_dashboard_compat.py")
WORKFLOW = Path(".github/workflows/remove-historical-dashboard-compat.yml")


def remove_exact_once(text: str, needle: str, label: str) -> str:
    count = text.count(needle)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label}, found {count}")
    return text.replace(needle, "", 1)


server = SERVER.read_text()
for needle, label in [
    ('import { BacktestCache } from "../io/backtest_cache";\n', "BacktestCache import"),
    ('import type { PipelineResultsReport } from "../schemas";\n', "PipelineResultsReport import"),
    ('import { backtestResultsHtml } from "./backtest_results_template";\n', "backtest template import"),
]:
    server = remove_exact_once(server, needle, label)

lines = server.splitlines(keepends=True)
removed_pipeline_links = sum('href="/pipeline/results"' in line for line in lines)
removed_backtest_links = sum('href="/backtest/results"' in line for line in lines)
if removed_pipeline_links == 0 or removed_backtest_links == 0:
    raise RuntimeError(
        f"expected dashboard navigation links, got pipeline={removed_pipeline_links}, "
        f"backtest={removed_backtest_links}"
    )
server = "".join(
    line
    for line in lines
    if 'href="/pipeline/results"' not in line
    and 'href="/backtest/results"' not in line
)

start_marker = "// AAARTS Pipeline Results Dashboard Routes"
end_marker = "interface ReferenceLink {"
if server.count(start_marker) != 1 or server.count(end_marker) != 1:
    raise RuntimeError("historical dashboard route boundary changed")
start = server.index(start_marker)
end = server.index(end_marker)
if start >= end:
    raise RuntimeError("invalid historical dashboard route boundary")
server = server[:start] + server[end:]
SERVER.write_text(server)

config = CONFIG.read_text()
config_line = "  cacheBacktestResults: /mnt/d/investor_all_cached_data/cache/backtest/results.sqlite\n"
config = remove_exact_once(config, config_line, "cacheBacktestResults config")
CONFIG.write_text(config)

schemas = SCHEMAS.read_text()
schema_path_line = "        cacheBacktestResults: z.string(),\n"
schemas = remove_exact_once(schemas, schema_path_line, "cacheBacktestResults schema path")
legacy_marker = "export const StandardOutcomeSchema"
if schemas.count(legacy_marker) != 1:
    raise RuntimeError("legacy schema boundary changed")
legacy_start = schemas.index(legacy_marker)
schemas = schemas[:legacy_start].rstrip() + "\n"
SCHEMAS.write_text(schemas)

for dead_file in [
    Path("src/io/backtest_cache.ts"),
    Path("src/dashboard/backtest_results_template.ts"),
]:
    if not dead_file.exists():
        raise RuntimeError(f"expected legacy file missing: {dead_file}")
    dead_file.unlink()

# Temporary scaffolding must not survive into the resulting branch diff.
WORKFLOW.unlink(missing_ok=True)
SELF.unlink(missing_ok=True)
