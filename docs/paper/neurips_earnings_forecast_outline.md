# 📝 AAARTS: Autonomous Agentic Alpha Trade System for Financial Earnings Forecasting

**Target Venue:** NeurIPS 2026 (Datasets and Benchmarks Track or Applied AI)
**Focus:** Earnings Forecast (利益予想) using Japanese Financial Statements (EDINET)

---

## 🌟 論文のストーリー展開 (The Narrative)

### 1. Introduction (導入)
*   **課題 (The Problem)**: 企業の業績予想（Earnings Forecast）は、クオンツ投資における最も重要なタスクの一つ。しかし、従来の定量データ（株価、純利益の数値など）だけを用いた予測モデルは、市場の非効率性を捉えきれず、限界に達している。
*   **解決策 (The Solution)**: 財務諸表の「定性データ（MD&A、リスク要因、事業の状況などのテキスト）」にこそ、次期の業績を予見する「暗黙のシグナル」が隠されている。
*   **提案手法 (Our Approach)**: 本論文では、LLMを用いて定性的な財務テキストから自律的にアルファ（予測シグナル）を発見・検証するシステム **AAARTS (Autonomous Agentic Alpha Trade System)** を提案する。
*   **貢献 (Contributions)**:
    1.  AAARTSによる、テキスト情報に基づく業績予想のエンドツーエンドのパイプラインの構築。
    2.  日本語の複雑な財務文書（EDINET）を対象とした、Sakana AI の `EDINET-Bench` を用いた厳密な評価。
    3.  AIの推論根拠（Reasoning）の分析による、業績変動メカニズムの解明。

### 2. Related Work

#### 2.1 Financial Language Modeling and NLP in Finance
Early applications of natural language processing (NLP) in quantitative finance relied primarily on dictionary-based approaches \cite{loughran2011liability} and shallow machine learning models to extract sentiment from corporate disclosures and financial news. The introduction of transformer-based architectures led to the development of domain-specific language models. FinBERT \cite{araci2019finbert, yang2020finbert} adapted the BERT architecture \cite{devlin2018bert} to financial corpora via target-domain pre-training, achieving substantial improvements in financial sentiment classification and named entity recognition. More recently, large-scale language models (LLMs) have demonstrated emergent reasoning capabilities on complex tasks. BloombergGPT \cite{wu2023bloomberggpt}, a 50-billion parameter model trained from scratch on a massive hybrid dataset of financial documents and general-purpose web text, showcased the power of dense representations in capturing nuanced financial terminology and semantic relationships. Subsequent open-source initiatives, such as FinGPT \cite{yang2023fingpt} and instruction-tuned LLaMA variants, have democratized financial LLMs. However, these models remain optimized for textual classification, semantic searches, or generic summarization rather than structured quantitative forecasting or multi-statement financial accounting.

#### 2.2 Agentic LLM Loops for Quantitative Trading
The transition from passive text processing to active decision-making in financial markets has been accelerated by agentic LLM frameworks. Drawing inspiration from general-purpose agentic architectures like ReAct \cite{yao2022react} and Reflexion \cite{shinn2023reflexion}, researchers have proposed agentic loops for portfolio management and trading simulation. Architectures such as FinMem \cite{yu2023finmem} integrate short-term working memory and long-term episodic memory to adjust trading decisions dynamically in response to streaming market news. Similarly, systems like StockAgent \cite{zhang2024stockagent} utilize multi-agent frameworks to simulate market microstructures, modeling the interactions between autonomous traders, analysts, and market makers. While these agentic loops are frequently equipped with external tools (e.g., search engines, calculators, and databases), their reasoning remains confined to unstructured textual signals or simple price time-series. They lack the capacity to perform deep, multi-step structural reasoning over complex corporate financial statements, which is a prerequisite for long-term equity valuation and earnings forecasting.

#### 2.3 Structured Financial Reasoning vs. Sentiment-Driven Alpha
The vast majority of sentiment-driven trading systems operate on the assumption that market sentiment acts as a leading indicator of short-term price action \cite{bollen2011twitter}. While sentiment can capture transient order-flow dynamics and behavioral biases, it suffers from high noise-to-signal ratios, rapid decay, and a lack of grounding in fundamental economic realities. In contrast, classical quantitative finance relies on fundamental analysis \cite{ou1989financial, abarbanell1997fundamental} to identify mispriced securities by examining a firm's core financial statements: the Balance Sheet (BS), Profit & Loss (P&L) statement, and Cash Flow (CF) statement.

AAARTS bridges the gap between unstructured textual reasoning and structured quantitative modeling. Unlike existing financial LLM agents that map corporate reports to a scalar sentiment score, AAARTS implements an agentic loop designed to enforce double-entry accounting constraints and structural relationships across the three primary financial statements. By reasoning explicitly about the interdependencies between revenue recognition (P&L), working capital changes (BS), and operational cash generation (CF), AAARTS detects earnings quality anomalies (e.g., divergence between net income and operating cash flows) that are invisible to pure sentiment-based models. This structured financial reasoning enables the system to generate highly explainable, low-decay alpha signals grounded in the structural mechanics of corporate finance.

### 3. Methodology: The AAARTS Agentic Architecture (提案手法)
*   **System Design Philosophy**: 単なるLLMラッパーではなく、複数のエージェントが協調する「自律型ループ（Autonomous Loop）」としての設計。
*   **Key Components**:
    1.  **Hypothesis Generator (LES Agent)**: 財務データとニュースから「なぜこの企業は成長するのか？」という仮説を生成。
    2.  **Verification Pillar (The Oracle)**: `EDINET-Bench` 等の客観的基準を用いて、生成された仮説を「ガチ評価」し、定量的なスコアを算出。
    3.  **Loop Supervisor (Decision Gate)**: 検証結果が基準（例：Precision > 70%）を満たさない場合、仮説を PIVOT（修正）させ、自己改善ループを回す。
*   **Data Ingestion**: EDINET XBRLからの `summary`, `bs`, `pl`, `cf` の抽出。
*   **Agentic Reasoning**: `gpt-4o` を用い、財務諸表間の「数値の矛盾（例：売上減＋純利増）」を論理的に説明する Chain-of-Thought プロセスの実装。

### 4. Experimental Setup (実験設定)
*   **Dataset**: `SakanaAI/EDINET-Bench` の `earnings_forecast` テストセット。
*   **Baselines**:
    *   Naive Prediction (常にマジョリティクラスを予測)。
    *   従来の機械学習モデル (XGBoost + 財務比率)。
    *   素のLLM (Zero-shot prompt)。
*   **AAARTS Configuration**: システムの推論エンジン（`src/commands/bench_eval.py` の実装）の設定詳細。

### 5. Results and Analysis (結果と考察) 🏆 ここが一番重要！
*   **Quantitative Results (定量評価)**:
    *   AAARTS の Accuracy (例: 55.00%), Precision (例: 72.73%), Recall (例: 57.14%) の報告。
    *   *ポイント*: Accuracy は 55% と発展途上だが、**Precision が 72.73% と高い**点に注目。「システムが増益だと判断した時の確度は極めて高い」という投資戦略上の優位性を主張する。
*   **Qualitative Analysis (定性評価・Error Analysis)**:
    *   **True Positives (成功例)**: AAARTS が「どのテキスト表現」から増益を見抜いたか（例：先行投資の回収フェーズへの移行、特定セグメントの好調な記述）。
    *   **False Negatives/Positives (失敗例)**: なぜ外したのか？（例：突発的なマクロ要因、為替変動など、過去の有報テキストだけでは予測不可能な外部ショック）。
*   **Ablation Study**: 「サマリー（数値）」だけを見せた場合と、「テキスト（MD&A等）」も合わせた場合の精度の違い。AAARTSがテキストから追加のアルファ（非構造化データからの予測力）を抽出できていることを証明する。

### 6. Discussion and Future Work (議論と今後の展望)
*   単年度の有報だけでなく、過去数年分のテキストの「変化（Delta）」を捉えることで、Accuracy をさらに向上させる可能性。
*   マクロ経済指標（金利、為替）とのマルチモーダルな統合。
*   AAARTS が実際のトレーディングシステム（Polymarketや日本株アルゴ）に与える影響。

### 7. Conclusion (結論)
*   AAARTSは、複雑な日本語財務文書から自律的に業績の方向性を高精度（High Precision）で予測できることを証明した。定性テキストはクオンツ投資における次世代のアルファ源泉である。

---
