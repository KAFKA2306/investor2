---
name: typescript-agent-skills
description: >
  Use when adding, modifying, or calling TypeScript runtime skills that agents
  invoke via `this.useSkill()`. Covers the skill registry, interface definition,
  built-in skills, and the distinction from Claude Code markdown skills.
---

# TypeScript Runtime Skill System

## 概念の区別（重要）

| 種別 | 場所 | 用途 |
|---|---|---|
| **Claude Code スキル** | `.agent/skills/<name>/SKILL.md` | Claude Code が読む作業ガイダンス（markdown） |
| **TypeScript ランタイムスキル** | `ts-agent/src/skills/` | エージェントが実行時に呼び出すコード |

この SKILL.md は後者（TypeScript ランタイムスキル）を扱う。

## ファイル構造

```
ts-agent/src/skills/
├── types.ts          ← Skill<TInput, TOutput> インターフェース
├── registry.ts       ← SkillRegistry シングルトン
├── index.ts          ← built-in スキルの登録（side-effect import）
└── builtin/
    └── validate_qlib_formula.ts  ← qlib式構文検証スキル
```

## Skill インターフェース

```typescript
import type { z } from "zod";

export interface Skill<TInput, TOutput> {
  name: string;
  description: string;  // LLMへの説明・ログ出力に使用
  schema: z.ZodType<TInput>;
  execute(args: TInput): Promise<TOutput>;
}
```

## エージェントからの呼び出し方

```typescript
// BaseAgent を継承したエージェント内で
const result = await this.useSkill<{ formula: string }, { valid: boolean; error?: string }>(
  "validate_qlib_formula",
  { formula: "Mean($close,20)/Mean($close,5)-1" }
);
```

## 新しいスキルの追加手順

1. `ts-agent/src/skills/builtin/<skill_name>.ts` を作成
2. Zod スキーマで入力型を定義
3. `Skill<Input, Output>` を実装して `export`
4. `ts-agent/src/skills/index.ts` に `skillRegistry.register(...)` を追加

```typescript
// builtin/my_skill.ts の例
import { z } from "zod";
import type { Skill } from "../types.ts";

const inputSchema = z.object({ value: z.string() });
type Input = z.infer<typeof inputSchema>;
type Output = { result: string };

export const mySkill: Skill<Input, Output> = {
  name: "my_skill",
  description: "このスキルが何をするかの説明",
  schema: inputSchema,
  execute: async ({ value }) => ({ result: value.toUpperCase() }),
};
```

## 既存の built-in スキル

| name | 用途 |
|---|---|
| `validate_qlib_formula` | qlib式アルファ表現の構文検証。未知カラム・括弧不整合を検出する |

## 初期化の仕組み

`app_runtime_core.ts` が `import "../skills/index.ts"` をトップレベルで行い、
モジュール評価時にすべての built-in スキルが登録される。
Bun のモジュールシステムでは同一モジュールは一度しか評価されないため、二重登録は発生しない。

## 禁止事項

- `any` 型の使用（Biome エラー）→ generics `<TInput, TOutput>` を使う
- `execute()` 内での try-catch（CDD 原則：クラッシュさせる）
- skills 登録を `index.ts` 以外の場所で行う
