"""Structured Lean diagnostics.

Raw compiler output is turned into ``LeanDiagnostic`` records with a category
and a suggested action, so the controller can route errors (retrieve a
declaration, continue a proof, fix syntax, ...) and so the model receives a
compact, structured description instead of thousands of characters of logs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from erdos_forge.lean.goal_parser import extract_goals


class Category(str, Enum):
    UNKNOWN_IDENTIFIER = "unknown_identifier"
    UNKNOWN_TACTIC = "unknown_tactic"
    TYPE_MISMATCH = "type_mismatch"
    UNSOLVED_GOALS = "unsolved_goals"
    TACTIC_FAILURE = "tactic_failure"
    FAILED_SYNTHESIS = "failed_synthesis"
    COERCION = "coercion"
    REWRITE_FAILURE = "rewrite_failure"
    TERMINATION = "termination"
    UNIVERSE = "universe"
    PARSER = "parser"
    IMPORT = "import"
    TIMEOUT = "timeout"
    FORBIDDEN = "forbidden"
    SORRY = "sorry"
    ELABORATION = "elaboration"
    LINTER = "linter"
    INFO = "info"
    OTHER = "other"


LIKELY_ACTION: dict[Category, str] = {
    Category.UNKNOWN_IDENTIFIER: "retrieve_declaration",
    Category.UNKNOWN_TACTIC: "fix_tactic_name",
    Category.TYPE_MISMATCH: "inspect_types_and_repair",
    Category.UNSOLVED_GOALS: "continue_proof",
    Category.TACTIC_FAILURE: "try_alternative_tactic",
    Category.FAILED_SYNTHESIS: "fix_instance_or_type",
    Category.COERCION: "insert_cast_or_lemma",
    Category.REWRITE_FAILURE: "check_rewrite_direction",
    Category.TERMINATION: "add_termination_proof",
    Category.UNIVERSE: "fix_universe_levels",
    Category.PARSER: "fix_syntax",
    Category.IMPORT: "fix_import",
    Category.TIMEOUT: "simplify_or_split",
    Category.FORBIDDEN: "reject",
    Category.SORRY: "reject",
    Category.ELABORATION: "repair",
    Category.LINTER: "ignore",
    Category.INFO: "ignore",
    Category.OTHER: "repair",
}

# Order matters: the first matching rule wins.
_RULES: list[tuple[Category, re.Pattern[str]]] = [
    (Category.TIMEOUT, re.compile(r"deterministic\)? timeout|maximum recursion depth|heartbeats|timed out", re.I)),
    (Category.SORRY, re.compile(r"declaration uses .sorry.|contains sorry", re.I)),
    (Category.IMPORT, re.compile(r"unknown module prefix|unknown (package|module)|object file .* does not exist|import .* failed|bad import", re.I)),
    (Category.UNKNOWN_IDENTIFIER, re.compile(r"unknown (identifier|constant|namespace)|unknown free variable", re.I)),
    (Category.UNKNOWN_TACTIC, re.compile(r"unknown tactic", re.I)),
    (Category.PARSER, re.compile(r"unexpected token|unexpected identifier|expected (term|command|'|\")|unterminated|: expected ", re.I)),
    (Category.FAILED_SYNTHESIS, re.compile(r"failed to synthesize", re.I)),
    (Category.TERMINATION, re.compile(r"fail(ed)? to (prove|show) termination|structural recursion|well-founded", re.I)),
    (Category.UNIVERSE, re.compile(r"universe level|stuck at solving universe", re.I)),
    (Category.REWRITE_FAILURE, re.compile(r"did not find instance of the pattern|motive is not type correct|rewrite failed|rw failed", re.I)),
    (Category.UNSOLVED_GOALS, re.compile(r"unsolved goals", re.I)),
    (Category.TYPE_MISMATCH, re.compile(r"type mismatch|has type .* but is expected to have type|application type mismatch", re.I | re.S)),
    (Category.COERCION, re.compile(r"coercion|cannot coerce|failed to coerce", re.I)),
    (Category.LINTER, re.compile(r"linter|unused variable|unused `have`|this tactic is never executed", re.I)),
    (Category.TACTIC_FAILURE, re.compile(
        r"tactic .* failed|failed|could not|did not|not applicable|unable to|no goals( to be (proved|solved))?|made no progress|"
        r"omega could not prove|linarith failed|simp made no progress|decide failed", re.I)),
]

# Lean ≥ 4.2x may tag messages with an error name: `error(lean.unknownIdentifier): ...`.
_HEADER = re.compile(
    r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+?):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<sev>error|warning|info)(?:\((?P<code>[^)]*)\))?: ?(?P<msg>.*)$"
)
_BARE_HEADER = re.compile(r"^(?P<sev>error|warning|info)(?:\((?P<code>[^)]*)\))?: (?P<msg>.*)$")
# Lean names may end in primes (`add_comm'`) and are quoted with '...' or `...`
# depending on the version, so match non-greedily up to the closing quote.
_IDENT = re.compile(r"unknown (?:identifier|constant|namespace) ['`](\S+?)['`](?:\s|$)", re.I)
_AXIOMS = re.compile(r"['`](\S+?)['`] depends on axioms: \[(.*?)\]", re.S)
_NO_AXIOMS = re.compile(r"['`](\S+?)['`] does not depend on any axioms")

# Error names reported by newer Lean versions map directly onto categories.
_CODE_CATEGORIES: dict[str, Category] = {
    "lean.unknownIdentifier": Category.UNKNOWN_IDENTIFIER,
    "lean.unknownConstant": Category.UNKNOWN_IDENTIFIER,
    "lean.unsolvedGoals": Category.UNSOLVED_GOALS,
    "lean.typeMismatch": Category.TYPE_MISMATCH,
    "lean.appTypeMismatch": Category.TYPE_MISMATCH,
    "lean.synthInstanceFailed": Category.FAILED_SYNTHESIS,
    "lean.parserError": Category.PARSER,
    "lean.unknownTactic": Category.UNKNOWN_TACTIC,
    "lean.deterministicTimeout": Category.TIMEOUT,
    "lean.maxHeartbeats": Category.TIMEOUT,
}


@dataclass
class LeanDiagnostic:
    severity: str
    message: str
    category: Category = Category.OTHER
    file: str | None = None
    line: int | None = None
    column: int | None = None
    identifier: str | None = None
    goals: list[str] = field(default_factory=list)
    likely_action: str = "repair"
    code: str | None = None  # Lean error name, e.g. `lean.unknownIdentifier`

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    @property
    def headline(self) -> str:
        return self.message.strip().splitlines()[0] if self.message.strip() else ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category.value,
            "code": self.code,
            "line": self.line,
            "column": self.column,
            "identifier": self.identifier,
            "headline": self.headline,
            "goals": len(self.goals),
            "likely_action": self.likely_action,
        }


def classify(message: str, severity: str = "error", code: str | None = None) -> Category:
    if severity == "info":
        return Category.INFO
    if code and code in _CODE_CATEGORIES:
        return _CODE_CATEGORIES[code]
    for category, pattern in _RULES:
        if pattern.search(message):
            return category
    if severity == "warning":
        return Category.OTHER
    return Category.ELABORATION


def parse_diagnostics(output: str) -> list[LeanDiagnostic]:
    """Parse ``lean`` output into diagnostics (multi-line messages are grouped)."""
    diags: list[LeanDiagnostic] = []
    current: LeanDiagnostic | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current, body
        if current is None:
            return
        message = "\n".join([current.message, *body]).rstrip() if body else current.message
        current.message = message
        current.category = classify(message, current.severity, current.code)
        current.likely_action = LIKELY_ACTION[current.category]
        if current.category == Category.UNKNOWN_IDENTIFIER:
            m = _IDENT.search(message)
            current.identifier = m.group(1) if m else None
        if current.category == Category.UNSOLVED_GOALS:
            current.goals = extract_goals(message)
        diags.append(current)
        current, body = None, []

    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if _AXIOMS.match(line) or _NO_AXIOMS.match(line):
            # `#print axioms` output may be printed without a location header;
            # keep it out of goal dumps.
            flush()
            diags.append(LeanDiagnostic("info", line, Category.INFO, likely_action="ignore"))
            continue
        m = _HEADER.match(line)
        if m:
            flush()
            current = LeanDiagnostic(
                severity=m.group("sev"),
                message=m.group("msg"),
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                code=m.group("code"),
            )
            continue
        b = _BARE_HEADER.match(line)
        if b:
            flush()
            current = LeanDiagnostic(severity=b.group("sev"), message=b.group("msg"), code=b.group("code"))
            continue
        if current is not None:
            body.append(line)
        elif line.strip():
            # Output outside any diagnostic (lake noise, panics). Keep as OTHER.
            diags.append(LeanDiagnostic("info", line, Category.OTHER, likely_action="ignore"))
    flush()
    return diags


def errors(diags: list[LeanDiagnostic]) -> list[LeanDiagnostic]:
    return [d for d in diags if d.is_error]


def axioms_from_output(output: str) -> dict[str, list[str]]:
    """Map declaration name -> axioms, read from ``#print axioms`` info messages."""
    found: dict[str, list[str]] = {}
    for m in _NO_AXIOMS.finditer(output):
        found[m.group(1)] = []
    for m in _AXIOMS.finditer(output):
        found[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    return found


def uses_sorry(output: str) -> bool:
    return bool(re.search(r"declaration uses .sorry.", output))


def summarize(diags: list[LeanDiagnostic], max_chars: int = 3000, max_items: int = 8,
              include_warnings: bool = False) -> str:
    """Compact, structured rendering of diagnostics for an LLM prompt."""
    chosen = [d for d in diags if d.is_error or (include_warnings and d.severity == "warning")]
    chosen = chosen[:max_items]
    if not chosen:
        return "(no errors)"
    blocks: list[str] = []
    budget = max_chars
    for i, d in enumerate(chosen, 1):
        loc = f"line {d.line}" if d.line is not None else "no location"
        head = f"[{i}] {d.severity} @ {loc} | category={d.category.value} | action={d.likely_action}"
        msg = d.message.strip()
        per_item = max(200, budget // max(1, len(chosen) - i + 1))
        if len(msg) > per_item:
            msg = msg[: per_item - 20].rstrip() + "\n... (truncated)"
        block = head + "\n" + msg
        blocks.append(block)
        budget -= len(block)
        if budget <= 0:
            break
    return "\n\n".join(blocks)
