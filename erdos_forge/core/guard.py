"""Open-problem guard.

For a problem whose target is an *open conjecture*, the agent is not allowed to
run proof search on the conjecture itself: it may only check that the
statement elaborates. It may still prove auxiliary targets (finite cases,
bounds, equivalences) that are registered as ``TargetKind.AUXILIARY`` or
``THEOREM``. Independently of status, no candidate may introduce axioms or
alter the statement; those checks live in the verification firewall and are
repeated here so the controller can refuse early.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from erdos_forge.core.state import Problem
from erdos_forge.lean.firewall import scan_source


@dataclass
class GuardDecision:
    allow_proof_search: bool
    reasons: list[str] = field(default_factory=list)
    mode: str = "prove"  # "prove" | "statement_only"


class OpenProblemGuard:
    def decide(self, problem: Problem) -> GuardDecision:
        if problem.is_open_conjecture:
            return GuardDecision(
                allow_proof_search=False,
                mode="statement_only",
                reasons=[
                    f"{problem.id} is an open conjecture (status={problem.status.value}); "
                    "only statement elaboration is allowed, never a proof attempt on the conjecture itself"
                ],
            )
        return GuardDecision(allow_proof_search=True)

    @staticmethod
    def candidate_violations(main_declaration: str, preamble: str) -> list[str]:
        """Early rejection reasons for a candidate (before spending a compile)."""
        found = scan_source(preamble) + scan_source(main_declaration)
        return sorted(set(found))
