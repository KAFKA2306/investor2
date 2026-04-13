import { Database } from "bun:sqlite";
import type { SpilloverBacktestResult } from "../schemas";

export class BacktestCache {
	private db: Database;

	constructor(dbPath: string | undefined) {
		if (!dbPath) {
			throw new Error("cacheBacktestResults path is not configured");
		}
		this.db = new Database(dbPath);
		this.init();
	}

	private init() {
		this.db.exec(`
      CREATE TABLE IF NOT EXISTS backtest_results (
        id TEXT PRIMARY KEY,
        hypothesis_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        start_date TEXT,
        end_date TEXT,
        sharpe_ratio REAL,
        max_drawdown_pct REAL,
        win_rate REAL,
        total_returns_pct REAL,
        num_trades INTEGER,
        result_json TEXT
      );
    `);
	}

	saveResult(result: SpilloverBacktestResult): void {
		const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO backtest_results 
      (id, hypothesis_id, start_date, end_date, sharpe_ratio, max_drawdown_pct, 
       win_rate, total_returns_pct, num_trades, result_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

		stmt.run(
			result.backtest_id,
			result.hypothesis_id || "default",
			result.start_date,
			result.end_date,
			result.sharpe_ratio,
			result.max_drawdown_pct,
			result.win_rate,
			result.total_returns_pct,
			result.num_trades,
			JSON.stringify(result),
		);
	}

	getLatestResult(hypothesisId?: string): SpilloverBacktestResult | null {
		let query = `SELECT result_json FROM backtest_results`;
		if (hypothesisId) {
			query += ` WHERE hypothesis_id = '${hypothesisId}'`;
		}
		query += ` ORDER BY created_at DESC LIMIT 1`;

		const stmt = this.db.prepare(query);
		const row = stmt.get() as { result_json: string } | undefined;
		return row ? JSON.parse(row.result_json) : null;
	}
}
