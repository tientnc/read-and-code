---
name: paper-triage
description: Decide whether a paper has usable official code or needs to be rebuilt from the PDF, before any implementation work starts.
---

# Paper triage

Given a paper (arXiv ID, PDF, or URL), decide the reproduction path.

## Steps

1. **Look for official code.** Check, in order: a link in the paper/abstract
   page, the paper's arXiv "Code" link, Papers with Code, and the authors'
   GitHub profiles. A repo named after the paper isn't necessarily official
   — confirm it's linked from the paper or an author's page.
2. **If a candidate repo exists, judge whether it's actually usable:**
   - Does it implement the method the paper describes, or a partial /
     earlier / different version?
   - Last commit recency, open issues about reproducibility, whether it has
     ever run end-to-end for anyone (check issues/discussions).
   - License compatible with forking and adapting.
   - Read the actual entry point and core algorithm file, not just the
     README — READMEs oversell.
3. **Decide:**
   - Usable → official-repo path. Fork/vendor into
     `reproductions/<slug>/`, note the source commit hash.
   - Missing, abandoned, or doesn't match the paper → PDF-only path. Hand
     off to the `pdf-to-spec` skill before writing code.
4. Record the decision and why in `reproductions/<slug>/README.md` — this
   is the first thing a future reader (or agent) needs to know.
