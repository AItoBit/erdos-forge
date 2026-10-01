"""Structured mathematical analysis of an Erdős (or benchmark) target.

Output is a ``ProblemAnalysis`` record, not prose. The controller and the
open-problem guard consume ``prove_vs_formalize`` so an open conjecture is
never silently treated as a theorem to prove.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from erdos_forge.core.state import Problem, ProblemStatus, TargetKind

_OBJECT_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bSet\b|set of"), "set"),
    (re.compile(r"\bList\b"), "list"),
    (re.compile(r"\bNat\b|ℕ|natural"), "natural number"),
    (re.compile(r"\bInt\b|ℤ"), "integer"),
    (re.compile(r"\bRat\b|ℚ"), "rational"),
    (re.compile(r"\bReal\b|ℝ"), "real"),
    (re.compile(r"arithmetic progression|IsAPOfLength|\bAP\b"), "arithmetic progression"),
    (re.compile(r"reciprocal|∑' |harmonic"), "reciprocal sum"),
    (re.compile(r"\bdvd\b|∣"), "divisibility"),
    (re.compile(r"subset of naturals|Set ℕ|Set Nat"), "subset of naturals"),
]

_DOMAIN_FROM_TAG = {
    "additive-combinatorics": "additive combinatorics",
    "combinatorics": "combinatorics",
    "number-theory": "number theory",
    "graph-theory": "graph theory",
    "analysis": "analysis",
    "van-der-waerden": "Ramsey theory",
}

# Only explicit Lean binders, never `(fun x : α => ...)` application arguments.
_BINDER = re.compile(
    r"[({[](?!(?:fun|match|if)\b)([A-Za-z_][A-Za-z0-9_']*(?:\s+[A-Za-z_][A-Za-z0-9_']*)*)\s*:\s*([^)}\]]+)[)}\]]"
)
_EXISTS = re.compile(r"∃\s*([^,{()]+)")
_FORALL = re.compile(r"∀\s*([^,{()]+)")


@dataclass
class ProblemAnalysis:
    problem_id: str
    status: str
    kind: str
    prove_vs_formalize: str  # "prove" | "formalize_only"
    domain: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    quantifiers: list[str] = field(default_factory=list)
    known_results: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    formalization_risks: list[str] = field(default_factory=list)
    notes: str = ""
    statement: str = ""

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "status": self.status,
            "kind": self.kind,
            "prove_vs_formalize": self.prove_vs_formalize,
            "domain": self.domain,
            "objects": self.objects,
            "quantifiers": self.quantifiers,
            "known_results": self.known_results,
            "dependencies": self.dependencies,
            "formalization_risks": self.formalization_risks,
            "notes": self.notes,
            "statement": self.statement,
        }


class MathematicalAnalyzer:
    """Deterministic analysis from Lean + metadata. An LLM can refine later."""

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        thm = problem.theorem
        text = " ".join(p for p in (thm.signature, thm.context, problem.notes, " ".join(problem.tags)) if p)
        prove = "formalize_only" if problem.is_open_conjecture else "prove"
        risks = list(_risks(problem, text))
        return ProblemAnalysis(
            problem_id=problem.id,
            status=problem.status.value,
            kind=problem.kind.value,
            prove_vs_formalize=prove,
            domain=_domains(problem, text),
            objects=_objects(text),
            quantifiers=_quantifiers(thm.signature),
            known_results=list(problem.metadata.get("known_results") or []),
            dependencies=_dependencies(thm.context),
            formalization_risks=risks,
            notes=problem.notes,
            statement=thm.signature,
        )


def _domains(problem: Problem, text: str) -> list[str]:
    found: list[str] = []
    for tag in problem.tags:
        mapped = _DOMAIN_FROM_TAG.get(tag, tag.replace("-", " "))
        if mapped not in found:
            found.append(mapped)
    if "Nat" in text or "ℕ" in text:
        found.append("arithmetic")
    if "List" in text:
        found.append("lists")
    if any(w in text.lower() for w in ("∧", "∨", "↔", "∃", "∀", "prop")):
        found.append("logic")
    # unique, stable order
    seen: set[str] = set()
    out: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _objects(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in _OBJECT_HINTS:
        if pattern.search(text) and label not in found:
            found.append(label)
    return found


def _quantifiers(signature: str) -> list[str]:
    out: list[str] = []
    for m in _BINDER.finditer(signature):
        names, typ = m.group(1).strip(), m.group(2).strip()
        out.append(f"∀ {names} : {typ}")
    for m in _FORALL.finditer(signature):
        out.append(f"∀ {m.group(1).strip()}")
    for m in _EXISTS.finditer(signature):
        out.append(f"∃ {m.group(1).strip()}")
    return out


def _dependencies(context: str) -> list[str]:
    deps: list[str] = []
    for line in context.splitlines():
        stripped = line.strip()
        if stripped.startswith("import "):
            deps.append(stripped[len("import ") :])
        elif stripped.startswith("def ") or stripped.startswith("abbrev "):
            deps.append(stripped.split()[1].split("(")[0].split(":")[0])
    return deps


def _risks(problem: Problem, text: str) -> list[str]:
    risks: list[str] = []
    if problem.is_open_conjecture:
        risks.append("OPEN conjecture: formalize the statement only; never invent a proof or an axiom")
    if problem.kind == TargetKind.CONJECTURE and problem.status == ProblemStatus.PARTIALLY_SOLVED:
        risks.append("partially solved: prove only documented special cases / bounds, not the full claim")
    if "import Mathlib" in (problem.theorem.imports or "") or "import Mathlib\n" in text:
        risks.append("full Mathlib import is expensive; prefer the existing Mathlib name over a new def")
    if re.search(r"\bdef\b", problem.theorem.body_context):
        risks.append("local definition in context: reuse it, do not reinvent the structure")
    if "sorry" in text.lower():
        risks.append("source still contains sorry — treat surrounding lemmas as untrusted until verified")
    return risks
