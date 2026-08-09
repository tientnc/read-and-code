"""Algorithm 1 (paper) orchestration: autoformalize -> consistency check ->
entailment check -> premise generation, per CoT step. See SPEC.md."""

from dataclasses import dataclass, field

from vericot.autoformalize import UntranslatableError, autoformalize
from vericot.premises import generate_supporting_premise
from vericot.solver import KnowledgeBase


@dataclass
class StepResult:
    index: int
    step_text: str
    status: str  # entailed_direct | entailed_with_premise | contradiction | ungrounded | untranslatable
    premise: str = ""
    detail: str = ""


@dataclass
class VerificationResult:
    steps: list = field(default_factory=list)

    @property
    def valid(self):
        return bool(self.steps) and all(
            r.status in ("entailed_direct", "entailed_with_premise") for r in self.steps
        )


def verify_cot(context_text, cot_steps, provider="openrouter", model=None):
    kb = KnowledgeBase()
    results = []
    for i, step_text in enumerate(cot_steps, start=1):
        try:
            decl, assertion = autoformalize(step_text, context_text, kb, provider=provider, model=model)
        except UntranslatableError as e:
            results.append(StepResult(i, step_text, "untranslatable", detail=str(e)))
            continue

        kb.add_declarations(decl)

        if kb.is_contradicted("", assertion):
            results.append(StepResult(i, step_text, "contradiction"))
            continue

        if kb.is_entailed("", assertion):
            kb.add_established(assertion)
            results.append(StepResult(i, step_text, "entailed_direct"))
            continue

        # generate_supporting_premise already commits each kept premise's
        # declarations to kb as it finds them -- don't re-add p_decl here.
        premise = generate_supporting_premise(step_text, context_text, kb, provider=provider, model=model)
        if premise is not None:
            _, p_assert = premise
            if kb.is_entailed("", assertion, extra_assertions=(p_assert,)):
                kb.add_established(p_assert)
                kb.add_established(assertion)
                results.append(StepResult(i, step_text, "entailed_with_premise", premise=p_assert))
                continue

        results.append(StepResult(i, step_text, "ungrounded"))

    return VerificationResult(results)
