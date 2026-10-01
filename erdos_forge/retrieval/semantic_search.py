"""Type-signature overlap ranking (no embedding model required).

A later version can swap this for dense embeddings. The interface stays:
``rank(query_type, candidates) -> scored candidates``.
"""

from __future__ import annotations

import re

from erdos_forge.retrieval.mathlib_index import Declaration
from erdos_forge.retrieval.theorem_search import ScoredDeclaration, tokenize

_COLON_BINDERS = re.compile(r"\([^)]*:\s*([^)]+)\)|\{[^}]*:\s*([^}]+)\}")


def type_tokens(signature: str) -> set[str]:
    """Tokens from binder types and the conclusion of a Lean signature."""
    text = signature or ""
    parts = [m.group(1) or m.group(2) for m in _COLON_BINDERS.finditer(text)]
    if " : " in text:
        parts.append(text.rsplit(" : ", 1)[-1])
    elif ":" in text:
        parts.append(text.rsplit(":", 1)[-1])
    return set(tokenize(" ".join(parts)))


def signature_overlap(query_sig: str, decl: Declaration) -> float:
    q = type_tokens(query_sig)
    d = type_tokens(decl.signature)
    if not q or not d:
        return 0.0
    inter = q & d
    if not inter:
        return 0.0
    return len(inter) / math_sqrt(len(q) * len(d))


def math_sqrt(x: float) -> float:
    return x ** 0.5


def rerank_by_type(query_sig: str, hits: list[ScoredDeclaration], *, weight: float = 2.0) -> list[ScoredDeclaration]:
    """Boost candidates whose binder/conclusion types overlap the query."""
    if not query_sig.strip():
        return hits
    out: list[ScoredDeclaration] = []
    for hit in hits:
        extra = weight * signature_overlap(query_sig, hit.declaration)
        reasons = list(hit.reasons)
        if extra > 0:
            reasons.append(f"type_overlap={extra:.2f}")
        out.append(ScoredDeclaration(hit.declaration, hit.score + extra, reasons))
    out.sort(key=lambda s: (-s.score, s.declaration.name))
    return out
