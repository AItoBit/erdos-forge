"""OpenAI-compatible chat completions (OpenAI, vLLM, llama.cpp, Ollama, OpenRouter...)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from erdos_forge.models.base import ChatModel, Completion, Message, ModelError


class OpenAIChatModel(ChatModel):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: float = 180.0,
        seed: int | None = None,
        retries: int = 3,
        extra: dict | None = None,
    ):
        self.model = model
        self.name = f"openai:{model}"
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.seed = seed
        self.retries = retries
        self.extra = extra or {}

    def complete(self, messages: list[Message], n: int = 1, temperature: float | None = None,
                 max_tokens: int | None = None) -> Completion:
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise ModelError("OPENAI_API_KEY is not set")
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "n": n,
            **self.extra,
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        t0 = time.perf_counter()
        data: dict = {}
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:500]
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise ModelError(f"HTTP {exc.code} from {self.base_url}: {body}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.retries - 1:
                    raise ModelError(f"request to {self.base_url} failed: {exc}") from exc
                time.sleep(2**attempt)
        usage = data.get("usage", {}) or {}
        return Completion(
            texts=[(c.get("message") or {}).get("content") or "" for c in data.get("choices", [])],
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            model=data.get("model", self.model),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
