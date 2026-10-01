"""Declaration index: seed + optional JSONL + optional Mathlib source scan."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from erdos_forge.config import REPO_ROOT
from erdos_forge.lean.source import find_top_level_assign, split_chunks, strip_docstring

log = logging.getLogger("erdos_forge.retrieval")

_DECL_KINDS = frozenset(
    {"theorem", "lemma", "def", "abbrev", "instance", "class", "structure", "inductive", "opaque"}
)


@dataclass
class Declaration:
    name: str
    signature: str
    kind: str = "theorem"
    namespace: str = ""
    docstring: str = ""
    source_file: str = ""
    dependencies: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    requires_mathlib: bool = False

    @property
    def short_name(self) -> str:
        return self.name.rsplit(".", 1)[-1]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "namespace": self.namespace,
            "kind": self.kind,
            "signature": self.signature,
            "docstring": self.docstring,
            "source_file": self.source_file,
            "dependencies": self.dependencies,
            "related": self.related,
            "tags": self.tags,
            "requires_mathlib": self.requires_mathlib,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Declaration":
        name = str(raw.get("name") or "")
        return cls(
            name=name,
            signature=str(raw.get("signature") or name),
            kind=str(raw.get("kind") or "theorem"),
            namespace=str(raw.get("namespace") or (name.rsplit(".", 1)[0] if "." in name else "")),
            docstring=str(raw.get("docstring") or ""),
            source_file=str(raw.get("source_file") or ""),
            dependencies=list(raw.get("dependencies") or []),
            related=list(raw.get("related") or []),
            tags=list(raw.get("tags") or []),
            requires_mathlib=bool(raw.get("requires_mathlib", False)),
        )

    def prompt_line(self) -> str:
        sig = self.signature.strip()
        if sig.startswith(self.kind + " "):
            sig = sig[len(self.kind) :].strip()
        doc = f"  -- {self.docstring}" if self.docstring else ""
        return f"{self.name}: {sig}{doc}"


class DeclarationIndex:
    """In-memory collection keyed by fully-qualified name (last write wins)."""

    def __init__(self, declarations: list[Declaration] | None = None):
        self._by_name: dict[str, Declaration] = {}
        for decl in declarations or []:
            self.add(decl)

    def add(self, decl: Declaration) -> None:
        if decl.name:
            self._by_name[decl.name] = decl

    def extend(self, decls: list[Declaration]) -> None:
        for decl in decls:
            self.add(decl)

    def get(self, name: str) -> Declaration | None:
        if name in self._by_name:
            return self._by_name[name]
        short = [d for d in self._by_name.values() if d.short_name == name or d.name.endswith("." + name)]
        return short[0] if len(short) == 1 else None

    def __len__(self) -> int:
        return len(self._by_name)

    def __iter__(self):
        return iter(self._by_name.values())

    def all(self) -> list[Declaration]:
        return list(self._by_name.values())

    def filter(self, *, allow_mathlib: bool = True) -> list[Declaration]:
        if allow_mathlib:
            return self.all()
        return [d for d in self._by_name.values() if not d.requires_mathlib]

    def merge(self, other: "DeclarationIndex") -> "DeclarationIndex":
        out = DeclarationIndex(self.all())
        out.extend(other.all())
        return out

    def write_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for decl in sorted(self._by_name.values(), key=lambda d: d.name):
                fh.write(json.dumps(decl.to_dict(), ensure_ascii=False) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "DeclarationIndex":
        path = Path(path)
        decls: list[Declaration] = []
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                decls.append(Declaration.from_dict(json.loads(line)))
        return cls(decls)

    @classmethod
    def load_default(cls, extra_dir: str | Path | None = None) -> "DeclarationIndex":
        from erdos_forge.retrieval.seed import seed_declarations

        index = cls(seed_declarations())
        extra = Path(extra_dir) if extra_dir else REPO_ROOT / "data" / "mathlib_index"
        if extra.is_dir():
            for path in sorted(extra.glob("*.jsonl")):
                if path.name.startswith("_"):
                    continue
                index.extend(cls.from_jsonl(path).all())
        return index


def find_mathlib_root(project_dir: str | Path) -> Path | None:
    root = Path(project_dir)
    candidates = [
        root / ".lake" / "packages" / "mathlib" / "Mathlib",
        root / "Mathlib",
        root.parent / "mathlib" / "Mathlib",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def index_lean_source(source: str, source_file: str = "", *, requires_mathlib: bool = True) -> list[Declaration]:
    """Extract theorem/lemma/def signatures from a Lean file (no compiler needed)."""
    decls: list[Declaration] = []
    stack: list[str] = []
    pending_doc = ""
    for chunk in split_chunks(source):
        stripped = strip_docstring(chunk.text) if chunk.text.strip() else ""
        head = stripped.splitlines()[0] if stripped.strip() else ""
        if chunk.kind == "namespace":
            parts = head.split()
            if len(parts) >= 2:
                stack.append(parts[1])
            pending_doc = ""
            continue
        if chunk.kind == "section":
            pending_doc = ""
            continue
        if chunk.kind == "end":
            if stack:
                stack.pop()
            pending_doc = ""
            continue
        if chunk.kind == "comment":
            text = chunk.text.strip()
            if text.startswith("/--"):
                pending_doc = text[3:].split("-/", 1)[0].strip()
            continue
        if chunk.kind not in _DECL_KINDS or not chunk.name:
            pending_doc = ""
            continue
        idx = find_top_level_assign(chunk.text)
        signature = (chunk.text[:idx] if idx != -1 else chunk.text).strip()
        signature = strip_docstring(signature)
        short = chunk.name
        if short.startswith("_root_."):
            fq = short[len("_root_.") :]
        else:
            fq = ".".join([*stack, short]) if stack else short
        ns = fq.rsplit(".", 1)[0] if "." in fq else ""
        decls.append(
            Declaration(
                name=fq,
                signature=signature,
                kind=chunk.kind,
                namespace=ns,
                docstring=pending_doc,
                source_file=source_file,
                requires_mathlib=requires_mathlib,
            )
        )
        pending_doc = ""
    return decls


def index_mathlib_tree(root: str | Path, *, limit: int | None = None) -> DeclarationIndex:
    """Walk a Mathlib source tree and collect declaration signatures."""
    root = Path(root)
    index = DeclarationIndex()
    files = sorted(p for p in root.rglob("*.lean") if "Test" not in p.parts)
    if limit is not None:
        files = files[:limit]
    for i, path in enumerate(files, 1):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("skip %s: %s", path, exc)
            continue
        rel = str(path.relative_to(root.parent) if root.name == "Mathlib" else path)
        index.extend(index_lean_source(source, rel, requires_mathlib=True))
        if i % 400 == 0:
            log.info("indexed %d/%d Mathlib files (%d decls)", i, len(files), len(index))
    return index
