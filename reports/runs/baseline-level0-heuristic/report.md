# Benchmark run `baseline-level0-heuristic`

- split: `level0_core`  
- model: `heuristic`  
- strategy: `repair` (max_repairs=3)  
- lean project: `C:\Users\Usuario\Downloads\formal-conjectures-green65` (leanprover/lean4:v4.33.1)  
- started: 2026-10-01T07:29:31  

## Headline

| Metric | Value |
|---|---:|
| **Kernel-verified solve rate** | **72.4%** (21/29) |
| First-attempt solve rate | 72.4% |
| Repair success rate | 0.0% |
| Compiler calls / problem | 2.55 |
| LLM calls / problem | 1.83 |
| Tokens / problem | 0 |
| Wall-clock / problem | 5.96 s |

## Outcomes

| Outcome | Count |
|---|---:|
| failed | 8 |
| verified | 21 |

## Error categories (all attempts)

| Category | Count |
|---|---:|
| tactic_failure | 29 |
| unsolved_goals | 2 |
| elaboration | 1 |

## Per problem

| Problem | Outcome | LLM calls | Compiles | Wall (s) | Last error / note |
|---|---|---:|---:|---:|---|
| `NatArith:add_zero_right` | verified | 1 | 2 | 8.5 | axioms:  |
| `NatArith:zero_add_left` | verified | 1 | 2 | 3.6 | axioms: propext, Quot.sound |
| `NatArith:add_comm'` | verified | 1 | 2 | 3.6 | axioms: propext, Quot.sound |
| `NatArith:le_add_right'` | verified | 1 | 2 | 3.4 | axioms: propext, Quot.sound |
| `NatArith:double_le` | verified | 1 | 2 | 3.0 | axioms: propext, Quot.sound |
| `NatArith:succ_ne_zero'` | verified | 1 | 2 | 3.0 | axioms: propext, Quot.sound |
| `NatArith:mul_comm'` | failed | 4 | 4 | 6.3 | compile errors: tactic_failure |
| `NatArith:lt_of_lt_of_le'` | verified | 1 | 2 | 5.8 | axioms: propext, Quot.sound |
| `NatArith:mod_two_cases` | verified | 1 | 2 | 4.3 | axioms: propext, Quot.sound |
| `NatArith:exists_gt'` | failed | 4 | 4 | 7.6 | compile errors: tactic_failure |
| `NatArith:sq_eq_mul` | failed | 4 | 4 | 8.8 | compile errors: tactic_failure |
| `NatArith:sumTo_zero` | verified | 1 | 2 | 9.2 | axioms:  |
| `NatArith:sumTo_ge` | failed | 4 | 4 | 8.8 | compile errors: tactic_failure |
| `NatArith:sumTo_formula` | failed | 4 | 4 | 10.5 | compile errors: tactic_failure |
| `Logic:and_swap'` | verified | 1 | 2 | 5.8 | axioms: propext |
| `Logic:or_swap'` | failed | 4 | 4 | 11.6 | compile errors: tactic_failure |
| `Logic:imp_trans'` | verified | 1 | 2 | 5.5 | axioms: propext |
| `Logic:not_not_intro'` | failed | 4 | 4 | 8.3 | compile errors: elaboration |
| `Logic:forall_and_split` | verified | 1 | 2 | 4.3 | axioms: propext, Quot.sound |
| `Logic:exists_imp'` | failed | 4 | 4 | 10.8 | compile errors: tactic_failure |
| `Logic:iff_symm'` | verified | 1 | 2 | 4.4 | axioms: propext |
| `Logic:de_morgan_or` | verified | 1 | 2 | 4.2 | axioms: propext |
| `Lists:length_append'` | verified | 1 | 2 | 4.6 | axioms: propext |
| `Lists:reverse_reverse'` | verified | 1 | 2 | 4.9 | axioms: propext |
| `Lists:map_length'` | verified | 1 | 2 | 4.3 | axioms: propext |
| `Lists:length_cons'` | verified | 1 | 2 | 4.7 | axioms:  |
| `Lists:mem_cons_self'` | verified | 1 | 2 | 4.3 | axioms: propext |
| `Lists:append_nil'` | verified | 1 | 2 | 4.6 | axioms: propext |
| `Lists:length_replicate'` | verified | 1 | 2 | 4.5 | axioms: propext |
