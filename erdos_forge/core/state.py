"""Problem metadata and the result types produced by a proof attempt."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from erdos_forge.lean.diagnostics import LeanDiagnostic
from erdos_forge.lean.source import Theorem, load_theorem


class ProblemStatus(str, Enum):
    """Mathematical status of the *statement* (not of our proof attempt)."""

    OPEN = "open"
    SOLVED = "solved"
    PARTIALLY_SOLVED = "partially_solved"
    UNKNOWN = "unknown"


class TargetKind(str, Enum):
    """What the target declaration asserts."""

    THEOREM = "theorem"  # a known result; proving it is the goal
    CONJECTURE = "conjecture"  # the open statement itself; may only be formalized
    AUXILIARY = "auxiliary"  # bound / finite case / equivalence around a conjecture


@dataclass
class Problem:
    id: str
    theorem: Theorem
    status: ProblemStatus = ProblemStatus.UNKNOWN
    kind: TargetKind = TargetKind.THEOREM
    level: int = 1
    tags: list[str] = field(default_factory=list)
    source: str | None = None
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_open_conjecture(self) -> bool:
        return self.kind == TargetKind.CONJECTURE and self.status in (ProblemStatus.OPEN, ProblemStatus.UNKNOWN)

    @classmethod
    def from_theorem(cls, theorem: Theorem, **kw: Any) -> "Problem":
        pid = kw.pop("id", None) or (f"{Path(theorem.source).stem}:{theorem.name}" if theorem.source else theorem.name)
        return cls(id=pid, theorem=theorem, **kw)

    @classmethod
    def from_json(cls, path: str | Path) -> "Problem":
        """Load ``data/problems/*.json`` metadata pointing at a ``FILE.lean:NAME`` target."""
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        target = raw["target"]
        if not Path(target.rpartition(":")[0]).is_absolute():
            target = str((path.parent / target.rpartition(":")[0]).resolve()) + ":" + target.rpartition(":")[2]
        theorem = load_theorem(target)
        return cls(
            id=raw.get("id", path.stem),
            theorem=theorem,
            status=ProblemStatus(raw.get("status", "unknown")),
            kind=TargetKind(raw.get("kind", "theorem")),
            level=int(raw.get("level", 1)),
            tags=list(raw.get("tags", [])),
            source=raw.get("source"),
            notes=raw.get("notes", ""),
            metadata={k: v for k, v in raw.items() if k not in {"id", "target", "status", "kind", "level", "tags", "source", "notes"}},
        )


@dataclass
class Attempt:
    """One LLM call followed by one compile (or a rejection before compiling)."""

    index: int
    kind: str  # "generate" | "repair"
    response: str
    main_declaration: str | None = None
    preamble: str = ""
    extraction_error: str | None = None
    forbidden: list[str] = field(default_factory=list)
    compiled: bool = False
    compile_ok: bool = False
    exit_code: int | None = None
    compile_ms: float = 0.0
    diagnostics: list[LeanDiagnostic] = field(default_factory=list)
    feedback: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_ms: float = 0.0
    verified: bool | None = None  # only set when the firewall ran
    retrieved: list[str] = field(default_factory=list)
    candidates_tried: int = 1

    @property
    def error_categories(self) -> list[str]:
        return sorted({d.category.value for d in self.diagnostics if d.is_error})

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "extraction_error": self.extraction_error,
            "forbidden": self.forbidden,
            "compiled": self.compiled,
            "compile_ok": self.compile_ok,
            "exit_code": self.exit_code,
            "compile_ms": round(self.compile_ms, 1),
            "error_categories": self.error_categories,
            "diagnostics": [d.to_dict() for d in self.diagnostics if d.is_error][:10],
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "model_ms": round(self.model_ms, 1),
            "verified": self.verified,
            "main_declaration": self.main_declaration,
            "preamble": self.preamble,
            "retrieved": self.retrieved,
            "candidates_tried": self.candidates_tried,
        }


@dataclass
class ProofResult:
    problem_id: str
    success: bool
    proof: str | None = None  # full target declaration, verified
    preamble: str = ""  # verified helper declarations
    attempts: list[Attempt] = field(default_factory=list)
    compiler_calls: int = 0
    axioms: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    outcome: str = "failed"  # verified | failed | budget_exhausted | guarded | infra_error | statement_ok | statement_error
    wall_ms: float = 0.0
    model: str = ""
    verification: dict[str, Any] | None = None
    retrieved: list[str] = field(default_factory=list)
    analysis: dict[str, Any] | None = None

    @property
    def repairs(self) -> int:
        return sum(1 for a in self.attempts if a.kind == "repair")

    @property
    def prompt_tokens(self) -> int:
        return sum(a.prompt_tokens for a in self.attempts)

    @property
    def completion_tokens(self) -> int:
        return sum(a.completion_tokens for a in self.attempts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "success": self.success,
            "outcome": self.outcome,
            "failure_reason": self.failure_reason,
            "proof": self.proof,
            "preamble": self.preamble,
            "axioms": self.axioms,
            "compiler_calls": self.compiler_calls,
            "repairs": self.repairs,
            "llm_calls": len(self.attempts),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "wall_ms": round(self.wall_ms, 1),
            "model": self.model,
            "verification": self.verification,
            "retrieved": self.retrieved,
            "analysis": self.analysis,
            "attempts": [a.to_dict() for a in self.attempts],
        }
