"""Typecheck candidate Lean statements (elaboration only; never a proof)."""

from __future__ import annotations

from dataclasses import dataclass, field

from erdos_forge.lean.diagnostics import LeanDiagnostic
from erdos_forge.lean.environment import LeanEnvironment, SnippetResult, statement_ok
from erdos_forge.lean.source import Theorem


@dataclass
class StatementValidation:
    ok: bool
    diagnostics: list[LeanDiagnostic] = field(default_factory=list)
    compile_ms: float = 0.0
    exit_code: int | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "compile_ms": round(self.compile_ms, 1),
            "errors": [d.to_dict() for d in self.diagnostics if d.is_error][:8],
        }


def validate_statement(env: LeanEnvironment, theorem: Theorem) -> StatementValidation:
    res: SnippetResult = env.check_statement(theorem)
    return StatementValidation(
        ok=statement_ok(res),
        diagnostics=res.diagnostics,
        compile_ms=res.compile.duration_ms,
        exit_code=res.compile.exit_code,
    )
