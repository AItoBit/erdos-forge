"""Load a problem from JSON metadata, ``FILE.lean:NAME``, or a raw Lean path."""

from __future__ import annotations

from pathlib import Path

from erdos_forge.core.state import Problem, ProblemStatus, TargetKind
from erdos_forge.lean.source import load_theorem, load_theorems


def parse_target(spec: str, *, status: str | None = None, kind: str | None = None) -> Problem:
    """Accept ``data/problems/*.json``, ``FILE.lean:NAME``, or a ``.lean`` file (first theorem)."""
    if spec.endswith(".json"):
        problem = Problem.from_json(spec)
    elif ".lean:" in spec.replace("\\", "/"):
        problem = Problem.from_theorem(load_theorem(spec))
    else:
        path = Path(spec)
        if path.suffix == ".lean" and path.is_file():
            theorems = load_theorems(path)
            if not theorems:
                raise KeyError(f"no theorems in {path}")
            problem = Problem.from_theorem(theorems[0])
        else:
            problem = Problem.from_theorem(load_theorem(spec))
    if status:
        problem.status = ProblemStatus(status)
    if kind:
        problem.kind = TargetKind(kind)
    return problem
