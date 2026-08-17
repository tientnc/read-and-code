# read-and-code

A Claude Code framework for turning a paper into working, verified code.

Point it at a paper. It figures out the fastest honest path to a running
reproduction, then walks that path with you:

- **Official code exists** -> find it, understand what it actually does (not
  just what the README claims), fork/vendor it, adapt to your environment,
  and verify outputs match the paper's reported numbers/behavior.
- **No usable code** -> read the PDF, pull out the algorithm (equations,
  pseudocode, architecture diagrams, hyperparameter tables), write an
  implementation spec, then build it from that spec.

This repo is the *framework* - skills, commands, and conventions. Individual
reproductions live in [`reproductions/`](reproductions/), one folder each.
Reproductions that outgrew this repo and became their own standalone project
are linked from [`showcase/`](showcase/) instead of vendored here.

## Structure

```
read-and-code/
|-- AGENTS.md              canonical instructions for any coding agent
|-- CLAUDE.md               -> @AGENTS.md (Claude Code entry point)
|-- .claude/commands/       slash commands (/new-paper, ...)
|-- .agents/skills/         reusable skills (paper-triage, pdf-to-spec, ...)
|-- reproductions/          one subfolder per paper reproduced in-repo
|   `-- TEMPLATE/           starting point for a new reproduction
`-- showcase/               write-ups pointing at reproductions that live
                            as their own standalone repos
```

## Workflow

1. `/new-paper <arxiv-id | pdf path | repo URL>` - scaffolds
   `reproductions/<slug>/` and runs the **paper-triage** skill to decide:
   official-repo path or PDF-only path.
2. Official-repo path: clone/fork it into the reproduction folder, read it
   for real (not just skim the README), adapt to run locally, and record
   what changed and why.
3. PDF-only path: run the **pdf-to-spec** skill to produce
   `SPEC.md` (equations, algorithm, architecture, hyperparameters) before
   writing any implementation code.
4. Either path ends the same way: a short `RESULTS.md` comparing what you
   got against what the paper claims, and an honest note on what doesn't
   match and why.

## Reproductions

| Paper | What it does | Scope reproduced | Status |
|---|---|---|---|
| [VeriCoT](reproductions/vericot/) - arXiv:2511.04662 | Verifies chain-of-thought reasoning step-by-step: autoformalizes each step to first-order logic and checks it against a growing Z3 knowledge base for entailment/contradiction. | Core loop only (Algorithm 1) - autoformalization, consistency/entailment checks, premise generation. | Done - see [RESULTS.md](reproductions/vericot/RESULTS.md) |
| [P-FOLIO](reproductions/p-folio/) - arXiv:2410.09207 | Human-written step-by-step reasoning chains built on FOLIO. | Dataset artifact reproduction: full reconstruction from spreadsheet dump, lineage matching against FOLIO ground truth, split reconstruction, and text encoding audit. | Done - see [RESULTS.md](reproductions/p-folio/RESULTS.md) |
| [AlphaAgent](reproductions/alphaagent/) - arXiv:2502.16789 | LLM-driven alpha factor mining with regularized exploration to counteract alpha decay. | Full factor mining workflow, hypothesis generation, Qlib factor execution, Rank IC / ICIR backtest evaluations, and Gemini OpenAI-compatible backend integration. | Done - see [RESULTS.md](reproductions/alphaagent/RESULTS.md) |

