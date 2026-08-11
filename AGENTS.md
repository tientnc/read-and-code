# read-and-code - agent instructions

This repo reproduces ML papers as working, verified code. Every reproduction
starts with the same fork in the road, decided by the **paper-triage**
skill (`.agents/skills/paper-triage/SKILL.md`):

1. **Official code exists.** Don't just skim the README - read the actual
   code to understand what it does, since paper repos routinely drift from
   what the paper claims. Fork or vendor it into
   `reproductions/<slug>/`, adapt it to run locally, and note every
   deviation from upstream and why it was necessary.
2. **No usable code.** Run the **pdf-to-spec** skill
   (`.agents/skills/pdf-to-spec/SKILL.md`) first. Produce
   `reproductions/<slug>/SPEC.md` - equations, algorithm/pseudocode,
   architecture, hyperparameters, evaluation protocol - before writing any
   implementation. Implementing straight from a half-remembered read of the
   PDF produces code that looks right and isn't.

Both paths converge on the same finish line: `reproductions/<slug>/RESULTS.md`
comparing what was actually obtained against what the paper reports, stated
honestly - including where it doesn't match and the best guess at why.

## Ground rules

- Don't fabricate results. If something wasn't run, say it wasn't run.
- Prefer the smallest reproduction that tests the paper's actual claim over
  a maximal, feature-complete port of the whole official repo.
- A reproduction that became its own large project (its own repo, its own
  environment, no longer a small folder) gets a short write-up in
  `showcase/` instead of being squeezed into `reproductions/`. See
  `showcase/alphaagent.md` for the shape of that write-up.
- Use `reproductions/TEMPLATE/` as the starting structure for a new
  reproduction folder.
