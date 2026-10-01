"""LLM abstraction. Every prover talks to a ``ChatModel``; see ``router.build_model``."""

from erdos_forge.models.base import ChatModel, Completion, Message  # noqa: F401
from erdos_forge.models.router import build_model  # noqa: F401
