"""Per-problem resource budget: compiler calls, tokens, wall-clock."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from erdos_forge.config import BudgetSettings


class BudgetExhausted(RuntimeError):
    def __init__(self, resource: str, detail: str = ""):
        super().__init__(f"budget exhausted: {resource}{(' (' + detail + ')') if detail else ''}")
        self.resource = resource


@dataclass
class Budget:
    max_compiler_calls: int = 12
    max_tokens: int = 200_000
    max_wall_seconds: float = 3600.0
    compiler_calls: int = 0
    tokens: int = 0
    started_at: float = field(default_factory=time.perf_counter)

    @classmethod
    def from_settings(cls, s: BudgetSettings) -> "Budget":
        return cls(s.max_compiler_calls, s.max_tokens, s.max_wall_seconds)

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.started_at

    def charge_compile(self, n: int = 1) -> None:
        self.compiler_calls += n
        if self.compiler_calls > self.max_compiler_calls:
            raise BudgetExhausted("compiler_calls", f"{self.compiler_calls}/{self.max_compiler_calls}")

    def charge_tokens(self, n: int) -> None:
        self.tokens += n
        if self.tokens > self.max_tokens:
            raise BudgetExhausted("tokens", f"{self.tokens}/{self.max_tokens}")

    def check_wall(self) -> None:
        if self.elapsed_seconds > self.max_wall_seconds:
            raise BudgetExhausted("wall_clock", f"{self.elapsed_seconds:.0f}s/{self.max_wall_seconds:.0f}s")

    def can_compile(self, n: int = 1) -> bool:
        return self.compiler_calls + n <= self.max_compiler_calls

    def snapshot(self) -> dict:
        return {
            "compiler_calls": self.compiler_calls,
            "tokens": self.tokens,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
        }
