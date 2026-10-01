import pytest

from erdos_forge.lean.firewall import scan_source
from erdos_forge.lean.source import Theorem
from erdos_forge.prover.extract import ExtractionError, extract_candidate
from tests.fakes import fake_env

THM = Theorem("add_zero_right", "theorem add_zero_right (n : Nat) : n + 0 = n", context="")


# ------------------------------------------------------------------ scanning


@pytest.mark.parametrize(
    "src,expected",
    [
        ("theorem t : True := by sorry", ["sorry"]),
        ("theorem t : True := by admit", ["admit"]),
        ("axiom bad : False\ntheorem t : True := trivial", ["axiom"]),
        ("theorem t : 1 = 1 := by native_decide", ["native_decide"]),
        ("theorem t : 1 = 1 := by decide +native", ["native_decide"]),
        ("@[implemented_by foo] def x := 1", ["implemented_by"]),
        ("-- sorry in a comment is fine\ntheorem t : True := trivial", []),
        ('def s := "sorry"\ntheorem t : True := trivial', []),
        ("theorem my_axiom_free : True := trivial", []),
    ],
)
def test_scan_source(src, expected):
    assert scan_source(src) == expected


# ---------------------------------------------------------------- extraction


def test_extract_simple_block():
    resp = "Here you go:\n```lean\ntheorem add_zero_right (n : Nat) : n + 0 = n := by\n  rfl\n```"
    cand = extract_candidate(resp, THM)
    assert cand.main_declaration.startswith("theorem add_zero_right")
    assert cand.preamble == ""


def test_extract_with_helpers_and_dropped_imports():
    resp = """```lean
import Mathlib

lemma helper (n : Nat) : n + 0 = n := rfl

theorem add_zero_right (n : Nat) : n + 0 = n := by
  exact helper n
```"""
    cand = extract_candidate(resp, THM)
    assert cand.dropped_imports == ["import Mathlib"]
    assert cand.preamble.startswith("lemma helper")
    assert "exact helper n" in cand.main_declaration


def test_extract_drops_repeated_context():
    thm = Theorem("t", "theorem t : double 1 = 2", context="def double (n : Nat) : Nat := 2 * n")
    resp = "```lean\ndef double (n : Nat) : Nat := 2 * n\n\ntheorem t : double 1 = 2 := by rfl\n```"
    cand = extract_candidate(resp, thm)
    assert cand.preamble == ""
    assert cand.dropped_duplicates


def test_extract_errors():
    with pytest.raises(ExtractionError):
        extract_candidate("I cannot do this.", THM)
    with pytest.raises(ExtractionError):
        extract_candidate("```lean\ntheorem add_zero_right (n : Nat) : n + 0 = n := by\n```", THM)
    with pytest.raises(ExtractionError):
        extract_candidate("```lean\ntheorem other : True := trivial\ntheorem another : True := trivial\n```", THM)


# ------------------------------------------------------------------ firewall


def test_firewall_accepts_clean_proof(tmp_path):
    env = fake_env(tmp_path)
    report = env.firewall.verify(THM, "theorem add_zero_right (n : Nat) : n + 0 = n := by\n  GOOD")
    assert report.ok, report.reasons
    assert report.axioms == ["propext", "Quot.sound"]
    assert "#print axioms add_zero_right" in report.source


def test_firewall_rejects_statement_change(tmp_path):
    env = fake_env(tmp_path)
    report = env.firewall.verify(THM, "theorem add_zero_right (n : Nat) : n = n := by\n  GOOD")
    assert not report.ok
    assert any("statement differs" in r for r in report.reasons)
    assert report.compile is None  # rejected before spending a compile


def test_firewall_rejects_sorry_and_bad_axioms(tmp_path):
    env = fake_env(tmp_path)
    r1 = env.firewall.verify(THM, "theorem add_zero_right (n : Nat) : n + 0 = n := by\n  sorry")
    assert not r1.ok and r1.forbidden == ["sorry"]
    r2 = env.firewall.verify(THM, "theorem add_zero_right (n : Nat) : n + 0 = n := by\n  BADAXIOM")
    assert not r2.ok and any("disallowed axioms: myAxiom" in r for r in r2.reasons)


def test_firewall_rejects_axiom_in_preamble(tmp_path):
    env = fake_env(tmp_path)
    report = env.firewall.verify(THM, "theorem add_zero_right (n : Nat) : n + 0 = n := by\n  GOOD",
                                 preamble="axiom cheat : ∀ n : Nat, n + 0 = n")
    assert not report.ok and report.forbidden == ["axiom"]


def test_check_file_audits_every_theorem(tmp_path):
    env = fake_env(tmp_path)
    src = "theorem a : True := GOOD\n\nlemma b : True := GOOD\n"
    report = env.firewall.check_file(src)
    assert report.ok
    assert "#print axioms a" in report.source and "#print axioms b" in report.source
