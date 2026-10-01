"""High-level facade over the Lean toolchain used by the agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from erdos_forge.config import LeanSettings
from erdos_forge.lean.compiler import CompileResult, LeanCompiler
from erdos_forge.lean.diagnostics import LeanDiagnostic, errors, parse_diagnostics, uses_sorry
from erdos_forge.lean.firewall import VerificationFirewall
from erdos_forge.lean.source import Theorem, assemble_file, split_imports


@dataclass
class SnippetResult:
    compile: CompileResult
    diagnostics: list[LeanDiagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.compile.ok and not errors(self.diagnostics)

    @property
    def errors(self) -> list[LeanDiagnostic]:
        return errors(self.diagnostics)


class LeanEnvironment:
    """Compiler + firewall + a few inspection helpers.

    ``check_statement`` is the only entry point that tolerates ``sorry``: it
    exists to validate that a *statement* elaborates (used for open
    conjectures) and its result is never reported as a proof.
    """

    def __init__(self, settings: LeanSettings | None = None):
        self.settings = settings or LeanSettings.load()
        self.compiler = LeanCompiler(self.settings)
        self.firewall = VerificationFirewall(self.compiler)

    # -------------------------------------------------------------- basics

    @property
    def compiler_calls(self) -> int:
        return self.compiler.calls

    def compile_source(self, source: str, name_hint: str = "snippet") -> SnippetResult:
        result = self.compiler.compile_source(source, name_hint=name_hint)
        return SnippetResult(result, parse_diagnostics(result.output))

    def compile_candidate(self, theorem: Theorem, main_declaration: str, preamble: str = "") -> SnippetResult:
        """Compile a candidate without the axiom audit (search-time check)."""
        source = assemble_file(theorem, main_declaration, preamble, self.settings.max_heartbeats, audit=False)
        return self.compile_source(source, name_hint=f"cand_{theorem.name}")

    def check_statement(self, theorem: Theorem) -> SnippetResult:
        """Does the statement elaborate? Uses `sorry` deliberately; never a proof."""
        source = assemble_file(theorem, theorem.with_sorry(), max_heartbeats=self.settings.max_heartbeats, audit=False)
        res = self.compile_source(source, name_hint=f"stmt_{theorem.name}")
        # The only acceptable warning is the sorry we introduced ourselves.
        return res

    def validate_import(self, module: str) -> SnippetResult:
        return self.compile_source(f"import {module}\n", name_hint="import_check")

    def inspect_constant(self, name: str, imports: str = "import Mathlib") -> SnippetResult:
        """Return `#check` output for a declaration (its type) if it exists."""
        imports, _ = split_imports(imports)
        return self.compile_source(f"{imports}\n\n#check @{name}\n", name_hint="inspect")

    def get_goals(self, source: str) -> list[str]:
        """Remaining goals after compiling ``source`` (empty if the file closed)."""
        res = self.compile_source(source, name_hint="goals")
        goals: list[str] = []
        for diag in res.diagnostics:
            goals.extend(diag.goals)
        return goals

    def search_declarations(self, query: str, k: int = 10, *, allow_mathlib: bool = True):
        """Premise retrieval over the declaration index (seed + optional Mathlib)."""
        from erdos_forge.retrieval.premise_selection import RetrievalQuery, default_selector

        return default_selector().select(
            RetrievalQuery(text=query, goal=query, allow_mathlib=allow_mathlib), k=k
        )

    def doctor(self) -> dict[str, object]:
        """Collect environment facts for the CLI `doctor` command."""
        info: dict[str, object] = {
            "project_dir": str(self.settings.project_dir),
            "lean_command": self.settings.lean_command,
            "toolchain": self.compiler.toolchain(),
            "project_problems": self.compiler.check_project(),
            "mathlib_built": (self.settings.project_dir / ".lake" / "packages" / "mathlib" / ".lake" / "build").is_dir(),
        }
        if not info["project_problems"]:
            res = self.compile_source("example : (1 : Nat) + 1 = 2 := rfl\n", name_hint="doctor")
            info["core_compile_ok"] = res.ok
            info["core_compile_ms"] = round(res.compile.duration_ms)
            info["compile_mode"] = "direct lean (cached lake env)" if self.compiler.lake_environment() else "lake env lean"
            info["lean_binary"] = res.compile.command[0] if res.compile.command else None
            if not res.ok:
                info["core_compile_output"] = res.compile.output[:1000]
        return info


def statement_ok(result: SnippetResult) -> bool:
    """A statement check passes if the only issue is our own `sorry`."""
    return result.compile.ok and not result.errors and uses_sorry(result.compile.output)
