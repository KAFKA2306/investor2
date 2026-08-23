from pathlib import Path

server_path = Path("src/dashboard/server.ts")
self_path = Path("scripts/remove_dashboard_dead_code.py")
workflow_path = Path(".github/workflows/remove-dashboard-dead-code.yml")

text = server_path.read_text()

old_import = 'import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";\n'
new_import = 'import { existsSync, readFileSync } from "node:fs";\n'
if text.count(old_import) != 1:
    raise RuntimeError("unexpected node:fs import")
text = text.replace(old_import, new_import, 1)

start_marker = "function getFileSize(path: string): number {"
end_marker = "async function getStats(): Promise<CacheStatistics> {"
if text.count(start_marker) != 1 or text.count(end_marker) != 1:
    raise RuntimeError("dashboard dead-code boundary changed")
start = text.index(start_marker)
end = text.index(end_marker)
if start >= end:
    raise RuntimeError("invalid dashboard dead-code boundary")
text = text[:start] + text[end:]

old_output = "    const _output = await new Response(proc.stdout).text();\n"
new_output = "    await new Response(proc.stdout).text();\n"
if text.count(old_output) != 1:
    raise RuntimeError("unexpected refresh output statement")
text = text.replace(old_output, new_output, 1)

server_path.write_text(text)
workflow_path.unlink(missing_ok=True)
self_path.unlink(missing_ok=True)
