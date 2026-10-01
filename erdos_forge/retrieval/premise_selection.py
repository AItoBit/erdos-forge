"""P(theorem useful | current Lean state) — V0.3 is lexical + type-aware.

Later this becomes a trained ranker. The input/output contract stays::

    local context + goal + identifiers + domain  →  [(lemma, score), ...]
"""

from __future__ import annotations

from dataclasses import dataclass, field

from erdos_forge.core.state import Problem
from erdos_forge.retrieval.mathlib_index import DeclarationIndex
from erdos_forge.retrieval.reranker import rerank
import re

from erdos_forge.retrieval.theorem_search import ScoredDeclaration, TheoremSearch

_IDENT = re.compile(r"\b[A-Z][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")


@dataclass
class RetrievalQuery:
    text: str
    goal: str = ""
    identifiers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    allow_mathlib: bool = False
    imports: str = ""

    @classmethod
    def from_problem(cls, problem: Problem, *, identifiers: list[str] | None = None,
                     goals: list[str] | None = None) -> "RetrievalQuery":
        thm = problem.theorem
        imports = thm.imports or ""
        goal = "\n".join(goals) if goals else thm.signature
        return cls(
            text=" ".join(p for p in (thm.signature, problem.notes, " ".join(problem.tags)) if p),
            goal=goal,
            identifiers=list(identifiers or _idents_from_signature(thm.signature)),
            tags=list(problem.tags),
            allow_mathlib="mathlib" in imports.lower(),
            imports=imports,
        )


def _idents_from_signature(signature: str) -> list[str]:
    return _IDENT.findall(signature or "")


def format_hits(hits: list[ScoredDeclaration]) -> list[str]:
    return [h.declaration.prompt_line() for h in hits]


class PremiseSelector:
    def __init__(self, index: DeclarationIndex, retrieve_k: int = 50, top_k: int = 10):
        self.index = index
        self.search = TheoremSearch(index)
        self.retrieve_k = retrieve_k
        self.top_k = top_k

    def select(self, query: RetrievalQuery, k: int | None = None) -> list[ScoredDeclaration]:
        top_k = k if k is not None else self.top_k
        extra = list(query.identifiers) + list(query.tags)
        blob = " ".join(p for p in (query.text, query.goal, *query.identifiers) if p)
        # Identifier-first pass so unknown names surface close matches.
        hits: dict[str, ScoredDeclaration] = {}
        for ident in query.identifiers:
            for hit in self.search.search(ident, k=12, allow_mathlib=query.allow_mathlib):
                prev = hits.get(hit.name)
                if prev is None or hit.score > prev.score:
                    hits[hit.name] = hit
        for hit in self.search.search(blob, k=self.retrieve_k, allow_mathlib=query.allow_mathlib, extra_terms=extra):
            prev = hits.get(hit.name)
            if prev is None or hit.score > prev.score:
                hits[hit.name] = hit
        pooled = sorted(hits.values(), key=lambda s: (-s.score, s.declaration.name))
        return rerank(query.goal or query.text, pooled, k=top_k)

    def select_for_problem(self, problem: Problem, k: int | None = None) -> list[ScoredDeclaration]:
        return self.select(RetrievalQuery.from_problem(problem), k=k)


_SELECTOR: PremiseSelector | None = None


def default_selector(index: DeclarationIndex | None = None, retrieve_k: int = 50, top_k: int = 10) -> PremiseSelector:
    global _SELECTOR
    if index is not None:
        return PremiseSelector(index, retrieve_k=retrieve_k, top_k=top_k)
    if _SELECTOR is None:
        _SELECTOR = PremiseSelector(DeclarationIndex.load_default(), retrieve_k=retrieve_k, top_k=top_k)
    return _SELECTOR
