"""Offline models: a scripted mock for tests and a tactic-cycling heuristic baseline.

Both implement ``ChatModel`` so the whole pipeline (prompting, extraction,
compilation, diagnostics, repair, firewall, trajectories) can run without an
API key. The heuristic baseline is also the "no LLM" row of ablation tables.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from erdos_forge.models.base import ChatModel, Completion, Message

_LEAN_BLOCK = re.compile(r"```lean\s*\n(.*?)```", re.S)


class MockModel(ChatModel):
    """Returns scripted responses in order (the last one repeats)."""

    is_llm = False

    def __init__(self, responses: Iterable[str] | Callable[[list[Message]], str], name: str = "mock"):
        self.name = name
        self._fn = responses if callable(responses) else None
        self._responses = list(responses) if not callable(responses) else []
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        self.calls.append(list(messages))
        if self._fn is not None:
            text = self._fn(messages)
        else:
            idx = min(len(self.calls) - 1, len(self._responses) - 1)
            text = self._responses[idx] if self._responses else ""
        return Completion([text] * max(1, n), prompt_tokens=0, completion_tokens=0, model=self.name)


def target_block(messages: list[Message]) -> str | None:
    """The target declaration shown in the first user prompt (see ``prover.prompts``)."""
    for m in messages:
        if m.role == "user":
            blocks = _LEAN_BLOCK.findall(m.content)
            if blocks:
                return blocks[-1].strip()
    return None


def imports_of(messages: list[Message]) -> str:
    for m in messages:
        if m.role == "user":
            return "\n".join(ln for ln in m.content.splitlines() if ln.startswith("import "))
    return ""


CORE_CLOSERS = ["rfl", "decide", "omega", "simp", "simp_all", "trivial"]
MATHLIB_CLOSERS = ["norm_num", "positivity", "aesop", "tauto", "linarith", "nlinarith", "ring", "field_simp", "exact?"]


class HeuristicModel(ChatModel):
    """No LLM: emits a different closing-tactic combination on every call.

    Call k (0-based) within one conversation produces schedule[k]. The
    schedule adapts to whether Mathlib is imported (its tactics would be parse
    errors in core Lean).
    """

    is_llm = False

    def __init__(self, name: str = "heuristic"):
        self.name = name

    @staticmethod
    def schedule(has_mathlib: bool) -> list[str]:
        closers = [c for c in CORE_CLOSERS + (MATHLIB_CLOSERS if has_mathlib else []) if c != "exact?"]
        alt = " | ".join(closers)
        return [
            f"first | {alt}",
            f"intros\n  first | {alt}",
            f"intros\n  constructor <;> first | {alt}",
            f"intros\n  simp_all\n  all_goals first | {alt}",
            f"intros\n  rcases ‹_› with _ | _ <;> first | {alt}",
        ]

    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        target = target_block(messages)
        if target is None:
            return Completion([""], model=self.name)
        k = sum(1 for m in messages if m.role == "assistant")
        has_mathlib = "import Mathlib" in imports_of(messages)
        sched = self.schedule(has_mathlib)
        tactic = sched[min(k, len(sched) - 1)]
        stmt = re.sub(r":=\s*by\s*$", "", target.rstrip()).rstrip()
        stmt = re.sub(r":=\s*by\s*\n\s*sorry\s*$", "", stmt).rstrip()
        text = f"```lean\n{stmt} := by\n  {tactic}\n```"
        return Completion([text] * max(1, n), model=self.name)
