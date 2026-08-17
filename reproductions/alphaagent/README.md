# AlphaAgent

- **Paper:** "AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay" (arXiv:2502.16789)
- **Official repo:** https://github.com/RndmVariableQ/AlphaAgent
- **Path taken:** official-repo path - adapted to run locally with Python 3.12+, modern Qlib daily data, isolated cache paths, and OpenAI/Gemini endpoint compatibility.
- **Status:** **Done** - see [`RESULTS.md`](RESULTS.md) for verification results.

---

## What AlphaAgent Does

AlphaAgent is an autonomous agent framework for quantitative alpha factor discovery. Given a financial research direction, it:
1. **Generates Hypotheses**: Asks an LLM to propose market anomalies, microstructure signals, or fundamental hypotheses.
2. **Generates Factor Code**: Converts hypotheses into executable domain-specific factor expressions.
3. **Executes & Backtests**: Calculates factor values against Qlib daily market data and evaluates Rank IC, ICIR, and turnover.
4. **Regularized Exploration**: Analyzes cross-factor correlations to penalize redundant alphas and mitigate alpha decay, feeding discoveries into subsequent iterations.

---

## Setup & Quickstart

### 1. Environment Setup

```bash
cd reproductions/alphaagent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configuration (.env)

Create a `.env` in the repository root or within this directory:

```bash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_API_KEY=your_api_key
CHAT_MODEL=gemini-3.1-flash-lite
REASONING_MODEL=gemini-3.1-flash-lite

USE_LOCAL=True
QLIB_PROVIDER_URI=./qlib_data/cn_data
QLIB_CACHE_DIR=./.cache/qlib
MPLCONFIGDIR=./.cache/matplotlib
```

### 3. Verify Pipeline

Run the verification suite:
```bash
python scripts/verify_pipeline.py
```

### 4. Run Alpha Mining

```bash
python scripts/prepare_cn_data.py
alphaagent run --scenario qlib
```
