import { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { DocumentRepository } from "../db/repos/document_repository.ts";
import { EvaluationRepository } from "../db/repos/evaluation_repository.ts";
import { EventRepository } from "../db/repos/event_repository.ts";
import { FeatureRepository } from "../db/repos/feature_repository.ts";
import { SignalRepository } from "../db/repos/signal_repository.ts";
import { core } from "../system/app_runtime_core.ts";
import { paths } from "../system/path_registry.ts";

export type KnowledgeDocumentInput = {
	docId: string;
	symbol: string;
	source: "EDINET" | "JQUANTS" | "MANUAL" | "ALPHA_DISCOVERY";
	filedAt: string;
	title: string;
};

export type KnowledgeSectionInput = {
	docId: string;
	sectionName: string;
	content: string;
	sentiment: number;
	riskTermCount: number;
	aiTermCount: number;
};

export type MarketDailyInput = {
	symbol: string;
	date: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	earningsFlag: boolean;
};

export type SignalInput = {
	signalId: string;
	symbol: string;
	date: string;
	riskDelta: number;
	pead1d: number;
	pead5d: number;
	combinedAlpha: number;
};

export type EventFeatureInput = {
	eventId: string;
	symbol: string;
	filedAt: string;
	docId: string;
	riskDelta: number;
	sentiment: number;
	aiExposure: number;
	kgCentrality: number;
	correctionFlag: boolean;
	correctionCount90d: number;
	featureVersion: string;
};

export type MacroRegimeInput = {
	date: string;
	regimeId: string;
	inflationZ: number;
	iipZ: number;
	yieldSlopeZ: number;
	riskOnScore: number;
};

export type GateDecisionInput = {
	signalId: string;
	date: string;
	gateName: string;
	passed: boolean;
	threshold: string;
	actualValue: number | null;
	reason: string;
};

export type FeatureVersionInput = {
	featureName: string;
	version: string;
	formula: string;
};

export type SignalLineageInput = {
	signalId: string;
	sourceDocId: string;
	sourceSection: string;
	modelVersion: string;
};

export type BacktestRunInput = {
	runId: string;
	strategyId: string;
	fromDate: string;
	toDate: string;
	sharpe: number;
	totalReturn: number;
	maxDrawdown: number;
};

export type SignalBacktestEvent = {
	signalId: string;
	symbol: string;
	date: string;
	combinedAlpha: number;
	riskDelta: number;
	pead1d: number;
	pead5d: number;
	nextReturn: number;
};

export type TradableSignalEvent = {
	signalId: string;
	symbol: string;
	date: string;
	combinedAlpha: number;
	riskDelta: number;
	pead1d: number;
	pead5d: number;
	nextReturn: number;
	correctionFlag: boolean;
	correctionCount90d: number;
	regimeId: string | null;
	entryClose: number;
	entryVolume: number;
};

export type SignalAuditTrace = {
	signal: {
		signalId: string;
		symbol: string;
		date: string;
		combinedAlpha: number;
		riskDelta: number;
		pead1d: number;
		pead5d: number;
	} | null;
	lineage: Array<{
		sourceDocId: string;
		sourceSection: string;
		modelVersion: string;
	}>;
	sourceDocument: {
		docId: string;
		source: string;
		filedAt: string;
		title: string;
	} | null;
	eventFeature: {
		eventId: string;
		featureVersion: string;
		correctionFlag: boolean;
		correctionCount90d: number;
	} | null;
	gateDecisions: Array<{
		gateName: string;
		passed: boolean;
		threshold: string;
		actualValue: number | null;
		reason: string;
	}>;
	backtestRuns: Array<{
		runId: string;
		strategyId: string;
		fromDate: string;
		toDate: string;
		sharpe: number;
		totalReturn: number;
		maxDrawdown: number;
		createdAt: string;
	}>;
};

export class AlphaKnowledgebase {
	private readonly db: Database;
	private readonly postgresRepos: {
		documents: DocumentRepository;
		features: FeatureRepository;
		signals: SignalRepository;
		events: EventRepository;
		evaluation: EvaluationRepository;
	} | null = null;

	constructor(dbPath?: string) {
		const targetPath = dbPath ?? paths.alphaKnowledgebaseSqlite;

		mkdirSync(dirname(dbPath), { recursive: true });
		mkdirSync(dirname(targetPath), { recursive: true });

		this.db = new Database(targetPath, { create: true });
		this.db.run("PRAGMA journal_mode = WAL");
		this.db.run("PRAGMA journal_mode = WAL;");

		if (core.postgres) {
			this.postgresRepos = {
				documents: new DocumentRepository(core.postgres),
				features: new FeatureRepository(core.postgres),
				signals: new SignalRepository(core.postgres),
				events: new EventRepository(core.postgres),
				evaluation: new EvaluationRepository(core.postgres),
			};
		}

		this.initialize();
	}

	private async ensureInstrument(symbol: string): Promise<string> {
		if (!core.postgres) return symbol;
		const instrumentId = symbol;
		return symbol;
		await core.postgres.query(
			`
      INSERT INTO ref.instrument (instrument_id, symbol, venue, status)
      VALUES ($1, $2, 'TSE', 'ACTIVE')
      ON CONFLICT(instrument_id) DO NOTHING
      `,
			[instrumentId, symbol],
		);
		return instrumentId;
	}

	private initialize(): void {
		this.db.exec("PRAGMA foreign_keys = ON;");
		this.db.exec(`
      CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        source TEXT NOT NULL,
        filed_at TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS sections (
        section_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        section_name TEXT NOT NULL,
        content TEXT NOT NULL,
        sentiment REAL NOT NULL,
        risk_term_count INTEGER NOT NULL,
        ai_term_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(doc_id, section_name),
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );

      CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
        section_id UNINDEXED,
        doc_id UNINDEXED,
        section_name,
        content,
        tokenize='unicode61'
      );

      CREATE TABLE IF NOT EXISTS market_daily (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        earnings_flag INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(symbol, date)
      );

      CREATE TABLE IF NOT EXISTS signals (
        signal_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        risk_delta REAL NOT NULL,
        pead_1d REAL NOT NULL,
        pead_5d REAL NOT NULL,
        combined_alpha REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(symbol, date)
      );

      CREATE TABLE IF NOT EXISTS edinet_event_features (
        event_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        filed_at TEXT NOT NULL,
        doc_id TEXT NOT NULL,
        risk_delta REAL NOT NULL,
        sentiment REAL NOT NULL,
        ai_exposure REAL NOT NULL,
        kg_centrality REAL NOT NULL,
        correction_flag INTEGER NOT NULL DEFAULT 0,
        correction_count_90d INTEGER NOT NULL DEFAULT 0,
        feature_version TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(symbol, filed_at),
        FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS macro_regime_daily (
        date TEXT PRIMARY KEY,
        regime_id TEXT NOT NULL,
        inflation_z REAL NOT NULL,
        iip_z REAL NOT NULL,
        yield_slope_z REAL NOT NULL,
        risk_on_score REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS signal_gate_decisions (
        signal_id TEXT NOT NULL,
        date TEXT NOT NULL,
        gate_name TEXT NOT NULL,
        passed INTEGER NOT NULL,
        threshold TEXT NOT NULL,
        actual_value REAL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY(signal_id, gate_name),
        FOREIGN KEY(signal_id) REFERENCES signals(signal_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS backtest_runs (
        run_id TEXT PRIMARY KEY,
        strategy_id TEXT NOT NULL,
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        sharpe REAL NOT NULL,
        total_return REAL NOT NULL,
        max_dd REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS feature_versions (
        feature_name TEXT NOT NULL,
        version TEXT NOT NULL,
        formula TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY(feature_name, version)
      );

      CREATE TABLE IF NOT EXISTS signal_lineage (
        signal_id TEXT NOT NULL,
        source_doc_id TEXT NOT NULL,
        source_section TEXT NOT NULL,
        model_version TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY(signal_id, source_doc_id, source_section),
        FOREIGN KEY(signal_id) REFERENCES signals(signal_id) ON DELETE CASCADE,
        FOREIGN KEY(source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_documents_symbol_filed_at
        ON documents(symbol, filed_at);
      CREATE INDEX IF NOT EXISTS idx_sections_doc_section
        ON sections(doc_id, section_name);
      CREATE INDEX IF NOT EXISTS idx_market_daily_symbol_date
        ON market_daily(symbol, date);
      CREATE INDEX IF NOT EXISTS idx_signals_symbol_date
        ON signals(symbol, date);
      CREATE INDEX IF NOT EXISTS idx_edinet_event_symbol_date
        ON edinet_event_features(symbol, filed_at);
      CREATE INDEX IF NOT EXISTS idx_edinet_event_doc
        ON edinet_event_features(doc_id);
      CREATE INDEX IF NOT EXISTS idx_macro_regime_date
        ON macro_regime_daily(date);
      CREATE INDEX IF NOT EXISTS idx_signal_gate_date
        ON signal_gate_decisions(date, gate_name, passed);
      CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
        ON backtest_runs(strategy_id, created_at);
      CREATE INDEX IF NOT EXISTS idx_signal_lineage_doc
        ON signal_lineage(source_doc_id, source_section);
    `);
	}

	public async upsertDocument(input: KnowledgeDocumentInput): Promise<void> {
		this.db
			.query(`
        INSERT INTO documents (doc_id, symbol, source, filed_at, title)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
          symbol = excluded.symbol,
          source = excluded.source,
          filed_at = excluded.filed_at,
          title = excluded.title
      `)
			.run(input.docId, input.symbol, input.source, input.filedAt, input.title);

		if (
			this.postgresRepos &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			const instrumentId = await this.ensureInstrument(input.symbol);
			await core.postgres?.query(
				`
        INSERT INTO ingest.source_document (source_doc_id, provider, external_id, instrument_id, filed_at, title)
        VALUES ($1, $2, $3, $4, $5::timestamptz, $6)
        ON CONFLICT(source_doc_id) DO UPDATE SET
          instrument_id = EXCLUDED.instrument_id,
          filed_at = EXCLUDED.filed_at,
          title = EXCLUDED.title
        `,
				[
					input.docId,
					input.source,
					input.docId,
					instrumentId,
					input.filedAt,
					input.title,
				],
			);
			await this.postgresRepos.documents.upsertDocument({
				documentId: input.docId,
				sourceDocId: input.docId,
				instrumentId,
				docType: input.source,
				filedAt: input.filedAt,
				title: input.title,
			});
		}
	}

	public async upsertSection(input: KnowledgeSectionInput): Promise<void> {
		const sectionId = `${input.docId}:${input.sectionName}`;
		const tx = this.db.transaction(() => {
			this.db
				.query(`
          INSERT INTO sections (
            section_id, doc_id, section_name, content, sentiment,
            risk_term_count, ai_term_count, updated_at
          )
          VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
          ON CONFLICT(doc_id, section_name) DO UPDATE SET
            content = excluded.content,
            sentiment = excluded.sentiment,
            risk_term_count = excluded.risk_term_count,
            ai_term_count = excluded.ai_term_count,
            updated_at = datetime('now')
        `)
				.run(
					sectionId,
					input.docId,
					input.sectionName,
					input.content,
					input.sentiment,
					input.riskTermCount,
					input.aiTermCount,
				);

			this.db
				.query("DELETE FROM sections_fts WHERE section_id = ?")
				.run(sectionId);
			this.db
				.query(`
          INSERT INTO sections_fts (section_id, doc_id, section_name, content)
          VALUES (?, ?, ?, ?)
        `)
				.run(sectionId, input.docId, input.sectionName, input.content);
		});
		tx();

		if (
			this.postgresRepos &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			await this.postgresRepos.documents.upsertSection({
				sectionId,
				documentId: input.docId,
				sectionName: input.sectionName,
				content: input.content,
				sentiment: input.sentiment,
				riskTermCount: input.riskTermCount,
				aiTermCount: input.aiTermCount,
			});
		}
	}

	public upsertMarketRows(rows: readonly MarketDailyInput[]): void {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly MarketDailyInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO market_daily (
          symbol, date, open, high, low, close, volume, earnings_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
          open = excluded.open,
          high = excluded.high,
          low = excluded.low,
          close = excluded.close,
          volume = excluded.volume,
          earnings_flag = excluded.earnings_flag
      `);
			for (const row of txRows) {
				stmt.run(
					row.symbol,
					row.date,
					row.open,
					row.high,
					row.low,
					row.close,
					row.volume,
					row.earningsFlag ? 1 : 0,
				);
			}
		});
		tx(rows);
	}

	public async upsertSignals(rows: readonly SignalInput[]): Promise<void> {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly SignalInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO signals (
          signal_id, symbol, date, risk_delta, pead_1d, pead_5d, combined_alpha
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(signal_id) DO UPDATE SET
          symbol = excluded.symbol,
          date = excluded.date,
          risk_delta = excluded.risk_delta,
          pead_1d = excluded.pead_1d,
          pead_5d = excluded.pead_5d,
          combined_alpha = excluded.combined_alpha
      `);
			for (const row of txRows) {
				stmt.run(
					row.signalId,
					row.symbol,
					row.date,
					row.riskDelta,
					row.pead1d,
					row.pead5d,
					row.combinedAlpha,
				);
			}
		});
		tx(rows);

		if (
			this.postgresRepos &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			for (const row of rows) {
				const instrumentId = await this.ensureInstrument(row.symbol);
				await this.postgresRepos.signals.upsertSignal({
					signalId: row.signalId,
					instrumentId,
					tradingDate: row.date,
					combinedAlpha: row.combinedAlpha,
					riskDelta: row.riskDelta,
					pead1d: row.pead1d,
					pead5d: row.pead5d,
				});
			}
		}
	}

	public async upsertEventFeatures(
		rows: readonly EventFeatureInput[],
	): Promise<void> {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly EventFeatureInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO edinet_event_features (
          event_id, symbol, filed_at, doc_id, risk_delta, sentiment,
          ai_exposure, kg_centrality, correction_flag, correction_count_90d,
          feature_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          symbol = excluded.symbol,
          filed_at = excluded.filed_at,
          doc_id = excluded.doc_id,
          risk_delta = excluded.risk_delta,
          sentiment = excluded.sentiment,
          ai_exposure = excluded.ai_exposure,
          kg_centrality = excluded.kg_centrality,
          correction_flag = excluded.correction_flag,
          correction_count_90d = excluded.correction_count_90d,
          feature_version = excluded.feature_version
      `);
			for (const row of txRows) {
				stmt.run(
					row.eventId,
					row.symbol,
					row.filedAt,
					row.docId,
					row.riskDelta,
					row.sentiment,
					row.aiExposure,
					row.kgCentrality,
					row.correctionFlag ? 1 : 0,
					Math.max(0, Math.floor(row.correctionCount90d)),
					row.featureVersion,
				);
			}
		});
		tx(rows);

		if (
			this.postgresRepos &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			for (const row of rows) {
				const instrumentId = await this.ensureInstrument(row.symbol);
				await this.postgresRepos.features.upsertFeatureVersion({
					featureName: "edinet_event",
					version: row.featureVersion,
					formula: "migrated_from_sqlite",
				});
				await this.postgresRepos.features.upsertEventFeature({
					eventFeatureId: row.eventId,
					sourceDocId: row.docId,
					instrumentId,
					filedAt: row.filedAt,
					featureName: "edinet_event",
					featureVersion: row.featureVersion,
					riskDelta: row.riskDelta,
					sentiment: row.sentiment,
					aiExposure: row.aiExposure,
					kgCentrality: row.kgCentrality,
					correctionFlag: row.correctionFlag,
					correctionCount90d: row.correctionCount90d,
				});
			}
		}
	}

	public upsertMacroRegimes(rows: readonly MacroRegimeInput[]): void {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly MacroRegimeInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO macro_regime_daily (
          date, regime_id, inflation_z, iip_z, yield_slope_z, risk_on_score
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
          regime_id = excluded.regime_id,
          inflation_z = excluded.inflation_z,
          iip_z = excluded.iip_z,
          yield_slope_z = excluded.yield_slope_z,
          risk_on_score = excluded.risk_on_score
      `);
			for (const row of txRows) {
				stmt.run(
					row.date,
					row.regimeId,
					row.inflationZ,
					row.iipZ,
					row.yieldSlopeZ,
					row.riskOnScore,
				);
			}
		});
		tx(rows);
	}

	public async upsertGateDecisions(
		rows: readonly GateDecisionInput[],
	): Promise<void> {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly GateDecisionInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO signal_gate_decisions (
          signal_id, date, gate_name, passed, threshold, actual_value, reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(signal_id, gate_name) DO UPDATE SET
          date = excluded.date,
          passed = excluded.passed,
          threshold = excluded.threshold,
          actual_value = excluded.actual_value,
          reason = excluded.reason
      `);
			for (const row of txRows) {
				stmt.run(
					row.signalId,
					row.date,
					row.gateName,
					row.passed ? 1 : 0,
					row.threshold,
					row.actualValue,
					row.reason,
				);
			}
		});
		tx(rows);

		if (
			this.postgresRepos &&
			core.postgres &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			for (const row of rows) {
				await core.postgres.query(
					`
          INSERT INTO feature.signal_gate_decision (signal_id, gate_name, trading_date, passed, threshold_text, actual_value, reason)
          VALUES ($1, $2, $3::date, $4, $5, $6, $7)
          ON CONFLICT(signal_id, gate_name) DO UPDATE SET
            trading_date = EXCLUDED.trading_date,
            passed = EXCLUDED.passed,
            threshold_text = EXCLUDED.threshold_text,
            actual_value = EXCLUDED.actual_value,
            reason = EXCLUDED.reason
          `,
					[
						row.signalId,
						row.gateName,
						row.date,
						row.passed,
						row.threshold,
						row.actualValue,
						row.reason,
					],
				);
			}
		}
	}

	public upsertFeatureVersion(input: FeatureVersionInput): void {
		this.db
			.query(`
        INSERT INTO feature_versions (feature_name, version, formula)
        VALUES (?, ?, ?)
        ON CONFLICT(feature_name, version) DO UPDATE SET
          formula = excluded.formula
      `)
			.run(input.featureName, input.version, input.formula);
	}

	public upsertSignalLineage(rows: readonly SignalLineageInput[]): void {
		if (rows.length === 0) return;
		const tx = this.db.transaction((txRows: readonly SignalLineageInput[]) => {
			const stmt = this.db.query(`
        INSERT INTO signal_lineage (
          signal_id, source_doc_id, source_section, model_version
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(signal_id, source_doc_id, source_section) DO UPDATE SET
          model_version = excluded.model_version
      `);
			for (const row of txRows) {
				stmt.run(
					row.signalId,
					row.sourceDocId,
					row.sourceSection,
					row.modelVersion,
				);
			}
		});
		tx(rows);
	}

	public async recordBacktestRun(input: BacktestRunInput): Promise<void> {
		this.db
			.query(`
        INSERT INTO backtest_runs (
          run_id, strategy_id, from_date, to_date, sharpe, total_return, max_dd
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          strategy_id = excluded.strategy_id,
          from_date = excluded.from_date,
          to_date = excluded.to_date,
          sharpe = excluded.sharpe,
          total_return = excluded.total_return,
          max_dd = excluded.max_dd
      `)
			.run(
				input.runId,
				input.strategyId,
				input.fromDate,
				input.toDate,
				input.sharpe,
				input.totalReturn,
				input.maxDrawdown,
			);

		if (
			this.postgresRepos &&
			core.config.database?.canonicalDb?.dualWriteEnabled
		) {
			await this.postgresRepos.evaluation.upsertBacktestRun({
				runId: input.runId,
				strategyId: input.strategyId,
				fromDate: input.fromDate,
				toDate: input.toDate,
				sharpe: input.sharpe,
				totalReturn: input.totalReturn,
				maxDrawdown: input.maxDrawdown,
			});
		}
	}

	public searchSections(
		query: string,
		limit = 10,
	): {
		docId: string;
		sectionName: string;
		rank: number;
	}[] {
		return this.db
			.query(`
        SELECT doc_id as docId, section_name as sectionName, bm25(sections_fts) as rank
        FROM sections_fts
        WHERE sections_fts MATCH ?
        ORDER BY rank
        LIMIT ?
      `)
			.all(query, Math.max(1, limit)) as {
			docId: string;
			sectionName: string;
			rank: number;
		}[];
	}

	public getCounts(): Record<string, number> {
		const countOf = (table: string): number => {
			const row = this.db
				.query(`SELECT COUNT(*) as count FROM ${table}`)
				.get() as { count: number } | null;
			return row?.count ?? 0;
		};
		return {
			documents: countOf("documents"),
			sections: countOf("sections"),
			market_daily: countOf("market_daily"),
			signals: countOf("signals"),
			edinet_event_features: countOf("edinet_event_features"),
			macro_regime_daily: countOf("macro_regime_daily"),
			signal_gate_decisions: countOf("signal_gate_decisions"),
			backtest_runs: countOf("backtest_runs"),
			feature_versions: countOf("feature_versions"),
			signal_lineage: countOf("signal_lineage"),
		};
	}

	public fetchSignalBacktestEvents(
		fromDate?: string,
		toDate?: string,
		tradeLagDays = 1,
	): SignalBacktestEvent[] {
		const lag = Math.max(1, Math.floor(tradeLagDays));
		const entryOffset = lag - 1;
		const exitOffset = lag;
		const rows = this.db
			.query(`
        SELECT
          s.signal_id AS signalId,
          s.symbol AS symbol,
          s.date AS date,
          s.combined_alpha AS combinedAlpha,
          s.risk_delta AS riskDelta,
          s.pead_1d AS pead1d,
          s.pead_5d AS pead5d,
          (
            (
              SELECT m_exit.close
              FROM market_daily m_exit
              WHERE m_exit.symbol = s.symbol AND m_exit.date > s.date
              ORDER BY m_exit.date ASC
              LIMIT 1 OFFSET ?
            ) / (
              SELECT m_entry.close
              FROM market_daily m_entry
              WHERE m_entry.symbol = s.symbol AND m_entry.date > s.date
              ORDER BY m_entry.date ASC
              LIMIT 1 OFFSET ?
            ) - 1
          ) AS nextReturn
        FROM signals s
        WHERE
          (? IS NULL OR s.date >= ?)
          AND (? IS NULL OR s.date <= ?)
        ORDER BY s.date ASC, s.symbol ASC
      `)
			.all(
				exitOffset,
				entryOffset,
				fromDate ?? null,
				fromDate ?? null,
				toDate ?? null,
				toDate ?? null,
			) as {
			signalId: string;
			symbol: string;
			date: string;
			combinedAlpha: number | null;
			riskDelta: number | null;
			pead1d: number | null;
			pead5d: number | null;
			nextReturn: number | null;
		}[];

		return rows
			.map((row) => ({
				signalId: row.signalId,
				symbol: row.symbol,
				date: row.date,
				combinedAlpha: Number(row.combinedAlpha ?? 0),
				riskDelta: Number(row.riskDelta ?? 0),
				pead1d: Number(row.pead1d ?? 0),
				pead5d: Number(row.pead5d ?? 0),
				nextReturn: Number(row.nextReturn ?? Number.NaN),
			}))
			.filter(
				(row) =>
					Number.isFinite(row.combinedAlpha) && Number.isFinite(row.nextReturn),
			);
	}

	public fetchTradableSignals(
		fromDate?: string,
		toDate?: string,
		tradeLagDays = 1,
	): TradableSignalEvent[] {
		const lag = Math.max(1, Math.floor(tradeLagDays));
		const entryOffset = lag - 1;
		const exitOffset = lag;
		const rows = this.db
			.query(`
        SELECT
          s.signal_id AS signalId,
          s.symbol AS symbol,
          s.date AS date,
          s.combined_alpha AS combinedAlpha,
          s.risk_delta AS riskDelta,
          s.pead_1d AS pead1d,
          s.pead_5d AS pead5d,
          COALESCE(ef.correction_flag, 0) AS correctionFlag,
          COALESCE(ef.correction_count_90d, 0) AS correctionCount90d,
          (
            SELECT mr.regime_id
            FROM macro_regime_daily mr
            WHERE mr.date <= s.date
            ORDER BY mr.date DESC
            LIMIT 1
          ) AS regimeId,
          (
            SELECT m_entry.close
            FROM market_daily m_entry
            WHERE m_entry.symbol = s.symbol AND m_entry.date > s.date
            ORDER BY m_entry.date ASC
            LIMIT 1 OFFSET ?
          ) AS entryClose,
          (
            SELECT m_entry.volume
            FROM market_daily m_entry
            WHERE m_entry.symbol = s.symbol AND m_entry.date > s.date
            ORDER BY m_entry.date ASC
            LIMIT 1 OFFSET ?
          ) AS entryVolume,
          (
            (
              SELECT m_exit.close
              FROM market_daily m_exit
              WHERE m_exit.symbol = s.symbol AND m_exit.date > s.date
              ORDER BY m_exit.date ASC
              LIMIT 1 OFFSET ?
            ) / (
              SELECT m_entry.close
              FROM market_daily m_entry
              WHERE m_entry.symbol = s.symbol AND m_entry.date > s.date
              ORDER BY m_entry.date ASC
              LIMIT 1 OFFSET ?
            ) - 1
          ) AS nextReturn
        FROM signals s
        LEFT JOIN edinet_event_features ef
          ON ef.symbol = s.symbol AND ef.filed_at = s.date
        WHERE
          (? IS NULL OR s.date >= ?)
          AND (? IS NULL OR s.date <= ?)
        ORDER BY s.date ASC, s.symbol ASC
      `)
			.all(
				entryOffset,
				entryOffset,
				exitOffset,
				entryOffset,
				fromDate ?? null,
				fromDate ?? null,
				toDate ?? null,
				toDate ?? null,
			) as Array<{
			signalId: string;
			symbol: string;
			date: string;
			combinedAlpha: number | null;
			riskDelta: number | null;
			pead1d: number | null;
			pead5d: number | null;
			nextReturn: number | null;
			correctionFlag: number | null;
			correctionCount90d: number | null;
			regimeId: string | null;
			entryClose: number | null;
			entryVolume: number | null;
		}>;

		return rows
			.map((row) => ({
				signalId: row.signalId,
				symbol: row.symbol,
				date: row.date,
				combinedAlpha: Number(row.combinedAlpha ?? 0),
				riskDelta: Number(row.riskDelta ?? 0),
				pead1d: Number(row.pead1d ?? 0),
				pead5d: Number(row.pead5d ?? 0),
				nextReturn: Number(row.nextReturn ?? Number.NaN),
				correctionFlag: Number(row.correctionFlag ?? 0) > 0,
				correctionCount90d: Number(row.correctionCount90d ?? 0),
				regimeId: row.regimeId ?? null,
				entryClose: Number(row.entryClose ?? 0),
				entryVolume: Number(row.entryVolume ?? 0),
			}))
			.filter(
				(row) =>
					Number.isFinite(row.combinedAlpha) &&
					Number.isFinite(row.nextReturn) &&
					Number.isFinite(row.entryClose) &&
					Number.isFinite(row.entryVolume),
			);
	}

	public getSignalAuditTrace(signalId: string): SignalAuditTrace {
		const signal = this.db
			.query(`
        SELECT
          signal_id AS signalId,
          symbol,
          date,
          combined_alpha AS combinedAlpha,
          risk_delta AS riskDelta,
          pead_1d AS pead1d,
          pead_5d AS pead5d
        FROM signals
        WHERE signal_id = ?
      `)
			.get(signalId) as {
			signalId: string;
			symbol: string;
			date: string;
			combinedAlpha: number | null;
			riskDelta: number | null;
			pead1d: number | null;
			pead5d: number | null;
		} | null;

		const lineage = this.db
			.query(`
        SELECT
          source_doc_id AS sourceDocId,
          source_section AS sourceSection,
          model_version AS modelVersion
        FROM signal_lineage
        WHERE signal_id = ?
        ORDER BY source_doc_id ASC, source_section ASC
      `)
			.all(signalId) as Array<{
			sourceDocId: string;
			sourceSection: string;
			modelVersion: string;
		}>;

		const primaryDocId = lineage[0]?.sourceDocId ?? null;

		const sourceDocument =
			primaryDocId === null
				? null
				: (this.db
						.query(`
              SELECT
                doc_id AS docId,
                source,
                filed_at AS filedAt,
                title
              FROM documents
              WHERE doc_id = ?
            `)
						.get(primaryDocId) as {
						docId: string;
						source: string;
						filedAt: string;
						title: string;
					} | null);

		const eventFeature =
			primaryDocId === null
				? null
				: (this.db
						.query(`
              SELECT
                event_id AS eventId,
                feature_version AS featureVersion,
                correction_flag AS correctionFlag,
                correction_count_90d AS correctionCount90d
              FROM edinet_event_features
              WHERE doc_id = ?
              ORDER BY filed_at DESC
              LIMIT 1
            `)
						.get(primaryDocId) as {
						eventId: string;
						featureVersion: string;
						correctionFlag: number;
						correctionCount90d: number | null;
					} | null);

		const gateDecisions = this.db
			.query(`
        SELECT
          gate_name AS gateName,
          passed,
          threshold,
          actual_value AS actualValue,
          reason
        FROM signal_gate_decisions
        WHERE signal_id = ?
        ORDER BY gate_name ASC
      `)
			.all(signalId) as Array<{
			gateName: string;
			passed: number;
			threshold: string;
			actualValue: number | null;
			reason: string;
		}>;

		const backtestRuns = this.db
			.query(`
        SELECT
          b.run_id AS runId,
          b.strategy_id AS strategyId,
          b.from_date AS fromDate,
          b.to_date AS toDate,
          b.sharpe,
          b.total_return AS totalReturn,
          b.max_dd AS maxDrawdown,
          b.created_at AS createdAt
        FROM backtest_runs b
        WHERE b.strategy_id IN (
          SELECT DISTINCT model_version
          FROM signal_lineage
          WHERE signal_id = ?
        )
        ORDER BY b.created_at DESC
        LIMIT 20
      `)
			.all(signalId) as Array<{
			runId: string;
			strategyId: string;
			fromDate: string;
			toDate: string;
			sharpe: number | null;
			totalReturn: number | null;
			maxDrawdown: number | null;
			createdAt: string;
		}>;

		return {
			signal: signal
				? {
						signalId: signal.signalId,
						symbol: signal.symbol,
						date: signal.date,
						combinedAlpha: Number(signal.combinedAlpha ?? 0),
						riskDelta: Number(signal.riskDelta ?? 0),
						pead1d: Number(signal.pead1d ?? 0),
						pead5d: Number(signal.pead5d ?? 0),
					}
				: null,
			lineage,
			sourceDocument,
			eventFeature: eventFeature
				? {
						eventId: eventFeature.eventId,
						featureVersion: eventFeature.featureVersion,
						correctionFlag: eventFeature.correctionFlag > 0,
						correctionCount90d: Number(eventFeature.correctionCount90d ?? 0),
					}
				: null,
			gateDecisions: gateDecisions.map((row) => ({
				gateName: row.gateName,
				passed: row.passed > 0,
				threshold: row.threshold,
				actualValue: row.actualValue,
				reason: row.reason,
			})),
			backtestRuns: backtestRuns.map((row) => ({
				runId: row.runId,
				strategyId: row.strategyId,
				fromDate: row.fromDate,
				toDate: row.toDate,
				sharpe: Number(row.sharpe ?? 0),
				totalReturn: Number(row.totalReturn ?? 0),
				maxDrawdown: Number(row.maxDrawdown ?? 0),
				createdAt: row.createdAt,
			})),
		};
	}

	public close(): void {
		this.db.close();
	}
}
