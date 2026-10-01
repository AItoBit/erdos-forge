"""Render benchmark results as JSON + Markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from erdos_forge.core.state import ProofResult


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def render_markdown(run: dict[str, Any], results: list[ProofResult]) -> str:
    m = run["metrics"]
    lines = [
        f"# Benchmark run `{run['run_id']}`",
        "",
        f"- split: `{run['split']}`  ",
        f"- model: `{run['model']}`  ",
        f"- strategy: `{run['strategy']}` (max_repairs={run['max_repairs']})  ",
        f"- lean project: `{run['lean_project']}` ({run.get('toolchain')})  ",
        f"- started: {run['started_at']}  ",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| **Kernel-verified solve rate** | **{_pct(m['verified_solve_rate'])}** ({m['verified']}/{m['problems']}) |",
        f"| First-attempt solve rate | {_pct(m['first_attempt_solve_rate'])} |",
        f"| Repair success rate | {_pct(m['repair_success_rate'])} |",
        f"| Compiler calls / problem | {m['compiler_calls_per_problem']} |",
        f"| LLM calls / problem | {m['llm_calls_per_problem']} |",
        f"| Tokens / problem | {m['tokens_per_problem']} |",
        f"| Retrieved lemmas / problem | {m.get('retrieved_lemmas_per_problem')} |",
        f"| Wall-clock / problem | {m['wall_seconds_per_problem']} s |",
        "",
        "## Outcomes",
        "",
        "| Outcome | Count |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in sorted(m["outcomes"].items())],
        "",
        "## Error categories (all attempts)",
        "",
        "| Category | Count |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in m["error_categories"].items()],
        "",
        "## Per problem",
        "",
        "| Problem | Outcome | LLM calls | Compiles | Wall (s) | Last error / note |",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in results:
        note = (r.failure_reason or ("axioms: " + ", ".join(r.axioms) if r.success else ""))[:80].replace("|", "\\|")
        lines.append(f"| `{r.problem_id}` | {r.outcome} | {len(r.attempts)} | {r.compiler_calls} | {r.wall_ms/1000:.1f} | {note} |")
    lines.append("")
    return "\n".join(lines)


def write_report(out_dir: Path, run: dict[str, Any], results: list[ProofResult]) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {**run, "results": [r.to_dict() for r in results]}
    paths = {
        "summary": out_dir / "summary.json",
        "report": out_dir / "report.md",
        "proofs": out_dir / "proofs.lean.txt",
    }
    paths["summary"].write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["report"].write_text(render_markdown(run, results), encoding="utf-8")
    proofs = [
        f"-- {r.problem_id}\n{(r.preamble + chr(10) + chr(10)) if r.preamble else ''}{r.proof}\n"
        for r in results
        if r.success and r.proof
    ]
    paths["proofs"].write_text("\n".join(proofs), encoding="utf-8")
    return paths
