"""Z3-backed consistency/entailment checks over accumulated SMT-LIB text.

See SPEC.md "Consistency / entailment checks" for the exact definitions
this implements.
"""

import z3


class SMTLIBError(RuntimeError):
    pass


def _parse(smt_text, ctx):
    try:
        return z3.parse_smt2_string(smt_text, ctx=ctx)
    except z3.Z3Exception as e:
        raise SMTLIBError(str(e)) from e


class KnowledgeBase:
    """Accumulated vocabulary (declarations) + established formulas.

    Z3's parser only resolves names against declarations present in the
    SMT-LIB text being parsed, so each check re-parses the full running
    vocabulary + assertion text from scratch under a fresh Context rather
    than merging z3 ASTs from separate parses (those live in separate
    contexts and don't mix directly).
    """

    def __init__(self):
        self.declarations_text = []  # list[str] of declare-* lines, in order
        self.established_text = []  # list[str] of "(assert ...)" lines already entailed/added

    def add_declarations(self, decl_text):
        if decl_text.strip():
            self.declarations_text.append(decl_text.strip())

    def add_established(self, assert_text):
        self.established_text.append(assert_text.strip())

    def _solver_with_established(self, extra_decl_text="", extra_assertions=()):
        """A fresh (ctx, solver) with all established assertions loaded,
        vocabulary extended with extra_decl_text (new decls for a
        not-yet-established formula), plus any extra_assertions (e.g. a
        candidate premise being tried tentatively, not yet committed)."""
        ctx = z3.Context()
        solver = z3.Solver(ctx=ctx)
        preamble = "\n".join(self.declarations_text + [extra_decl_text])
        for a in _parse("\n".join([preamble] + self.established_text + list(extra_assertions)), ctx):
            solver.add(a)
        return ctx, solver, preamble

    def check_new_formula(self, decl_text, assert_text):
        """Validate decl_text/assert_text parse against current vocab plus
        any new declarations. Raises SMTLIBError on syntax/scope errors.
        Returns the parsed new assertions (for informational use only)."""
        ctx = z3.Context()
        _parse("\n".join(self.declarations_text + [decl_text]), ctx)
        return _parse("\n".join(self.declarations_text + [decl_text, assert_text]), ctx)

    def is_contradicted(self, decl_text, assert_text, extra_assertions=()):
        """True if established U extra_assertions U {assert_text} is unsat,
        i.e. that set |= not(assert_text)."""
        ctx, solver, preamble = self._solver_with_established(decl_text, extra_assertions)
        new_formulas = _parse("\n".join([preamble, assert_text]), ctx)
        if not new_formulas:
            raise SMTLIBError("assert_text produced no assertions")
        for f in new_formulas:
            solver.add(f)
        return solver.check() == z3.unsat

    def is_entailed(self, decl_text, assert_text, extra_assertions=()):
        """True if established U extra_assertions |= assert_text, i.e.
        established U extra_assertions U {not assert_text} is unsat.

        extra_assertions lets a candidate premise be tried tentatively
        (Section 2.3) without committing it via add_established first."""
        ctx, solver, preamble = self._solver_with_established(decl_text, extra_assertions)
        new_formulas = _parse("\n".join([preamble, assert_text]), ctx)
        if not new_formulas:
            raise SMTLIBError("assert_text produced no assertions")
        negated = z3.Not(z3.And(new_formulas)) if len(new_formulas) > 1 else z3.Not(new_formulas[0])
        solver.add(negated)
        return solver.check() == z3.unsat

    def is_consistent_with(self, decl_text, assert_text, extra_assertions=()):
        """True if established U extra_assertions U {assert_text} is sat
        (not contradicted)."""
        return not self.is_contradicted(decl_text, assert_text, extra_assertions)
