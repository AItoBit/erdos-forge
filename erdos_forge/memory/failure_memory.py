"""Remember compiler failures so similar goals do not repeat the same mistake."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from erdos_forge.core.state import Attempt, Problem
from erdos_forge.retrieval.theorem_search import tokenize


@dataclass
class FailureRecord:
    problem: str
    category: str
    identifier: str | None
    statement_tokens: list[str]
    note: str
    action: str = ""

    def to_dict(self) -> dict:
        return {
            "problem": self.problem,
            "category": self.category,
            "identifier": self.identifier,
            "statement_tokens": self.statement_tokens,
            "note": self.note,
            "action": self.action,
        }


class FailureMemory:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.records: list[FailureRecord] = []
        if self.path and self.path.exists():
            with self.path.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        self.records.append(FailureRecord(**json.loads(line)))

    def remember(self, problem: Problem, attempt: Attempt) -> list[FailureRecord]:
        added: list[FailureRecord] = []
        tokens = tokenize(problem.theorem.signature)
        if attempt.forbidden:
            rec = FailureRecord(problem.id, "forbidden", None, tokens, ",".join(attempt.forbidden), "reject")
            self._append(rec)
            added.append(rec)
        for diag in attempt.diagnostics:
            if not diag.is_error:
                continue
            rec = FailureRecord(
                problem=problem.id,
                category=diag.category.value,
                identifier=diag.identifier,
                statement_tokens=tokens,
                note=diag.headline[:240],
                action=diag.likely_action,
            )
            self._append(rec)
            added.append(rec)
        return added

    def hints(self, problem: Problem, *, identifiers: list[str] | None = None, limit: int = 4) -> list[str]:
        """Short warnings for the current statement / unknown identifiers."""
        tokens = set(tokenize(problem.theorem.signature))
        idents = set(identifiers or [])
        scored: list[tuple[int, FailureRecord]] = []
        for rec in self.records:
            overlap = len(tokens & set(rec.statement_tokens))
            if rec.identifier and rec.identifier in idents:
                overlap += 5
            if overlap:
                scored.append((overlap, rec))
        scored.sort(key=lambda p: -p[0])
        hints: list[str] = []
        seen: set[str] = set()
        for _, rec in scored:
            key = f"{rec.category}:{rec.identifier or rec.note}"
            if key in seen:
                continue
            seen.add(key)
            if rec.identifier:
                hints.append(f"previously failed: {rec.category} on `{rec.identifier}` ({rec.note})")
            else:
                hints.append(f"previously failed: {rec.category} ({rec.note})")
            if len(hints) >= limit:
                break
        return hints

    def _append(self, rec: FailureRecord) -> None:
        self.records.append(rec)
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
