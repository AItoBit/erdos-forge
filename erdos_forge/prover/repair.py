"""Build the structured feedback shown to the model after a rejected attempt."""

from __future__ import annotations

from collections import Counter

from erdos_forge.core.state import Attempt
from erdos_forge.lean.diagnostics import Category, LeanDiagnostic, errors, summarize


def _hint(diags: list[LeanDiagnostic]) -> str:
    cats = Counter(d.category for d in errors(diags))
    hints: list[str] = []
    if cats[Category.UNKNOWN_IDENTIFIER]:
        names = sorted({d.identifier for d in diags if d.identifier})
        hints.append(
            "Unknown identifiers: " + ", ".join(names or ["?"])
            + ". These names do not exist with the current imports; use a different Mathlib lemma or prove the fact inline."
        )
    if cats[Category.UNKNOWN_TACTIC]:
        hints.append("A tactic name is unknown here (core Lean without Mathlib has no norm_num/linarith/aesop/ring).")
    if cats[Category.UNSOLVED_GOALS]:
        hints.append("Goals remain after your tactic block; the remaining goals are listed above. Close each of them.")
    if cats[Category.TYPE_MISMATCH]:
        hints.append("A term has the wrong type; check argument order, implicit arguments and coercions (↑).")
    if cats[Category.PARSER]:
        hints.append("Syntax error: check Lean 4 syntax (fun x => ..., `·` bullets, `with` in induction/cases, indentation).")
    if cats[Category.TIMEOUT]:
        hints.append("The elaborator timed out; use a more targeted tactic (simp only [...], specific lemmas) or split the proof.")
    if cats[Category.FAILED_SYNTHESIS]:
        hints.append("A typeclass instance could not be found; the statement may need a different form or an explicit instance.")
    if cats[Category.REWRITE_FAILURE]:
        hints.append("rw could not find the pattern; check the rewrite direction (←) or use simp only / conv.")
    return "\n".join(f"- {h}" for h in hints)


def feedback_for(attempt: Attempt, max_chars: int = 3000, retrieved: list[str] | None = None,
                 failure_hints: list[str] | None = None) -> str:
    if attempt.extraction_error:
        parts = [
            f"Your response could not be used: {attempt.extraction_error}.",
            "Return exactly one ```lean block with the full target declaration (statement verbatim) and a non-empty proof.",
        ]
        if retrieved:
            parts.append("Possibly relevant declarations:\n" + "\n".join(f"- {r}" for r in retrieved))
        return "\n".join(parts)
    if attempt.forbidden:
        return (
            "Your response uses forbidden constructs: " + ", ".join(attempt.forbidden)
            + ". Remove them; the proof must be complete and axiom-free."
        )
    if attempt.feedback and not attempt.diagnostics:
        return attempt.feedback
    body = summarize(attempt.diagnostics, max_chars=max_chars)
    hint = _hint(attempt.diagnostics)
    parts = [body]
    if hint:
        parts.append("Hints:\n" + hint)
    if failure_hints:
        parts.append("Failure memory:\n" + "\n".join(f"- {h}" for h in failure_hints))
    if retrieved:
        parts.append("Possibly relevant declarations:\n" + "\n".join(f"- {r}" for r in retrieved))
    if attempt.feedback:
        parts.append(attempt.feedback)
    return "\n\n".join(parts)
