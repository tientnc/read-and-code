"""Sanity check: reproduce the paper's own Section 2.1 worked example (Figure 1 /
Charlie-Bob benefits) purely with hand-written SMT-LIB, no LLM involved.
This validates solver.py's semantics before autoformalization (which adds
LLM noise) is layered on top."""

from vericot.solver import KnowledgeBase

BASE_DECL = """
(declare-sort Person)
(declare-const charlie Person)
(declare-const bob Person)
(declare-fun birthYear (Person) Int)
(declare-fun LivesWith (Person Person) Bool)
(declare-fun Parent (Person Person) Bool)
"""

kb = KnowledgeBase()
kb.add_declarations(BASE_DECL)

# Step 1: F1 = birthYear(charlie)=2005 & LivesWith(charlie,bob) & Parent(bob,charlie)
F1 = "(assert (and (= (birthYear charlie) 2005) (LivesWith charlie bob) (Parent bob charlie)))"
assert not kb.is_entailed("", F1), "F1 should not be entailed by empty F_0"
assert kb.is_consistent_with("", F1), "F1 should be consistent (F_0 is empty)"
kb.add_established(F1)  # P1 == F1, per the paper
print("Step 1 OK: F1 added as its own premise.")

# Step 2: F2 = age(charlie,2023) <= 18
AGE_DECL = "(declare-fun age (Person Int) Int)"
F2 = "(assert (<= (age charlie 2023) 18))"
assert not kb.is_entailed(AGE_DECL, F2), "F2 should not follow from F1 alone"

P2 = "(assert (forall ((x Person) (y Int)) (<= (age x y) (- y (birthYear x)))))"
assert kb.is_consistent_with(AGE_DECL, P2), "P2 should be consistent with F1"
assert kb.is_entailed(AGE_DECL, F2, extra_assertions=(P2,)), "F1 + P2 should entail F2"
kb.add_declarations(AGE_DECL)
kb.add_established(P2)
kb.add_established(F2)
print("Step 2 OK: P2 generated, F1+P2 |= F2.")

# Step 3: F3 = forall x. (age(x,2023)<=18 & exists y. LivesWith(x,y) & Parent(y,x)) -> Qualifies(x)
QUALIFIES_DECL = "(declare-fun Qualifies (Person) Bool)"
F3 = """(assert (forall ((x Person))
          (=> (and (<= (age x 2023) 18)
                   (exists ((y Person)) (and (LivesWith x y) (Parent y x))))
              (Qualifies x))))"""
assert not kb.is_entailed(QUALIFIES_DECL, F3), "F3 should not follow from F1+P2+F2 alone"

# P3: the stronger rule from the source document (threshold 21, not 18)
P3 = """(assert (forall ((x Person))
          (=> (and (< (age x 2023) 21)
                   (exists ((y Person)) (and (LivesWith x y) (Parent y x))))
              (Qualifies x))))"""
assert kb.is_consistent_with(QUALIFIES_DECL, P3), "P3 should be consistent with F1+P2+F2"
assert kb.is_entailed(QUALIFIES_DECL, F3, extra_assertions=(P3,)), "established + P3 should entail F3"
kb.add_declarations(QUALIFIES_DECL)
kb.add_established(P3)
kb.add_established(F3)
print("Step 3 OK: P3 generated (stronger threshold), established + P3 |= F3.")

# Step 4: F4 = Qualifies(charlie) -- should now be entailed with NO new premise
F4 = "(assert (Qualifies charlie))"
assert kb.is_entailed("", F4), "F4 should be entailed by established knowledge with no new premise"
print("Step 4 OK: F4 entailed directly, no premise needed -- matches the paper.")

print("\nAll assertions from the paper's worked example hold. solver.py is sound for this case.")
