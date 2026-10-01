"""Proof-state search primitives (used by V0.5+ beam / best-first).

V0.3 stores nodes and scores them; the default controller is still the
whole-proof repair loop. Deduplication via ``state_hash`` is already used
so later search becomes a DAG rather than a duplicated tree.
"""

from erdos_forge.search.node import ProofNode
from erdos_forge.search.pruning import should_prune
from erdos_forge.search.scoring import ScoreWeights, score_state
from erdos_forge.search.tree import ProofTree

__all__ = ["ProofNode", "ProofTree", "ScoreWeights", "score_state", "should_prune"]
