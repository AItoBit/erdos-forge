"""Prune repeated states, looping tactics and over-deep branches."""

from __future__ import annotations

from erdos_forge.search.node import ProofNode


def should_prune(
    node: ProofNode,
    visited: set[str],
    *,
    max_depth: int = 40,
    parent_action: str | None = None,
) -> tuple[bool, str]:
    if node.depth > max_depth:
        return True, "max_depth"
    if node.state_hash and node.state_hash in visited:
        return True, "repeated_state"
    if parent_action and node.action and parent_action.strip() == node.action.strip():
        # The same tactic twice in a row almost never makes progress.
        return True, "repeated_action"
    if not node.compile_ok and node.depth > 0:
        return True, "invalid"
    return False, ""
