"""Load benchmark splits and run the controller over them."""

from __future__ import annotations

import datetime as _dt
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from erdos_forge.config import REPO_ROOT, BenchmarkSettings, SearchSettings
from erdos_forge.core.controller import RepairController
from erdos_forge.core.events import EventBus
from erdos_forge.core.state import Problem, ProblemStatus, ProofResult, TargetKind
from erdos_forge.evaluation.metrics import compute_metrics
from erdos_forge.evaluation.report import write_report
from erdos_forge.lean.environment import LeanEnvironment
from erdos_forge.lean.source import load_theorems
from erdos_forge.memory.trajectories import TrajectoryWriter
from erdos_forge.models.base import ChatModel

BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
log = logging.getLogger("erdos_forge.benchmark")


@dataclass
class Split:
    name: str
    level: int
    description: str
    files: list[Path]
    status: ProblemStatus = ProblemStatus.SOLVED
    kind: TargetKind = TargetKind.THEOREM
    tags: list[str] = field(default_factory=list)


def load_splits(path: Path | None = None) -> dict[str, Split]:
    path = path or BENCHMARKS_DIR / "splits.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    splits: dict[str, Split] = {}
    for name, spec in raw.items():
        splits[name] = Split(
            name=name,
            level=int(spec.get("level", 1)),
            description=spec.get("description", ""),
            files=[(path.parent / f).resolve() for f in spec.get("files", [])],
            status=ProblemStatus(spec.get("status", "solved")),
            kind=TargetKind(spec.get("kind", "theorem")),
            tags=list(spec.get("tags", [])),
        )
    return splits


def load_problems(split: Split, only: set[str] | None = None, limit: int | None = None) -> list[Problem]:
    problems: list[Problem] = []
    for file in split.files:
        for thm in load_theorems(file):
            pid = f"{file.stem}:{thm.name}"
            if only and pid not in only and thm.name not in only:
                continue
            problems.append(
                Problem(id=pid, theorem=thm, status=split.status, kind=split.kind, level=split.level,
                        tags=list(split.tags), source=str(file))
            )
    return problems[:limit] if limit else problems


def run_benchmark(
    env: LeanEnvironment,
    model: ChatModel,
    split: Split,
    search: SearchSettings | None = None,
    bench: BenchmarkSettings | None = None,
    run_id: str | None = None,
    only: set[str] | None = None,
    limit: int | None = None,
    events: EventBus | None = None,
    on_result: Callable[[Problem, ProofResult], None] | None = None,
) -> tuple[dict[str, Any], list[ProofResult], Path]:
    search = search or SearchSettings.load()
    bench = bench or BenchmarkSettings.load()
    started = _dt.datetime.now()
    run_id = run_id or f"{started:%Y%m%d-%H%M%S}-{split.name}-{model.name.replace(':', '_').replace('/', '_')}"
    out_dir = bench.reports_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectories = TrajectoryWriter(out_dir / "trajectories.jsonl")
    controller = RepairController(env, model, search, events)

    problems = load_problems(split, only, limit)
    results: list[ProofResult] = []
    infra_failures = 0
    for i, problem in enumerate(problems, 1):
        log.info("[%d/%d] %s", i, len(problems), problem.id)
        result = controller.prove(problem)
        results.append(result)
        trajectories.record(problem, result, run_id)
        if on_result:
            on_result(problem, result)
        if result.outcome == "infra_error":
            infra_failures += 1
            if infra_failures >= bench.max_infra_failures:
                log.error("stopping after %d infrastructure failures: %s", infra_failures, result.failure_reason)
                break
        else:
            infra_failures = 0

    run = {
        "run_id": run_id,
        "split": split.name,
        "level": split.level,
        "model": model.name,
        "strategy": search.strategy,
        "max_repairs": search.repair.max_repairs,
        "lean_project": str(env.settings.project_dir),
        "toolchain": env.compiler.toolchain(),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "problems_total": len(problems),
        "metrics": compute_metrics(results),
    }
    write_report(out_dir, run, results)
    return run, results, out_dir
