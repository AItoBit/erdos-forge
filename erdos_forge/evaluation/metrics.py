"""Aggregate metrics over a list of ``ProofResult``s."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from erdos_forge.core.state import ProofResult


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def compute_metrics(results: list[ProofResult]) -> dict[str, Any]:
    n = len(results)
    verified = [r for r in results if r.success]
    attempted = [r for r in results if r.outcome not in ("guarded", "statement_ok", "statement_error")]
    needed_repair = [r for r in attempted if r.repairs > 0 or (not r.success and len(r.attempts) > 1)]
    solved_after_repair = [r for r in verified if any(a.kind == "repair" and a.verified for a in r.attempts)]
    first_shot = [r for r in verified if r.attempts and r.attempts[0].verified]
    categories: Counter[str] = Counter()
    for r in attempted:
        for a in r.attempts:
            categories.update(a.error_categories)
    outcomes = Counter(r.outcome for r in results)

    return {
        "problems": n,
        "verified": len(verified),
        "verified_solve_rate": _rate(len(verified), len(attempted)),
        "first_attempt_solve_rate": _rate(len(first_shot), len(attempted)),
        "repair_success_rate": _rate(len(solved_after_repair), len(needed_repair)),
        "compiler_calls_total": sum(r.compiler_calls for r in results),
        "compiler_calls_per_problem": round(mean(r.compiler_calls for r in results), 2) if n else None,
        "llm_calls_per_problem": round(mean(len(r.attempts) for r in attempted), 2) if attempted else None,
        "prompt_tokens_total": sum(r.prompt_tokens for r in results),
        "completion_tokens_total": sum(r.completion_tokens for r in results),
        "tokens_per_problem": round(mean(r.prompt_tokens + r.completion_tokens for r in attempted), 1) if attempted else None,
        "wall_seconds_total": round(sum(r.wall_ms for r in results) / 1000, 1),
        "wall_seconds_per_problem": round(mean(r.wall_ms for r in results) / 1000, 2) if n else None,
        "retrieved_lemmas_per_problem": round(mean(len(r.retrieved) for r in attempted), 2) if attempted else None,
        "outcomes": dict(outcomes),
        "error_categories": dict(categories.most_common()),
    }
