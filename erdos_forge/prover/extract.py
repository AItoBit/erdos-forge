"""Turn a model response into a ``Candidate`` (target declaration + helper preamble)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from erdos_forge.lean.source import (
    Chunk,
    Theorem,
    find_top_level_assign,
    normalize_signature,
    split_chunks,
    split_declaration,
    strip_docstring,
)

_FENCE = re.compile(r"```(?:lean4?|Lean)?[^\n]*\n(.*?)```", re.S)


class ExtractionError(ValueError):
    pass


@dataclass
class Candidate:
    main_declaration: str
    preamble: str = ""
    dropped_imports: list[str] = field(default_factory=list)
    dropped_duplicates: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def source(self) -> str:
        return (self.preamble + "\n\n" + self.main_declaration).strip()


def code_from_response(text: str) -> str:
    blocks = [b for b in _FENCE.findall(text) if b.strip()]
    if blocks:
        return "\n\n".join(b.strip("\n") for b in blocks)
    if re.search(r"^\s*(theorem|lemma|example)\b", text, re.M):
        return text
    raise ExtractionError("response contains no ```lean code block and no declaration")


def _context_keys(theorem: Theorem) -> set[str]:
    return {normalize_signature(c.text) for c in split_chunks(theorem.context) if c.kind != "comment"}


def _is_target(chunk: Chunk, theorem: Theorem) -> bool:
    if not chunk.is_theorem:
        return False
    if theorem.is_example:
        try:
            sig, _ = split_declaration(chunk.text)
        except ValueError:
            return False
        return normalize_signature(sig) == theorem.normalized_signature
    name = chunk.name
    if name is None:
        return False
    short = theorem.name.split(".")[-1]
    return name == theorem.name or name.split(".")[-1] == short


def extract_candidate(response: str, theorem: Theorem) -> Candidate:
    code = code_from_response(response)
    chunks = split_chunks(code)
    ctx_keys = _context_keys(theorem)

    main: Chunk | None = None
    preamble: list[str] = []
    dropped_imports: list[str] = []
    dropped_dups: list[str] = []
    theorem_chunks: list[Chunk] = []

    for chunk in chunks:
        if chunk.kind == "import":
            dropped_imports.extend(ln.strip() for ln in chunk.text.splitlines() if ln.strip().startswith("import"))
            continue
        if chunk.kind == "comment" and not chunk.text.strip():
            continue
        if chunk.kind != "comment" and normalize_signature(chunk.text) in ctx_keys:
            dropped_dups.append(chunk.text.splitlines()[0][:80])
            continue
        if chunk.is_theorem:
            theorem_chunks.append(chunk)
        if main is None and _is_target(chunk, theorem):
            main = chunk
            continue
        preamble.append(chunk.text)

    if main is None:
        if len(theorem_chunks) == 1:
            main = theorem_chunks[0]
            preamble = [p for p in preamble if p != main.text]
        else:
            raise ExtractionError(
                f"could not find the target declaration `{theorem.name}` in the response "
                f"(found {len(theorem_chunks)} theorem-like declarations)"
            )

    decl = main.text.strip()
    idx = find_top_level_assign(decl)
    if idx == -1:
        raise ExtractionError("target declaration has no `:=`")
    proof = decl[idx + 2 :].strip()
    if not proof or proof == "by":
        raise ExtractionError("target declaration has an empty proof")

    # Normalise the main declaration: keep the response's docstring out of the
    # way so statement comparison works, and let the verifier re-add nothing.
    decl = strip_docstring(decl) if decl.lstrip().startswith("/-") else decl

    cand = Candidate(decl, "\n\n".join(preamble).strip(), dropped_imports, dropped_dups)
    if dropped_imports:
        cand.notes.append("ignored import lines (imports are fixed)")
    if dropped_dups:
        cand.notes.append("ignored declarations that repeat the given context")
    return cand
