---
name: pdf-to-spec
description: Extract a paper's method into an implementation spec (equations, algorithm, architecture, hyperparameters) before writing code, for papers with no usable official code.
---

# PDF to spec

Used when `paper-triage` decides there's no usable official code. Goal: a
`SPEC.md` complete enough that implementing from it doesn't require
re-reading the PDF for every design decision.

## What to pull out of the PDF

- **Core equations/algorithm**, transcribed exactly - don't paraphrase math.
  Include the algorithm box/pseudocode verbatim if the paper has one.
- **Architecture**: layers, dimensions, connections - from diagrams and the
  text describing them (diagrams alone often omit details the text has).
- **Hyperparameters and training setup**: learning rate, batch size,
  optimizer, schedule, number of steps/epochs, dataset splits - usually
  buried in an appendix or a table, not the main text.
- **Evaluation protocol**: exact metric definitions, which split, how
  results in the paper's tables were produced. This is what `RESULTS.md`
  will later be compared against, so it has to be unambiguous.
- **Ambiguities**: anywhere the paper underspecifies something needed to
  implement it. List these explicitly in `SPEC.md` rather than silently
  picking a default - the choice made should be visible and revisitable.

## Output

Write `reproductions/<slug>/SPEC.md` with these sections. Only after it's
done, start implementing - and implement to the spec, not back to a fresh
read of the PDF.
