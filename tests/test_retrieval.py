from erdos_forge.core.state import Problem
from erdos_forge.lean.source import Theorem
from erdos_forge.retrieval.mathlib_index import DeclarationIndex, index_lean_source
from erdos_forge.retrieval.premise_selection import PremiseSelector, RetrievalQuery, default_selector
from erdos_forge.retrieval.seed import seed_declarations
from erdos_forge.retrieval.theorem_search import TheoremSearch


def test_seed_contains_core_lemmas_used_by_level0():
    names = {d.name for d in seed_declarations()}
    assert {"Nat.add_zero", "Nat.mul_comm", "Nat.pow_two", "List.length_append", "Or.inl"} <= names
    assert any(d.requires_mathlib for d in seed_declarations())


def test_search_finds_add_zero_from_a_goal():
    search = TheoremSearch(DeclarationIndex(seed_declarations()))
    hits = search.search("n + 0 = n", k=10, allow_mathlib=False)
    names = [h.declaration.name for h in hits]
    assert "Nat.add_zero" in names


def test_unknown_identifier_still_surfaces_nearby_nat_lemmas():
    sel = PremiseSelector(DeclarationIndex(seed_declarations()), retrieve_k=40, top_k=10)
    hits = sel.select(RetrievalQuery(text="n + 0 = n", goal="n : Nat\n⊢ n + 0 = n",
                                     identifiers=["Nat.foo"], allow_mathlib=False))
    names = [h.declaration.name for h in hits]
    assert "Nat.add_zero" in names


def test_mathlib_only_decls_are_hidden_without_mathlib_imports():
    sel = default_selector()
    core = sel.select(RetrievalQuery(text="0 ≤ x ^ 2", goal="0 ≤ x ^ 2", allow_mathlib=False))
    assert all(not h.declaration.requires_mathlib for h in core)
    mathlib = sel.select(RetrievalQuery(text="0 ≤ x ^ 2", goal="0 ≤ x ^ 2", allow_mathlib=True))
    assert any(h.declaration.name == "sq_nonneg" for h in mathlib)


def test_index_lean_source_reads_namespaces_and_docs():
    src = """
namespace Foo
/-- addition commutes -/
theorem add_comm (n m : Nat) : n + m = m + n := rfl
end Foo
"""
    decls = index_lean_source(src, "Foo.lean", requires_mathlib=False)
    assert decls[0].name == "Foo.add_comm"
    assert decls[0].docstring == "addition commutes"
    assert "n + m = m + n" in decls[0].signature


def test_select_for_problem_uses_signature_tokens():
    thm = Theorem("mul_comm'", "theorem mul_comm' (a b : Nat) : a * b = b * a")
    problem = Problem(id="t:mul", theorem=thm)
    hits = default_selector().select_for_problem(problem)
    assert any(h.declaration.name == "Nat.mul_comm" for h in hits)
