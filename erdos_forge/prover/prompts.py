"""Prompt construction for whole-proof generation and error-driven repair.

Conventions the rest of the system relies on:

* the first user message lists the imports as plain ``import ...`` lines and
  shows the target statement as the *last* ```lean block, ending in ``:= by``;
* the model must answer with one ```lean block containing the complete target
  declaration (statement verbatim) plus optional helper lemmas placed before it.
"""

from __future__ import annotations

from erdos_forge.core.state import Problem
from erdos_forge.lean.source import Theorem
from erdos_forge.models.base import Message

SYSTEM_PROMPT = """You are an expert Lean 4 and Mathlib prover working inside an automated loop.

Rules (violations are rejected automatically by a verifier you cannot bypass):
1. Return exactly one ```lean code block containing the complete target declaration.
2. Keep the target statement VERBATIM: same name, binders, hypotheses and conclusion. Never weaken, rename or generalize it.
3. Never use `sorry`, `admit`, `axiom`, `unsafe`, `native_decide`, `decide +native`, `@[implemented_by]`, `@[extern]` or `partial def`.
4. Do not add or change `import` lines; the imports are fixed. Do not repeat the given context (defs, opens) in your answer.
5. You MAY add helper `lemma`/`theorem`/`def` declarations before the target declaration, fully proved.
6. Prefer existing Mathlib lemmas over re-proving them. Use Lean 4 syntax (`fun x => ...`, `·` for focusing, `omega`, `simp`, `norm_num`, `linarith`, `nlinarith`, `positivity`, `aesop`, `decide`, `induction ... with`).
7. When repairing, read the structured diagnostics carefully: fix the reported line, do not rewrite unrelated parts, and do not re-try an approach that already failed the same way.
8. No prose is needed; a short comment inside the code block is fine.
"""


def describe_context(theorem: Theorem, max_chars: int = 6000) -> str:
    body = theorem.body_context
    if len(body) > max_chars:
        body = body[:max_chars] + "\n-- ... (context truncated)"
    return body


def initial_messages(problem: Problem, retrieved: list[str] | None = None) -> list[Message]:
    thm = problem.theorem
    imports = thm.imports or "-- (no imports: core Lean 4 only; Mathlib tactics are NOT available)"
    parts = [
        f"Problem: {problem.id}",
        f"Imports (fixed):\n{imports}",
    ]
    ctx = describe_context(thm)
    if ctx:
        parts.append(f"Context already in the file (do not repeat it):\n```lean\n{ctx}\n```")
    if problem.notes:
        parts.append(f"Notes: {problem.notes}")
    if retrieved:
        parts.append("Possibly relevant declarations:\n" + "\n".join(f"- {r}" for r in retrieved))
    parts.append(
        "Target (complete this declaration; keep the statement verbatim):\n"
        f"```lean\n{thm.signature} := by\n```"
    )
    return [Message("system", SYSTEM_PROMPT), Message("user", "\n\n".join(parts))]


def repair_message(feedback: str, attempt_index: int, remaining: int) -> Message:
    text = (
        f"Attempt {attempt_index} was rejected. Structured compiler feedback:\n\n{feedback}\n\n"
        f"Repairs remaining after this one: {remaining}. "
        "Return the full corrected target declaration (plus any helper lemmas) in one ```lean block."
    )
    return Message("user", text)
