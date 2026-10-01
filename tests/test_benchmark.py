from erdos_forge.config import BenchmarkSettings, RepairSettings, SearchSettings
from erdos_forge.core.state import Problem, TargetKind
from erdos_forge.evaluation.benchmark import load_problems, load_splits, run_benchmark
from erdos_forge.models.mock import MockModel
from erdos_forge.models.router import resolve_spec
from tests.fakes import fake_env


def test_splits_and_problem_counts():
    splits = load_splits()
    assert {"level0_core", "level1_mathlib", "erdos_auxiliary"} <= set(splits)
    level0 = load_problems(splits["level0_core"])
    assert len(level0) >= 20, "V0.1 milestone needs at least 20 core problems"
    assert all(p.theorem.imports == "" for p in level0)
    level1 = load_problems(splits["level1_mathlib"])
    assert all("import Mathlib.Tactic" in p.theorem.imports for p in level1)
    erdos = load_problems(splits["erdos_auxiliary"])
    assert erdos and all(p.kind == TargetKind.AUXILIARY for p in erdos)


def test_problem_from_json():
    from erdos_forge.config import REPO_ROOT

    p = Problem.from_json(REPO_ROOT / "data" / "problems" / "erdos_169_apfree_mono.json")
    assert p.theorem.name == "apFree_mono" and p.kind == TargetKind.AUXILIARY
    c = Problem.from_json(REPO_ROOT / "data" / "problems" / "erdos_169_conjecture.json")
    assert c.is_open_conjecture


def test_run_benchmark_writes_reports(tmp_path):
    env = fake_env(tmp_path)
    splits = load_splits()
    model = MockModel(lambda msgs: _answer(msgs))
    search = SearchSettings()
    search.repair = RepairSettings(max_repairs=1)
    bench = BenchmarkSettings(reports_dir=tmp_path / "runs")
    run, results, out_dir = run_benchmark(env, model, splits["level0_core"], search, bench, run_id="t", limit=5)
    assert run["metrics"]["problems"] == 5
    assert (out_dir / "summary.json").exists() and (out_dir / "report.md").exists()
    assert (out_dir / "trajectories.jsonl").read_text(encoding="utf-8").count("\n") >= 5
    assert run["metrics"]["verified"] == 5


def _answer(msgs):
    # Echo the target statement back with a proof the fake compiler accepts.
    import re

    user = msgs[1].content
    target = re.findall(r"```lean\n(.*?)```", user, re.S)[-1].strip()
    stmt = target[: target.rfind(":= by")].rstrip()
    return f"```lean\n{stmt} := by\n  GOOD\n```"


def test_model_specs():
    assert resolve_spec("heuristic")["provider"] == "heuristic"
    assert resolve_spec("openai:gpt-4.1") == {**resolve_spec("openai:gpt-4.1")}
    assert resolve_spec("claude")["provider"] == "anthropic"
    assert resolve_spec("local")["provider"] == "local"
    assert resolve_spec("ensemble:heuristic,heuristic")["provider"] == "ensemble"


def test_ablation_presets_toggle_retrieval_and_repairs():
    from erdos_forge.evaluation.ablations import PRESETS, apply_ablation

    base = SearchSettings()
    only = apply_ablation(base, PRESETS["llm_only"])
    assert only.repair.max_repairs == 0 and only.retrieval.enabled is False
    full = apply_ablation(base, PRESETS["llm_retrieval_repair"])
    assert full.repair.max_repairs == 3 and full.retrieval.enabled is True
