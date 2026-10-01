"""Build a ``ChatModel`` from a spec string and ``config/models.yaml``."""

from __future__ import annotations

from typing import Any

from erdos_forge.config import ModelSettings
from erdos_forge.models.base import ChatModel

PROVIDERS = ("openai", "anthropic", "heuristic", "mock", "local", "ensemble")


def resolve_spec(spec: str | None, settings: ModelSettings | None = None) -> dict[str, Any]:
    """Turn an alias or ``provider:model`` string into a flat parameter dict."""
    settings = settings or ModelSettings.load()
    spec = spec or settings.default
    params: dict[str, Any] = dict(settings.defaults)
    if spec in settings.aliases:
        params.update(settings.aliases[spec])
        params.setdefault("alias", spec)
    elif ":" in spec:
        provider, _, model = spec.partition(":")
        params.update({"provider": provider, "model": model})
    elif spec in PROVIDERS:
        params["provider"] = spec
    else:
        raise ValueError(f"unknown model spec {spec!r}; use an alias from config/models.yaml or provider:model")
    if params.get("provider") not in PROVIDERS:
        raise ValueError(f"unknown provider {params.get('provider')!r}; expected one of {PROVIDERS}")
    return params


def build_model(spec: str | None = None, settings: ModelSettings | None = None, **overrides: Any) -> ChatModel:
    params = resolve_spec(spec, settings)
    params.update({k: v for k, v in overrides.items() if v is not None})
    provider = params.pop("provider")
    params.pop("alias", None)
    common = {k: params[k] for k in ("temperature", "max_tokens", "timeout") if k in params}

    if provider == "heuristic":
        from erdos_forge.models.mock import HeuristicModel

        return HeuristicModel()
    if provider == "mock":
        from erdos_forge.models.mock import MockModel

        return MockModel(params.get("responses", [""]))
    if provider == "openai":
        from erdos_forge.models.openai import OpenAIChatModel

        return OpenAIChatModel(
            model=params["model"],
            base_url=params.get("base_url"),
            api_key=params.get("api_key"),
            seed=params.get("seed"),
            extra=params.get("extra"),
            **common,
        )
    if provider == "anthropic":
        from erdos_forge.models.anthropic import AnthropicChatModel

        return AnthropicChatModel(
            model=params["model"],
            api_key=params.get("api_key"),
            base_url=params.get("base_url"),
            extra=params.get("extra"),
            **common,
        )
    if provider == "local":
        from erdos_forge.models.local import LocalChatModel

        return LocalChatModel(
            model=params["model"],
            base_url=params.get("base_url"),
            api_key=params.get("api_key"),
            extra=params.get("extra"),
            **common,
        )
    if provider == "ensemble":
        from erdos_forge.prover.ensemble import EnsembleModel

        specs = [s.strip() for s in str(params.get("model", "")).split(",") if s.strip()]
        if not specs:
            raise ValueError("ensemble spec needs a comma-separated list of model specs, e.g. ensemble:gpt,claude")
        return EnsembleModel([build_model(s, settings) for s in specs])
    raise ValueError(provider)
