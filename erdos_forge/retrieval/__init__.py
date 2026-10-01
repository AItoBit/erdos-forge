"""Mathlib / core-Lean retrieval and premise selection (V0.3).

Pipeline::

    retrieve 50  →  semantic rank  →  type-aware filter  →  rerank 10  →  LLM

The LLM is never expected to memorise Mathlib. Everything that reaches a
prompt is a declaration that actually exists in the index (seed + optional
Mathlib source scan + extra JSONL).
"""

from erdos_forge.retrieval.mathlib_index import Declaration, DeclarationIndex
from erdos_forge.retrieval.premise_selection import PremiseSelector, RetrievalQuery, default_selector
from erdos_forge.retrieval.theorem_search import ScoredDeclaration

__all__ = [
    "Declaration",
    "DeclarationIndex",
    "PremiseSelector",
    "RetrievalQuery",
    "ScoredDeclaration",
    "default_selector",
]
