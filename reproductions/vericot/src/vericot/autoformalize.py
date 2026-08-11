"""Two-stage NL -> SMT-LIB autoformalization (paper Section 2.2).

Stage 1 asks the LLM to translate a CoT step into SMT-LIB using only the
vocabulary already declared. If that's insufficient (or doesn't parse),
stage 2 asks for new declarations, then stage 1 is retried. Up to
MAX_RETRIES attempts total, per the paper ("we allow this to repeat up to
three times before giving up").
"""

import re

from vericot.llm import complete
from vericot.solver import SMTLIBError

MAX_RETRIES = 3

INSUFFICIENT_MARKER = "INSUFFICIENT_VOCAB"

STAGE1_PROMPT = """You are translating one step of a chain-of-thought into first-order logic, encoded as SMT-LIB (to be checked with the Z3 solver).

Existing declared vocabulary (sorts, functions, constants) available to you:
{vocab}

Context (question and/or source document, for reference only):
{context}

Step to translate:
"{step_text}"

Using ONLY the vocabulary listed above (do not invent any new declare-fun / declare-sort / declare-const), write one or more SMT-LIB `(assert ...)` statements that formalize this step as a first-order logic formula. Use `forall` / `exists` for universally/existentially quantified statements, and reuse existing predicate/function/constant names exactly as declared.

If the existing vocabulary is NOT sufficient to express this step, respond with exactly the single line:
{marker}

Otherwise, respond with ONLY the SMT-LIB assert statement(s) - no explanation, no markdown code fences, no commentary."""

STAGE2_PROMPT = """The following chain-of-thought step could not be translated to SMT-LIB with the current vocabulary.

Existing vocabulary:
{vocab}

Context:
{context}

Step:
"{step_text}"

Write ONLY the new SMT-LIB declarations (declare-sort / declare-fun / declare-const) needed to express this step. Use new names that don't collide with the existing vocabulary above. Respond with ONLY the declarations - no explanation, no markdown code fences, no commentary."""


class UntranslatableError(RuntimeError):
    def __init__(self, step_text, reason):
        super().__init__(f"untranslatable after {MAX_RETRIES} attempts: {step_text!r} ({reason})")
        self.step_text = step_text
        self.reason = reason


def extract_sexprs(text, heads):
    """Pull out balanced top-level S-expressions from text whose head atom
    is one of `heads` (e.g. "declare-fun", "assert"). Tolerates prose /
    markdown fences the model added despite instructions not to."""
    text = re.sub(r"```[a-zA-Z0-9]*", "", text).replace("```", "")
    exprs = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                head_match = re.match(r"\(\s*([\w-]+)", candidate)
                if head_match and head_match.group(1) in heads:
                    exprs.append(candidate)
                start = None
    return exprs


def _declared_names(decls):
    """Names introduced by a list of declare-* SMT-LIB lines."""
    names = set()
    for d in decls:
        m = re.match(r"\(\s*declare-(?:fun|sort|const)\s+([\w.\-]+)", d)
        if m:
            names.add(m.group(1))
    return names


def _dedupe_new_decls(new_decls, existing_decls):
    """Drop any declaration whose name is already declared -- small
    models sometimes re-emit a declare-* for a name that's already in
    vocab (e.g. when stage 1 failed for a reason unrelated to missing
    vocab), which Z3 rejects as a redeclaration error."""
    existing_names = _declared_names(existing_decls)
    kept = []
    for d in new_decls:
        name = next(iter(_declared_names([d])), None)
        if name and name not in existing_names:
            kept.append(d)
            existing_names.add(name)
    return kept


def autoformalize(step_text, context_text, kb, provider="openrouter", model=None):
    """Translate step_text into (decl_text, assert_text) SMT-LIB against
    kb's current vocabulary. Returns the pair on success. Raises
    UntranslatableError after MAX_RETRIES failed attempts."""
    accumulated_new_decls = []
    last_reason = "no attempts made"
    for attempt in range(MAX_RETRIES):
        vocab = "\n".join(kb.declarations_text + accumulated_new_decls) or "(none declared yet)"
        stage1_out = complete(
            STAGE1_PROMPT.format(vocab=vocab, context=context_text, step_text=step_text, marker=INSUFFICIENT_MARKER),
            provider=provider,
            model=model,
        )
        if INSUFFICIENT_MARKER not in stage1_out:
            asserts = extract_sexprs(stage1_out, heads={"assert"})
            if asserts:
                decl_text = "\n".join(accumulated_new_decls)
                assert_text = "\n".join(asserts)
                try:
                    kb.check_new_formula(decl_text, assert_text)
                    return decl_text, assert_text
                except SMTLIBError as e:
                    last_reason = f"parse error: {e}"
            else:
                last_reason = "stage-1 output had no (assert ...) forms"
        else:
            last_reason = "model reported insufficient vocabulary"

        # Extend vocabulary (stage 2) and retry.
        stage2_out = complete(
            STAGE2_PROMPT.format(vocab=vocab, context=context_text, step_text=step_text),
            provider=provider,
            model=model,
        )
        raw_new_decls = extract_sexprs(stage2_out, heads={"declare-fun", "declare-sort", "declare-const"})
        new_decls = _dedupe_new_decls(raw_new_decls, kb.declarations_text + accumulated_new_decls)
        if new_decls:
            accumulated_new_decls.extend(new_decls)
        else:
            last_reason = f"{last_reason}; stage-2 produced no new (non-duplicate) declarations"

    raise UntranslatableError(step_text, last_reason)
