# Benchmark run `baseline-level1-heuristic`

- split: `level1_mathlib`  
- model: `heuristic`  
- strategy: `repair` (max_repairs=3)  
- lean project: `C:\Users\Usuario\Downloads\formal-conjectures-green65` (leanprover/lean4:v4.33.1)  
- started: 2026-10-01T07:33:12  

## Headline

| Metric | Value |
|---|---:|
| **Kernel-verified solve rate** | **0.0%** (0/13) |
| First-attempt solve rate | 0.0% |
| Repair success rate | 0.0% |
| Compiler calls / problem | 4 |
| LLM calls / problem | 4 |
| Tokens / problem | 0 |
| Wall-clock / problem | 91.6 s |

## Outcomes

| Outcome | Count |
|---|---:|
| failed | 13 |

## Error categories (all attempts)

| Category | Count |
|---|---:|
| unknown_tactic | 52 |
| unsolved_goals | 20 |

## Per problem

| Problem | Outcome | LLM calls | Compiles | Wall (s) | Last error / note |
|---|---|---:|---:|---:|---|
| `IntRatAlgebra:sq_nonneg_int` | failed | 4 | 4 | 120.2 | compile errors: unknown_tactic |
| `IntRatAlgebra:add_sq_int` | failed | 4 | 4 | 94.8 | compile errors: unknown_tactic |
| `IntRatAlgebra:sub_sq_int` | failed | 4 | 4 | 70.6 | compile errors: unknown_tactic |
| `IntRatAlgebra:cube_succ_int` | failed | 4 | 4 | 62.5 | compile errors: unknown_tactic |
| `IntRatAlgebra:two_mul_le_rat` | failed | 4 | 4 | 70.4 | compile errors: unknown_tactic |
| `IntRatAlgebra:rat_lt_mid` | failed | 4 | 4 | 60.7 | compile errors: unknown_tactic |
| `IntRatAlgebra:pow_ten_rat` | failed | 4 | 4 | 61.9 | compile errors: unknown_tactic |
| `IntRatAlgebra:div_rat` | failed | 4 | 4 | 93.2 | compile errors: unknown_tactic |
| `IntRatAlgebra:am_gm_two_int` | failed | 4 | 4 | 65.1 | compile errors: unknown_tactic |
| `IntRatAlgebra:sq_sum_bound_int` | failed | 4 | 4 | 74.0 | compile errors: unknown_tactic |
| `IntRatAlgebra:int_mul_pos'` | failed | 4 | 4 | 68.1 | compile errors: unknown_tactic |
| `IntRatAlgebra:nat_sq_ge_four` | failed | 4 | 4 | 266.4 | compile errors: unknown_tactic |
| `IntRatAlgebra:rat_abs_free` | failed | 4 | 4 | 82.9 | compile errors: unknown_tactic |
