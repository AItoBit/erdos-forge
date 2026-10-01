"""Minimal event bus so logging, trajectories and progress display stay decoupled."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Listener = Callable[["Event"], None]


@dataclass
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    def __init__(self) -> None:
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def emit(self, kind: str, /, **payload: Any) -> Event:
        event = Event(kind, payload)
        for listener in list(self._listeners):
            listener(event)
        return event


def logging_listener(logger: logging.Logger | None = None, level: int = logging.INFO) -> Listener:
    log = logger or logging.getLogger("erdos_forge")

    def _listen(event: Event) -> None:
        summary = {k: v for k, v in event.payload.items() if isinstance(v, (str, int, float, bool)) or v is None}
        log.log(level, "%s %s", event.kind, summary)

    return _listen
