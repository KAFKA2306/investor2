# LongFinanceQA — 長文財務文書の理解

**タイトル**: Facilitating Long Context Understanding via Supervised Chain-of-Thought Reasoning  
**公開**: arXiv, 2025  
**目的**: 長大な財務文書に対するLLMの長文理解を、supervised Chain-of-Thought reasoningで改善する。

## 一次情報

- arXiv: https://arxiv.org/abs/2502.13127

## 代表能力

論文は LongFinanceQA を含む長文理解taskを用い、単にcontext windowを拡大するのではなく、長い入力から必要な情報を統合して回答する能力を評価する。

## investor2での比較契約

CryptoTradeとは別familyとして扱う。取引P&Lへ変換せず、論文の長文QA task・split・評価指標をIssue #51で固定し、同一入力・同一評価条件でAAARTSと代表手法を比較する。直接比較が完了するまでは `BEAT / TIE / LOSE / BLOCKED` を付けない。
