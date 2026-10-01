"""Command-line interface.

    erdos-forge doctor                         # toolchain / project / API-key check
    erdos-forge prove FILE.lean:NAME [--model gpt]
    erdos-forge prove data/problems/erdos_169.json
    erdos-forge bench --split level0_core --model heuristic
    erdos-forge check FILE.lean                # verification firewall on a full file
    erdos-forge statement FILE.lean:NAME       # does the statement elaborate?
    erdos-forge diagnose FILE.lean             # structured diagnostics for a file
    erdos-forge retrieve "n + 0 = n"           # Mathlib / core premise retrieval
    erdos-forge analyze data/problems/erdos_169_conjecture.json
    erdos-forge index                          # scan a built Mathlib tree into the index
    erdos-forge ablate --split level0_core --model heuristic
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from erdos_forge import __version__
from erdos_forge.config import BenchmarkSettings, LeanSettings, ModelSettings, SearchSettings
from erdos_forge.core.controller import RepairController
from erdos_forge.core.events import EventBus, logging_listener
from erdos_forge.core.state import Problem, ProblemStatus, TargetKind
from erdos_forge.evaluation.ablations import PRESETS, render_comparison, run_ablations
from erdos_forge.evaluation.benchmark import load_splits, run_benchmark
from erdos_forge.formalizer.math_analyzer import MathematicalAnalyzer
from erdos_forge.formalizer.problem_parser import parse_target
from erdos_forge.lean.diagnostics import parse_diagnostics, summarize
from erdos_forge.lean.environment import LeanEnvironment, statement_ok
from erdos_forge.models.router import build_model
from erdos_forge.retrieval.mathlib_index import DeclarationIndex, find_mathlib_root, index_mathlib_tree
from erdos_forge.retrieval.premise_selection import RetrievalQuery, default_selector


def _env(args: argparse.Namespace) -> LeanEnvironment:
    return LeanEnvironment(LeanSettings.load(project_dir=getattr(args, "lean_project", None)))


def _search(args: argparse.Namespace) -> SearchSettings:
    s = SearchSettings.load()
    if getattr(args, "max_repairs", None) is not None:
        s.repair.max_repairs = args.max_repairs
    if getattr(args, "no_retrieval", False):
        s.retrieval.enabled = False
    return s


def _load_problem(spec: str, status: str | None, kind: str | None) -> Problem:
    return parse_target(spec, status=status, kind=kind)


# ----------------------------------------------------------------- commands


def cmd_doctor(args: argparse.Namespace) -> int:
    env = _env(args)
    info = env.doctor()
    info["python"] = sys.version.split()[0]
    info["api_keys"] = {
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL") or None,
    }
    info["models"] = ModelSettings.load().aliases and sorted(ModelSettings.load().aliases)
    info["retrieval_index_size"] = len(DeclarationIndex.load_default())
    print(json.dumps(info, indent=2, default=str))
    ok = not info["project_problems"] and info.get("core_compile_ok", False)
    print("\nOK: Lean project usable" if ok else "\nPROBLEM: fix the items above (see workspace/lean_project/README.md)")
    return 0 if ok else 1


def cmd_prove(args: argparse.Namespace) -> int:
    env = _env(args)
    model = build_model(args.model)
    problem = _load_problem(args.target, args.status, args.kind)
    events = EventBus()
    events.subscribe(logging_listener())
    controller = RepairController(env, model, _search(args), events)
    result = controller.prove(problem)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"\n== {problem.id}: {result.outcome.upper()}  (model={result.model}, llm_calls={len(result.attempts)}, "
              f"compiles={result.compiler_calls}, {result.wall_ms/1000:.1f}s)")
        if result.success:
            if result.preamble:
                print(result.preamble, "\n")
            print(result.proof)
            print(f"\n-- axioms: {', '.join(result.axioms) or 'none'}")
        else:
            print(f"reason: {result.failure_reason}")
            if result.attempts and args.verbose:
                last = result.attempts[-1]
                print("\n-- last response --\n" + last.response[:3000])
                print("\n-- feedback --\n" + last.feedback[:3000])
    if args.save and result.success:
        Path(args.save).write_text(
            (result.preamble + "\n\n" if result.preamble else "") + (result.proof or "") + "\n", encoding="utf-8")
        print(f"saved to {args.save}")
    return 0 if result.success or result.outcome == "statement_ok" else 1


def cmd_bench(args: argparse.Namespace) -> int:
    env = _env(args)
    model = build_model(args.model)
    splits = load_splits()
    bench = BenchmarkSettings.load()
    name = args.split or bench.default_split
    if name not in splits:
        print(f"unknown split {name!r}; available: {', '.join(splits)}", file=sys.stderr)
        return 2
    events = EventBus()
    if args.verbose:
        events.subscribe(logging_listener())

    def show(problem: Problem, result) -> None:  # type: ignore[no-untyped-def]
        mark = "✓" if result.success else ("·" if result.outcome.startswith("statement") else "✗")
        print(f"{mark} {problem.id:<45} {result.outcome:<16} llm={len(result.attempts)} compiles={result.compiler_calls} "
              f"{result.wall_ms/1000:6.1f}s  {(result.failure_reason or '')[:60]}", flush=True)

    run, results, out_dir = run_benchmark(
        env, model, splits[name], _search(args), bench, run_id=args.run_id,
        only=set(args.only) if args.only else None, limit=args.limit, events=events, on_result=show,
    )
    m = run["metrics"]
    print(f"\nverified {m['verified']}/{m['problems']}  solve_rate={m['verified_solve_rate']}  "
          f"compiles/problem={m['compiler_calls_per_problem']}  llm_calls/problem={m['llm_calls_per_problem']}")
    print(f"report: {out_dir / 'report.md'}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    env = _env(args)
    source = Path(args.file).read_text(encoding="utf-8")
    report = env.firewall.check_file(source, name_hint=Path(args.file).stem)
    print(json.dumps(report.to_dict(), indent=2))
    if not report.ok and report.diagnostics:
        print("\n" + summarize(report.diagnostics, max_chars=4000, include_warnings=True))
    print("\nVERIFIED" if report.ok else "\nREJECTED")
    return 0 if report.ok else 1


def cmd_statement(args: argparse.Namespace) -> int:
    env = _env(args)
    problem = _load_problem(args.target, None, None)
    res = env.check_statement(problem.theorem)
    ok = statement_ok(res)
    print(f"{problem.id}: statement {'elaborates' if ok else 'FAILED'} ({res.compile.duration_ms/1000:.1f}s)")
    if not ok:
        print(summarize(res.diagnostics, include_warnings=True))
    return 0 if ok else 1


def cmd_diagnose(args: argparse.Namespace) -> int:
    env = _env(args)
    if args.file.endswith(".lean"):
        res = env.compiler.compile_file(args.file)
        diags = parse_diagnostics(res.output)
        print(f"exit={res.exit_code} ({res.duration_ms/1000:.1f}s)")
    else:
        diags = parse_diagnostics(Path(args.file).read_text(encoding="utf-8"))
    for d in diags:
        print(json.dumps(d.to_dict(), ensure_ascii=False))
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    query = RetrievalQuery(
        text=args.query,
        goal=args.query,
        identifiers=list(args.identifier or []),
        allow_mathlib=not args.core_only,
    )
    hits = default_selector().select(query, k=args.k)
    if not hits:
        print("no declarations matched")
        return 1
    for hit in hits:
        print(f"{hit.score:7.3f}  {hit.declaration.name}")
        print(f"         {hit.declaration.signature}")
        if args.verbose and hit.declaration.docstring:
            print(f"         {hit.declaration.docstring}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    problem = _load_problem(args.target, args.status, args.kind)
    analysis = MathematicalAnalyzer().analyze(problem)
    print(json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False))
    return 0 if analysis.prove_vs_formalize == "prove" or analysis.kind == "conjecture" else 0


def cmd_index(args: argparse.Namespace) -> int:
    env = _env(args)
    root = Path(args.mathlib_root) if args.mathlib_root else find_mathlib_root(env.settings.project_dir)
    if root is None:
        print("Mathlib source not found (pass --mathlib-root or point ERDOS_FORGE_LEAN_PROJECT at a Lake project with Mathlib)", file=sys.stderr)
        return 1
    print(f"indexing {root} ...", flush=True)
    index = index_mathlib_tree(root, limit=args.limit)
    dest = SearchSettings.load().retrieval.mathlib_cache
    index.write_jsonl(dest)
    print(f"wrote {len(index)} declarations to {dest}")
    return 0


def cmd_ablate(args: argparse.Namespace) -> int:
    env = _env(args)
    model = build_model(args.model)
    splits = load_splits()
    bench = BenchmarkSettings.load()
    name = args.split or bench.default_split
    if name not in splits:
        print(f"unknown split {name!r}; available: {', '.join(splits)}", file=sys.stderr)
        return 2
    names = args.presets or list(PRESETS)
    events = EventBus()
    if args.verbose:
        events.subscribe(logging_listener())

    def show(problem: Problem, result) -> None:  # type: ignore[no-untyped-def]
        mark = "✓" if result.success else ("·" if result.outcome.startswith("statement") else "✗")
        print(f"{mark} {problem.id:<45} {result.outcome:<16} llm={len(result.attempts)} compiles={result.compiler_calls}", flush=True)

    rows = run_ablations(
        env, model, splits[name], names, _search(args), bench,
        run_prefix=args.run_id, only=set(args.only) if args.only else None,
        limit=args.limit, on_result=show,
    )
    print()
    print(render_comparison(rows))
    return 0


# --------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="erdos-forge", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"erdos-forge {__version__}")
    p.add_argument("--lean-project", help="Lake project directory (overrides config/lean.yaml and ERDOS_FORGE_LEAN_PROJECT)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("doctor", help="check Lean toolchain, project and API keys")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("prove", help="prove one target with the repair loop")
    sp.add_argument("target", help="FILE.lean:NAME or data/problems/*.json")
    sp.add_argument("--model", help="alias from config/models.yaml or provider:model")
    sp.add_argument("--max-repairs", type=int)
    sp.add_argument("--no-retrieval", action="store_true", help="disable Mathlib/core premise retrieval")
    sp.add_argument("--status", choices=[s.value for s in ProblemStatus])
    sp.add_argument("--kind", choices=[k.value for k in TargetKind])
    sp.add_argument("--save", help="write the verified proof to this file")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_prove)

    sp = sub.add_parser("bench", help="run a benchmark split")
    sp.add_argument("--split")
    sp.add_argument("--model")
    sp.add_argument("--max-repairs", type=int)
    sp.add_argument("--no-retrieval", action="store_true")
    sp.add_argument("--only", nargs="*", help="problem ids or theorem names")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--run-id")
    sp.set_defaults(func=cmd_bench)

    sp = sub.add_parser("check", help="run the verification firewall on a complete Lean file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("statement", help="check that a statement elaborates (open-problem mode)")
    sp.add_argument("target")
    sp.set_defaults(func=cmd_statement)

    sp = sub.add_parser("diagnose", help="structured diagnostics for a .lean file or saved compiler log")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_diagnose)

    sp = sub.add_parser("retrieve", help="search the declaration index (seed + optional Mathlib scan)")
    sp.add_argument("query", help="goal, identifier or free-text query")
    sp.add_argument("-k", type=int, default=10)
    sp.add_argument("--identifier", action="append", help="boost this identifier (repeatable)")
    sp.add_argument("--core-only", action="store_true", help="hide Mathlib-only declarations")
    sp.set_defaults(func=cmd_retrieve)

    sp = sub.add_parser("analyze", help="structured mathematical analysis (prove vs formalize)")
    sp.add_argument("target", help="FILE.lean:NAME or data/problems/*.json")
    sp.add_argument("--status", choices=[s.value for s in ProblemStatus])
    sp.add_argument("--kind", choices=[k.value for k in TargetKind])
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("index", help="scan a Mathlib source tree into data/mathlib_index/")
    sp.add_argument("--mathlib-root", help="path to the Mathlib/ directory")
    sp.add_argument("--limit", type=int, help="index at most this many .lean files (debug)")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("ablate", help="run the same split under several system configurations")
    sp.add_argument("--split")
    sp.add_argument("--model")
    sp.add_argument("--presets", nargs="*", choices=list(PRESETS), help="subset of ablation names")
    sp.add_argument("--only", nargs="*")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--run-id")
    sp.add_argument("--max-repairs", type=int)
    sp.set_defaults(func=cmd_ablate)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
