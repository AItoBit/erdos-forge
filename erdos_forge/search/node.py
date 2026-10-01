"""A single node in the proof-search DAG."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ProofNode:
    id: str
    parent: str | None
    proof_state: str
    code: str
    action: str
    depth: int
    retrieved_lemmas: list[str] = field(default_factory=list)
    score: float = 0.0
    verified: bool = False
    terminal: bool = False
    state_hash: str = ""
    n_goals: int = 0
    compile_ok: bool = False

    @classmethod
    def root(cls, proof_state: str, code: str = "", state_hash: str = "") -> "ProofNode":
        return cls(
            id=uuid.uuid4().hex[:12],
            parent=None,
            proof_state=proof_state,
            code=code,
            action="",
            depth=0,
            state_hash=state_hash,
        )

    def child(self, *, action: str, proof_state: str, code: str, state_hash: str,
              n_goals: int = 0, compile_ok: bool = False) -> "ProofNode":
        return ProofNode(
            id=uuid.uuid4().hex[:12],
            parent=self.id,
            proof_state=proof_state,
            code=code,
            action=action,
            depth=self.depth + 1,
            state_hash=state_hash,
            n_goals=n_goals,
            compile_ok=compile_ok,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent": self.parent,
            "depth": self.depth,
            "action": self.action,
            "score": self.score,
            "verified": self.verified,
            "terminal": self.terminal,
            "state_hash": self.state_hash,
            "n_goals": self.n_goals,
            "compile_ok": self.compile_ok,
            "retrieved_lemmas": self.retrieved_lemmas,
        }
