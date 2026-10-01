"""Verification firewall: the only component allowed to declare success.

A candidate passes only if, in this order:

1. its source contains none of the forbidden constructs (``sorry``, ``admit``,
   ``axiom``, ``unsafe``, ``native_decide``, ...);
2. the target statement is byte-for-byte (modulo whitespace/docstrings) the
   original one, so nothing was silently weakened;
3. a file rebuilt from scratch (imports + context + helpers + target +
   ``#print axioms``) compiles with exit code 0 in a fresh ``lake env lean``
   process, with no errors and no ``declaration uses 'sorry'`` warnings;
4. the axioms reported by the kernel are a subset of the allowed set.

The LLM never sees or controls this component.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from erdos_forge.lean.compiler import CompileResult, LeanCompiler
from erdos_forge.lean.diagnostics import LeanDiagnostic, axioms_from_output, errors, parse_diagnostics, uses_sorry
from erdos_forge.lean.source import (
    SAFETY_OPTIONS,
    Theorem,
    assemble_file,
    audit_name,
    normalize_signature,
    qualified_theorem_names,
    split_declaration,
    split_imports,
)

# Patterns matched against source with comments and strings removed.
FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("sorry", re.compile(r"\bsorry\b")),
    ("admit", re.compile(r"\badmit\b")),
    ("axiom", re.compile(r"(^|\n)\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?axiom\b")),
    ("unsafe", re.compile(r"\bunsafe\b")),
    ("native_decide", re.compile(r"\bnative_decide\b|\bdecide\s*\+\s*native\b|\bNat\.decEq\s*\+\s*native")),
    ("ofReduceBool", re.compile(r"\bLean\.ofReduceBool\b|\bLean\.trustCompiler\b")),
    ("implemented_by", re.compile(r"@\[\s*(?:implemented_by|extern)\b")),
    ("partial", re.compile(r"\bpartial\s+def\b")),
    ("opaque", re.compile(r"(^|\n)\s*opaque\b")),
    ("set_option_dangerous", re.compile(r"set_option\s+(?:debug\.skipKernelTC|maxRecDepth\s+0|pp\.all)\b")),
]


def strip_comments_and_strings(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text.startswith("--", i):
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue
        if text.startswith("/-", i):
            end = text.find("-/", i + 2)
            i = n if end == -1 else end + 2
            out.append(" ")
            continue
        if text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            out.append('""')
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def scan_source(text: str) -> list[str]:
    """Names of forbidden constructs present in ``text``."""
    cleaned = strip_comments_and_strings(text)
    return [name for name, pat in FORBIDDEN_PATTERNS if pat.search(cleaned)]


@dataclass
class VerificationReport:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    axioms: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    compile: CompileResult | None = None
    diagnostics: list[LeanDiagnostic] = field(default_factory=list)
    source: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reasons": self.reasons,
            "axioms": self.axioms,
            "forbidden": self.forbidden,
            "exit_code": self.compile.exit_code if self.compile else None,
            "duration_ms": round(self.duration_ms, 1),
        }


class VerificationFirewall:
    def __init__(self, compiler: LeanCompiler, allowed_axioms: set[str] | None = None,
                 max_heartbeats: int | None = None):
        self.compiler = compiler
        self.allowed_axioms = set(allowed_axioms) if allowed_axioms is not None else set(compiler.settings.allowed_axioms)
        self.max_heartbeats = max_heartbeats if max_heartbeats is not None else compiler.settings.max_heartbeats

    # ----------------------------------------------------------- statement

    @staticmethod
    def statement_matches(theorem: Theorem, main_declaration: str) -> tuple[bool, str]:
        try:
            signature, _ = split_declaration(main_declaration)
        except ValueError as exc:
            return False, str(exc)
        if normalize_signature(signature) != theorem.normalized_signature:
            return False, "target statement differs from the original (statement must be kept verbatim)"
        return True, ""

    # ---------------------------------------------------------------- main

    def verify(self, theorem: Theorem, main_declaration: str, preamble: str = "") -> VerificationReport:
        t0 = time.perf_counter()
        report = VerificationReport(ok=False)

        forbidden = scan_source(preamble) + scan_source(main_declaration) + scan_source(theorem.context)
        report.forbidden = sorted(set(forbidden))
        if report.forbidden:
            report.reasons.append("forbidden constructs: " + ", ".join(report.forbidden))

        matches, why = self.statement_matches(theorem, main_declaration)
        if not matches:
            report.reasons.append(why)

        if report.reasons:
            report.duration_ms = (time.perf_counter() - t0) * 1000
            return report

        source = assemble_file(theorem, main_declaration, preamble, max_heartbeats=self.max_heartbeats, audit=True)
        report.source = source
        result = self.compiler.compile_source(source, name_hint=f"verify_{theorem.name}")
        report.compile = result
        report.diagnostics = parse_diagnostics(result.output)

        if result.timed_out:
            report.reasons.append("verification compile timed out")
        if result.exit_code != 0 and not result.timed_out:
            report.reasons.append(f"lean exited with code {result.exit_code}")
        errs = errors(report.diagnostics)
        if errs:
            report.reasons.append(f"{len(errs)} compiler error(s): " + "; ".join(e.headline for e in errs[:3]))
        if uses_sorry(result.output):
            report.reasons.append("declaration uses sorry")

        axioms = axioms_from_output(result.output)
        target = audit_name(theorem)
        if target not in axioms and not report.reasons:
            # `#print axioms` names are printed as written inside the current namespace.
            candidates = [k for k in axioms if k.endswith("." + target) or k == target]
            if candidates:
                target = candidates[0]
            else:
                report.reasons.append("could not read `#print axioms` output for the target")
        report.axioms = axioms.get(target, [])
        bad = sorted(a for a in report.axioms if a not in self.allowed_axioms)
        if bad:
            report.reasons.append("disallowed axioms: " + ", ".join(bad))

        report.ok = not report.reasons
        report.duration_ms = (time.perf_counter() - t0) * 1000
        return report

    # ------------------------------------------------- whole-file checking

    def check_file(self, source: str, name_hint: str = "file") -> VerificationReport:
        """Firewall for a complete, human-written Lean file (CLI ``check``).

        Appends ``#print axioms`` for every named theorem/lemma and applies the
        same rules as ``verify``.
        """
        t0 = time.perf_counter()
        report = VerificationReport(ok=False, forbidden=sorted(set(scan_source(source))))
        if report.forbidden:
            report.reasons.append("forbidden constructs: " + ", ".join(report.forbidden))
            report.duration_ms = (time.perf_counter() - t0) * 1000
            return report

        names = qualified_theorem_names(source)
        imports, body = split_imports(source)
        audited = "\n\n".join(
            p for p in (imports, "\n".join(SAFETY_OPTIONS), body.rstrip(),
                        "\n".join(f"#print axioms {n}" for n in names)) if p.strip()
        ) + "\n"
        report.source = audited
        result = self.compiler.compile_source(audited, name_hint=name_hint)
        report.compile = result
        report.diagnostics = parse_diagnostics(result.output)
        if result.timed_out:
            report.reasons.append("compile timed out")
        elif result.exit_code != 0:
            report.reasons.append(f"lean exited with code {result.exit_code}")
        errs = errors(report.diagnostics)
        if errs:
            report.reasons.append(f"{len(errs)} compiler error(s): " + "; ".join(e.headline for e in errs[:3]))
        if uses_sorry(result.output):
            report.reasons.append("declaration uses sorry")
        all_axioms = axioms_from_output(result.output)
        used = sorted({a for axs in all_axioms.values() for a in axs})
        report.axioms = used
        bad = [a for a in used if a not in self.allowed_axioms]
        if bad:
            report.reasons.append("disallowed axioms: " + ", ".join(bad))
        report.ok = not report.reasons
        report.duration_ms = (time.perf_counter() - t0) * 1000
        return report
