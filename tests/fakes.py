"""Test doubles: a scripted Lean compiler so the whole loop runs without Lean."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from erdos_forge.config import LeanSettings
from erdos_forge.lean.compiler import CompileResult, LeanCompiler
from erdos_forge.lean.environment import LeanEnvironment

Oracle = Callable[[str], tuple[int, str]]


def fake_settings(tmp_path: Path) -> LeanSettings:
    project = tmp_path / "proj"
    project.mkdir(exist_ok=True)
    (project / "lakefile.toml").write_text('name = "fake"\n', encoding="utf-8")
    (project / "lean-toolchain").write_text("leanprover/lean4:v4.33.1\n", encoding="utf-8")
    return LeanSettings(project_dir=project, scratch_dir=tmp_path / "scratch", compile_timeout=5)


class FakeCompiler(LeanCompiler):
    """Decides success by inspecting the assembled source text.

    ``oracle(source) -> (exit_code, output)``. The default oracle accepts a
    proof iff it contains the token ``GOOD``, reports ``unsolved goals`` for a
    proof containing ``PARTIAL``, ``unknown identifier`` for ``Nat.foo``, and
    emits a proper ``#print axioms`` line when asked to.
    """

    def __init__(self, settings: LeanSettings, oracle: Oracle | None = None):
        super().__init__(settings)
        self.oracle = oracle or default_oracle
        self.sources: list[str] = []

    def compile_file(self, path: str | Path, timeout: float | None = None) -> CompileResult:
        source = Path(path).read_text(encoding="utf-8")
        self.sources.append(source)
        self.calls += 1
        code, out = self.oracle(source)
        return CompileResult(code, out, "", 1.0, source_path=str(path), command=["fake"])


def _audit_lines(source: str, axioms: str = "[propext, Quot.sound]") -> str:
    names = re.findall(r"^#print axioms (\S+)", source, re.M)
    return "\n".join(f"'{n}' depends on axioms: {axioms}" for n in names)


def default_oracle(source: str) -> tuple[int, str]:
    f = "C:\\fake\\file.lean"
    if "sorry" in source:
        return 0, f"{f}:3:0: warning: declaration uses 'sorry'\n" + _audit_lines(source, "[propext, sorryAx]")
    if "Nat.foo" in source:
        return 1, f"{f}:4:10: error: unknown identifier 'Nat.foo'\n" + _audit_lines(source)
    if "PARTIAL" in source:
        return 1, f"{f}:4:2: error: unsolved goals\nn : Nat\n⊢ n + 0 = n\n" + _audit_lines(source)
    if "BADAXIOM" in source:
        return 0, _audit_lines(source, "[propext, myAxiom]")
    if "GOOD" in source:
        return 0, _audit_lines(source)
    return 1, f"{f}:4:2: error: type mismatch\n  h\nhas type\n  a ≤ b : Prop\nbut is expected to have type\n  a < b : Prop\n" + _audit_lines(source)


def fake_env(tmp_path: Path, oracle: Oracle | None = None) -> LeanEnvironment:
    settings = fake_settings(tmp_path)
    env = LeanEnvironment.__new__(LeanEnvironment)
    env.settings = settings
    env.compiler = FakeCompiler(settings, oracle)
    from erdos_forge.lean.firewall import VerificationFirewall

    env.firewall = VerificationFirewall(env.compiler)
    return env
