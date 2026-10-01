"""erdos-forge: autonomous Lean 4 formalization & proof-search system for Erdős problems.

The package is organised by roadmap layer:

- ``lean``        ground truth: compiler, diagnostics, source parsing, verification firewall
- ``models``      LLM abstraction (OpenAI-compatible, Anthropic, local, ensemble, heuristic)
- ``prover``      prompt construction, candidate extraction, repair, ensemble
- ``retrieval``   Mathlib / core-Lean index, premise selection, reranking
- ``formalizer``  mathematical analysis (prove vs formalize) and statement checks
- ``search``      proof-state DAG, scoring, pruning (beam/best-first comes next)
- ``lemma``       verified helper-lemma library
- ``core``        problem state, budgets, events, open-problem guard, controllers
- ``memory``      trajectory + failure memory
- ``evaluation``  benchmark runner, metrics, reports, ablations
"""

__version__ = "0.3.0"
