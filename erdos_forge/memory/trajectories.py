"""Append-only JSONL trajectory store.

One record per (problem, attempt). Every record carries the eventual outcome
of the problem so the file can be used directly as supervised data::

    {"problem": ..., "attempt": 2, "kind": "repair", "candidate": "...",
     "compile_ok": false, "error_categories": ["unsolved_goals"],
     "feedback": "...", "verified": null, "eventual_success": true, ...}
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from erdos_forge.core.state import Problem, ProofResult


class TrajectoryWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = 0

    def record(self, problem: Problem, result: ProofResult, run_id: str | None = None) -> int:
        """Write all attempts of ``result`` with the final outcome attached."""
        rows: list[dict[str, Any]] = []
        for a in result.attempts:
            rows.append(
                {
                    "run_id": run_id,
                    "timestamp": time.time(),
                    "problem": problem.id,
                    "level": problem.level,
                    "status": problem.status.value,
                    "statement": problem.theorem.signature,
                    "imports": problem.theorem.imports,
                    "model": result.model,
                    "attempt": a.index,
                    "kind": a.kind,
                    "response": a.response,
                    "candidate": a.main_declaration,
                    "preamble": a.preamble,
                    "extraction_error": a.extraction_error,
                    "forbidden": a.forbidden,
                    "compiled": a.compiled,
                    "compile_ok": a.compile_ok,
                    "error_categories": a.error_categories,
                    "diagnostics": [d.to_dict() for d in a.diagnostics if d.is_error][:10],
                    "feedback": a.feedback,
                    "verified": a.verified,
                    "prompt_tokens": a.prompt_tokens,
                    "completion_tokens": a.completion_tokens,
                    "retrieved_lemmas": a.retrieved or result.retrieved,
                    "eventual_success": result.success,
                    "outcome": result.outcome,
                }
            )
        with self.path.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.records += len(rows)
        return len(rows)


def read_trajectories(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
