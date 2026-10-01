"""Canonical proof-state representation used for deduplication and scoring."""

from __future__ import annotations

import hashlib
import re


def extract_goals(message: str) -> list[str]:
    """Split the goal dump that follows ``unsolved goals`` into individual goals."""
    lines = message.splitlines()[1:]
    goals: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                goals.append(current)
                current = []
            continue
        if line.startswith("case ") and current:
            goals.append(current)
            current = []
        current.append(line)
    if current:
        goals.append(current)
    return ["\n".join(g) for g in goals if any("⊢" in ln for ln in g)]


def normalize_goal(goal: str) -> str:
    text = re.sub(r"--[^\n]*", "", goal)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def canonicalize_state(goals: list[str], context: str = "") -> str:
    """Order-insensitive representation of (local context, remaining goals)."""
    norm_goals = sorted(normalize_goal(g) for g in goals if normalize_goal(g))
    ctx = normalize_goal(context)
    return ctx + "\n---\n" + "\n\n".join(norm_goals)


def state_hash(goals: list[str], context: str = "") -> str:
    payload = canonicalize_state(goals, context).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
