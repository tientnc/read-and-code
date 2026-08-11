# VeriCoT

- **Paper:** "VeriCoT: Neuro-symbolic Chain-of-Thought Validation via
  Logical Consistency Checks" - arXiv:2511.04662 / OpenReview zHuV3Vatov
- **Official repo:** none found. Checked: arXiv abstract page, GitHub
  repo search for "VeriCoT", GitHub code search for "VeriCoT" (one hit,
  `shan-shan-dar/improving_reasoning` - an unrelated neuro-symbolic
  reasoning project that happens to share vocabulary like "formalizer" and
  "smt", not affiliated with this paper).
- **Path taken:** PDF-only. Read the full 37-page PDF, wrote
  [`SPEC.md`](SPEC.md) from it before writing any code.

## What the paper does

LLMs reason step-by-step with chain-of-thought (CoT), but a final correct
answer doesn't mean every intermediate step was actually valid - the model
can get to a right answer via wrong reasoning. VeriCoT checks each step of
a CoT for real logical validity, not just plausibility: it translates each
step into first-order logic (autoformalization, via LLM), keeps a running
set of established formulas, and uses the Z3 SMT solver to check whether
each new step's formula is *entailed* by what's already established. If a
step doesn't follow directly, VeriCoT asks the LLM for a supporting
premise (from the source context, or commonsense) that would make it
follow, and only accepts the step if that premise is both consistent with
everything established so far and sufficient to entail it. Steps that
can't be formalized, that contradict prior steps, or that have no valid
supporting premise are flagged (`untranslatable` / `contradiction` /
`ungrounded`) rather than silently accepted. The paper then uses this
per-step verification signal for three things beyond just flagging bad
CoTs: prompting the model to self-correct at inference time, distilling a
high-fidelity fine-tuning dataset from verified CoTs, and generating
pairwise preference-optimization (DPO) reward signals - all three improve
downstream reasoning validity/accuracy on ProofWriter, LegalBench-SARA,
and BioASQ.

## Scope

Core verification loop only (Algorithm 1): autoformalize each CoT step to
first-order logic, check it against a running Z3 knowledge base for
contradiction/entailment, generate a supporting premise when neither
holds. **Not** reproduced: inference-time self-reflection, SFT/DPO
fine-tuning, LLM-as-judge premise filtering - those need training infra
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
to use - the paper's executor model, Claude-3.5-Sonnet-V2, is substituted
with a free-tier model here, which is a real deviation from the paper).

## Run

```bash
# deterministic check, no LLM calls -- validates the Z3 layer against
# the paper's own worked example
uv run python scripts/test_solver_paper_example.py

# full pipeline against a handful of ProofWriter examples (keep --n small,
# see RESULTS.md for why -- free-tier providers have tight limits, and
# reliability, not just quota, varies between models -- gemma-4-31b-it
# was the most reliable option found, see .agents/skills/llm-call/SKILL.md)
uv run python scripts/demo.py --n 5 --provider gemini --model gemma-4-31b-it
```

**Status: done for this reproduction's scope.** See
[`RESULTS.md`](RESULTS.md) for what was run and what came out - short
version: the Z3 consistency/entailment layer reproduces the paper's own
worked example exactly, and the full pipeline runs end-to-end against
three different real free-tier LLMs without crashing on the happy path,
correctly hitting all four of the paper's own error categories
(`untranslatable` / `contradiction` / `ungrounded` / valid) on real
inputs - including one case (run 4, example 3 in `RESULTS.md`) where the
model reached the *correct final answer* through a CoT step VeriCoT
correctly flagged as self-contradictory, which is the exact failure mode
the paper is motivated by. The ProofWriter numbers (n=3, n=5 across two
runs) are smoke-test scale, not comparable to the paper's Table 1.
