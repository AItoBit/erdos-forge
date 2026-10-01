"""Store only kernel-verified helper lemmas. Nothing unverified enters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from erdos_forge.lemma.deduplicator import signature_key
from erdos_forge.lean.source import split_chunks
from erdos_forge.retrieval.mathlib_index import Declaration


@dataclass
class GeneratedLemma:
    name: str
    declaration: str
    source_problem: str
    signature_key: str
    uses: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "declaration": self.declaration,
            "source_problem": self.source_problem,
            "signature_key": self.signature_key,
            "uses": self.uses,
        }

    def as_declaration(self) -> Declaration:
        return Declaration(name=self.name, signature=self.declaration.split(":=", 1)[0].strip(), kind="lemma")


class GeneratedLemmaLibrary:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._by_key: dict[str, GeneratedLemma] = {}
        if self.path and self.path.exists():
            self._load()

    def __len__(self) -> int:
        return len(self._by_key)

    def add(self, declaration: str, source_problem: str) -> GeneratedLemma | None:
        key = signature_key(declaration)
        if key in self._by_key:
            return self._by_key[key]
        name = None
        for chunk in split_chunks(declaration):
            if chunk.is_theorem and chunk.name:
                name = chunk.name
                break
        if not name:
            return None
        lemma = GeneratedLemma(name=name, declaration=declaration.strip(), source_problem=source_problem, signature_key=key)
        self._by_key[key] = lemma
        self._flush()
        return lemma

    def add_from_preamble(self, preamble: str, source_problem: str) -> list[GeneratedLemma]:
        added: list[GeneratedLemma] = []
        for chunk in split_chunks(preamble):
            if chunk.is_theorem:
                lemma = self.add(chunk.text, source_problem)
                if lemma is not None:
                    added.append(lemma)
        return added

    def all(self) -> list[GeneratedLemma]:
        return list(self._by_key.values())

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                raw = json.loads(line)
                lemma = GeneratedLemma(
                    name=raw["name"],
                    declaration=raw["declaration"],
                    source_problem=raw["source_problem"],
                    signature_key=raw["signature_key"],
                    uses=int(raw.get("uses", 0)),
                )
                self._by_key[lemma.signature_key] = lemma

    def _flush(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            for lemma in self._by_key.values():
                fh.write(json.dumps(lemma.to_dict(), ensure_ascii=False) + "\n")
