"""Load the YAML files under ``config/`` into plain dataclasses."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def _resolve(path: str | Path) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else (REPO_ROOT / p).resolve()


@dataclass
class LeanSettings:
    project_dir: Path
    lean_command: list[str] = field(default_factory=lambda: ["lake", "env", "lean"])
    compile_timeout: float = 900.0
    max_heartbeats: int = 400_000
    scratch_dir: Path = REPO_ROOT / "workspace" / "scratch"
    allowed_axioms: set[str] = field(default_factory=lambda: {"propext", "Classical.choice", "Quot.sound"})
    cache_lake_env: bool = True

    @classmethod
    def load(cls, path: Path | None = None, project_dir: str | Path | None = None) -> "LeanSettings":
        raw = _load_yaml(path or CONFIG_DIR / "lean.yaml")
        chosen = project_dir or os.environ.get("ERDOS_FORGE_LEAN_PROJECT") or raw.get("project_dir", "workspace/lean_project")
        return cls(
            project_dir=_resolve(chosen),
            lean_command=list(raw.get("lean_command", ["lake", "env", "lean"])),
            compile_timeout=float(raw.get("compile_timeout", 900)),
            max_heartbeats=int(raw.get("max_heartbeats", 400_000)),
            scratch_dir=_resolve(raw.get("scratch_dir", "workspace/scratch")),
            allowed_axioms=set(raw.get("allowed_axioms", ["propext", "Classical.choice", "Quot.sound"])),
            cache_lake_env=bool(raw.get("cache_lake_env", True)),
        )


@dataclass
class RepairSettings:
    max_repairs: int = 3
    samples_per_call: int = 1
    feedback_max_chars: int = 3000


@dataclass
class RetrievalSettings:
    enabled: bool = True
    retrieve_k: int = 50
    top_k: int = 10
    extra_index_dir: Path = REPO_ROOT / "data" / "mathlib_index"
    mathlib_cache: Path = REPO_ROOT / "data" / "mathlib_index" / "mathlib_cache.jsonl"


@dataclass
class BudgetSettings:
    max_compiler_calls: int = 12
    max_wall_seconds: float = 3600.0
    max_tokens: int = 200_000


@dataclass
class SearchSettings:
    strategy: str = "repair"
    repair: RepairSettings = field(default_factory=RepairSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    budget: BudgetSettings = field(default_factory=BudgetSettings)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "SearchSettings":
        raw = _load_yaml(path or CONFIG_DIR / "search.yaml")
        rep = raw.get("repair", {})
        bud = raw.get("budget", {})
        ret = raw.get("retrieval", {})
        return cls(
            strategy=raw.get("strategy", "repair"),
            repair=RepairSettings(
                max_repairs=int(rep.get("max_repairs", 3)),
                samples_per_call=int(rep.get("samples_per_call", 1)),
                feedback_max_chars=int(rep.get("feedback_max_chars", 3000)),
            ),
            retrieval=RetrievalSettings(
                enabled=bool(ret.get("enabled", True)),
                retrieve_k=int(ret.get("retrieve_k", 50)),
                top_k=int(ret.get("top_k", 10)),
                extra_index_dir=_resolve(ret.get("extra_index_dir", "data/mathlib_index")),
                mathlib_cache=_resolve(ret.get("mathlib_cache", "data/mathlib_index/mathlib_cache.jsonl")),
            ),
            budget=BudgetSettings(
                max_compiler_calls=int(bud.get("max_compiler_calls", 12)),
                max_wall_seconds=float(bud.get("max_wall_seconds", 3600)),
                max_tokens=int(bud.get("max_tokens", 200_000)),
            ),
            raw=raw,
        )


@dataclass
class ModelSettings:
    default: str = "heuristic"
    defaults: dict[str, Any] = field(default_factory=dict)
    aliases: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "ModelSettings":
        raw = _load_yaml(path or CONFIG_DIR / "models.yaml")
        return cls(
            default=raw.get("default", "heuristic"),
            defaults=dict(raw.get("defaults", {})),
            aliases={k: dict(v) for k, v in (raw.get("aliases") or {}).items()},
        )


@dataclass
class BenchmarkSettings:
    default_split: str = "level0_core"
    reports_dir: Path = REPO_ROOT / "reports" / "runs"
    max_infra_failures: int = 3

    @classmethod
    def load(cls, path: Path | None = None) -> "BenchmarkSettings":
        raw = _load_yaml(path or CONFIG_DIR / "benchmark.yaml")
        return cls(
            default_split=raw.get("default_split", "level0_core"),
            reports_dir=_resolve(raw.get("reports_dir", "reports/runs")),
            max_infra_failures=int(raw.get("max_infra_failures", 3)),
        )
