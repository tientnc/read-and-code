# RESULTS - AlphaAgent Reproduction

- **Paper:** "AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay" (arXiv:2502.16789)
- **Official repo:** https://github.com/RndmVariableQ/AlphaAgent
- **Status:** **Migrated, Adapted & Verified**

---

## 1. Reproduction Summary

The official AlphaAgent implementation has been migrated into `read-and-code/reproductions/alphaagent/` and adapted for local reproducibility:

1. **Packaging & Python Compatibility**:
   - Packaged with standard `pyproject.toml` supporting Python 3.10 through 3.12+.
   - Cleaned circular dependencies and isolated project artifacts (Qlib cache, Matplotlib cache, prompt caches).

2. **LLM Adaptor Compatibility**:
   - Verified support for Google Gemini OpenAI-compatible endpoints (`https://generativelanguage.googleapis.com/v1beta/openai/`) using `gemini-2.5` / `gemini-3.1` models.

3. **Pipeline Verification**:
   - Created `scripts/verify_pipeline.py` to test factor generation, Rank IC evaluation, Information Ratio (ICIR) calculation, and scenario architecture.
   - All smoke tests executed and passed.

---

## 2. Deviations from Upstream

| Upstream Default | Local Reproduction | Reason |
|---|---|---|
| Hardcoded Python 3.10 dependencies | Standard `pyproject.toml` (>=3.10, tested on 3.12.3) | Allows running on modern server environments without legacy python build constraints. |
| Global paths for Qlib & prompt caches | Local configurable paths (`.cache/qlib`, `.cache/matplotlib`) | Prevents filesystem collisions and keeps reproduction self-contained. |
| Azure OpenAI specific hardcoding | Standard OpenAI-compatible API base URL support | Enables using Google Gemini API (`generativelanguage.googleapis.com`) or local vLLM. |

---

## 3. Verification Commands

```bash
python scripts/verify_pipeline.py
```
