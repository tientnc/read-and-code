"""Premise generation (paper Section 2.3): when a step is neither entailed nor
contradicted, ask the LLM for supporting NL premises (context or
commonsense), autoformalize each, keep only the ones consistent with what's
established so far, and conjoin the survivors into a candidate P_i.

LLM-as-judge filtering (Section 2.4) is explicitly out of scope for this
reproduction's core-loop-only pass - see SPEC.md.
"""

from vericot.autoformalize import UntranslatableError, autoformalize
from vericot.llm import complete

PREMISE_PROMPT = """Given the context and a chain-of-thought step that does not yet logically follow from what's established, propose supporting premises: standalone natural-language statements which, if accepted, would help justify the step. Each premise should come from either (a) the source context/document, or (b) general commonsense - not from the step itself (don't just restate it).

Context:
{context}

Step that needs support:
"{step_text}"

Respond with each premise on its own line, prefixed with "PREMISE: ". Keep each premise minimal and specific. If you can't think of any reasonable supporting premise, respond with exactly: NONE"""


def propose_nl_premises(step_text, context_text, provider="openrouter", model=None):
    out = complete(
        PREMISE_PROMPT.format(context=context_text, step_text=step_text),
        provider=provider,
        model=model,
    )
    if "NONE" in out and "PREMISE:" not in out:
        return []
    premises = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("PREMISE:"):
            premises.append(line[len("PREMISE:") :].strip())
    return premises


def generate_supporting_premise(step_text, context_text, kb, provider="openrouter", model=None):
    """Returns (decl_text, assert_text) for a combined candidate premise
    P_i, or None if no candidate premise could be formalized/kept."""
    nl_premises = propose_nl_premises(step_text, context_text, provider=provider, model=model)
    kept_decls = []
    kept_asserts = []
    for nl in nl_premises:
        try:
            p_decl, p_assert = autoformalize(nl, context_text, kb, provider=provider, model=model)
        except UntranslatableError:
            continue
        if kb.is_consistent_with(p_decl, p_assert, extra_assertions=tuple(kept_asserts)):
            kb.add_declarations(p_decl)
            kept_decls.append(p_decl)
            kept_asserts.append(p_assert)
    if not kept_asserts:
        return None
    return "\n".join(kept_decls), "\n".join(kept_asserts)
