---
description: Scaffold a new paper reproduction and run triage to pick its path
---

Given `$ARGUMENTS` (an arXiv ID, a path to a PDF, or an official repo URL):

1. Pick a short `kebab-case` slug for the paper (author+year or a
   recognizable short name) and create `reproductions/<slug>/` by copying
   the structure of `reproductions/TEMPLATE/`.
2. Run the **paper-triage** skill to decide the official-repo path or the
   PDF-only path, and record the decision in
   `reproductions/<slug>/README.md`.
3. If PDF-only, immediately hand off to the **pdf-to-spec** skill to
   produce `reproductions/<slug>/SPEC.md` before writing any code.
4. Stop after triage (and spec, if applicable) - don't start implementing
   in the same pass. Report the decision and next step back to the user.
