"""Canonical keys so the same helper lemma is not stored twice."""

from __future__ import annotations

from erdos_forge.lean.source import normalize_signature


def signature_key(declaration: str) -> str:
    return normalize_signature(declaration)
