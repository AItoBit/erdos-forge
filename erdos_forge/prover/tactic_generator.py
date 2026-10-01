"""Parse several tactic / proof candidates out of one model response.

The controller still asks for whole proofs by default. When a response lists
``Candidate N:`` blocks (or several ```lean fences), every distinct candidate
is compiled; Lean is the filter.
"""

from __future__ import annotations

import re

from erdos_forge.prover.extract import _FENCE

_CANDIDATE = re.compile(
    r"(?:^|\n)\s*(?:Candidate\s+\d+|Option\s+\d+|Tactic\s+\d+)\s*:\s*(.*?)(?=\n\s*(?:Candidate|Option|Tactic)\s+\d+\s*:|\Z)",
    re.S | re.I,
)


def split_candidates(text: str) -> list[str]:
    """Unique non-empty candidate strings, original order preserved."""
    found: list[str] = []
    for block in _FENCE.findall(text):
        if block.strip():
            found.append(block.strip())
    if not found:
        labelled = [m.group(1).strip() for m in _CANDIDATE.finditer(text)]
        found.extend(b for b in labelled if b)
    if not found and text.strip():
        found.append(text.strip())
    seen: set[str] = set()
    unique: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique
