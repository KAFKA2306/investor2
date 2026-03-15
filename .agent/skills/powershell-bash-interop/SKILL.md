---
name: powershell-bash-interop
description: >
  MANDATORY TRIGGER: Invoke for any task that executes Bash from PowerShell
  (especially via wsl/bash -lc) where $, $(...), here-docs, redirections, or
  nested quoting may be interpreted by PowerShell first. If command behavior
  differs between direct Bash and PowerShell-launched Bash, this skill must be
  used before retrying.
---

# PowerShell Bash Interop Skill

## Objective
Prevent PowerShell from mutating Bash syntax.

## Hard Rules
- Do not embed complex Bash directly in PowerShell double-quoted command strings because PowerShell will attempt to interpolate variables like `$HOME` or `$(...)` before passing them to Bash.
- Do not rely on backslash escaping for Bash `$` in PowerShell because nested escaping rules are inconsistent across PowerShell versions and lead to "broken" shell scripts.
- Do not keep Bash `$(...)` substitutions inside PowerShell-parsed strings because the outer shell will execute the substitution locally instead of inside the target environment.
- For multi-line Bash, always write a script file first and execute it from WSL because file-based handoff avoids all shell-quoting edge cases and provides a clean audit trail.

## Safe Patterns

### Pattern A: Script file handoff (default)
1. Build script with a PowerShell single-quoted here-string.
2. Write to `\\wsl.localhost\Ubuntu-22.04-LTS\tmp\<name>.sh` in UTF-8.
3. Run with `wsl -d <distro> bash /tmp/<name>.sh`.

Template:
```powershell
$script = @'
#!/usr/bin/env bash
set -euo pipefail
cd /path/to/repo
# Bash code with $, $(...), here-docs, pipes, redirects
'@
Set-Content -Path '\\wsl.localhost\Ubuntu-22.04-LTS\tmp\run.sh' -Value $script -Encoding utf8
wsl -d Ubuntu-22.04-LTS bash /tmp/run.sh
```

### Pattern B: Single simple command only
Use only when no Bash variables, no command substitution, and no here-doc.

Template:
```powershell
wsl -d Ubuntu-22.04-LTS bash -lc 'cd /path && ls -la'
```

## Failure Signatures and Fix
1. `seq : The term 'seq' is not recognized`
- Cause: PowerShell evaluated Bash `$(seq ...)`.
- Fix: move command to script file handoff.

2. `syntax error near unexpected token '2'`
- Cause: quoting/redirection was broken before Bash execution.
- Fix: run through script file handoff.

3. here-doc delimiter warning or unexpected EOF
- Cause: outer shell parsed delimiter or body.
- Fix: keep here-doc only inside handed-off Bash script.

## Done Criteria
- Command reruns produce consistent behavior.
- No PowerShell-side parse/interpolation error appears.
