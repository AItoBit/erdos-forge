from erdos_forge.lean.source import (
    Theorem,
    assemble_file,
    find_top_level_assign,
    load_theorems,
    normalize_signature,
    parse_theorems,
    split_imports,
)
from erdos_forge.config import REPO_ROOT

SRC = """import Mathlib.Tactic.Ring

/-! Module doc -/

namespace Demo

/-- A helper. -/
def double (n : Nat) : Nat := 2 * n

/-- First theorem. -/
theorem double_eq (n : Nat) : double n = n + n := by
  unfold double
  omega

lemma uses_assign_in_binder (f : Nat → Nat := fun x => x) : f 0 = f 0 := rfl

example : (1 : Nat) + 1 = 2 := by decide

end Demo
"""


def test_parse_theorems_hides_proofs_and_builds_context():
    thms = parse_theorems(SRC, "demo.lean")
    assert [t.name for t in thms] == ["double_eq", "uses_assign_in_binder", "example_L17"]
    first = thms[0]
    assert first.reference_proof.startswith("by")
    assert "sorry" not in first.signature
    assert first.signature.startswith("/-- First theorem. -/")
    assert "def double" in first.context
    assert "theorem double_eq" not in thms[1].context  # sibling theorems hidden
    assert thms[2].is_example


def test_assign_inside_binder_default_is_skipped():
    text = "lemma foo (f : Nat → Nat := fun x => x) : f 0 = f 0 := rfl"
    idx = find_top_level_assign(text)
    assert text[idx:].startswith(":= rfl")


def test_split_imports():
    imports, body = split_imports("import A\nimport B\n\nopen Nat\n\ndef x := 1")
    assert imports == "import A\nimport B"
    assert body.startswith("open Nat")


def test_normalize_signature_ignores_docstring_and_whitespace():
    a = "/-- doc -/\ntheorem foo (n : Nat) :\n    n = n"
    b = "theorem foo (n:Nat) : n = n"
    assert normalize_signature(a) == normalize_signature(b)
    assert normalize_signature(a) != normalize_signature("theorem foo (n : Nat) : n ≤ n")


def test_assemble_file_layout_and_audit():
    thm = Theorem("foo", "theorem foo (n : Nat) : n = n", context="import X\n\nopen Nat")
    src = assemble_file(thm, "theorem foo (n : Nat) : n = n := by\n  rfl", preamble="lemma h : True := trivial",
                        max_heartbeats=1000)
    assert src.startswith("import X\n\nset_option autoImplicit false\nset_option relaxedAutoImplicit false\n"
                          "set_option maxHeartbeats 1000\n\nopen Nat")
    assert "lemma h : True := trivial" in src
    assert src.rstrip().endswith("#print axioms foo")


def test_assemble_example_is_renamed_for_audit():
    thm = Theorem("example_L1", "example : True")
    src = assemble_file(thm, "example : True := trivial")
    assert "theorem erdos_forge_audit_target : True := trivial" in src
    assert "#print axioms erdos_forge_audit_target" in src


def test_qualified_theorem_names():
    from erdos_forge.lean.source import qualified_theorem_names

    src = ("namespace A\nsection\ntheorem x : True := trivial\nend\nnamespace B\nlemma y : True := trivial\n"
           "theorem _root_.z : True := trivial\nend B\nend A\ntheorem w : True := trivial\n")
    assert qualified_theorem_names(src) == ["A.x", "A.B.y", "z", "w"]


def test_benchmark_files_parse():
    for rel in ["level0_core/NatArith.lean", "level0_core/Logic.lean", "level0_core/Lists.lean",
                "level1_mathlib/IntRatAlgebra.lean", "erdos/Erdos169Aux.lean"]:
        thms = load_theorems(REPO_ROOT / "benchmarks" / rel)
        assert thms, rel
        for t in thms:
            assert t.reference_proof and "sorry" not in t.reference_proof, (rel, t.name)
