from erdos_forge.lean.diagnostics import Category, axioms_from_output, parse_diagnostics, summarize, uses_sorry

OUTPUT = """C:\\Users\\me\\Temp\\probe.lean:5:23: error: unsolved goals
a b : Nat
h : a ∣ b
⊢ a ≤ b

case succ
n : Nat
⊢ False
C:\\Users\\me\\Temp\\probe.lean:9:4: error: unknown identifier 'Nat.foo'
C:\\Users\\me\\Temp\\probe.lean:12:0: warning: declaration uses 'sorry'
't1' depends on axioms: [propext, Classical.choice]
C:\\Users\\me\\Temp\\probe.lean:14:0: info: 't2' does not depend on any axioms
"""


def test_parse_groups_multiline_messages_and_goals():
    diags = parse_diagnostics(OUTPUT)
    errs = [d for d in diags if d.is_error]
    assert len(errs) == 2
    unsolved = errs[0]
    assert unsolved.category is Category.UNSOLVED_GOALS
    assert unsolved.line == 5 and unsolved.column == 23
    assert len(unsolved.goals) == 2
    assert "⊢ a ≤ b" in unsolved.goals[0]
    assert unsolved.likely_action == "continue_proof"

    unknown = errs[1]
    assert unknown.category is Category.UNKNOWN_IDENTIFIER
    assert unknown.identifier == "Nat.foo"
    assert unknown.likely_action == "retrieve_declaration"


def test_axioms_and_sorry_detection():
    assert axioms_from_output(OUTPUT) == {"t1": ["propext", "Classical.choice"], "t2": []}
    assert uses_sorry(OUTPUT)
    assert not uses_sorry("all good")


def test_lean_4_3x_tagged_format():
    out = (
        "C:\\p\\dbg.lean:2:8: error(lean.unknownIdentifier): Unknown constant `Nat.foo`\n"
        "C:\\p\\dbg.lean:4:8: warning: declaration uses `sorry`\n"
        "`t` depends on axioms: [propext]\n"
    )
    diags = parse_diagnostics(out)
    assert diags[0].category is Category.UNKNOWN_IDENTIFIER
    assert diags[0].code == "lean.unknownIdentifier"
    assert diags[0].identifier == "Nat.foo"
    assert uses_sorry(out)
    assert axioms_from_output(out) == {"t": ["propext"]}


def test_primed_names():
    out = "'add_comm'' depends on axioms: [propext]\n'foo'' does not depend on any axioms\nx.lean:1:1: error: unknown identifier 'Nat.foo''\n"
    assert axioms_from_output(out) == {"add_comm'": ["propext"], "foo'": []}
    assert parse_diagnostics(out)[-1].identifier == "Nat.foo'"


def test_unix_paths_and_lake_noise():
    out = "/home/u/x.lean:2:0: error: type mismatch\n  foo\nhas type Nat\nerror: some lake failure\n"
    diags = parse_diagnostics(out)
    assert diags[0].category is Category.TYPE_MISMATCH
    assert diags[0].message.count("\n") == 2
    assert diags[1].file is None and diags[1].is_error


def test_import_errors_are_classified():
    out = "x.lean:1:0: error: object file '.../Mathlib/Data/Nat/Defs.olean' of module Mathlib.Data.Nat.Defs does not exist"
    assert parse_diagnostics(out)[0].category is Category.IMPORT


def test_summary_is_compact():
    diags = parse_diagnostics(OUTPUT)
    text = summarize(diags, max_chars=400)
    assert "category=unsolved_goals" in text
    assert "declaration uses 'sorry'" not in text  # warnings hidden by default
    assert len(text) <= 700
