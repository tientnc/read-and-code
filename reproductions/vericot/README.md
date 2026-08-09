# VeriCoT

- **Paper:** "VeriCoT: Neuro-symbolic Chain-of-Thought Validation via
  Logical Consistency Checks" — arXiv:2511.04662 / OpenReview zHuV3Vatov
- **Official repo:** none found. Checked: arXiv abstract page, GitHub
  repo search for "VeriCoT", GitHub code search for "VeriCoT" (one hit,
  `shan-shan-dar/improving_reasoning` — an unrelated neuro-symbolic
  reasoning project that happens to share vocabulary like "formalizer" and
  "smt", not affiliated with this paper).
- **Path taken:** PDF-only. Read the full 37-page PDF, wrote
  [`SPEC.md`](SPEC.md) from it before writing any code.

## Scope

Core verification loop only (Algorithm 1): autoformalize each CoT step to
first-order logic, check it against a running Z3 knowledge base for
contradiction/entailment, generate a supporting premise when neither
holds. **Not** reproduced: inference-time self-reflection, SFT/DPO
fine-tuning, LLM-as-judge premise filtering — those need training infra
this environment doesn't have, or add scope beyond validating the core
mechanism. See `SPEC.md` for exactly what's in vs. out and why.

## Setup

```bash
cd reproductions/vericot
uv venv
uv pip install -e .
```

Needs `OPEN_ROUTER_API_KEY` and/or `AI_STUDIO_API_KEY` in the repo root's
`.env` (see `.agents/skills/llm-call/SKILL.md` for which models/providers
to use — the paper's executor model, Claude-3.5-Sonnet-V2, is substituted
with a free-tier model here, which is a real deviation from the paper).

## Run

```bash
# deterministic check, no LLM calls -- validates the Z3 layer against
# the paper's own worked example
uv run python scripts/test_solver_paper_example.py

# full pipeline against a handful of ProofWriter examples (keep --n small,
# see RESULTS.md for why -- both free-tier providers have tight limits)
uv run python scripts/demo.py --n 3 --provider gemini
```

**Status: done for this reproduction's scope.** See
[`RESULTS.md`](RESULTS.md) for what was run and what came out — short
version: the Z3 consistency/entailment layer reproduces the paper's own
worked example exactly, and the full pipeline runs end-to-end against real
free-tier LLMs without crashing, including correctly hitting the paper's
own `untranslatable`/`ungrounded` error categories on real failures. The
ProofWriter numbers are from n=3 (free-tier rate limits, see
`RESULTS.md`) and aren't meant to compare against the paper's Table 1.
