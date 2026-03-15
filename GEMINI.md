Achieve the goal with MINIMAL changes. Extra changes introduce extra bugs and slow review. NO comments in code. Good code reads itself; comments rot and mislead. Respond clearly, specifically, and concisely. Vague answers waste time and create misunderstanding.

# No Safety Nets
NEVER write defensive code. NO error handling, NO dummy code, NO try-catch. Defensive code hides bugs and delays discovery. Focus on making the main logic succeed.
- Build the minimal thing, run it, and let it crash. Real failures teach faster than hypothetical planning.
- Implement the smallest possible structure and EXECUTE IMMEDIATELY. Speed of iteration beats depth of speculation.
- A crash is NOT a problem — it is design feedback. NEVER fear execution. Fear of running code leads to over-engineering.
- Follow the strict cycle: CRASH → IDENTIFY ROOT CAUSE → MINIMAL FIX. Repeat relentlessly. Each cycle sharpens understanding of the actual system.
- REJECT upfront over-engineering. Only real failures dictate real improvements. Imagined edge cases produce imagined solutions.
- READ every crash log and traceback with absolute precision. Fix the ROOT CAUSE, not the symptom. Symptom fixes guarantee repeat failures.

# Project Structure Rules
Always consider proper directory structure. Disorganized layout makes code hard to find and responsibilities unclear.
- Taskfile.yml is the CLI. All executable operations MUST be defined as Taskfile tasks. Direct script invocation is forbidden. A single entry point keeps execution discoverable and reproducible.
- **TS/Bun**: ALWAYS use `bun` to run scripts. ALL dependencies MUST be managed via `package.json` and `bun install`. No direct `node` invocation, no ad-hoc installs. **Python**: ALWAYS use `uv run`. ALL dependencies via `pyproject.toml`. No `pip install`, no `requirements.txt`.
- src/domain/* holds ALL domain logic. Business rules, models, and core computations live here exclusively. Scattering domain logic across layers makes it untestable and hard to reason about.
- src/io/* holds ALL data input/output. File reads, API calls, database access, and any external data exchange live here exclusively. Isolating I/O from domain logic keeps the core pure and testable.
- config/default.yaml is the SINGLE source of configuration. No hardcoded values, no scattered config files. One config file means one place to look, one place to change.
- Agent skills are managed via `agr` (agent-resources). Use `agr add` to install, `agr.toml` to track dependencies, and `agr sync` to reproduce environments. Manual skill file management leads to inconsistency across machines and team members.

# Code Quality Rules
- Run linters and type checkers before every commit via Taskfile tasks. **TS/Bun**: `tsc --noEmit` + `eslint src`. **Python**: `ruff check` + `ruff format` + `uv run ty check`. Automated checks catch style drift and type errors before review.
- Use schema-validated models for ALL data structures. **TS/Bun**: Use Zod. No plain objects or `any`. **Python**: Use Pydantic. No dataclasses or plain dicts. Validation at the boundary makes schemas explicit and failures loud.
- Use higher-order functions or decorators to share cross-cutting concerns (logging, timing, caching). Duplicating boilerplate across functions invites inconsistency; centralizing behavior keeps it consistent.

# Frontend Rules
- Keep it simple HTML. No frameworks unless explicitly required. Plain HTML is fast to write, easy to debug, and has zero build overhead.
- Serve and develop via `task dev`. Frontend dev workflow MUST go through Taskfile like everything else. Separate dev commands fragment knowledge and break onboarding.
