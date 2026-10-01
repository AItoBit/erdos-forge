from erdos_forge.config import REPO_ROOT
from erdos_forge.core.state import Problem, ProblemStatus, TargetKind
from erdos_forge.formalizer.equivalence_checker import check_equivalence
from erdos_forge.formalizer.math_analyzer import MathematicalAnalyzer
from erdos_forge.formalizer.problem_parser import parse_target
from erdos_forge.formalizer.statement_validator import validate_statement
from erdos_forge.lean.source import Theorem
from tests.fakes import fake_env


def test_open_conjecture_is_formalize_only_not_prove():
    problem = parse_target(str(REPO_ROOT / "data" / "problems" / "erdos_169_conjecture.json"))
    analysis = MathematicalAnalyzer().analyze(problem)
    assert analysis.prove_vs_formalize == "formalize_only"
    assert analysis.kind == "conjecture"
    assert any("OPEN" in r for r in analysis.formalization_risks)
    assert "additive combinatorics" in analysis.domain


def test_analyzer_extracts_quantifiers_and_objects():
    thm = Theorem("exists_gt'", "theorem exists_gt' (n : Nat) : ∃ m, n < m")
    problem = Problem(id="t:ex", theorem=thm, status=ProblemStatus.SOLVED, kind=TargetKind.THEOREM)
    analysis = MathematicalAnalyzer().analyze(problem)
    assert analysis.prove_vs_formalize == "prove"
    assert "natural number" in analysis.objects
    assert any(q.startswith("∀ n") for q in analysis.quantifiers)
    assert any(q.startswith("∃") for q in analysis.quantifiers)


def test_statement_validator_and_equivalence(tmp_path):
    env = fake_env(tmp_path)
    left = Theorem("add_zero_right", "theorem add_zero_right (n : Nat) : n + 0 = n")
    right = Theorem("add_zero_right", "theorem add_zero_right (n : Nat) : n + 0 = n")
    other = Theorem("add_zero_right", "theorem add_zero_right (n : Nat) (h : n = 0) : n + 0 = n")
    assert validate_statement(env, left).ok  # fake oracle treats sorry as warning-only success
    eq = check_equivalence(env, left, right)
    assert eq.syntactic and eq.both_elaborate
    assert not check_equivalence(env, left, other).syntactic
