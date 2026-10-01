"""Type-aware filter + final top-k cut.

The LLM only ever sees the reranked slice (default 10), never the raw 50.
"""

from __future__ import annotations

from erdos_forge.retrieval.semantic_search import rerank_by_type, type_tokens
from erdos_forge.retrieval.theorem_search import ScoredDeclaration


def type_aware_filter(query_sig: str, hits: list[ScoredDeclaration], *, min_keep: int = 8) -> list[ScoredDeclaration]:
    """Drop declarations with no type overlap, unless that would empty the list.

    Exact-name / short-name hits always survive (unknown-identifier repair).
    """
    if not query_sig.strip() or not hits:
        return hits
    q = type_tokens(query_sig)
    if not q:
        return hits
    kept: list[ScoredDeclaration] = []
    weak: list[ScoredDeclaration] = []
    for hit in hits:
        forced = any(r in {"exact_name", "short_name"} for r in hit.reasons)
        if forced:
            kept.append(hit)
            continue
        d = type_tokens(hit.declaration.signature)
        if q & d:
            kept.append(hit)
        else:
            weak.append(hit)
    if len(kept) >= min_keep:
        return kept
    return kept + weak[: max(0, min_keep - len(kept))]


def rerank(query_sig: str, hits: list[ScoredDeclaration], k: int = 10) -> list[ScoredDeclaration]:
    filtered = type_aware_filter(query_sig, hits)
    ranked = rerank_by_type(query_sig, filtered)
    return ranked[:k]
