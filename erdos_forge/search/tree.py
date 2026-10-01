"""Proof-search DAG: children share a parent, equivalent states are merged."""

from __future__ import annotations

from erdos_forge.search.node import ProofNode
from erdos_forge.search.pruning import should_prune


class ProofTree:
    def __init__(self, root: ProofNode, *, max_depth: int = 40):
        self.root = root
        self.max_depth = max_depth
        self.nodes: dict[str, ProofNode] = {root.id: root}
        self.visited: set[str] = {root.state_hash} if root.state_hash else set()
        self.children: dict[str, list[str]] = {root.id: []}

    def add(self, node: ProofNode) -> ProofNode | None:
        """Insert ``node`` unless it is pruned. Returns the stored node or ``None``."""
        parent_action = self.nodes[node.parent].action if node.parent and node.parent in self.nodes else None
        prune, _reason = should_prune(node, self.visited, max_depth=self.max_depth, parent_action=parent_action)
        if prune:
            node.terminal = True
            return None
        if node.state_hash:
            self.visited.add(node.state_hash)
        self.nodes[node.id] = node
        if node.parent:
            self.children.setdefault(node.parent, []).append(node.id)
        self.children.setdefault(node.id, [])
        return node

    def frontier(self) -> list[ProofNode]:
        return [n for n in self.nodes.values() if not n.terminal and not n.verified]

    def best(self, k: int) -> list[ProofNode]:
        open_nodes = [n for n in self.frontier() if n.compile_ok or n.depth == 0]
        open_nodes.sort(key=lambda n: n.score, reverse=True)
        return open_nodes[:k]

    def mark_verified(self, node_id: str) -> None:
        node = self.nodes[node_id]
        node.verified = True
        node.terminal = True
        node.score = 1.0
