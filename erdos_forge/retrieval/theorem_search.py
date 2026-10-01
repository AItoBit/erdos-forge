"""Lexical / BM25-style search over declaration names, signatures and docs."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from erdos_forge.retrieval.mathlib_index import Declaration, DeclarationIndex

# Lean identifiers, numerals and a handful of mathematical operators that appear in goals.
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_']*|[0-9]+|[≤≥≠∈∉⊆⊇∪∩∧∨→↔∀∃⊢∣%*+\-^=<>]+")
_NUM_WORDS = {"0": "zero", "1": "one", "2": "two"}
_CAMEL = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-cased tokens, with ``Nat.add_comm`` also yielding ``nat``, ``add``, ``comm``."""
    out: list[str] = []
    for raw in _TOKEN.findall(text or ""):
        low = raw.lower()
        out.append(low)
        if "_" in raw:
            out.extend(p.lower() for p in raw.split("_") if p)
        else:
            parts = _CAMEL.findall(raw)
            if len(parts) > 1:
                out.extend(p.lower() for p in parts)
        if low in _NUM_WORDS:
            out.append(_NUM_WORDS[low])
    return [t for t in out if t and t not in _STOP]


_STOP = frozenset(
    {
        "the", "a", "an", "of", "to", "in", "for", "and", "or", "is", "are",
        "type", "prop", "sort", "theorem", "lemma", "def", "abbrev",
    }
)


@dataclass
class ScoredDeclaration:
    declaration: Declaration
    score: float
    reasons: list[str]

    @property
    def name(self) -> str:
        return self.declaration.name


class TheoremSearch:
    """Inverted-index search. Built once per ``DeclarationIndex``."""

    def __init__(self, index: DeclarationIndex):
        self.index = index
        self._docs: list[Declaration] = []
        self._tf: list[Counter[str]] = []
        self._df: dict[str, int] = defaultdict(int)
        self._by_name: dict[str, Declaration] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        self._docs = self.index.all()
        self._tf = []
        self._df = defaultdict(int)
        self._by_name = {d.name: d for d in self._docs}
        for decl in self._docs:
            bag = Counter(tokenize(f"{decl.name} {decl.short_name} {decl.signature} {decl.docstring} {' '.join(decl.tags)}"))
            self._tf.append(bag)
            for tok in bag:
                self._df[tok] += 1
        self._n = max(len(self._docs), 1)

    def lookup(self, name: str) -> Declaration | None:
        if name in self._by_name:
            return self._by_name[name]
        return self.index.get(name)

    def search(self, query: str, k: int = 50, *, allow_mathlib: bool = True,
               extra_terms: list[str] | None = None) -> list[ScoredDeclaration]:
        q_tokens = tokenize(query)
        if extra_terms:
            q_tokens = q_tokens + tokenize(" ".join(extra_terms))
        if not q_tokens:
            return []
        q_set = set(q_tokens)
        q_counts = Counter(q_tokens)
        scored: list[ScoredDeclaration] = []
        for decl, bag in zip(self._docs, self._tf):
            if decl.requires_mathlib and not allow_mathlib:
                continue
            raw = 0.0
            reasons: list[str] = []
            # Exact / suffix name hits dominate: unknown-identifier repair.
            q = query.strip()
            if q == decl.name or q == decl.short_name:
                raw += 12.0
                reasons.append("exact_name")
            elif q and (decl.name.endswith("." + q) or decl.short_name == q):
                raw += 8.0
                reasons.append("short_name")
            elif q and q in decl.name:
                raw += 3.0
                reasons.append("name_contains")
            q_norm = re.sub(r"\s+", " ", q)
            sig_norm = re.sub(r"\s+", " ", decl.signature)
            conclusion = sig_norm.rsplit(" : ", 1)[-1] if " : " in sig_norm else sig_norm
            if conclusion and (q_norm == conclusion or conclusion in q_norm):
                raw += 8.0
                reasons.append("conclusion_match")
            elif q_norm and q_norm in sig_norm:
                raw += 5.0
                reasons.append("signature_contains")
            overlap = q_set & set(bag)
            if not overlap and raw == 0:
                continue
            idf_sum = 0.0
            for tok, qf in q_counts.items():
                df = self._df.get(tok, 0)
                if not df:
                    continue
                idf = math.log((self._n + 1) / (df + 0.5))
                idf_sum += qf * bag[tok] * idf
            raw += idf_sum
            if decl.short_name.lower() in q_set:
                raw += 2.5
                reasons.append("short_token")
            scored.append(ScoredDeclaration(decl, raw, reasons))
        scored.sort(key=lambda s: (-s.score, s.declaration.name))
        return scored[:k]
