"""Compare two Lean statements: syntactic identity first, then elaboration.

A later version can attempt ``⊢ A ↔ B``. Until then we never claim semantic
equivalence from an LLM judgement — only from the Lean kernel (elaboration)
and from the same normaliser the firewall uses.
"""

from __future__ import annotations

from dataclasses import dataclass

from erdos_forge.formalizer.statement_validator import validate_statement
from erdos_forge.lean.environment import LeanEnvironment
from erdos_forge.lean.source import Theorem, normalize_signature


@dataclass
class EquivalenceReport:
    syntactic: bool
    left_elaborates: bool
    right_elaborates: bool

    @property
    def both_elaborate(self) -> bool:
        return self.left_elaborates and self.right_elaborates

    def to_dict(self) -> dict:
        return {
            "syntactic": self.syntactic,
            "left_elaborates": self.left_elaborates,
            "right_elaborates": self.right_elaborates,
            "both_elaborate": self.both_elaborate,
        }


def check_equivalence(env: LeanEnvironment, left: Theorem, right: Theorem) -> EquivalenceReport:
    syntactic = normalize_signature(left.signature) == normalize_signature(right.signature)
    return EquivalenceReport(
        syntactic=syntactic,
        left_elaborates=validate_statement(env, left).ok,
        right_elaborates=validate_statement(env, right).ok,
    )
