# Benchmark run `baseline-erdos-aux-heuristic`

- split: `erdos_auxiliary`  
- model: `heuristic`  
- strategy: `repair` (max_repairs=3)  
- lean project: `C:\Users\Usuario\Downloads\formal-conjectures-green65` (leanprover/lean4:v4.33.1)  
- started: 2026-10-01T07:53:05  

## Headline

| Metric | Value |
|---|---:|
| **Kernel-verified solve rate** | **0.0%** (0/6) |
| First-attempt solve rate | 0.0% |
| Repair success rate | 0.0% |
| Compiler calls / problem | 4 |
| LLM calls / problem | 4 |
| Tokens / problem | 0 |
| Retrieved lemmas / problem | 9.67 |
| Wall-clock / problem | 58.9 s |

## Outcomes

| Outcome | Count |
|---|---:|
| failed | 6 |

## Error categories (all attempts)

| Category | Count |
|---|---:|
| unknown_tactic | 24 |
| unsolved_goals | 15 |

## Per problem

| Problem | Outcome | LLM calls | Compiles | Wall (s) | Last error / note |
|---|---|---:|---:|---:|---|
| `Erdos169Aux:hasAP_mono` | failed | 4 | 4 | 92.6 | compile errors: unknown_tactic |
| `Erdos169Aux:hasAP_of_le` | failed | 4 | 4 | 48.1 | compile errors: unknown_tactic |
| `Erdos169Aux:apFree_of_le` | failed | 4 | 4 | 57.6 | compile errors: unknown_tactic |
| `Erdos169Aux:apFree_mono` | failed | 4 | 4 | 52.8 | compile errors: unknown_tactic |
| `Erdos169Aux:hasAP_one_of_nonempty` | failed | 4 | 4 | 42.3 | compile errors: unknown_tactic |
| `Erdos169Aux:apFree_empty` | failed | 4 | 4 | 59.9 | compile errors: unknown_tactic |
