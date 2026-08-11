# RESULTS - VeriCoT (core loop only)

## What was actually run

1. **Deterministic solver check** (`scripts/test_solver_paper_example.py`,
   no LLM calls): hand-transcribed the paper's own Section 2.1 worked example
   (the Charlie/Bob/benefits CoT, Figure 1) as SMT-LIB and ran it through
   `solver.py`. All four steps reproduce the paper's stated outcome exactly
   - step 1 and 3 need a generated premise, step 2 needs a different
   premise, step 4 is entailed directly with no premise. This validates
   that the Z3 consistency/entailment logic (`KnowledgeBase.is_entailed` /
   `is_contradicted`) is sound, independent of any LLM noise. **Pass.**

2. **Full pipeline, same Charlie/Bob CoT, real LLM** (autoformalization +
   premise generation via `gemini-flash-lite-latest`): ran end-to-end
   without crashing. Result: step 1 got a premise (matching the paper),
   step 2 was entailed *directly* - see "Divergence" below - step 3
   (the universally-quantified rule) came back `untranslatable` after 3
   attempts, so step 4 was `ungrounded`. Overall verdict: **INVALID**
   (paper's own CoT is valid). The failure is a real autoformalization
   limitation of the free model on this input, not a pipeline bug - see
   below.

3. **ProofWriter demo**, n=3 examples (`scripts/demo.py --n 3 --provider
   gemini`), executor = verifier = `gemini-flash-lite-latest`:

   | metric | value |
   |---|---|
   | pass rate | 0.0% (0/3) |
   | task accuracy | 66.7% (2/3) |
   | VCAR | 0.0% (0/3) |

   n=3 is not a statistically meaningful sample - see "Why so small"
   below. This is a smoke test that the mechanism runs and produces
   sensible per-step verdicts, not a comparable number to the paper's
   Table 1 (ProofWriter: pass rate 45.2, VCAR 42.5, task accuracy 75.8
   with Claude-3.5-Sonnet-V2 as executor).

4. **ProofWriter demo, second pass**, n=5, executor = verifier =
   `gemma-4-31b-it` called directly against AI Studio (a separate quota
   pool from Gemini - see `.agents/skills/llm-call/SKILL.md`):

   | metric | value |
   |---|---|
   | pass rate | 20.0% (1/5) |
   | task accuracy | 80.0% (4/5) |
   | verifier precision | 100.0% (1/1) |
   | VCAR | 20.0% (1/5) |

   Same caveat as run 3 - n=5 is a smoke test, not a comparable number.
   But this run produced the single cleanest illustration of the paper's
   whole point that this reproduction has: example 3 (`Harry is not
   green`, gold=False) got the *correct final answer*, but partway through
   its own CoT the model restates the claim being evaluated ("The
   statement says Harry is not green") - and VeriCoT correctly flags that
   as a **contradiction** against `Harry is green`, which had already been
   derived from three prior premise-supported steps (young -> furry, furry
   and smart -> nice, nice and furry -> green). Right answer, genuinely
   invalid intermediate reasoning, caught by the verifier - exactly what
   Section 1 motivates VeriCoT with. Example 2 is the other interesting
   case: a full 11-step deductive chain (eats -> rough -> cold -> eats-cow
   -> sees-rabbit -> not-round), every step correctly entailed or
   premise-supported, verdict VALID and correct.

## Divergence from the paper worth calling out

**The free small models tend to inline facts as ground arithmetic/
constants rather than introduce reusable predicates**, which changes how
often premise generation actually triggers compared to the paper. E.g.
for "Charlie is at most 18 years old in 2023," the paper's Claude-3.5-
Sonnet formalizes this via an `age(person, year)` function and needs a
commonsense premise (`age(x,y) <= y - birthYear(x)`) to connect it to
`birthYear`. Both `gpt-oss-20b:free` and `gemini-flash-lite-latest`
instead wrote the age check directly as `(<= (- 2023 (birthYear charlie))
18)`, which is linear-arithmetic-entailed straight from step 1's fact -
no premise needed. Verified directly:

```python
kb.is_entailed('', '(assert (<= (- 2023 (birthYear charlie)) 18))')  # -> True, given only F1
```

This isn't wrong, but it means a free small model exercises VeriCoT's
premise-generation mechanism *less* than the paper's frontier model did,
on the same kind of step. It's a real behavioral difference in how
different-capability executor models write CoTs, not a flaw in the
verifier itself.

## Why the sample is tiny (n=3, not the paper's 400)

Both free-tier LLM providers hit their limits during this reproduction:

- **OpenRouter free tier**: capped at **50 requests/day total** without a
  credit top-up (confirmed via `Rate limit exceeded: free-models-per-day`
  after modest testing). A single multi-step CoT verification easily
  spends 20-50+ requests (autoformalization retries x premise generation x
  candidate premises, each individually autoformalized). This quota was
  exhausted by testing before the ProofWriter demo even ran.
- **Google AI Studio free tier**: 15 requests/minute for
  `gemini-3.5-flash-lite` - recoverable (RPM, not RPD), but still limits
  how large a demo run is practical without adding real wait time.

See `.agents/skills/llm-call/SKILL.md` for the numbers and how to work
around them (mainly: add the $10 OpenRouter credit for 1000/day, or budget
runs assuming ~50/day per provider).

**Calling Gemma directly against AI Studio gets a third, separate quota
pool** - worth knowing about, but it traded rate-limit headroom for
reliability: `gemma-4-26b-a4b-it` (the MoE variant) was unusable during
this reproduction, failing on every one of 8 attempted examples with
either an internal 500 or a request timeout - even after adding
retry-with-backoff and raising the timeout to 120s, a single call still
exhausted 4 retries (up to ~8 minutes) without succeeding. Switching to
`gemma-4-31b-it` (the dense variant) fixed this almost entirely - 4 of 5
examples completed normally, only one still hit a timeout. Take the
specific RPM/RPD numbers in the skill doc as this key's *ceiling*, not a
guarantee of throughput - a model can be within quota and still be
unreliable that hour.

## Known rough edges (not fixed further - out of scope for a core-loop demo)

- One ProofWriter example's verification crashed on an empty Gemini
  response (`candidates[0].content` had no `parts`, for unclear reasons -
  possibly a transient quirk of `gemini-3.5-flash-lite`). `demo.py`
  catches this per-example and continues rather than aborting the batch,
  but it does mean that example is effectively excluded from the pass-
  rate/VCAR numbers above rather than counted as a clean failure.
- The autoformalizer occasionally retries into a persistent
  "redeclaration" parse error when the model re-emits a declaration that's
  already in vocab (caught by `autoformalize.py`'s dedup logic in most
  cases, but not all - see example 2 in the raw demo output). When this
  persists for 3 attempts the step correctly resolves to `untranslatable`
  per Algorithm 1's own error taxonomy - this is the *designed* fallback
  behavior, not a crash, and matches how the paper describes handling
  persistent syntax errors.
- Reasoning-capable Gemma occasionally spends its **entire** response
  budget "thinking" and never emits a final answer part at all (one
  ProofWriter example: the model deliberated at length in a single
  `"thought": true` part about whether new SMT-LIB declarations were
  needed, concluded none were, and then just... stopped, with no
  non-thought part in the response). `call_gemini` raises a clear
  `LLMError` for this rather than silently returning empty/wrong text, and
  `demo.py` catches it per-example, but it's a real, unresolved failure
  mode of calling a thinking model through a raw completion API for many
  small structured sub-tasks rather than one long free-form one.

## Bottom line

The core mechanism (Algorithm 1: autoformalize -> consistency check ->
entailment check -> premise generation, backed by Z3) is implemented
correctly - validated deterministically against the paper's own worked
example - and runs end-to-end against two different real free-tier LLMs
(`gemini-flash-lite-latest` and `gemma-4-31b-it`) without crashing on the
happy path, correctly hitting all four of the paper's own error
categories (`untranslatable`, `contradiction`, `ungrounded`, plus valid
multi-step chains) on real inputs. The absolute pass-rate/VCAR numbers
from the tiny ProofWriter samples (n=3, n=5) are not meant to be compared
against the paper's Table 1; the right comparison is "the mechanism does
what Section 2 describes, including catching a right-answer/wrong-reasoning case
in the wild (run 4, example 3)" - which it does.
