"""V0.1/V0.3 controller: retrieve → generate N candidates → Lean → repair → firewall.

::

    guard ──► retrieve ──► generate ──► extract ──► scan ──► compile ──► diagnostics
                               ▲                                   │
                               └──────── repair (≤ N) ◄────────────┘
                                                                   │ ok
                                                                   ▼
                                                         verification firewall
                                                                   │
                                                         VERIFIED / rejected

Nothing in this module can declare success on its own; the final word belongs to
``VerificationFirewall.verify``.
"""

from __future__ import annotations

import time

from erdos_forge.config import SearchSettings
from erdos_forge.core.budget import Budget, BudgetExhausted
from erdos_forge.core.events import EventBus
from erdos_forge.core.guard import OpenProblemGuard
from erdos_forge.core.state import Attempt, Problem, ProofResult
from erdos_forge.formalizer.math_analyzer import MathematicalAnalyzer
from erdos_forge.lean.compiler import LeanNotAvailable
from erdos_forge.lean.diagnostics import Category, LeanDiagnostic
from erdos_forge.lean.environment import LeanEnvironment, statement_ok
from erdos_forge.lean.firewall import VerificationFirewall
from erdos_forge.memory.failure_memory import FailureMemory
from erdos_forge.models.base import ChatModel, Message, ModelError
from erdos_forge.prover.extract import ExtractionError, extract_candidate
from erdos_forge.prover.prompts import initial_messages, repair_message
from erdos_forge.prover.repair import feedback_for
from erdos_forge.prover.tactic_generator import split_candidates
from erdos_forge.retrieval.premise_selection import (
    PremiseSelector,
    RetrievalQuery,
    default_selector,
    format_hits,
)


class RepairController:
    def __init__(
        self,
        env: LeanEnvironment,
        model: ChatModel,
        settings: SearchSettings | None = None,
        events: EventBus | None = None,
        guard: OpenProblemGuard | None = None,
        retriever: PremiseSelector | None | bool = None,
        failure_memory: FailureMemory | None = None,
    ):
        self.env = env
        self.model = model
        self.settings = settings or SearchSettings.load()
        self.events = events or EventBus()
        self.guard = guard or OpenProblemGuard()
        self.firewall: VerificationFirewall = env.firewall
        self.analyzer = MathematicalAnalyzer()
        self.failure_memory = failure_memory
        if retriever is False:
            self.retriever = None
        elif retriever is None:
            self.retriever = _build_retriever(self.settings)
        else:
            self.retriever = retriever

    # ------------------------------------------------------------- helpers

    def _finish(self, result: ProofResult, t0: float, budget: Budget) -> ProofResult:
        result.wall_ms = (time.perf_counter() - t0) * 1000
        result.compiler_calls = budget.compiler_calls
        result.model = self.model.name
        self.events.emit("problem.end", problem=result.problem_id, outcome=result.outcome,
                         success=result.success, compiler_calls=result.compiler_calls,
                         llm_calls=len(result.attempts), wall_ms=round(result.wall_ms))
        return result

    def _statement_only(self, problem: Problem, result: ProofResult, budget: Budget) -> None:
        """Open conjecture: only check that the statement elaborates."""
        budget.charge_compile()
        res = self.env.check_statement(problem.theorem)
        ok = statement_ok(res)
        result.outcome = "statement_ok" if ok else "statement_error"
        if not ok:
            detail = "; ".join(e.headline for e in res.errors[:3]) or "statement did not elaborate"
            result.failure_reason = f"{result.failure_reason}; statement check failed: {detail}"
        result.verification = {"statement_check": ok, "exit_code": res.compile.exit_code}
        self.events.emit("statement.checked", problem=problem.id, ok=ok)

    def _retrieve(self, problem: Problem, *, identifiers: list[str] | None = None,
                  goals: list[str] | None = None) -> list[str]:
        if self.retriever is None:
            return []
        query = RetrievalQuery.from_problem(problem, identifiers=identifiers, goals=goals)
        hits = self.retriever.select(query)
        lines = format_hits(hits)
        self.events.emit("retrieval.hits", problem=problem.id, n=len(hits),
                         names=",".join(h.declaration.name for h in hits[:8]))
        return lines

    # ---------------------------------------------------------------- main

    def prove(self, problem: Problem) -> ProofResult:
        t0 = time.perf_counter()
        budget = Budget.from_settings(self.settings.budget)
        result = ProofResult(problem_id=problem.id, success=False)
        analysis = self.analyzer.analyze(problem)
        result.analysis = analysis.to_dict()
        self.events.emit("problem.start", problem=problem.id, model=self.model.name, status=problem.status.value,
                         kind=problem.kind.value, mode=analysis.prove_vs_formalize)
        self.events.emit("analysis.ready", problem=problem.id, mode=analysis.prove_vs_formalize,
                         risks="; ".join(analysis.formalization_risks))

        decision = self.guard.decide(problem)
        if not decision.allow_proof_search:
            result.outcome = "guarded"
            result.failure_reason = "; ".join(decision.reasons)
            self.events.emit("guard.blocked", problem=problem.id, reason=result.failure_reason)
            try:
                self._statement_only(problem, result, budget)
            except (BudgetExhausted, LeanNotAvailable) as exc:
                result.failure_reason = str(exc)
            return self._finish(result, t0, budget)

        rep = self.settings.repair
        retrieved = self._retrieve(problem)
        result.retrieved = retrieved
        messages: list[Message] = initial_messages(problem, retrieved=retrieved or None)
        max_attempts = 1 + rep.max_repairs
        failures = self.failure_memory if self.failure_memory is not None else FailureMemory()

        try:
            for index in range(max_attempts):
                budget.check_wall()
                kind = "generate" if index == 0 else "repair"
                attempt = Attempt(index=index, kind=kind, response="")
                result.attempts.append(attempt)

                # ---- model
                tm = time.perf_counter()
                completion = self.model.complete(messages, n=rep.samples_per_call)
                attempt.model_ms = (time.perf_counter() - tm) * 1000
                attempt.response = completion.text
                attempt.prompt_tokens = completion.prompt_tokens
                attempt.completion_tokens = completion.completion_tokens
                budget.charge_tokens(completion.total_tokens)
                self.events.emit("model.completion", problem=problem.id, attempt=index, kind=kind,
                                 model=self.model.name, tokens=completion.total_tokens,
                                 latency_ms=round(attempt.model_ms))

                texts = _unique_texts(completion.texts)
                attempt.candidates_tried = 0
                verified = False
                for text in texts:
                    if self._try_candidate(problem, attempt, text, result, budget):
                        verified = True
                        break
                if verified:
                    return self._finish(result, t0, budget)

                failures.remember(problem, attempt)
                if index == max_attempts - 1:
                    break
                if not budget.can_compile():
                    raise BudgetExhausted("compiler_calls")
                extra = self._repair_retrieval(problem, attempt)
                attempt.retrieved = extra
                hints = failures.hints(problem, identifiers=_identifiers(attempt))
                messages = self._extend(
                    messages, attempt.response, attempt, index, max_attempts,
                    rep.feedback_max_chars, extra, hints,
                )

            result.outcome = "failed"
            result.failure_reason = self._last_failure(result)
        except BudgetExhausted as exc:
            result.outcome = "budget_exhausted"
            result.failure_reason = str(exc)
        except ModelError as exc:
            result.outcome = "infra_error"
            result.failure_reason = f"model error: {exc}"
        except LeanNotAvailable as exc:
            result.outcome = "infra_error"
            result.failure_reason = f"lean unavailable: {exc}"
        return self._finish(result, t0, budget)

    def _try_candidate(self, problem: Problem, attempt: Attempt, text: str,
                       result: ProofResult, budget: Budget) -> bool:
        """Extract, scan, compile and maybe firewall one candidate. True if verified."""
        attempt.candidates_tried += 1
        attempt.response = text
        try:
            cand = extract_candidate(text, problem.theorem)
        except ExtractionError as exc:
            attempt.extraction_error = str(exc)
            self.events.emit("candidate.rejected", problem=problem.id, attempt=attempt.index,
                             reason="extraction", detail=str(exc))
            return False
        attempt.extraction_error = None
        attempt.main_declaration = cand.main_declaration
        attempt.preamble = cand.preamble

        matches, why = self.firewall.statement_matches(problem.theorem, cand.main_declaration)
        if not matches:
            attempt.extraction_error = why
            self.events.emit("candidate.rejected", problem=problem.id, attempt=attempt.index,
                             reason="statement_mismatch")
            return False
        attempt.forbidden = self.guard.candidate_violations(cand.main_declaration, cand.preamble)
        if attempt.forbidden:
            self.events.emit("candidate.rejected", problem=problem.id, attempt=attempt.index,
                             reason="forbidden", detail=",".join(attempt.forbidden))
            return False

        budget.charge_compile()
        res = self.env.compile_candidate(problem.theorem, cand.main_declaration, cand.preamble)
        attempt.compiled = True
        attempt.exit_code = res.compile.exit_code
        attempt.compile_ms += res.compile.duration_ms
        attempt.diagnostics = res.diagnostics
        attempt.compile_ok = res.ok
        if res.compile.timed_out:
            attempt.diagnostics.append(
                LeanDiagnostic("error", "compile timed out", Category.TIMEOUT, likely_action="simplify_or_split")
            )
            attempt.compile_ok = False
        self.events.emit("candidate.compiled", problem=problem.id, attempt=attempt.index,
                         ok=attempt.compile_ok, exit_code=attempt.exit_code,
                         ms=round(res.compile.duration_ms),
                         categories=",".join(attempt.error_categories))

        if not attempt.compile_ok:
            return False

        budget.charge_compile()
        report = self.firewall.verify(problem.theorem, cand.main_declaration, cand.preamble)
        attempt.verified = report.ok
        result.verification = report.to_dict()
        self.events.emit("firewall.result", problem=problem.id, attempt=attempt.index, ok=report.ok,
                         reasons="; ".join(report.reasons), axioms=",".join(report.axioms))
        if report.ok:
            result.success = True
            result.outcome = "verified"
            result.proof = cand.main_declaration
            result.preamble = cand.preamble
            result.axioms = report.axioms
            return True
        attempt.feedback = "Verification firewall rejected the proof: " + "; ".join(report.reasons)
        attempt.diagnostics = report.diagnostics or attempt.diagnostics
        return False

    def _repair_retrieval(self, problem: Problem, attempt: Attempt) -> list[str]:
        idents = _identifiers(attempt)
        goals: list[str] = []
        for diag in attempt.diagnostics:
            goals.extend(diag.goals)
        if not idents and not goals:
            return []
        return self._retrieve(problem, identifiers=idents or None, goals=goals or None)

    # ------------------------------------------------------------ internals

    def _extend(self, messages: list[Message], response: str, attempt: Attempt, index: int,
                max_attempts: int, max_chars: int, retrieved: list[str] | None = None,
                failure_hints: list[str] | None = None) -> list[Message]:
        attempt.feedback = feedback_for(attempt, max_chars=max_chars, retrieved=retrieved,
                                        failure_hints=failure_hints)
        remaining = max_attempts - index - 2
        self.events.emit("repair.feedback", problem=problem_id_of(messages), attempt=index,
                         chars=len(attempt.feedback))
        return [*messages, Message("assistant", response), repair_message(attempt.feedback, index, max(0, remaining))]

    @staticmethod
    def _last_failure(result: ProofResult) -> str:
        if not result.attempts:
            return "no attempts"
        last = result.attempts[-1]
        if last.extraction_error:
            return f"extraction: {last.extraction_error}"
        if last.forbidden:
            return "forbidden: " + ", ".join(last.forbidden)
        if last.verified is False:
            return last.feedback or "firewall rejected"
        cats = last.error_categories
        return "compile errors: " + (", ".join(cats) if cats else "unknown")


def problem_id_of(messages: list[Message]) -> str:
    for m in messages:
        if m.role == "user" and m.content.startswith("Problem: "):
            return m.content.splitlines()[0][len("Problem: "):]
    return "?"


def _unique_texts(texts: list[str]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in texts or [""]:
        for part in split_candidates(raw) if raw.strip() else [raw]:
            key = part.strip()
            if key and key not in seen:
                seen.add(key)
                found.append(part)
    return found or [""]


def _identifiers(attempt: Attempt) -> list[str]:
    return sorted({d.identifier for d in attempt.diagnostics if d.identifier})


def _build_retriever(settings: SearchSettings) -> PremiseSelector | None:
    if not settings.retrieval.enabled:
        return None
    r = settings.retrieval
    extra = r.extra_index_dir if r.extra_index_dir.exists() else None
    from erdos_forge.retrieval.mathlib_index import DeclarationIndex

    if extra is None and r.retrieve_k == 50 and r.top_k == 10:
        return default_selector()
    index = DeclarationIndex.load_default(extra)
    return PremiseSelector(index, retrieve_k=r.retrieve_k, top_k=r.top_k)
