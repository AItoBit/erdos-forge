"""State scoring for beam / best-first search.

::

    Score(s) = α P_LLM + β P_progress + γ P_retrieval − δ C_depth − ε C_repetition
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreWeights:
    llm: float = 0.35
    progress: float = 0.30
    retrieval: float = 0.15
    depth: float = 0.10
    repetition: float = 0.10


def progress_signal(n_goals: int, goal_complexity: float) -> float:
    """High when few, simple goals remain. ``n_goals == 0`` is a solved state."""
    if n_goals <= 0:
        return 1.0
    return (1.0 / (1.0 + n_goals)) * (1.0 / (1.0 + max(goal_complexity, 0.0)))


def score_state(
    *,
    llm_p: float = 0.5,
    n_goals: int = 1,
    goal_complexity: float = 1.0,
    retrieval_p: float = 0.0,
    depth: int = 0,
    repeated: bool = False,
    compile_ok: bool = True,
    weights: ScoreWeights | None = None,
) -> float:
    w = weights or ScoreWeights()
    if not compile_ok:
        return -1.0
    progress = progress_signal(n_goals, goal_complexity)
    return (
        w.llm * _clamp(llm_p)
        + w.progress * progress
        + w.retrieval * _clamp(retrieval_p)
        - w.depth * (depth / 40.0)
        - (w.repetition if repeated else 0.0)
    )


def goal_complexity(goal: str) -> float:
    """Cheap syntactic complexity: binders, connectives, length."""
    if not goal:
        return 0.0
    markers = sum(goal.count(ch) for ch in ("∀", "∃", "→", "↔", "∧", "∨", "∫", "∑"))
    return min(8.0, markers + len(goal) / 120.0)


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x
