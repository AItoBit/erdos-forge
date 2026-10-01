# Erdős benchmark levels

This directory holds the Erdős-specific layers of the benchmark ladder
(levels 4–6 in the design): solved `formal-conjectures` entries, known Erdős
theorems, and known results *surrounding* open problems (finite cases, bounds,
equivalences, conditional results).

Each target is a Lean file plus a metadata JSON in `data/problems/`:

```json
{
  "id": "erdos_169_aux_ap_free_subset",
  "target": "../../benchmarks/erdos/Erdos169Aux.lean:Erdos169.apFree_subset",
  "status": "solved",
  "kind": "auxiliary",
  "level": 6,
  "tags": ["additive-combinatorics", "erdos-169"],
  "source": "formal-conjectures FormalConjectures/ErdosProblems/169.lean",
  "notes": "Monotonicity of AP-freeness under subsets."
}
```

`kind` and `status` drive the open-problem guard:

| kind         | status            | what the agent may do                                  |
|--------------|-------------------|--------------------------------------------------------|
| `conjecture` | `open`/`unknown`  | check that the statement elaborates; **never** prove it |
| `theorem`    | any               | full proof search                                      |
| `auxiliary`  | any               | full proof search                                      |

Files here should use the same imports as the `formal-conjectures` entry they
come from (usually `import Mathlib`). Be aware that `import Mathlib` is slow
on a cold machine; use `erdos-forge doctor` to check compile times first.
