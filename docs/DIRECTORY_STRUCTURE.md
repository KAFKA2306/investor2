# Directory Structure (v2)

## Explicit, Self-Documenting Organization

All files in `src/` are organized into **exactly one subdirectory level**:

### `src/dashboard/`
**Purpose**: Investor-facing web dashboard application
- `investor_dashboard_server.ts` - Web server (Hono + HTMX + Tailwind)

### `src/commands/`
**Purpose**: Command-line tasks (executed via `task` CLI)
- `print_cache_statistics.ts` - Display cache overview
- `sync_edinet_companies.ts` - Fetch all EDINET company documents
- `sync_jquants_latest_prices.ts` - Fetch latest 2-year market data

### `src/shared/`
**Purpose**: Shared schemas and utilities
- `schemas.ts` - Zod schemas and type definitions
- `index.ts` - Shared exports

### `src/context/`, `src/io/`, `src/system/`, `src/db/`
**Purpose**: Existing domain-specific modules
- Not modified in this refactor

## Naming Convention

**Directory names**: Clear, plural nouns describing *what is inside*
- `dashboard/` contains dashboard code
- `commands/` contains CLI commands
- `shared/` contains shared modules

**File names**: Imperative verb phrases describing *what it does*
- `investor_dashboard_server.ts` - "server for investor dashboard"
- `print_cache_statistics.ts` - "print cache statistics"
- `sync_edinet_companies.ts` - "sync EDINET companies"
- `sync_jquants_latest_prices.ts` - "sync J-Quants latest prices"

All names are **self-documenting** and **unambiguous**.
