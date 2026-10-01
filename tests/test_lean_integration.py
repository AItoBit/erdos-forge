"""Integration tests against a real Lean toolchain.

They run only when `ERDOS_FORGE_LEAN_PROJECT` (or config/lean.yaml) points to a
usable Lake project. Mathlib tests additionally need a built Mathlib.
"""

import os

import pytest

from erdos_forge.config import LeanSettings, RepairSettings, SearchSettings
from erdos_forge.core.controller import RepairController
from erdos_forge.core.state import Problem
from erdos_forge.lean.environment import LeanEnvironment, statement_ok
from erdos_forge.lean.source import Theorem
from erdos_forge.models.mock import HeuristicModel, MockModel

pytestmark = pytest.mark.lean


@pytest.fixture(scope="module")
def env():
    settings = LeanSettings.load()
    env = LeanEnvironment(settings)
    if env.compiler.check_project():
        pytest.skip("no usable Lean project configured (set ERDOS_FORGE_LEAN_PROJECT)")
    return env


def test_doctor_core_compile(env):
    info = env.doctor()
    assert info["core_compile_ok"], info


def test_firewall_real_proof_and_axioms(env):
    thm = Theorem("add_comm'", "theorem add_comm' (a b : Nat) : a + b = b + a")
    report = env.firewall.verify(thm, "theorem add_comm' (a b : Nat) : a + b = b + a := by\n  omega")
    assert report.ok, report.reasons
    assert set(report.axioms) <= {"propext", "Classical.choice", "Quot.sound"}


def test_firewall_rejects_real_sorry_and_wrong_proof(env):
    thm = Theorem("t", "theorem t (a : Nat) : a + 0 = a")
    bad = env.firewall.verify(thm, "theorem t (a : Nat) : a + 0 = a := by\n  exact Nat.foo a")
    assert not bad.ok and any(d.category.value == "unknown_identifier" for d in bad.diagnostics)
    srry = env.firewall.verify(thm, "theorem t (a : Nat) : a + 0 = a := by\n  sorry")
    assert not srry.ok and srry.compile is None


def test_statement_check_tolerates_sorry_only(env):
    thm = Theorem("open_thing", "theorem open_thing : ∀ n : Nat, ∃ m, n < m")
    assert statement_ok(env.check_statement(thm))
    broken = Theorem("broken", "theorem broken : ∀ n : Nat, n < undefined_thing")
    assert not statement_ok(env.check_statement(broken))


def test_repair_loop_end_to_end(env):
    thm = Theorem("lt_succ'", "theorem lt_succ' (n : Nat) : n < n + 1")
    problem = Problem.from_theorem(thm)
    model = MockModel([
        "```lean\ntheorem lt_succ' (n : Nat) : n < n + 1 := by\n  exact Nat.lt_succ_self_wrong n\n```",
        "```lean\ntheorem lt_succ' (n : Nat) : n < n + 1 := by\n  omega\n```",
    ])
    s = SearchSettings()
    s.repair = RepairSettings(max_repairs=2)
    result = RepairController(env, model, s).prove(problem)
    assert result.success, result.failure_reason
    assert result.attempts[0].error_categories == ["unknown_identifier"]
    assert "Nat.lt_succ_self_wrong" in model.calls[1][-1].content


def test_heuristic_baseline_solves_something(env):
    thm = Theorem("mod_two_cases", "theorem mod_two_cases (n : Nat) : n % 2 = 0 ∨ n % 2 = 1")
    s = SearchSettings()
    s.repair = RepairSettings(max_repairs=1)
    result = RepairController(env, HeuristicModel(), s).prove(Problem.from_theorem(thm))
    assert result.success, result.failure_reason


@pytest.mark.mathlib
def test_mathlib_narrow_import(env):
    if not os.environ.get("ERDOS_FORGE_TEST_MATHLIB"):
        pytest.skip("set ERDOS_FORGE_TEST_MATHLIB=1 to run Mathlib tests (slow)")
    thm = Theorem("sq_nonneg_int", "theorem sq_nonneg_int (x : ℤ) : 0 ≤ x ^ 2", context="import Mathlib.Tactic.Positivity")
    report = env.firewall.verify(thm, "theorem sq_nonneg_int (x : ℤ) : 0 ≤ x ^ 2 := by\n  positivity")
    assert report.ok, report.reasons
