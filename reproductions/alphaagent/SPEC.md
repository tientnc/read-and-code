# SPEC - AlphaAgent

- **Paper:** "AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay" (arXiv:2502.16789)
- **Official repo:** https://github.com/RndmVariableQ/AlphaAgent
- **Path taken:** official-repo path - adapted to run locally with modern Python 3.12+, configurable OpenAI / Google Gemini endpoints, and Qlib data adapter.

---

## 1. Core Architecture & Workflow

AlphaAgent implements an iterative, closed-loop quantitative alpha factor discovery pipeline:

```
+-------------------------------------------------------------+
|                      AlphaAgent Loop                        |
|                                                             |
|  1. Hypothesis Generator (LLM)                              |
|     - Proposes novel economic/market anomalies               |
|     - Formulates financial intuition and trading rationale   |
|                                                             |
|  2. Factor Implementation & Code Generator (LLM)            |
|     - Converts hypothesis into domain-specific factor DSL   |
|     - Formulates formulas with rolling windows & transforms  |
|                                                             |
|  3. Factor Execution & Evaluation (Qlib Engine)             |
|     - Calculates factor values across asset universe        |
|     - Evaluates Rank IC, Information Ratio (IR), Turnover    |
|                                                             |
|  4. Regularized Exploration & Feedback Loop                 |
|     - Computes factor correlation against existing library  |
|     - Penalizes redundant alphas to counteract decay        |
|     - Feeds performance feedback into next iteration        |
+-------------------------------------------------------------+
```

---

## 2. Key Components

1. **`alphaagent.components`**:
   - `HypothesisAgent`: Generates structured market hypotheses based on economic principles (momentum, reversal, volatility, liquidity, sentiment).
   - `FactorAgent`: Translates hypotheses into executable factor expressions.
   - `FeedbackLoop`: Evaluates factor performance metrics and updates context memory.

2. **`alphaagent.scenarios.qlib`**:
   - Adapts Qlib daily market data (e.g., CSI300, CSI500, VN30, Alpha158 base data).
   - Runs cross-sectional backtesting and evaluates Rank Information Coefficient (IC) and Information Ratio (IR).

3. **`alphaagent.oai`**:
   - LLM client with support for OpenAI endpoints, Azure OpenAI, and Google Gemini OpenAI-compatible endpoints (`gemini-2.5/3.1` via `generativelanguage.googleapis.com`).

---

## 3. Environment & Configuration

Configuration is loaded via environment variables or a local `.env` file:

```bash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_API_KEY=your_api_key
CHAT_MODEL=gemini-3.1-flash-lite
REASONING_MODEL=gemini-3.1-flash-lite

QLIB_PROVIDER_URI=./qlib_data/cn_data
QLIB_CACHE_DIR=./.cache/qlib
MPLCONFIGDIR=./.cache/matplotlib
```
