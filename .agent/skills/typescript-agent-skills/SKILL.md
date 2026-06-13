---
name: typescript-agent-skills
description: >
  Use when adding, modifying, or calling TypeScript runtime skills that agents
  invoke via `this.useSkill()`. Covers the skill registry, interface definition,
  built-in skills, and the distinction from Claude Code markdown skills.
origin: local-git-analysis
---

# TypeScript Runtime Skill System

## When to Use
Use for tasks related to TypeScript agent skills.

## Core Concepts

| Type | Location | Purpose |
|---|---|---|
| **Claude Code Skill** | `.agent/skills/<name>/SKILL.md` | Guidance for Claude Code to read (markdown) |
| **TypeScript Runtime Skill** | `ts-agent/src/skills/` | Code the agent calls at runtime |

This SKILL.md handles the latter (TypeScript Runtime Skill).

## File Structure

```
ts-agent/src/skills/
├── types.ts          ← Skill<TInput, TOutput> interface
├── registry.ts       ← SkillRegistry singleton
├── index.ts          ← Registered built-in skills (side-effect import)
└── builtin/
    └── validate_qlib_formula.ts  ← qlib expression syntax validation skill
```

## Skill Interface

```typescript
import type { z } from "zod";

export interface Skill<TInput, TOutput> {
  name: string;
  description: string;  // Used for explanations to the LLM and log output
  schema: z.ZodType<TInput>;
  execute(args: TInput): Promise<TOutput>;
}
```

## Code Examples

```typescript
// Within an agent that inherits from BaseAgent
const result = await this.useSkill<{ formula: string }, { valid: boolean; error?: string }>(
  "validate_qlib_formula",
  { formula: "Mean($close,20)/Mean($close,5)-1" }
);
```

## Steps to Add a New Skill

1. Create `ts-agent/src/skills/builtin/<skill_name>.ts`
2. Define the input type with a Zod schema
3. Implement `Skill<Input, Output>` and export it
4. Add `skillRegistry.register(...)` in `ts-agent/src/skills/index.ts`

```typescript
// Example of builtin/my_skill.ts
import { z } from "zod";
import type { Skill } from "../types.ts";

const inputSchema = z.object({ value: z.string() });
type Input = z.infer<typeof inputSchema>;
type Output = { result: string };

export const mySkill: Skill<Input, Output> = {
  name: "my_skill",
  description: "Description of what this skill does.",
  schema: inputSchema,
  execute: async ({ value }) => ({ result: value.toUpperCase() }),
};
```

## Existing Built-in Skills

| name | Purpose |
|---|---|
| `validate_qlib_formula` | Validation of qlib formula syntax. Detect unknown columns and parentheses mismatches |

## Initialization Mechanism

`app_runtime_core.ts` imports `../skills/index.ts` at the top level, causing all built-in skills to be registered during module evaluation. In Bun's module system, the same module is evaluated only once, so duplicate registrations do not occur.

## Best Practices

- Avoid using the any type (Biome error) — use generics `<TInput, TOutput>`.
- Use try-catch inside `execute()` (CDD principle: crash on failure).
- Register skills somewhere other than `index.ts`.