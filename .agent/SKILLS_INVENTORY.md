# Skills Inventory

All 31 skills in `.agent/skills/` are ECC SKILL.md template compliant.

## Compliance Criteria

Each skill must have:
- **Frontmatter**: `name`, `description`, `origin` fields
- **4 required sections**: Core Concepts, Code Examples, Best Practices, When to Use

## Inventory

| # | Skill | Origin | Frontmatter | Core Concepts | Code Examples | Best Practices | When to Use | Status |
|---|-------|--------|-------------|---------------|---------------|----------------|-------------|--------|
| 1 | `alpha-mining` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 2 | `claude-expertise-bridge` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 3 | `edinet` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 4 | `edinet-dataset-builder` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 5 | `env-management` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 6 | `fail-fast-coding-rules` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 7 | `finmcp-analyst-workflows` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 8 | `fred-economic-data` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 9 | `frontend-design` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 10 | `fundamental-analysis` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 11 | `harness-governance` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 12 | `harness-quality-pipeline` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 13 | `market-intelligence` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 14 | `mixseek-backtest-engine` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 15 | `mixseek-competitive-framework` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 16 | `mixseek-data-pipeline` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 17 | `mixseek-ranking-scoring` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 18 | `polymarket` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 19 | `polymarket-alpha-miner` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 20 | `polymarket-data-validation` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 21 | `powershell-bash-interop` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 22 | `qlib-investor-integration` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 23 | `qwen-local-inference` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 24 | `schema-management` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 25 | `system-ops` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 26 | `trading-strategies` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 27 | `typescript-agent-skills` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 28 | `vllm-io` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 29 | `vllm-qwen-agent-integration` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 30 | `web-ai-bridge` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |
| 31 | `where-to-save` | local-git-analysis | OK | OK | OK | OK | OK | COMPLIANT |

## Validation Command

```bash
python3 -c "
import glob, re
required = ['Core Concepts', 'Code Examples', 'Best Practices', 'When to Use']
for path in sorted(glob.glob('.agent/skills/*/SKILL.md')):
    with open(path) as f: content = f.read().lstrip('\ufeff')
    fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    sections = [s.lower() for s in re.findall(r'^## (.+)$', content, re.MULTILINE)]
    ok = fm and all(k in fm.group(1) for k in ['name:','description:','origin:'])
    ok = ok and all(any(r.lower() in s for s in sections) for r in required)
    name = path.split('/')[2]
    print(f'  {\"PASS\" if ok else \"FAIL\"} {name}')
"
```
