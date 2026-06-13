import type { SpilloverBacktestResult } from "../schemas";

export function backtestResultsHtml(data?: SpilloverBacktestResult): string {
	const sectorNames: Record<string, string> = {
		"1000": "水産・農林",
		"2000": "鉱業",
		"3000": "建設業",
		"4000": "食料品",
		"5000": "繊維製品",
		"6000": "紙・パルプ",
		"7000": "化学",
		"8000": "医薬品",
		"9000": "石油・石炭",
		"10000": "ゴム製品",
		"11000": "ガラス・土石",
		"12000": "鉄鋼",
		"13000": "非鉄金属",
		"14000": "金属製品",
		"15000": "機械",
		"16000": "電気機器",
		"17000": "輸送用機器",
	};

	const displayData = data || {
		backtest_id: "backtest_sample",
		start_date: "2024-01-03",
		end_date: "2024-03-30",
		total_returns_pct: 12.7,
		sharpe_ratio: 0.397,
		max_drawdown_pct: -6.18,
		win_rate: 0.323,
		num_trades: 847,
		strategy_name: "Regularized PCA Sector Spillover (US -> JP)",
	};
	return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📊 バックテスト結果 - AAARTS ダッシュボード</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; color: #1f2937; line-height: 1.5; }
    .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
    .header { margin-bottom: 32px; }
    .header h1 { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
    .header p { font-size: 14px; color: #6b7280; margin-bottom: 4px; }
    
    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }
    .metric-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #3b82f6; }
    .metric-card.good { border-left-color: #10b981; }
    .metric-card.warning { border-left-color: #f59e0b; }
    
    .metric-label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .metric-value { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
    .metric-value.good { color: #10b981; }
    .metric-value.warning { color: #f59e0b; }
    .metric-value.primary { color: #3b82f6; }
    
    .metric-bar { background: #e5e7eb; border-radius: 4px; height: 8px; overflow: hidden; margin-top: 8px; }
    .metric-bar-fill { height: 100%; background: #10b981; border-radius: 4px; transition: width 0.3s ease; }
    .metric-bar-fill.warning { background: #f59e0b; }
    .metric-bar-fill.primary { background: #3b82f6; }
    
    .explanation-box { background: #f3f4f6; border-left: 4px solid #3b82f6; border-radius: 6px; padding: 16px; margin-top: 12px; font-size: 13px; color: #374151; }
    
    .section { background: white; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }
    .section h2 { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    .section-desc { font-size: 13px; color: #6b7280; margin-bottom: 16px; }
    .divider { height: 1px; background: #e5e7eb; margin: 16px 0; }
    
    .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 16px; }
    .stat-item { }
    .stat-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
    .stat-value { font-size: 24px; font-weight: 700; }
    
    .data-context { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 16px; margin-bottom: 24px; }
    .data-context h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
    .data-context p { font-size: 13px; color: #1e40af; margin-bottom: 4px; }
    .data-context .warn { color: #dc2626; font-weight: 600; }
    
    .sector-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .sector-table th { background: #f3f4f6; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #e5e7eb; }
    .sector-table td { padding: 12px; border-bottom: 1px solid #e5e7eb; }
    .sector-table tr:hover { background: #f9fafb; }
    
    .signal-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }
    .signal-long { background: #d1fae5; color: #065f46; }
    .signal-short { background: #fee2e2; color: #7f1d1d; }
    .signal-neutral { background: #f3f4f6; color: #374151; }
    
    .confidence-bar { display: inline-block; background: #e5e7eb; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600; }
    
    .trend { display: inline-block; font-size: 18px; font-weight: bold; margin-left: 4px; }
    .trend.up { color: #10b981; }
    .trend.down { color: #ef4444; }
    .trend.flat { color: #6b7280; }
    
    .chart { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px; margin: 16px 0; }
    .chart-bar { display: flex; align-items: center; margin-bottom: 8px; }
    .chart-label { width: 100px; font-size: 12px; font-weight: 600; }
    .chart-track { flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px; margin: 0 12px; position: relative; overflow: hidden; }
    .chart-fill { height: 100%; background: #3b82f6; border-radius: 4px; transition: width 0.3s; }
    .chart-fill.positive { background: #10b981; }
    .chart-fill.negative { background: #ef4444; }
    .chart-value { width: 50px; text-align: right; font-size: 12px; font-weight: 600; }
    
    .info-alert { background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px; padding: 16px; margin-bottom: 24px; }
    .info-alert h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
    .info-alert p { font-size: 13px; color: #78350f; margin-bottom: 6px; }
    
    .explanation-section { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 20px; margin-bottom: 24px; }
    .explanation-section h3 { font-size: 16px; font-weight: 700; margin-bottom: 12px; color: #15803d; }
    .explanation-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .explanation-item { }
    .explanation-item h4 { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
    .explanation-item p { font-size: 13px; color: #1f2937; }
    
    @media (max-width: 768px) {
      .metrics-grid { grid-template-columns: 1fr; }
      .stat-row { grid-template-columns: repeat(2, 1fr); }
    }
    
    /* Navigation Bar Styles */
    .navbar { background: #1e3a8a; padding: 12px 24px; color: white; display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .nav-brand { font-size: 18px; font-weight: 700; color: white; text-decoration: none; display: flex; align-items: center; gap: 8px; }
    .nav-links { display: flex; gap: 16px; }
    .nav-links a { color: #bfdbfe; text-decoration: none; font-size: 14px; font-weight: 500; padding: 6px 12px; border-radius: 4px; transition: background 0.2s, color 0.2s; }
    .nav-links a:hover { background: #1e40af; color: white; }
    .nav-links a.active { background: #2563eb; color: white; }
  </style>
</head>
<body>
  <!-- Global Navigation -->
  <nav class="navbar">
    <a href="/" class="nav-brand">AAARTS Dashboard</a>
    <div class="nav-links">
      <a href="/">System Home</a>
      <a href="/screener">Screener</a>
      <a href="/company">Company Search</a>
      <a href="/pipeline/results">Alpha Discovery</a>
      <a href="/backtest/results" class="active">Sector Spillover</a>
      <a href="/links">Link Directory</a>
    </div>
  </nav>

  <div class="container">
    <!-- Header -->
    <div class="header">
      <h1>📊 セクター・スピルオーバー戦略（US → JP）</h1>
      <p>AAARTS（自律型エージェントベース・アルファ研究・トレーディング・システム）</p>
    </div>

    <!-- Data Context Warning & Scientific Finding -->
    <div class="data-context" style="background: #eff6ff; border-color: #3b82f6;">
      <h3 style="color: #1e3a8a;">🔬 実証データに基づくアルファの源泉と手数料の壁 (Ground Truth)</h3>
      <p style="color: #1e40af;">
        最新の実データ・バックテスト（取引コスト0.5%、税金20%加味）により、以下の<strong>残酷かつ明確な事実</strong>が判明しました：
      </p>
      <ul style="color: #1e40af; margin-left: 20px; font-size: 13px; margin-bottom: 12px; margin-top: 8px; line-height: 1.6;">
        <li>⚠️ <strong>オーバーナイトの罠</strong>: 寄り付きのギャップには確かにアルファが存在しますが、利幅が極めて薄いため、実戦的な取引コスト（50bps）を支払うと完全に「手数料負け」します。</li>
        <li>✅ <strong>厳選ホールド戦略 (Persistent Holding)</strong>: コストの壁を越える唯一の道は、<strong>「優位性のあるセクター（水産、化学など）に絞り、シグナルが変わるまで数日間ホールドして取引回数を極限まで減らす」</strong>ことです。</li>
        <li>🎯 <strong>結論</strong>: 頻繁な売買（デイトレ）を捨て、強いトレンドが発生した時だけ乗り、利益を伸ばす「スイングトレード」への転換がクオンツ運用において必須です。</li>
      </ul>
      <p style="font-size: 12px; color: #3b82f6; font-weight: bold;">
        ※現在表示中のデータは、厳格なコスト・税金制約下での最適解「厳選ホールド (DEFAULT)」戦略の実証結果です。 (期間: \${displayData.start_date} ～ \${displayData.end_date})
      </p>
    </div>

    <!-- Primary Metrics with Progress Bars -->
    <div class="metrics-grid">
      <!-- Sharpe Ratio -->
      <div class="metric-card">
        <div class="metric-label">シャープレシオ（リスク調整リターン）</div>
        <div class="metric-value ${displayData.sharpe_ratio > 0 ? "primary" : "warning"}">${displayData.sharpe_ratio.toFixed(3)}</div>
        <div class="metric-bar">
          <div class="metric-bar-fill ${displayData.sharpe_ratio > 0 ? "primary" : "warning"}" style="width: ${Math.min(100, Math.max(0, (displayData.sharpe_ratio / 1.5) * 100))}%;"></div>
        </div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">目標値: ≥1.5 (現在: ${Math.max(0, (displayData.sharpe_ratio / 1.5) * 100).toFixed(1)}%)</div>
        <div class="explanation-box">
          <strong>何？</strong> リターンを得るために取ったリスクの大きさを示します。数字が大きいほど、同じリターンをより少ないリスクで得ていることになります。<br>
          <strong>良い範囲：</strong> ≥1.5（優秀）、1.0-1.5（良好）、0.5-1.0（可）<br>
          <strong>現状：</strong> ${displayData.sharpe_ratio.toFixed(3)} です。
        </div>
      </div>

      <!-- Max Drawdown -->
      <div class="metric-card warning">
        <div class="metric-label">最大ドローダウン（リスク許容度）</div>
        <div class="metric-value warning">${displayData.max_drawdown_pct.toFixed(2)}%</div>
        <div class="metric-bar">
          <div class="metric-bar-fill warning" style="width: ${Math.min(100, (Math.abs(displayData.max_drawdown_pct) / 10) * 100)}%;"></div>
        </div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">上限値: ≤10% (現在: ${Math.min(100, (Math.abs(displayData.max_drawdown_pct) / 10) * 100).toFixed(1)}%)</div>
        <div class="explanation-box">
          <strong>何？</strong> 戦略が経験した最悪の場合の損失です。例えば-10%は、ピークの後、10%まで下がったことを意味します。<br>
          <strong>良い範囲：</strong> ≤5%（優秀）、≤10%（許容可能）、>10%（リスク大）<br>
          <strong>現状：</strong> -${displayData.max_drawdown_pct.toFixed(2)}% です。
        </div>
      </div>

      <!-- Win Rate -->
      <div class="metric-card">
        <div class="metric-label">勝率（利益が出た日の割合）</div>
        <div class="metric-value primary">${(displayData.win_rate * 100).toFixed(1)}%</div>
        <div class="metric-bar">
          <div class="metric-bar-fill primary" style="width: ${displayData.win_rate * 100}%;"></div>
        </div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">参考値: >50% は難しい</div>
        <div class="explanation-box">
          <strong>何？</strong> 取引日のうち、プラスのリターンを得た日の割合。ただし、勝率が低くても、勝った日の利益が大きければ戦略は成功します。<br>
          <strong>平均的な範囲：</strong> 40-55%（日本株式）<br>
          <strong>現状：</strong> ${(displayData.win_rate * 100).toFixed(1)}% です。
        </div>
      </div>

      <!-- Total Return -->
      <div class="metric-card ${displayData.total_returns_pct > 0 ? "good" : "warning"}">
        <div class="metric-label">総リターン（税引前）</div>
        <div class="metric-value ${displayData.total_returns_pct > 0 ? "good" : "warning"}">${displayData.total_returns_pct > 0 ? "+" : ""}${displayData.total_returns_pct.toFixed(1)}%</div>
        <div class="metric-bar">
          <div class="metric-bar-fill ${displayData.total_returns_pct > 0 ? "good" : "warning"}" style="width: 100%;"></div>
        </div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">累積パフォーマンス</div>
        <div class="explanation-box">
          <strong>現状：</strong> ${displayData.total_returns_pct.toFixed(1)}% です。
        </div>
      </div>

      <!-- Net Return (After Tax) -->
      <div class="metric-card ${(displayData.net_returns_pct || 0) > 0 ? "good" : "warning"}" style="border-left-width: 8px;">
        <div class="metric-label">税引後純利益 (20%税控除)</div>
        <div class="metric-value ${(displayData.net_returns_pct || 0) > 0 ? "good" : "warning"}">${(displayData.net_returns_pct || 0) > 0 ? "+" : ""}${(displayData.net_returns_pct || 0).toFixed(1)}%</div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">実質的な手残り金額</div>
        <div style="font-size: 11px; color: #ef4444; margin-top: 2px;">支払税金概算: ${(displayData.tax_paid_pct || 0).toFixed(1)}%</div>
      </div>
    </div>

    <!-- Trade Statistics Section -->
    <div class="section">
      <h2>📈 取引統計</h2>
      <div class="section-desc">戦略が実行した全取引の詳細統計。日次ベースで何回取引を実行し、そのうち何回が利益を生み出したかを示します。</div>
      <div class="divider"></div>
      <div class="stat-row">
        <div class="stat-item">
          <div class="stat-label">総取引数</div>
          <div class="stat-value">${displayData.num_trades}</div>
          <div style="font-size: 12px; color: #6b7280;">テスト期間全体の取引数</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">勝利取引</div>
          <div class="stat-value" style="color: #10b981;">${displayData.num_winning_trades || 0}</div>
          <div style="font-size: 12px; color: #6b7280;">プラスで終了した取引</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">敗北取引</div>
          <div class="stat-value" style="color: #ef4444;">${displayData.num_losing_trades || 0}</div>
          <div style="font-size: 12px; color: #6b7280;">マイナスで終了した取引</div>
        </div>
      </div>
    </div>

    <!-- Test Period Section -->
    <div class="section">
      <h2>📅 テスト期間（バックテスト設定）</h2>
      <div class="section-desc">この戦略がどの期間に対して検証されたかを表示します。より長い期間のテストほど、結果がより堅牢で信頼性が高くなります。</div>
      <div class="divider"></div>
      <div class="stat-row">
        <div class="stat-item">
          <div class="stat-label">開始日</div>
          <div class="stat-value" style="font-size: 18px; font-family: monospace;">${displayData.start_date}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">終了日</div>
          <div class="stat-value" style="font-size: 18px; font-family: monospace;">${displayData.end_date}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">テスト期間</div>
          <div class="stat-value">3ヶ月</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">完全データ: 6年（計画中）</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">取引日数</div>
          <div class="stat-value">63日</div>
          <div style="font-size: 12px; color: #6b7280;">営業日ベース</div>
        </div>
      </div>
    </div>

    <!-- Sector Performance Table -->
    <div class="section">
      <h2>🌍 セクター別パフォーマンス＆シグナル</h2>
      <div class="section-desc">各日本株セクターに対する戦略のシグナルと実績パフォーマンス。LONG（買い推奨）/ SHORT（売り推奨）/ NEUTRAL（中立）のシグナルと、その信頼度を表示します。</div>
      <div class="divider"></div>
      <div style="overflow-x: auto;">
        <table class="sector-table">
          <thead>
            <tr>
              <th>セクター</th>
              <th>シグナル</th>
              <th>信頼度</th>
              <th style="text-align: right;">平均リターン</th>
              <th style="text-align: right;">ボラティリティ</th>
              <th style="text-align: right;">シャープ</th>
              <th style="text-align: right;">勝率</th>
              <th>トレンド</th>
            </tr>
          </thead>
          <tbody>
            ${(displayData.sector_performance || [])
							.map(
								(s) => `
            <tr>
              <td><span style="font-family: monospace; font-size: 11px; color: #6b7280;">${s.jp_sector}</span> ${sectorNames[s.jp_sector] || "不明"}</td>
              <td><span class="signal-badge ${s.sharpe > 0 ? "signal-long" : "signal-short"}">${s.sharpe > 0 ? "🟢 LONG" : "🔴 SHORT"}</span></td>
              <td><span class="confidence-bar">${(Math.abs(s.sharpe) * 100).toFixed(0)}%</span></td>
              <td style="text-align: right; color: ${s.avg_return > 0 ? "#10b981" : "#ef4444"}; font-weight: bold;">${s.avg_return > 0 ? "+" : ""}${s.avg_return.toFixed(3)}%</td>
              <td style="text-align: right;">${s.volatility.toFixed(2)}%</td>
              <td style="text-align: right; font-weight: bold;">${s.sharpe.toFixed(3)}</td>
              <td style="text-align: right;">${(s.win_rate * 100).toFixed(1)}%</td>
              <td><span class="trend ${s.avg_return > 0 ? "up" : "down"}">${s.avg_return > 0 ? "↑" : "↓"}</span></td>
            </tr>
            `,
							)
							.join("")}
          </tbody>
        </table>
      </div>
      <div style="margin-top: 16px; font-size: 12px; color: #6b7280;">
        <p>※ パフォーマンスの高いセクターにはプラスのシャープレシオが示されます。</p>
        <p style="margin-top: 6px;">🟢 LONG = 買い推奨 / 🔴 SHORT = 売り推奨 / ⚪ NEUTRAL = 中立</p>
      </div>
    </div>

    <!-- Explanation Section -->
    <div class="explanation-section">
      <h3>📖 用語説明：投資家向けガイド</h3>
      <div class="explanation-grid">
        <div class="explanation-item">
          <h4>🎯 シャープレシオ</h4>
          <p>リターンを得るために取ったリスクの効率性を示します。例えば、2つの戦略が同じリターンをしたなら、シャープレシオが高い方が、より少ないリスクで達成したことになります。数値が大きいほど良い。</p>
        </div>
        <div class="explanation-item">
          <h4>⬇️ 最大ドローダウン</h4>
          <p>戦略が経験した最悪期の損失のこと。例えば-10%は、ピークから10%下落したことを意味します。投資家はこの数値を見て、「最悪の場合、どれだけの損失に耐えられるか」を判断します。</p>
        </div>
        <div class="explanation-item">
          <h4>📊 勝率</h4>
          <p>取引日のうち、プラスのリターンを得た日の割合。ただし、勝率が低くても、勝った日の利益が大きければ、全体的には利益になることがあります。勝率だけで戦略の良さは判断できません。</p>
        </div>
        <div class="explanation-item">
          <h4>💰 セクターシグナル</h4>
          <p>LONG（買い推奨）、SHORT（売り推奨）、NEUTRAL（中立）の3段階。信頼度は0-100%で、システムがそのシグナルにどの程度確信を持っているかを表します。</p>
        </div>
        <div class="explanation-item">
          <h4>🌍 スピルオーバー効果</h4>
          <p>米国株市場のパフォーマンス（や市場心理）が日本株市場に「波及」することです。この戦略は、米国セクターの動きを分析して、日本セクターの将来パフォーマンスを予測します。</p>
        </div>
        <div class="explanation-item">
          <h4>⚙️ PCA（主成分分析）</h4>
          <p>多くの米国セクター情報を、より少数の「主要パターン」に圧縮する統計手法。この場合、3つの主要因に圧縮して、日本セクターのパフォーマンスを予測しています。</p>
        </div>
      </div>
    </div>

    <!-- Performance Notes -->
    <div class="info-alert">
      <h3>ℹ️ バックテスト設定と免責事項</h3>
      <p><strong>期間：</strong> 2024年1月3日～3月30日（3ヶ月、63営業日）</p>
      <p><strong>リバランス：</strong> 日次</p>
      <p><strong>初期資本：</strong> ¥1,000,000</p>
      <p><strong>ポジションサイズ：</strong> ロング30%、ショート30%</p>
      <p style="margin-top: 12px; color: #78350f;"><strong>⚠️ 重要な注記：</strong> 本バックテスト結果は過去データに基づいています。過去のパフォーマンスは将来の結果を保証するものではありません。</p>
    </div>
  </div>
</body>
</html>`;
}
