import { Database } from "bun:sqlite";
import { existsSync } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import yaml from "js-yaml";
import {
	type AceBullet,
	type AcePlaybook,
	AcePlaybookSchema,
	BaseEventSchema,
	type EventType,
	type UQTLEvent,
} from "../schemas.ts";
import { paths } from "../system/path_registry.ts";

export class ContextPlaybook {
	private playbook: AcePlaybook = { bullets: [] };
	private filePath: string;

	constructor(filePath?: string) {
		this.filePath =
			filePath || path.join(process.cwd(), "data", "playbook.yaml");
	}

	async load(): Promise<void> {
		if (!existsSync(this.filePath)) {
			this.playbook = { bullets: [] };
			await this.save();
			return;
		}
		const data = await fs.readFile(this.filePath, "utf-8");
		const parsed = yaml.load(data);
		this.playbook = AcePlaybookSchema.parse(parsed);
	}

	async save(): Promise<void> {
		const dir = path.dirname(this.filePath);
		await fs.mkdir(dir, { recursive: true });
		const tempPath = `${this.filePath}.tmp.${Date.now()}`;
		await fs.writeFile(
			tempPath,
			yaml.dump(this.playbook, {
				lineWidth: 120,
				noRefs: true,
				sortKeys: false,
			}),
			"utf-8",
		);
		await fs.rename(tempPath, this.filePath);
	}

	addBullet(
		bullet: Omit<AceBullet, "id" | "helpful_count" | "harmful_count">,
	): string {
		const id = `ctx-${crypto.randomUUID().split("-")[0]}`;
		const newBullet: AceBullet = {
			...bullet,
			id,
			helpful_count: 0,
			harmful_count: 0,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString(),
		};
		this.playbook.bullets.push(newBullet);
		return id;
	}

	getBullets(section?: AceBullet["section"]): AceBullet[] {
		if (!section) return this.playbook.bullets;
		return this.playbook.bullets.filter((b) => b.section === section);
	}

	async prune(harmfulThreshold: number = 3): Promise<number> {
		const originalCount = this.playbook.bullets.length;
		this.playbook.bullets = this.playbook.bullets.filter(
			(b) => b.harmful_count < harmfulThreshold,
		);
		await this.save();
		return originalCount - this.playbook.bullets.length;
	}

	getRankedBullets(section?: AceBullet["section"]): AceBullet[] {
		const filtered = this.getBullets(section);
		return filtered.sort((a, b) => b.helpful_count - a.helpful_count);
	}

	async deduplicate(): Promise<number> {
		const seen = new Set<string>();
		const originalCount = this.playbook.bullets.length;
		this.playbook.bullets = this.playbook.bullets.filter((b) => {
			if (seen.has(b.content)) return false;
			seen.add(b.content);
			return true;
		});
		return originalCount - this.playbook.bullets.length;
	}

	async applyFeedbackByMetadataId(args: {
		metadataId: string;
		feedback: "HELPFUL" | "HARMFUL";
		reason?: string;
		runId?: string;
		loopIteration?: number;
	}): Promise<number> {
		const { metadataId, feedback, reason, runId, loopIteration } = args;
		let updated = 0;
		for (const bullet of this.playbook.bullets) {
			const metaId = String(bullet.metadata?.id ?? "");
			if (metaId !== metadataId) continue;
			if (feedback === "HELPFUL") {
				bullet.helpful_count += 1;
			} else if (feedback === "HARMFUL") {
				bullet.harmful_count += 1;
			} else {
				throw new Error(`[AUDIT] Unknown feedback type: ${feedback}`);
			}
			bullet.updated_at = new Date().toISOString();
			bullet.metadata = {
				...bullet.metadata,
				lastFeedback: feedback,
				lastFeedbackReason: reason ?? "",
				lastFeedbackAt: bullet.updated_at,
				lastRunId: runId ?? "",
				lastLoopIteration: loopIteration ?? 0,
			};
			updated += 1;
		}
		if (updated > 0) {
			await this.save();
		}
		return updated;
	}

	updateBulletMetadata(
		metadataId: string,
		patch: Record<string, unknown>,
	): void {
		const bullet = this.playbook.bullets.find(
			(b) => b.metadata?.id === metadataId,
		);
		if (!bullet) return;
		bullet.metadata = { ...bullet.metadata, ...patch };
		bullet.updated_at = new Date().toISOString();
	}
}

export interface ExperimentRecord {
	id: string;
	name: string;
	scenario: string;
	context_prompt: string;
	started_at: string;
}

export interface AlphaRecord {
	id: string;
	experiment_id: string;
	formula: string;
	description: string;
	reasoning: string;
	created_at: string;
}

export interface EvaluationRecord {
	id: string;
	alpha_id: string;
	market_date: string;
	metrics_json: string;
	overall_score: number;
}

export class MemoryCenter {
	private db: Database;

	constructor(dbPath?: string) {
		const targetPath = dbPath || paths.memorySqlite;
		this.db = new Database(targetPath, { create: true });
		this.initializeSchema();
	}

	private initializeSchema() {
		this.db.exec(`
      CREATE TABLE IF NOT EXISTS experiments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        scenario TEXT NOT NULL,
        context_prompt TEXT NOT NULL,
        started_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS alphas (
        id TEXT PRIMARY KEY,
        experiment_id TEXT NOT NULL,
        formula TEXT NOT NULL,
        description TEXT NOT NULL,
        reasoning TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(experiment_id) REFERENCES experiments(id)
      );

      CREATE TABLE IF NOT EXISTS evaluations (
        id TEXT PRIMARY KEY,
        alpha_id TEXT NOT NULL,
        market_date TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        overall_score REAL NOT NULL,
        FOREIGN KEY(alpha_id) REFERENCES alphas(id)
      );

      CREATE TABLE IF NOT EXISTS uqtl_events (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        type TEXT NOT NULL,
        agent_id TEXT,
        operator_id TEXT,
        experiment_id TEXT,
        parent_event_id TEXT,
        payload_json TEXT NOT NULL,
        metadata_json TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_alphas_experiment ON alphas(experiment_id);
      CREATE INDEX IF NOT EXISTS idx_evaluations_alpha ON evaluations(alpha_id);
      CREATE INDEX IF NOT EXISTS idx_evaluations_score ON evaluations(overall_score DESC);
      CREATE INDEX IF NOT EXISTS idx_uqtl_timestamp ON uqtl_events(timestamp);
      CREATE INDEX IF NOT EXISTS idx_uqtl_type ON uqtl_events(type);
      CREATE INDEX IF NOT EXISTS idx_uqtl_parent ON uqtl_events(parent_event_id);
    `);
	}

	public recordExperiment(exp: ExperimentRecord) {
		const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO experiments (id, name, scenario, context_prompt, started_at)
      VALUES ($id, $name, $scenario, $context_prompt, $started_at)
    `);
		stmt.run({
			$id: exp.id,
			$name: exp.name,
			$scenario: exp.scenario,
			$context_prompt: exp.context_prompt,
			$started_at: exp.started_at,
		});
	}

	public recordAlpha(alpha: AlphaRecord) {
		const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO alphas (id, experiment_id, formula, description, reasoning, created_at)
      VALUES ($id, $exp_id, $formula, $desc, $reasoning, $created_at)
    `);
		stmt.run({
			$id: alpha.id,
			$exp_id: alpha.experiment_id,
			$formula: alpha.formula,
			$desc: alpha.description,
			$reasoning: alpha.reasoning,
			$created_at: alpha.created_at,
		});
	}

	public recordEvaluation(evalRecord: EvaluationRecord) {
		const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO evaluations (id, alpha_id, market_date, metrics_json, overall_score)
      VALUES ($id, $alpha_id, $date, $metrics, $score)
    `);
		stmt.run({
			$id: evalRecord.id,
			$alpha_id: evalRecord.alpha_id,
			$date: evalRecord.market_date,
			$metrics: evalRecord.metrics_json,
			$score: evalRecord.overall_score,
		});
	}

	public pushEvent(event: Record<string, unknown>) {
		const runId =
			(event.runId as string | undefined) ||
			process.env.UQTL_RUN_ID ||
			undefined;
		const loopIterationRaw =
			(event.loopIteration as number | string | undefined) ||
			process.env.UQTL_LOOP_ITERATION;
		const parsedLoopIteration = Number(loopIterationRaw);
		const baseMetadata =
			event.metadata && typeof event.metadata === "object"
				? (event.metadata as Record<string, unknown>)
				: {};
		const metadata = {
			...baseMetadata,
			...(runId ? { runId } : {}),
			...(Number.isFinite(parsedLoopIteration)
				? { loopIteration: parsedLoopIteration }
				: {}),
		};
		const stmt = this.db.prepare(`
      INSERT INTO uqtl_events (id, timestamp, type, agent_id, experiment_id, payload_json, metadata_json)
      VALUES ($id, $ts, $type, $agent, $exp, $payload, $meta)
    `);
		stmt.run({
			$id:
				(event.id as string | undefined) ||
				`evt_${Date.now()}_${crypto.randomUUID().split("-")[0]}`,
			$ts: (event.timestamp as string | undefined) || new Date().toISOString(),
			$type: event.type as string,
			$agent: (event.agentId as string | undefined) || null,
			$exp: (event.experimentId as string | undefined) || null,
			$payload: JSON.stringify(event.payload),
			$meta: Object.keys(metadata).length > 0 ? JSON.stringify(metadata) : null,
		} as Record<string, string | number | boolean | null>);
	}

	public getRecentSuccesses(limit: number = 5): unknown[] {
		const stmt = this.db.prepare(`
      SELECT a.id, a.description, a.formula, e.overall_score, e.metrics_json
      FROM alphas a
      JOIN evaluations e ON a.id = e.alpha_id
      WHERE e.overall_score > 0.05
      ORDER BY e.overall_score DESC
      LIMIT $limit
    `);
		return stmt.all({ $limit: limit });
	}

	public getRecentFailures(limit: number = 5): unknown[] {
		const stmt = this.db.prepare(`
      SELECT a.id, a.description, a.formula, e.overall_score, e.metrics_json
      FROM alphas a
      JOIN evaluations e ON a.id = e.alpha_id
      WHERE e.overall_score < 0.01
      ORDER BY e.overall_score ASC
      LIMIT $limit
    `);
		return stmt.all({ $limit: limit });
	}

	public getEvents(limit: number = 50): unknown[] {
		const stmt = this.db.prepare(`
      SELECT * FROM uqtl_events
      ORDER BY timestamp DESC
      LIMIT $limit
    `);
		return stmt.all({ $limit: limit });
	}

	public close() {
		this.db.close();
	}
}

export class EventStore {
	private readonly db: Database;

	constructor(dbPath?: string) {
		this.db = new Database(dbPath || paths.uqtlSqlite, { create: true });
		this.initialize();
	}

	private initialize() {
		this.db.run(`
            CREATE TABLE IF NOT EXISTS uqtl_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                agent_id TEXT,
                operator_id TEXT,
                experiment_id TEXT,
                parent_event_id TEXT,
                payload TEXT NOT NULL, -- JSON
                metadata TEXT           -- JSON
            )
        `);
		this.db.run(
			`CREATE INDEX IF NOT EXISTS idx_uqtl_timestamp ON uqtl_events(timestamp)`,
		);
		this.db.run(
			`CREATE INDEX IF NOT EXISTS idx_uqtl_type ON uqtl_events(type)`,
		);
		this.db.run(
			`CREATE INDEX IF NOT EXISTS idx_uqtl_parent ON uqtl_events(parent_event_id)`,
		);
	}

	public appendEvent(event: UQTLEvent): void {
		const validated = BaseEventSchema.parse(event);
		console.log(
			`[EventStore] Appending event: ${validated.type} (ID: ${validated.id.slice(0, 8)})`,
		);
		this.db.run(
			`INSERT INTO uqtl_events (id, timestamp, type, agent_id, operator_id, experiment_id, parent_event_id, payload, metadata) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			[
				validated.id,
				validated.timestamp,
				validated.type,
				validated.agentId || null,
				validated.operatorId || null,
				validated.experimentId || null,
				validated.parentEventId || null,
				JSON.stringify(validated.payload),
				validated.metadata ? JSON.stringify(validated.metadata) : null,
			],
		);
	}

	public getEventsSince(timestamp: string): UQTLEvent[] {
		const rows = this.db
			.query(
				"SELECT * FROM uqtl_events WHERE timestamp >= ? ORDER BY timestamp ASC",
			)
			.all(timestamp) as {
			id: string;
			timestamp: string;
			type: string;
			agent_id: string | null;
			operator_id: string | null;
			experiment_id: string | null;
			parent_event_id: string | null;
			payload: string;
			metadata: string | null;
		}[];
		return rows.map(
			(row) =>
				({
					id: row.id,
					timestamp: row.timestamp,
					type: row.type as EventType,
					agentId: row.agent_id || undefined,
					operatorId: row.operator_id || undefined,
					experimentId: row.experiment_id || undefined,
					parentEventId: row.parent_event_id || undefined,
					payload: JSON.parse(row.payload),
					metadata: row.metadata ? JSON.parse(row.metadata) : undefined,
				}) as UQTLEvent,
		);
	}

	public close() {
		this.db.close();
	}
}

export const eventStore = new EventStore();
