"""Anthropic Messages API client (no SDK dependency)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from erdos_forge.models.base import ChatModel, Completion, Message, ModelError


class AnthropicChatModel(ChatModel):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: float = 180.0,
        retries: int = 3,
        extra: dict | None = None,
    ):
        self.model = model
        self.name = f"anthropic:{model}"
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = (base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self.extra = extra or {}

    def _call(self, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:500]
                if exc.code in (429, 500, 502, 503, 504, 529) and attempt < self.retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise ModelError(f"HTTP {exc.code} from Anthropic: {body}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.retries - 1:
                    raise ModelError(f"request to Anthropic failed: {exc}") from exc
                time.sleep(2**attempt)
        raise ModelError("unreachable")

    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        if not self.api_key:
            raise ModelError("ANTHROPIC_API_KEY is not set")
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        convo = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            "messages": convo,
            **self.extra,
        }
        if system:
            payload["system"] = system
        t0 = time.perf_counter()
        texts: list[str] = []
        prompt_tokens = completion_tokens = 0
        # The Messages API returns one sample per request.
        for _ in range(max(1, n)):
            data = self._call(payload)
            texts.append("".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"))
            usage = data.get("usage", {}) or {}
            prompt_tokens += int(usage.get("input_tokens", 0) or 0)
            completion_tokens += int(usage.get("output_tokens", 0) or 0)
        return Completion(texts, prompt_tokens, completion_tokens, self.model, (time.perf_counter() - t0) * 1000)
