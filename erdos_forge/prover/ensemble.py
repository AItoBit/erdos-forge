"""Query several models and let Lean filter the union of their candidates."""

from __future__ import annotations

from erdos_forge.models.base import ChatModel, Completion, Message


class EnsembleModel(ChatModel):
    """``provers = [GPT, Claude, Local]`` — diversity vs. same-compute-on-one-model."""

    def __init__(self, models: list[ChatModel], name: str | None = None):
        if not models:
            raise ValueError("ensemble needs at least one model")
        self.models = models
        self.name = name or ("ensemble:" + "+".join(m.name for m in models))
        self.is_llm = any(m.is_llm for m in models)

    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        texts: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        seen: set[str] = set()
        for model in self.models:
            result = model.complete(messages, n=n, temperature=temperature, max_tokens=max_tokens)
            prompt_tokens += result.prompt_tokens
            completion_tokens += result.completion_tokens
            for text in result.texts:
                key = text.strip()
                if key and key not in seen:
                    seen.add(key)
                    texts.append(text)
        return Completion(texts or [""], prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, model=self.name)
