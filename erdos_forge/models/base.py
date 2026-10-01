"""Provider-agnostic chat interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class Completion:
    texts: list[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    latency_ms: float = 0.0
    raw: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.texts[0] if self.texts else ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ModelError(RuntimeError):
    """The provider could not produce a completion (auth, network, quota...)."""


class ChatModel(ABC):
    """A chat model. ``name`` identifies it in reports; ``complete`` is the only operation."""

    name: str = "model"
    is_llm: bool = True

    @abstractmethod
    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        ...

    def describe(self) -> dict:
        return {"name": self.name, "is_llm": self.is_llm}
