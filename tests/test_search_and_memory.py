from erdos_forge.core.state import Attempt, Problem
from erdos_forge.lean.diagnostics import Category, LeanDiagnostic
from erdos_forge.lean.goal_parser import state_hash
from erdos_forge.lean.source import Theorem
from erdos_forge.lemma.library import GeneratedLemmaLibrary
from erdos_forge.memory.failure_memory import FailureMemory
from erdos_forge.models.base import Completion
from erdos_forge.models.mock import MockModel
from erdos_forge.prover.ensemble import EnsembleModel
from erdos_forge.prover.tactic_generator import split_candidates
from erdos_forge.search.node import ProofNode
from erdos_forge.search.scoring import score_state
from erdos_forge.search.tree import ProofTree


def test_equivalent_goals_share_a_hash():
    a = "n : Nat\n⊢ n + 0 = n"
    b = "n : Nat\n  \n⊢ n + 0 = n"
    assert state_hash([a]) == state_hash([b])
    assert state_hash([a]) != state_hash(["n : Nat\n⊢ 0 + n = n"])


def test_tree_deduplicates_repeated_states():
    root = ProofNode.root("S0", state_hash="h0")
    tree = ProofTree(root)
    first = tree.add(root.child(action="simp", proof_state="S1", code="simp", state_hash="h1", compile_ok=True))
    again = tree.add(root.child(action="rw", proof_state="S1", code="rw", state_hash="h1", compile_ok=True))
    assert first is not None and again is None
    assert len(tree.nodes) == 2


def test_solved_state_outscores_a_deep_unsolved_state():
    solved = score_state(llm_p=0.4, n_goals=0, depth=3, compile_ok=True)
    stuck = score_state(llm_p=0.9, n_goals=4, goal_complexity=3, depth=20, compile_ok=True)
    assert solved > stuck
    assert score_state(compile_ok=False) < 0


def test_failure_memory_recalls_unknown_identifiers():
    mem = FailureMemory()
    problem = Problem(id="t", theorem=Theorem("add_zero_right", "theorem add_zero_right (n : Nat) : n + 0 = n"))
    attempt = Attempt(index=0, kind="generate", response="", diagnostics=[
        LeanDiagnostic("error", "unknown identifier 'Nat.foo'", Category.UNKNOWN_IDENTIFIER, identifier="Nat.foo"),
    ])
    mem.remember(problem, attempt)
    hints = mem.hints(problem, identifiers=["Nat.foo"])
    assert hints and "Nat.foo" in hints[0]


def test_lemma_library_deduplicates_and_round_trips(tmp_path):
    lib = GeneratedLemmaLibrary(tmp_path / "lemmas.jsonl")
    decl = "lemma helper (n : Nat) : n + 0 = n := by rfl"
    assert lib.add(decl, "p1") is not None
    assert lib.add(decl, "p2") is not None
    assert len(lib) == 1
    again = GeneratedLemmaLibrary(tmp_path / "lemmas.jsonl")
    assert len(again) == 1 and again.all()[0].name == "helper"


def test_tactic_generator_splits_labelled_and_fenced_candidates():
    text = """
Candidate 1:
rw [Nat.add_comm]
Candidate 2:
omega
"""
    assert split_candidates(text) == ["rw [Nat.add_comm]", "omega"]
    fenced = "```lean\nrfl\n```\n```lean\nomega\n```"
    assert split_candidates(fenced) == ["rfl", "omega"]


def test_ensemble_deduplicates_model_outputs():
    a = MockModel(["```lean\nrfl\n```"])
    b = MockModel(["```lean\nrfl\n```", "```lean\nomega\n```"])
    ens = EnsembleModel([a, b])
    # each inner model is called once; b returns its first scripted response
    out = ens.complete([])
    assert out.texts == ["```lean\nrfl\n```"]
    # two distinct models, same text → one candidate
    assert isinstance(out, Completion)
