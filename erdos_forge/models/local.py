"""Local OpenAI-compatible servers (vLLM, llama.cpp, Ollama, ...)."""

from __future__ import annotations

import os

from erdos_forge.models.openai import OpenAIChatModel


class LocalChatModel(OpenAIChatModel):
    """Same protocol as ``OpenAIChatModel``, defaulting to ``http://127.0.0.1:8000/v1``."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs,
    ):
        super().__init__(
            model=model,
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or "http://127.0.0.1:8000/v1",
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or "local",
            **kwargs,
        )
        self.name = f"local:{model}"
