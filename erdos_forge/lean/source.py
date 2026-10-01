"""Parse Lean source files into benchmark theorems and assemble candidate files.

A ``Theorem`` is a declaration whose proof is hidden from the prover. Its
``context`` is every *non-theorem* top-level chunk preceding it (imports,
``open``, ``namespace``, ``def``s, ...), so sibling benchmark problems are never
visible as usable lemmas.

This module is the single place that turns text into Lean files. The
verification firewall relies on it to rebuild a candidate from scratch, so the
LLM never controls the file layout, the statement, or the trailing audit
commands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MODIFIERS = r"(?:(?:private|protected|noncomputable|partial|unsafe|nonrec)\s+)*"
_DECL_START = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?"
    + _MODIFIERS
    + r"(?P<kw>theorem|lemma|example|def|abbrev|instance|structure|inductive|class|axiom|opaque"
    r"|open|namespace|end|section|variable|universe|import|set_option|attribute|notation"
    r"|infix|infixl|infixr|prefix|postfix|macro|syntax|macro_rules|elab|mutual|#\w+)\b"
)
_COMMENT_START = re.compile(r"^/-")
THEOREM_KEYWORDS = {"theorem", "lemma", "example"}
_OPEN = "([{⟨⦃"
_CLOSE = ")]}⟩⦄"


@dataclass(frozen=True)
class Theorem:
    """A statement to prove, with the context it lives in and its hidden reference proof."""

    name: str
    signature: str
    context: str = ""
    source: str | None = None
    line: int = 0
    reference_proof: str | None = None

    @property
    def is_example(self) -> bool:
        return self.decl_keyword == "example"

    @property
    def decl_keyword(self) -> str:
        m = _DECL_START.match(strip_docstring(self.signature))
        return m.group("kw") if m else "theorem"

    @property
    def imports(self) -> str:
        return split_imports(self.context)[0]

    @property
    def body_context(self) -> str:
        return split_imports(self.context)[1]

    @property
    def normalized_signature(self) -> str:
        return normalize_signature(self.signature)

    def with_sorry(self) -> str:
        return f"{self.signature} := by\n  sorry"

    def with_proof(self, proof_body: str) -> str:
        """Full declaration with a tactic block body (lines are re-indented)."""
        body = indent_block(proof_body.strip()) if proof_body.strip() else "  skip"
        return f"{self.signature} := by\n{body}"


def indent_block(text: str, prefix: str = "  ") -> str:
    lines = text.splitlines()
    # Remove the common leading indentation so nested blocks stay aligned.
    nonblank = [ln for ln in lines if ln.strip()]
    common = min((len(ln) - len(ln.lstrip()) for ln in nonblank), default=0)
    return "\n".join(prefix + ln[common:] if ln.strip() else "" for ln in lines)


def strip_docstring(text: str) -> str:
    text = text.lstrip()
    while text.startswith("/-"):
        end = text.find("-/")
        if end == -1:
            break
        text = text[end + 2 :].lstrip()
    return text


def normalize_signature(signature: str) -> str:
    """Whitespace- and docstring-insensitive form used to detect statement changes."""
    text = strip_docstring(signature)
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*([(){}\[\]:,⟨⟩⦃⦄])\s*", r"\1", text)
    return text


def find_top_level_assign(text: str) -> int:
    """Index of the first ``:=`` outside brackets, strings and comments, or -1."""
    depth = 0
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("--", i):
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue
        if text.startswith("/-", i):
            end = text.find("-/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth = max(0, depth - 1)
        elif depth == 0 and text.startswith(":=", i):
            return i
        i += 1
    return -1


@dataclass(frozen=True)
class Chunk:
    line: int
    kind: str  # declaration keyword or "comment"
    text: str

    @property
    def is_theorem(self) -> bool:
        return self.kind in THEOREM_KEYWORDS

    @property
    def name(self) -> str | None:
        if self.kind == "example":
            return None
        m = re.search(rf"\b{self.kind}\s+([^\s(\[{{:⦃]+)", strip_docstring(self.text))
        return m.group(1) if m else None


def split_chunks(source: str) -> list[Chunk]:
    """Split source into top-level chunks (one per declaration or comment block)."""
    chunks: list[tuple[int, str, list[str]]] = []
    in_block_comment = 0
    for lineno, line in enumerate(source.splitlines(), start=1):
        if in_block_comment == 0 and line and not line[0].isspace():
            m = _DECL_START.match(line)
            if m:
                chunks.append((lineno, m.group("kw"), [line]))
                in_block_comment += line.count("/-") - line.count("-/")
                continue
            if _COMMENT_START.match(line):
                chunks.append((lineno, "comment", [line]))
                in_block_comment += line.count("/-") - line.count("-/")
                continue
        in_block_comment = max(0, in_block_comment + line.count("/-") - line.count("-/"))
        if chunks:
            chunks[-1][2].append(line)
        else:
            chunks.append((lineno, "comment", [line]))
    return [Chunk(ln, kind, "\n".join(lines).rstrip()) for ln, kind, lines in chunks]


def qualified_theorem_names(source: str) -> list[str]:
    """Fully qualified names of all named theorems/lemmas, following namespaces.

    `#print axioms` commands appended at the end of a file run outside any
    namespace that was closed with `end`, so short names would not resolve.
    """
    names: list[str] = []
    stack: list[tuple[str, str | None]] = []  # (kind, name)
    for chunk in split_chunks(source):
        stripped = strip_docstring(chunk.text)
        head = stripped.splitlines()[0] if stripped.strip() else ""
        if chunk.kind == "namespace":
            m = re.match(r"namespace\s+(\S+)", head)
            stack.append(("namespace", m.group(1) if m else None))
        elif chunk.kind == "section":
            m = re.match(r"section(?:\s+(\S+))?", head)
            stack.append(("section", m.group(1) if m else None))
        elif chunk.kind == "end":
            if stack:
                stack.pop()
        elif chunk.is_theorem and chunk.name:
            name = chunk.name
            if name.startswith("_root_."):
                names.append(name[len("_root_."):])
            else:
                prefix = [n for k, n in stack if k == "namespace" and n]
                names.append(".".join([*prefix, name]))
    return names


def split_declaration(text: str) -> tuple[str, str]:
    """Split ``<signature> := <proof>`` at the top-level ``:=``.

    Returns ``(signature, proof)`` where ``proof`` keeps a leading ``by`` if present.
    """
    idx = find_top_level_assign(text)
    if idx == -1:
        raise ValueError("declaration has no top-level ':='")
    return text[:idx].rstrip(), text[idx + 2 :].strip()


def proof_body(proof: str) -> str:
    """Strip a leading ``by`` from a proof term so it can be re-indented as a tactic block."""
    proof = proof.strip()
    if proof == "by":
        return ""
    if proof.startswith("by\n") or proof.startswith("by "):
        return proof[2:].strip("\n")
    return "exact " + proof


def parse_theorems(source: str, source_name: str | None = None) -> list[Theorem]:
    theorems: list[Theorem] = []
    context: list[str] = []
    pending_doc: Chunk | None = None

    for chunk in split_chunks(source):
        if chunk.kind == "comment":
            if pending_doc is not None:
                context.append(pending_doc.text)
            pending_doc = chunk if chunk.text.lstrip().startswith("/--") else None
            if pending_doc is None:
                context.append(chunk.text)
            continue

        if chunk.is_theorem:
            idx = find_top_level_assign(chunk.text)
            if idx == -1:
                raise ValueError(f"{source_name}:{chunk.line}: cannot find ':=' in declaration")
            signature = chunk.text[:idx].rstrip()
            start_line = chunk.line
            if pending_doc is not None:
                signature = pending_doc.text.rstrip() + "\n" + signature
                start_line = pending_doc.line
                pending_doc = None
            name = chunk.name or f"example_L{chunk.line}"
            theorems.append(
                Theorem(
                    name=name,
                    signature=signature,
                    context="\n".join(context).strip(),
                    source=source_name,
                    line=start_line,
                    reference_proof=chunk.text[idx + 2 :].strip(),
                )
            )
            continue

        if pending_doc is not None:
            context.append(pending_doc.text)
            pending_doc = None
        context.append(chunk.text)

    return theorems


def split_imports(context: str) -> tuple[str, str]:
    """Split a context into its leading ``import`` block and the rest."""
    lines = context.splitlines()
    imports: list[str] = []
    i = 0
    in_comment = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if in_comment or stripped.startswith("/-"):
            in_comment += line.count("/-") - line.count("-/")
            in_comment = max(in_comment, 0)
        elif stripped.startswith("import "):
            imports.append(stripped)
        elif stripped and not stripped.startswith("--"):
            break
        i += 1
    return "\n".join(imports), "\n".join(lines[i:]).strip()


def load_theorems(path: str | Path) -> list[Theorem]:
    path = Path(path)
    return parse_theorems(path.read_text(encoding="utf-8"), source_name=str(path))


def load_theorem(spec: str) -> Theorem:
    """Load ``path/to/File.lean:theorem_name``."""
    path, sep, name = spec.rpartition(":")
    if not sep or not path or len(path) == 1:
        raise ValueError(f"expected FILE.lean:NAME, got {spec!r}")
    theorems = load_theorems(path)
    for thm in theorems:
        if thm.name == name or thm.name.split(".")[-1] == name:
            return thm
    available = ", ".join(t.name for t in theorems)
    raise KeyError(f"theorem {name!r} not found in {path}. Available: {available}")


# ----------------------------------------------------------------- assembly

AUDIT_NAME = "erdos_forge_audit_target"

# Plain `lean` (unlike a Lake build of Mathlib-style projects) has autoImplicit
# enabled, so a typo such as `undefined_thing` silently becomes a bound
# variable and the statement still elaborates. That is exactly the "silently
# weakened statement" failure mode, so every assembled file disables it.
SAFETY_OPTIONS = ["set_option autoImplicit false", "set_option relaxedAutoImplicit false"]


def audit_name(theorem: Theorem) -> str:
    return AUDIT_NAME if theorem.is_example else theorem.name


def assemble_file(
    theorem: Theorem,
    main_declaration: str,
    preamble: str = "",
    max_heartbeats: int | None = None,
    audit: bool = True,
) -> str:
    """Build a complete Lean file: imports, options, context, helpers, target, audit.

    ``main_declaration`` must be the full target declaration (signature and
    proof). ``example``s are renamed so ``#print axioms`` can inspect them.
    """
    imports, body = split_imports(theorem.context)
    parts: list[str] = []
    if imports:
        parts.append(imports)
    options = list(SAFETY_OPTIONS)
    if max_heartbeats is not None:
        options.append(f"set_option maxHeartbeats {max_heartbeats}")
    parts.append("\n".join(options))
    if body:
        parts.append(body)
    if preamble.strip():
        parts.append(preamble.strip())
    decl = main_declaration.strip()
    if theorem.is_example and audit:
        decl = re.sub(r"\bexample\b", f"theorem {AUDIT_NAME}", decl, count=1)
    parts.append(decl)
    if audit:
        parts.append(f"#print axioms {audit_name(theorem)}")
    return "\n\n".join(parts) + "\n"
