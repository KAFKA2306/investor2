---
name: harness-quality-pipeline
description: Deploy comprehensive quality pipeline with hooks (format → lint → architecture check → CDD validation). Enforce layer boundaries and prevent defensive code patterns automatically. Use when setting up project quality gates, integrating linters with auto-fix, protecting architectural boundaries, or preventing AI-generated anti-patterns.
---

# Harness Quality Pipeline Skill

Comprehensive automated quality assurance system with:
- **PreToolUse Hook** — Config protection (prevent agent tampering)
- **PostToolUse Hook** — Full pipeline (format → lint → architecture → CDD)
- **Architecture Rules** — Layer boundary enforcement (ast-grep)
- **CDD Validation** — Prevent defensive code patterns

---

## When to Use

✅ Use when:
- Setting up project quality gates
- Integrating linters with auto-fix hooks
- Enforcing architectural boundaries (domain ≠ IO)
- Preventing AI-generated anti-patterns (try-catch, mock, null returns)
- Protecting config files from agent tampering

❌ Don't use:
- For simple linting (use Biome directly)
- For one-off code cleanup
- If you just need type checking (use tsc)

---

## What Gets Deployed

### Files Created
1. `.agent/hooks/pre-tool-use.mjs` — Config protection
2. `.agent/hooks/post-tool-use-enhanced.mjs` — Full quality pipeline
3. `.agent/hooks/post-tool-use.sh` — Bash wrapper
4. `.ast-grep-rule.yaml` — Architecture rules
5. `scripts/quality-check.sh` — Manual integration script

### Configuration Added
- Hooks automatically invoked by Claude Code on file edits
- PreToolUse blocks protected files (biome.json, tsconfig.json, etc.)
- PostToolUse runs format → lint → architecture → CDD checks

---

## How It Works

### Phase 1: Auto-Format (Biome)
```
Input: Changed TypeScript files
↓
Process: biome format --write <file>
↓
Output: 40-50% of issues auto-fixed (indentation, spacing, etc.)
Speed: <100ms per file
```

### Phase 2: Lint (Biome)
```
Input: Formatted files
↓
Process: biome lint <file>
↓
Detects: Unused vars, style inconsistencies, undefined references
Output: Blocking errors + warnings
```

### Phase 3: Architecture Check (ast-grep)
```
Input: All changed files
↓
Enforces:
  • Domain cannot import IO/providers/DB
  • Business logic: no try-catch
  • No defensive returns (null/undefined/[]/{}）
  • No mock/stub/fake declarations
↓
Output: Layer boundary violations
```

### Phase 4: CDD Check
```
Input: Logic layer files
↓
Detects:
  • Math.random() in deterministic code
  • Defensive || patterns
  • Hardcoded paths
↓
Output: CDD violations
```

### Config Protection (PreToolUse)
```
Agent tries to edit: biome.json
     ↓
Hook intercepts
     ↓
Message: "Fix code, not config"
     ↓
Edit blocked (exit code 2)
```

---

## Quick Start

### 1. Copy Hooks to Project
```bash
mkdir -p .agent/hooks
cp -v pre-tool-use.mjs post-tool-use-enhanced.mjs .agent/hooks/
chmod +x .agent/hooks/*.mjs
```

### 2. Copy Rules
```bash
cp -v .ast-grep-rule.yaml .
```

### 3. Install Tools (if needed)
```bash
# Biome (usually already installed)
npm install -D @biomejs/biome

# ast-grep for architecture rules
npm install -g @ast-grep/cli
# or
cargo install ast-grep
```

### 4. Test Locally
```bash
# Manual quality check
bash scripts/quality-check.sh

# Or invoke hook directly
node .agent/hooks/post-tool-use-enhanced.mjs
```

---

## Customization

### Add Protected Config Files
Edit `.agent/hooks/pre-tool-use.mjs`:
```javascript
const PROTECTED_CONFIGS = [
  "biome.json",
  "your-config.json",  // ← Add here
  // ...
];
```

### Add Architecture Rules
Edit `.ast-grep-rule.yaml`:
```yaml
rules:
  - id: custom-rule
    pattern: |
      [pattern here]
    message: "Custom violation"
    severity: error
```

### Adjust Lint Settings
Edit `ts-agent/biome.json`:
```json
{
  "linter": {
    "rules": {
      "recommended": true,
      "custom": { "level": "warn" }
    }
  }
}
```

---

## Anti-Patterns Detected

| Pattern | Severity | Why Blocked |
|---------|----------|-------------|
| `try-catch` in agents | ERROR | CDD: let exceptions propagate |
| `return null` in logic | ERROR | Defensive: throw instead |
| `\|\| defaults` | ERROR | Defensive: explicit error handling |
| `mock/stub/fake` declarations | ERROR | Use real data in production |
| `Math.random()` | ERROR | Non-deterministic in quant logic |
| Domain imports IO | ERROR | Architecture: violates boundaries |
| Console.log in agents | WARNING | Use logger for structure |
| Hardcoded paths | ERROR | Use PathRegistry for portability |

---

## Integration with Claude Code

Hooks are automatically triggered:
- **On Write** — PostToolUse runs after creating files
- **On Edit** — PreToolUse checks before edit, PostToolUse after
- **On MultiEdit** — Runs for each file in batch

If hooks don't run:
1. Verify files are executable: `chmod +x .agent/hooks/*.mjs`
2. Restart Claude Code session
3. Check `.agent/hooks/` exists and is readable

---

## Troubleshooting

### "biome not found"
```bash
npm install -D @biomejs/biome
which biome  # should return path
```

### "ast-grep not found"
```bash
npm install -g @ast-grep/cli
# or use locally:
# npx ast-grep --version
```

### Hooks not triggering
```bash
# Check permissions
ls -la .agent/hooks/

# Should show:
# -rwxr-xr-x pre-tool-use.mjs
# -rwxr-xr-x post-tool-use-enhanced.mjs

# If not executable, fix:
chmod +x .agent/hooks/*.mjs
```

### Too many false positives
Edit hook to adjust regex patterns:
```javascript
// Make patterns more specific
const pattern = /^const\s+\w*mock\w*\s*=/; // More strict
```

---

## Performance

| Phase | Tool | Time |
|-------|------|------|
| Format | Biome | <100ms |
| Lint | Biome | 200-500ms |
| Architecture | ast-grep | 1-2s |
| CDD | Node regex | <50ms |
| **Total** | — | **~2s** |

Target: Full pipeline completes in <2 seconds per commit.

---

## References

- [Biome Linter](https://biomejs.dev/)
- [ast-grep Documentation](https://ast-grep.github.io/)
- [Claude Code Hooks](https://claude.com/docs/claude-code)
- [Crash-Driven Development (CDD)](https://zenn.dev/kafka2306/articles/11cd731eebded1)

---

## Next Steps

1. **Deploy** — Run `bash scripts/quality-check.sh` to test
2. **Monitor** — Watch hook output for violations
3. **Fix** — Address reported issues before committing
4. **Iterate** — Add custom rules as team patterns emerge

