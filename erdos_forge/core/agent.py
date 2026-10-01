"""Top-level facade: analyze → retrieve → prove, with the Lean kernel as authority."""

from __future__ import annotations

from erdos_forge.config import SearchSettings
from erdos_forge.core.controller import RepairController
from erdos_forge.core.events import EventBus
from erdos_forge.core.state import Problem, ProofResult
from erdos_forge.formalizer.math_analyzer import MathematicalAnalyzer, ProblemAnalysis
from erdos_forge.lean.environment import LeanEnvironment
from erdos_forge.models.base import ChatModel


class ErdosForgeAgent:
    def __init__(
        self,
        env: LeanEnvironment,
        model: ChatModel,
        settings: SearchSettings | None = None,
        events: EventBus | None = None,
    ):
        self.env = env
        self.model = model
        self.settings = settings or SearchSettings.load()
        self.events = events or EventBus()
        self.analyzer = MathematicalAnalyzer()
        self.controller = RepairController(env, model, self.settings, self.events)

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        return self.analyzer.analyze(problem)

    def prove(self, problem: Problem) -> ProofResult:
        return self.controller.prove(problem)
