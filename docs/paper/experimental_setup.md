# AAARTS実験設定ドラフト（Experimental Setup）セクション

AAARTS (Autonomous Agentic Alpha Trade System) の NeurIPS 2026 向け論文における「Experimental Setup」セクションの英語ドラフトである。日本の財務諸表（EDINET）および日本語特有の難点（漢字の多さ等）に焦点を当て、学術的で厳密な英語表現で記述した。

---

## NeurIPS LaTeX/Markdown Draft (English)

```latex
\section{Experimental Setup}
\label{sec:experimental_setup}

To systematically evaluate the performance of the Autonomous Agentic Alpha Trade System (AAARTS), we conduct comprehensive benchmarking experiments. In this section, we describe the dataset, the forecasting task, and the baseline methodologies employed in our evaluation.

\subsection{Dataset: EDINET-Bench (Japanese Corporate Annual Reports)}
\label{subsec:dataset}

The empirical evaluation of AAARTS is conducted on a curated subset of \texttt{EDINET-Bench}~\cite{sakana2025edinetbench}, an open-source evaluation suite designed for testing Large Language Models (LLMs) on complex regulatory financial documents in the Japanese market. Our evaluation corpus consists of \textbf{224 Japanese corporate annual reports} (known as \textit{Yukashoken Hokokusho} or \textit{Yuhou}), representing a diverse group of publicly traded firms on the Tokyo Stock Exchange.

The Japanese corporate disclosure landscape presents several unique, market-specific challenges that distinguish it from standard Western counterparts (e.g., US SEC Form 10-K):
\begin{itemize}
    \item \textbf{Linguistic Complexity:} Japanese annual reports are written in dense, formal prose with a high frequency of domain-specific terminology (e.g., \begin{CJK*}{UTF8}{ipm}有価証券報告書\end{CJK*}). Extracting semantic structure from unstructured sections such as the Management's Discussion and Analysis (MD\&A) equivalent (``経営方針、経営環境及び対処すべき課題等'') and Business Risks (``事業等のリスク'') requires advanced understanding of Japanese grammatical pragmatics and financial nuances.
    \item \textbf{XBRL Taxonomy Diversity:} Financial reports filed through the Electronic Disclosure for Investors' NETwork (EDINET) are formatted using eXtensible Business Reporting Language (XBRL). Japanese listed entities are permitted to use four distinct accounting standards: J-GAAP, IFRS, US GAAP, and JMIS. This introduces structural heterogeneity across taxonomy mappings, which our data parser must dynamically align.
    \item \textbf{Point-in-Time (PIT) Alignment:} Under Japanese regulations, corporate entities must submit their annual reports within three months of their fiscal year-end. To eliminate lookahead bias (leakage of future information), we align all reports using their official filing date and timestamps, ensuring the model only accesses information that was publicly available at the exact point of execution.
\end{itemize}

\subsection{Task Definition: Binary Earnings Direction Forecasting}
\label{subsec:task_definition}

We formulate the forecasting objective as a binary classification task. Given a corporate annual report $d_{i,t}$ for firm $i$ filed at time $t$ (covering fiscal year $T$), the goal is to predict whether the firm will achieve an increase or decrease in operating income (or net earnings) in the subsequent fiscal year $T+1$.

Let $E_{i, T}$ represent the operating income of firm $i$ for fiscal year $T$, and $E_{i, T+1}$ represent the operating income for the subsequent fiscal year. We define the target variable $Y_{i, T+1} \in \{0, 1\}$ as:
\begin{equation}
    Y_{i, T+1} = \begin{cases} 
    1 & \text{if } E_{i, T+1} > E_{i, T} \\
    0 & \text{if } E_{i, T+1} \le E_{i, T}
    \end{cases}
\end{equation}

Predicting operating income direction serves as a robust proxy for fundamental business operations. Unlike raw stock returns, which are heavily contaminated by short-term sentiment, market noise, and macroeconomic shocks (e.g., foreign exchange rate volatility, interest rate changes), operating income directly reflects a company's business performance and operational efficiency. The test dataset is approximately balanced, preventing trivial classifiers from obtaining high scores via class-skew exploitation. All evaluations are executed under strict information-barrier constraints to prevent lookahead leakage.

\subsection{Baselines for Benchmarking}
\label{subsec:baselines}

To demonstrate the efficacy of the AAARTS framework, we benchmark it against three baseline paradigms:
\begin{enumerate}
    \item \textbf{Naive Majority:} A simple statistical baseline that computes the mode of the training labels and predicts that majority class for all instances in the test set. Since our dataset is roughly balanced, this baseline serves as the empirical lower bound (random-guess benchmark).
    \item \textbf{XGBoost with Basic Financial Ratios:} A quantitative machine learning baseline representing the predictive capacity of structured financial statements. We extract fundamental financial ratios from the Balance Sheet (BS), Profit \& Loss (P\&L), and Cash Flow (CF) statements, categorized into three categories:
    \begin{itemize}
        \item \textit{Profitability:} Return on Assets (ROA), Return on Equity (ROE), Operating Income Margin.
        \item \textit{Liquidity \& Leverage:} Current Ratio, Debt-to-Equity (D/E) Ratio.
        \item \textit{Cash Flow Quality:} Operating Cash Flow to Net Income Ratio, Free Cash Flow.
    \end{itemize}
    An Extreme Gradient Boosting (XGBoost) classifier is trained on these features. This baseline assesses the performance of a model reliant solely on numerical financial indicators, omitting the qualitative narratives.
    \item \textbf{Zero-shot LLM Prompts:} A modern LLM baseline representing the performance of a raw foundation model (e.g., \texttt{gpt-4o}) without agentic loops or feedback structures. The model is prompted with the raw textual summary and key financial tables, and is instructed to perform zero-shot binary classification alongside a step-by-step reasoning chain. This baseline establishes the direct utility gains obtained by the self-evolutionary, multi-agent hypothesis generation, and verification loops of AAARTS.
\end{enumerate}
```

---

## 補足説明（Supplementary Notes）

1. EDINET-Benchの構成:
   earnings_forecastクエストは、日本株に特化した有価証券報告書のテキストと数値を統合して予測を行うクエストである。

2. 日本市場特化のポイント:
   日本語の複雑な文字コード、IFRS/J-GAAPなどの会計基準の混在、そして有価証券報告書が公表されてから投資判断に反映されるまでの厳密なタイムスタンプ管理（PIT）の難しさを、英語において適切に主張している。