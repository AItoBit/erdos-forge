"""Compile single Lean files with ``lake env lean`` inside a built Lake project."""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from erdos_forge.config import LeanSettings


class LeanNotAvailable(RuntimeError):
    """The Lean toolchain or the Lake project cannot be used."""


@dataclass
class CompileResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    source_path: str | None = None
    command: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        return (self.stdout + ("\n" + self.stderr if self.stderr else "")).strip()


class LeanCompiler:
    """Thin, stateless wrapper around ``lake env lean <file>``.

    Every call is a fresh process: there is no shared environment between
    compiles, which is exactly what the verification firewall needs. The
    price is that imports are re-loaded on every call.
    """

    def __init__(self, settings: LeanSettings):
        self.settings = settings
        self.calls = 0
        self.total_ms = 0.0
        self._lake_env: dict[str, str] | None = None
        self._lake_env_failed = False

    # ---------------------------------------------------- lake environment

    def lake_environment(self) -> dict[str, str] | None:
        """Resolve Lake's environment (LEAN, LEAN_PATH, ...) once and cache it.

        ``lake env <cmd>`` re-loads the workspace on every call, which costs
        20+ seconds on some machines, while ``lean`` itself needs ~1 s for a
        core file. Running the toolchain's ``lean`` directly with the cached
        environment keeps every compile a fresh process without that overhead.
        Returns ``None`` (and falls back to ``lake env lean``) if it fails.
        """
        if self._lake_env is not None or self._lake_env_failed or not self.settings.cache_lake_env:
            return self._lake_env
        lake = self.settings.lean_command[0] if self.settings.lean_command else "lake"
        try:
            proc = subprocess.run(
                [lake, "env"], cwd=str(self.project_dir), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.settings.compile_timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._lake_env_failed = True
            return None
        if proc.returncode != 0:
            self._lake_env_failed = True
            return None
        env = dict(os.environ)
        found_lean = False
        for line in proc.stdout.splitlines():
            key, sep, value = line.partition("=")
            if sep and key and key.isupper():
                env[key] = value
                found_lean = found_lean or key == "LEAN"
        if not found_lean or not Path(env["LEAN"]).exists():
            self._lake_env_failed = True
            return None
        self._lake_env = env
        return env

    def _command_and_env(self, path: Path) -> tuple[list[str], dict[str, str] | None]:
        env = self.lake_environment()
        if env is not None:
            return [env["LEAN"], str(path)], env
        return [*self.settings.lean_command, str(path)], None

    # ----------------------------------------------------------- utilities

    @property
    def project_dir(self) -> Path:
        return self.settings.project_dir

    def check_project(self) -> list[str]:
        """Return a list of problems with the configured project (empty if fine)."""
        problems: list[str] = []
        pd = self.project_dir
        if not pd.is_dir():
            problems.append(f"project_dir does not exist: {pd}")
            return problems
        if not (pd / "lakefile.toml").exists() and not (pd / "lakefile.lean").exists():
            problems.append(f"no lakefile.toml / lakefile.lean in {pd}")
        if not (pd / "lean-toolchain").exists():
            problems.append(f"no lean-toolchain in {pd}")
        return problems

    def toolchain(self) -> str | None:
        p = self.project_dir / "lean-toolchain"
        return p.read_text(encoding="utf-8").strip() if p.exists() else None

    def _scratch_path(self, source: str, name_hint: str) -> Path:
        self.settings.scratch_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
        safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name_hint)[:40] or "snippet"
        return self.settings.scratch_dir / f"{safe}_{digest}_{os.getpid()}.lean"

    # ------------------------------------------------------------ compiling

    def compile_file(self, path: str | Path, timeout: float | None = None) -> CompileResult:
        path = Path(path).resolve()
        cmd, env = self._command_and_env(path)
        t0 = time.perf_counter()
        self.calls += 1
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.settings.compile_timeout,
            )
        except FileNotFoundError as exc:
            raise LeanNotAvailable(f"cannot run {cmd[0]!r}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            ms = (time.perf_counter() - t0) * 1000
            self.total_ms += ms
            out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return CompileResult(-1, out, err, ms, timed_out=True, source_path=str(path), command=cmd)
        ms = (time.perf_counter() - t0) * 1000
        self.total_ms += ms
        return CompileResult(proc.returncode, proc.stdout, proc.stderr, ms, source_path=str(path), command=cmd)

    def compile_source(self, source: str, name_hint: str = "snippet", keep: bool = False,
                       timeout: float | None = None) -> CompileResult:
        """Write ``source`` to a scratch file and compile it."""
        path = self._scratch_path(source, name_hint)
        path.write_text(source, encoding="utf-8")
        try:
            return self.compile_file(path, timeout=timeout)
        finally:
            if not keep:
                try:
                    path.unlink()
                except OSError:
                    pass
