"""Ablation presets: same problems, timeout and compiler budget; one knob changes.

This is what turns a GitHub project into a research artefact. The numbers in
the README table are measured here, not claimed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erdos_forge.config import BenchmarkSettings, SearchSettings
from erdos_forge.evaluation.benchmark import Split, run_benchmark
from erdos_forge.lean.environment import LeanEnvironment
from erdos_forge.models.base import ChatModel


@dataclass(frozen=True)
class Ablation:
    name: str
    description: str
    max_repairs: int
    retrieval: bool
    samples_per_call: int = 1


PRESETS: dict[str, Ablation] = {
    "llm_only": Ablation("llm_only", "single generation, no repair, no retrieval", 0, False),
    "llm_repair": Ablation("llm_repair", "compiler-feedback repair, no retrieval", 3, False),
    "llm_retrieval": Ablation("llm_retrieval", "retrieval on the first prompt, no repair", 0, True),
    "llm_retrieval_repair": Ablation("llm_retrieval_repair", "retrieval + bounded repair", 3, True),
}


def apply_ablation(base: SearchSettings, ablation: Ablation) -> SearchSettings:
    settings = deepcopy(base)
    settings.repair.max_repairs = ablation.max_repairs
    settings.repair.samples_per_call = ablation.samples_per_call
    settings.retrieval.enabled = ablation.retrieval
    settings.strategy = ablation.name
    return settings


def run_ablations(
    env: LeanEnvironment,
    model: ChatModel,
    split: Split,
    names: list[str],
    search: SearchSettings | None = None,
    bench: BenchmarkSettings | None = None,
    run_prefix: str | None = None,
    limit: int | None = None,
    only: set[str] | None = None,
    on_result=None,
) -> list[tuple[Ablation, dict[str, Any], Path]]:
    search = search or SearchSettings.load()
    bench = bench or BenchmarkSettings.load()
    unknown = [n for n in names if n not in PRESETS]
    if unknown:
        raise ValueError(f"unknown ablation presets: {unknown}; choose from {sorted(PRESETS)}")
    rows: list[tuple[Ablation, dict[str, Any], Path]] = []
    for name in names:
        ablation = PRESETS[name]
        run_id = "-".join(p for p in (run_prefix, ablation.name) if p)
        run, _results, out_dir = run_benchmark(
            env, model, split, apply_ablation(search, ablation), bench,
            run_id=run_id or None, only=only, limit=limit, on_result=on_result,
        )
        run["ablation"] = ablation.name
        run["ablation_description"] = ablation.description
        rows.append((ablation, run, out_dir))
    return rows


def render_comparison(rows: list[tuple[Ablation, dict[str, Any], Path]]) -> str:
    lines = [
        "# Ablation comparison",
        "",
        "| System | Verified | Solve rate | Compiles/problem | LLM/problem | Tokens/problem |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for ablation, run, _ in rows:
        m = run["metrics"]
        lines.append(
            f"| {ablation.name} | {m['verified']}/{m['problems']} | {m['verified_solve_rate']} | "
            f"{m['compiler_calls_per_problem']} | {m['llm_calls_per_problem']} | {m['tokens_per_problem']} |"
        )
    lines.append("")
    return "\n".join(lines)
