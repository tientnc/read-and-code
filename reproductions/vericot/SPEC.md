# SPEC - VeriCoT

Paper: "VeriCoT: Neuro-symbolic Chain-of-Thought Validation via Logical
Consistency Checks" (Feng, Weir, Bostrom, Bayless, Cassel, Chaudhary,
Kiesl-Reiter, Rangwala - Penn/AWS). arXiv:2511.04662, OpenReview zHuV3Vatov.

Scope of this reproduction: **the core verification loop only**
(Algorithm 1 - autoformalization, consistency check, entailment check,
premise generation). Not reproduced: inference-time self-reflection,
SFT/DPO fine-tuning, LLM-as-judge premise filtering, the LegalBench-SARA
and BioASQ datasets (ProofWriter only). Those need either a training setup
this environment doesn't have, or dataset/domain-specific tuning that adds
scope beyond validating the core mechanism.

## Algorithm (paper's Algorithm 1)

Given a context (question + optional source document) and a CoT
`C_1, ..., C_n`:

```
F_0 = {}, P_0 = {}, errors = {}
for i in 1..n:
    (a) Autoformalize C_i into FOL formula F_i.
        If untranslatable after retries: errors += (i, untranslatable); continue.
    (b) Consistency check: if F_{i-1} |= not F_i (contradiction):
            errors += (i, contradiction); continue.
    (c) Entailment check: if F_{i-1} |= F_i:
            F_i := F_{i-1} + {F_i}; P_i := P_{i-1}; continue.
        else: generate a supporting premise P_i (see below).
    (d) If F_{i-1} + {P_i} |= F_i: F_i := F_{i-1} + {P_i} + {F_i}; P_i := P_{i-1} + {P_i}.
        else: errors += (i, ungrounded).
return F_n, P_n, errors
```

A CoT is **valid** iff every step is entailed (directly, or via a
premise) with no contradiction/untranslatable/ungrounded errors.

## Autoformalization (Section 2.2) - two-stage LLM translation

1. **Stage 1**: prompt an LLM to translate `C_i` into SMT-LIB (an
   assertion or set of assertions) using *only* the existing declared
   vocabulary (sorts/functions/constants already introduced by prior
   steps/premises). The LLM also returns metadata mapping text spans to
   parts of the formula (we skip this - not needed for the pass/fail
   verification signal itself).
2. **Stage 2**: if the LLM says the existing vocabulary can't express part
   of `C_i`, prompt it again to emit new `declare-fun`/`declare-sort`/
   `declare-const` statements, add those to the vocabulary, and retry
   stage 1. **Retry limit: 3 attempts**, then mark the step untranslatable.

Logic fragment: first-order logic with linear arithmetic and uninterpreted
functions/quantifiers, encoded as SMT-LIB, checked with Z3.

## Consistency / entailment checks

Both checks are ordinary SMT queries against the accumulated formula set
`F_{i-1}` (as Z3 assertions):
- **Contradiction**: the paper defines this as `F_{i-1} |= not F_i`, which
  means `F_{i-1} + {F_i}` is **unsat**. Check: assert `F_{i-1}`, assert
  `F_i`, `solver.check()` -> `unsat` means contradiction.
- **Entailment**: `F_{i-1} |= F_i`, i.e. `F_{i-1} + {not F_i}` is
  **unsat**. Check: assert `F_{i-1}`, assert `not F_i`, `solver.check()`
  -> `unsat` means entailed.
- **Premise consistency** (Section 2.3): a candidate premise `p` is kept
  only if `F_{i-1} + {p}` is **sat** (not already contradicted).

## Premise generation (Section 2.3)

When a step is neither entailed nor contradicted: prompt an LLM to
generate candidate NL premises (from context or commonsense) sufficient to
entail `F_i`, autoformalize each candidate (reusing Section 2.2), keep
only those consistent with `F_{i-1}`, conjoin the survivors into `P_i`,
and re-run the entailment check with `F_{i-1} + {P_i}`.

## Error taxonomy

- `untranslatable` - step can't be expressed in the supported SMT-LIB
  subset after 3 autoformalization retries.
- `contradiction` - step's formula is inconsistent with everything
  established so far.
- `ungrounded` - no consistent, sufficient premise could be found to make
  the step entailed.

## Evaluation protocol (paper, for reference - not fully reproduced here)

- **Datasets**: ProofWriter (OWA/CWA depth-5 subsets, entailment/
  contradiction labels only), LegalBench-SARA, BioASQ task 12b. This
  reproduction uses ProofWriter only (`renma/ProofWriter` on HF, `validation`
  split - the paper's own train/test split isn't published as such, so
  exact splits won't match).
- **Executor model** (generates the CoT to be verified):
  Claude-3.5-Sonnet-V2 in the paper. This reproduction substitutes a free
  model (see `.agents/skills/llm-call/SKILL.md`) - **this is a real
  deviation**, note it in `RESULTS.md`, not just here.
- **Metrics**: pass rate (% CoTs verified valid), verifier precision (%
  verified CoTs whose final answer is correct), VCAR = pass rate x
  precision, task accuracy (% correct answers regardless of verification).
  Table 1 numbers for ProofWriter + full VERICOT: pass rate 45.2, precision
  94.1, VCAR 42.5, task accuracy 75.8 - this is the reference point, not a
  target we expect to hit with a free small model and a tiny sample.

## Ambiguities / choices made here (not fully specified in the paper)

- Exact LLM prompts are not given verbatim anywhere in the paper (main
  text or appendix) - only the *effect* of each stage is described, plus
  worked examples (Section 2.1, Appendix A.2). Prompts in this reproduction are
  written from those, not transcribed from the original implementation
  (which doesn't appear to be public - see `README.md` for the triage
  decision).
- The paper doesn't specify how the CoT to be verified is produced for the
  "direct evaluation of VeriCoT" experiment (Section 3.3) - presumably the
  executor model is prompted to answer with a CoT, and that raw CoT is
  fed to VeriCoT unmodified. This reproduction does the same: ask the
  executor model to answer the ProofWriter question with a numbered
  step-by-step CoT, then verify that CoT as given.
- SMT-LIB fragment supported here is narrower than a full first-order
  solver: uninterpreted sorts/functions/predicates, quantifiers (forall/
  exists), boolean connectives, and basic arithmetic comparisons - enough
  for ProofWriter-style rulebases, not the richer schemas seen in the
  paper's BioASQ/SARA examples (real numbers with `<=`/`>`, dates).
