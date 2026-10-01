import json

from erdos_forge.config import RepairSettings, SearchSettings
from erdos_forge.core.controller import RepairController
from erdos_forge.core.events import EventBus
from erdos_forge.core.state import Problem, ProblemStatus, TargetKind
from erdos_forge.lean.source import Theorem
from erdos_forge.memory.trajectories import TrajectoryWriter, read_trajectories
from erdos_forge.models.base import ChatModel, Completion
from erdos_forge.models.mock import HeuristicModel, MockModel
from erdos_forge.prover.prompts import initial_messages
from tests.fakes import fake_env

THM = Theorem("add_zero_right", "theorem add_zero_right (n : Nat) : n + 0 = n", context="")
PROBLEM = Problem(id="t:add_zero_right", theorem=THM, status=ProblemStatus.SOLVED)


def block(body: str) -> str:
    return f"```lean\ntheorem add_zero_right (n : Nat) : n + 0 = n := by\n  {body}\n```"


def settings(max_repairs: int = 3) -> SearchSettings:
    s = SearchSettings()
    s.repair = RepairSettings(max_repairs=max_repairs)
    return s


def test_first_attempt_verified(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("GOOD")])
    result = RepairController(env, model, settings()).prove(PROBLEM)
    assert result.success and result.outcome == "verified"
    assert len(result.attempts) == 1
    assert result.compiler_calls == 2  # candidate compile + independent firewall compile
    assert result.attempts[0].verified is True
    assert result.axioms == ["propext", "Quot.sound"]


def test_repair_loop_uses_structured_feedback(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("exact Nat.foo n"), block("PARTIAL"), block("GOOD")])
    events = []
    bus = EventBus()
    bus.subscribe(lambda e: events.append(e.kind))
    result = RepairController(env, model, settings(3), bus).prove(PROBLEM)
    assert result.success
    assert [a.kind for a in result.attempts] == ["generate", "repair", "repair"]
    assert result.attempts[0].error_categories == ["unknown_identifier"]
    assert result.attempts[1].error_categories == ["unsolved_goals"]
    # the second prompt contains the structured feedback of the first failure
    second_prompt = model.calls[1][-1].content
    assert "category=unknown_identifier" in second_prompt
    assert "Nat.foo" in second_prompt
    assert "⊢ n + 0 = n" in model.calls[2][-1].content
    assert "firewall.result" in events and "repair.feedback" in events


def test_budget_of_repairs_is_respected(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("PARTIAL")])
    result = RepairController(env, model, settings(2)).prove(PROBLEM)
    assert not result.success and result.outcome == "failed"
    assert len(result.attempts) == 3  # 1 generate + 2 repairs
    assert "unsolved_goals" in result.failure_reason


def test_sorry_is_rejected_without_compiling(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("sorry"), block("GOOD")])
    result = RepairController(env, model, settings(1)).prove(PROBLEM)
    assert result.success
    first = result.attempts[0]
    assert first.forbidden == ["sorry"] and not first.compiled
    assert "forbidden constructs" in model.calls[1][-1].content


def test_statement_change_is_rejected(tmp_path):
    env = fake_env(tmp_path)
    weakened = "```lean\ntheorem add_zero_right (n : Nat) (h : n = 0) : n + 0 = n := by\n  GOOD\n```"
    model = MockModel([weakened])
    result = RepairController(env, model, settings(0)).prove(PROBLEM)
    assert not result.success
    assert result.attempts[0].extraction_error and "statement differs" in result.attempts[0].extraction_error
    assert result.compiler_calls == 0


def test_open_conjecture_is_guarded(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("GOOD")])
    open_problem = Problem(id="erdos:open", theorem=THM, status=ProblemStatus.OPEN, kind=TargetKind.CONJECTURE)
    result = RepairController(env, model, settings()).prove(open_problem)
    assert not result.success
    assert result.outcome == "statement_ok"
    assert model.calls == []  # the model is never consulted
    assert "sorry" in env.compiler.sources[-1]  # statement check uses sorry on purpose
    assert "open conjecture" in result.failure_reason


def test_heuristic_model_cycles_tactics():
    model = HeuristicModel()
    msgs = initial_messages(PROBLEM)
    first = model.complete(msgs).text
    assert first.startswith("```lean\ntheorem add_zero_right (n : Nat) : n + 0 = n := by\n  first |")
    from erdos_forge.models.base import Message

    second = model.complete([*msgs, Message("assistant", first), Message("user", "fix")]).text
    assert second != first and "intros" in second


def test_all_samples_are_compiled_and_first_verified_wins(tmp_path):
    env = fake_env(tmp_path)

    class Multi(ChatModel):
        name = "multi"
        is_llm = False

        def complete(self, messages, n=1, temperature=None, max_tokens=None):
            return Completion([block("exact Nat.foo n"), block("GOOD")])

    s = settings(0)
    s.repair.samples_per_call = 2
    result = RepairController(env, Multi(), s).prove(PROBLEM)
    assert result.success and result.outcome == "verified"
    assert result.attempts[0].candidates_tried == 2
    assert result.compiler_calls == 3  # failed Nat.foo + GOOD compile + firewall


def test_repair_prompt_includes_retrieved_declarations(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("exact Nat.foo n"), block("GOOD")])
    result = RepairController(env, model, settings(1)).prove(PROBLEM)
    assert result.success
    repair_prompt = model.calls[1][-1].content
    assert "Nat.add_zero" in repair_prompt
    assert "Possibly relevant declarations" in repair_prompt


def test_trajectories_round_trip(tmp_path):
    env = fake_env(tmp_path)
    model = MockModel([block("PARTIAL"), block("GOOD")])
    result = RepairController(env, model, settings(1)).prove(PROBLEM)
    writer = TrajectoryWriter(tmp_path / "traj.jsonl")
    assert writer.record(PROBLEM, result, run_id="r1") == 2
    rows = read_trajectories(tmp_path / "traj.jsonl")
    assert [r["kind"] for r in rows] == ["generate", "repair"]
    assert all(r["eventual_success"] for r in rows)
    assert rows[0]["error_categories"] == ["unsolved_goals"]
    json.dumps(result.to_dict())  # serialisable
