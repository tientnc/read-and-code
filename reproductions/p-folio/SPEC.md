# SPEC - P-FOLIO

Paper: "P-FOLIO: Evaluating and Improving Logical Reasoning with Abundant
Human-Written Reasoning Chains" (Han, Yu, Shen, Riddell, Zhou, Qiao, Zhao,
Yavuz, Liu, Joty, Zhou, Xiong, Radev, Ying, Cohan - Yale/Harvard/NVIDIA/
Salesforce). ACL Anthology 2024.findings-emnlp.966, arXiv:2410.09207.

Built on top of FOLIO: "FOLIO: Natural Language Reasoning with First-Order
Logic" (Han et al., overlapping authors). ACL Anthology 2024.emnlp-main.1229,
arXiv:2209.00840. Official repo: github.com/Yale-LILY/FOLIO.

## Scope

This is a **dataset paper**, not an algorithm paper. "Reproducing" it does
not mean re-running the paper's LLM experiments (single-step inference-rule
classification, proof generation, pass@k, fine-tuning/OOD generalization) -
those are downstream evaluations of the dataset, not the dataset itself.
This reproduction instead rebuilds and validates **the dataset artifact**,
against four concrete concerns:

1. The released data is a raw spreadsheet dump, not a clean structured
   format - rebuild it into one row per instance (JSONL).
2. The paper claims a 70/15/15 train/dev/test split "the same as the split
   for FOLIO" (Section 5) - the released artifact doesn't visibly carry
   this split. Reconstruct it.
3. Verify every P-FOLIO instance is actually traceable to a real FOLIO
   instance, rather than trusting the paper's "built on FOLIO" claim as-is.
4. Verify all natural-language annotation text is readable English (no
   mojibake, encoding issues, or non-English content).

Not reproduced: any of the paper's model evaluations (Sections 4-6),
fine-tuning, or the NL-FOL translation task from the FOLIO paper.

## Data sources

- **Raw released artifact (primary source used here):** ACL Anthology
  attachment,
  `https://aclanthology.org/attachments/2024.findings-emnlp.966.data.zip`.
  Unzips to one file, `LogicSpider Manual Annotation Collection - V1 -
  Proof Collection - All.csv`. Despite being commonly described as "Excel
  format", it is actually a CSV (a Google Sheets export, judging by the
  filename and the vertical-merge artifacts described below) - same
  underlying problem either way: a spreadsheet dump, not a dataset schema.
- **Also exists on HuggingFace** as `yale-nlp/P-FOLIO` (files: `FOLIO.csv`,
  `P-FOLIO.csv`). This repo is **gated** (`"gated": "auto"` per the HF API)
  and there is no `HF_TOKEN` in this environment's `.env`, so unauthenticated
  downloads 401. Not used as a source here. If cross-checking against it
  matters later, the user needs to accept the gate while logged in to
  huggingface.co, generate a token, and add `HF_TOKEN` to the repo-root
  `.env` - noted as a follow-up, not a blocker for this reproduction.
- **FOLIO source of truth:** `github.com/Yale-LILY/FOLIO`,
  `data/v0.0/folio-train.jsonl` (1004 examples) and
  `data/v0.0/folio-validation.jsonl` (204 examples). Fields: `story_id`,
  `example_id`, `premises` (list[str]), `premises-FOL` (list[str]),
  `conclusion` (str), `label` (True/False/Unknown), `source` (wiki/hyb).
  **Only train and validation are public** - the FOLIO repo has never
  released a test split (its README mentions a leaderboard for the
  unreleased test set "coming soon", which as of this writing never
  materialized). 1004 + 204 = 1208, and the FOLIO paper's own reported
  split is 1001/203/226 (train/validation/test) out of 1430 total examples
  - close enough (within rounding/versioning) to confirm the held-out
  remainder is ~226 examples, consistent with test never being released.

  This directly shapes goals 2 and 3 below: since FOLIO's test labels are
  not public, P-FOLIO's claim to inherit FOLIO's split can only be checked
  by elimination, not by direct comparison against a public FOLIO test
  file. (Several P-FOLIO authors are also FOLIO authors - e.g. Simeng Han,
  Dragomir Radev, Caiming Xiong - so private access to FOLIO's held-out
  test set is plausible; this reproduction can't confirm that access, only
  work around its absence from public data.)

## Raw CSV structure (reverse-engineered from the actual file, not assumed)

16071 data rows (plus header), 24 columns:

```
story_id, factuality, bias, NL_grammar_mechanics_check, FOL,
proof_correctness, Corrected Premises - NL, Premises - NL,
Conclusions - NL, Corrected Conclusions - NL, Truth Value,
Premises used, Derivation, Derivation - Corrected, Derivation index,
Inference rule, Premises - FOL - corrected - optimized,
Premises - FOL - corrected, Premises - FOL,
Corrected Conclusions - FOL - optimized, Corrected Conclusion - FOL,
Conclusion - FOL, comment on FOL, comment on Bias
```

Row semantics, inferred from spreadsheet vertical-merge behavior on export
(confirmed by inspecting several story groups directly):

- `story_id` is populated only on the **first row** of a story's block;
  every other row in that block has `story_id = ""` and must be
  forward-filled to reconstruct grouping.
- Within a story block, an **instance row** is any row with a non-empty
  `Truth Value` - it carries one `(premises, conclusion, label)` triple
  plus FOL annotations. `Premises - NL` (and `Premises - FOL`) is
  populated only on the **first instance row** of a story (another
  vertical merge, since multiple instances/conclusions can share one
  premise set) and must be forward-filled within the story to the next
  instance row.
- **Derivation rows** (no Truth Value; has `Derivation` / `Derivation
  index` / `Inference rule`) are proof steps belonging to the instance
  immediately preceding them, up to the next instance or story boundary.
- **Blank rows** (every column empty) are spacer rows between stories in
  the original spreadsheet - drop.
- One corrupted `story_id` value observed: a literal `"("` at row 11690 in
  the data (0-indexed after header), isolated, every other column blank -
  a stray spreadsheet artifact, not a real story. Drop it.
- 493 distinct raw `story_id` tokens; 492 after dropping the `"("`
  artifact. Of those, 490 have >=1 instance row (2 have zero, apparently
  ids whose stories were never annotated or were later removed but the id
  row survived - drop these too, they contribute no instances).
- **1438 instance rows** total (non-empty `Truth Value`) vs. the paper's
  stated **1430** (abstract, Section 1, Section 7). This 8-instance
  discrepancy must be resolved and reported in `RESULTS.md`, not silently
  matched to the paper's number - check for exact-duplicate rows first,
  then any row that looks like leftover QA scratch rather than a real
  instance, before concluding it's a genuine discrepancy between the
  paper and the release.

## Target clean schema (goal 1)

One JSON object per line (JSONL - matches FOLIO's own release format, and
survives embedded newlines/commas in NL fields better than CSV):

- `instance_id`: synthetic, stable - `pfolio-<story_id>-<n>` where `n` is
  the 0-based index of the instance within its story.
- `story_id`: raw story id, as string.
- `premises`: `list[str]`, forward-filled within story. Prefer `Corrected
  Premises - NL` when non-empty, else `Premises - NL`; split the cell on
  embedded newlines (each premise was written one-per-line in the source).
- `premises_fol`: `list[str]`, same forward-fill + newline-split, preferring
  `Premises - FOL - corrected - optimized` > `Premises - FOL - corrected` >
  `Premises - FOL`.
- `conclusion`: `str`, preferring `Corrected Conclusions - NL` else
  `Conclusions - NL`.
- `conclusion_fol`: `str`, preferring `Corrected Conclusions - FOL -
  optimized` > `Corrected Conclusion - FOL` > `Conclusion - FOL`.
- `label`: normalized from raw `Truth Value` (`T`/`F`/`U`) to
  `"True"`/`"False"`/`"Unknown"` - matches FOLIO's own label strings, which
  matters for the split-matching step below.
- `proof`: `list` of `{premises_used, derivation, derivation_index,
  inference_rule}` in row order; use `Derivation - Corrected` when
  non-empty else `Derivation`.
- `num_proof_steps`: `len(proof)`.
- `qc_flags`: `{factuality, bias, nl_grammar_mechanics_check,
  proof_correctness, comment_on_fol, comment_on_bias}` carried through
  verbatim from the instance's first row. These are the paper's own
  annotation-QC columns (Section 3.2's cross-checking process) - kept
  rather than dropped, since discarding annotator-facing QC metadata isn't
  this reproduction's call to make silently.

## Split reconstruction + lineage verification (goals 2 and 3 - same mechanism)

Since FOLIO's own test split was never released, the only way to check the
paper's "same 70/15/15 split as FOLIO" claim is by elimination against what
*is* public:

1. Build a lookup from every FOLIO train/validation example
   (`folio-train.jsonl` + `folio-validation.jsonl`): key =
   `(sorted tuple of normalized premises, normalized conclusion, label)`.
   Normalization: strip, collapse internal whitespace, casefold. Premises
   are sorted defensively even though they're likely written in a fixed
   order per story.
2. For every rebuilt P-FOLIO instance, compute the same key and look it up:
   - Match in `folio-train` -> `split = "train"`.
   - Match in `folio-validation` -> `split = "dev"`.
   - No match anywhere -> `split = "test"` (**inferred, not verified** -
     there is no public FOLIO test file to confirm this against).
3. A match (train or dev) *is* the lineage verification for that instance
   - matching on premises + conclusion + label together is strong enough
     evidence it's a real FOLIO example, not a coincidence.
4. Unmatched instances can't be positively verified from public data alone.
   Report the count, and manually spot-check a sample: does the premise
   topic/vocabulary/style look like a plausible FOLIO story (rather than,
   say, a HybLogic template artifact or something that looks fabricated)?
   This is a manual sanity check, not an automated pass/fail - say so
   plainly in `RESULTS.md`.
5. Report final split sizes and check: (a) proportions close to 70/15/15
   as the paper claims, (b) proportions close to FOLIO's own reported
   1001/203/226 (roughly matching, since P-FOLIO is a subset/superset
   variant of FOLIO's instance set, not identical in count).
6. **Key risk to matching:** P-FOLIO's NL premises/conclusions went through
   its own "Corrected" editing pass (grammar/wording fixes per the
   `Corrected Premises - NL` / `Corrected Conclusions - NL` columns), which
   can break exact-text matching against FOLIO's original wording even for
   genuinely-derived instances. Mitigation, in order of preference:
   - Try matching on **uncorrected** NL text first (`Premises - NL` /
     `Conclusions - NL`, before any correction) - most likely to match
     FOLIO's original wording verbatim.
   - If the NL match rate is low, fall back to matching on **FOL
     formulas** (`premises_fol` / `conclusion_fol`) against FOLIO's
     `premises-FOL`, with light normalization (whitespace, and treating
     the "optimized" FOL columns' algebraic simplifications as expected
     drift rather than a correction of meaning).
   - Report which matching strategy was actually used, and the resulting
     match rate for each, in `RESULTS.md` - don't silently pick the one
     that gives the "nicer" numbers.

## English-annotation check (goal 4)

Scope: NL fields only - `premises`, `conclusion`, and all `derivation`/
`premises_used` text in the `proof` list. FOL formula fields are explicitly
**out of scope** here: they legitimately contain non-ASCII logic symbols
(`forall`, `exists`, negation, conjunction, disjunction, implication, XOR)
that are not an encoding bug.

Approach: **heuristic, not an LLM call.** The dataset's own QC process
(Section 3.2 of the FOLIO paper: Grammarly + graduate-student review for
language naturalness) plus the fact that every instance is meant to derive
from FOLIO (itself English-only) make this fundamentally a mojibake/
encoding sniff test, not a nuanced language-quality judgment call - LLM
judging would be overkill for what heuristics catch cheaply and
deterministically.

- **Mojibake/encoding check:** flag any NL field containing U+FFFD
  (replacement character), unpaired surrogate artifacts, or common
  mojibake byte patterns from UTF-8 text mis-decoded as Latin-1 (the
  classic case: an accented character turning into a two-character
  garble starting with a capital A-with-tilde).
- **Non-English check:** run `langdetect` (or equivalent) per NL field
  (joined premises, conclusion, each derivation string), with a length
  floor (skip fields under ~20 characters - too short for reliable
  language ID) and flag anything not detected as English.
- **Manually review every flagged field** before reporting "no issues" -
  `langdetect` gives false positives on short/formulaic/heavily-symbolic
  sentences, so the raw flag count is a worklist, not a verdict.

## Ambiguities / choices made here

- The two zero-instance `story_id` groups (raw ids with a story_id row but
  no instance rows) are dropped entirely rather than kept as empty
  placeholders - they contribute nothing to the dataset and there's no
  clean way to represent "a story with no instances" in the target schema.
- `qc_flags` fields are kept even though most are expected to be sparse/
  empty (they're the annotators' scratch notes, not populated for most
  rows) - decision explained above.
- Matching FOLIO by `(premises, conclusion, label)` assumes no two
  distinct FOLIO examples share the exact same triple. Spot-check this
  assumption (count exact-duplicate keys within FOLIO itself) before
  trusting 1:1 matches as unambiguous.
- HF's gated `yale-nlp/P-FOLIO` copy is not cross-checked against the ACL
  zip in this reproduction (no token available) - flagged as a follow-up
  for the user, not a blocker.
