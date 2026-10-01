# erdos-forge

**Autonomous Lean 4 formalization & proof-search system for Erdős problems.**

`erdos-forge` turns mathematical sources about Erdős problems into faithful
Lean 4 formalizations and tries to kernel-verify as much of the *surrounding
known mathematics* as possible: equivalent formulations, finite cases, known
bounds, implications, auxiliary lemmas and solved variants.

It unifies three earlier designs — **LeanSearch** (proof-state search),
**LeanLemma** (reusable lemma discovery) and the **Autonomous Mathematical
Research System** (strategy-level planning) — around one concrete, measurable
use case.

```text
Erdős problem / paper / existing .lean
                │
                ▼
     Mathematical Analyzer ─► Statement Formalizer ─► Lean statement
                                                         │
                                                         ▼
                                         Autonomous Proof Controller
                                        ┌──────────┼──────────┐
                                        ▼          ▼          ▼
                                    Retrieval  LLM Prover  Lemma Discovery
                                        └──────────┼──────────┘
                                                   ▼
                                          Candidate proofs ─► Lean
                                                   │
                                        ┌──────────┴──────────┐
                                      ERROR                 VERIFIED
                                        │                      │
                                   Error repair      Verification firewall
```

## Hard constraints

```text
NO sorry      NO admit      NO fabricated axioms
NO silently weakened theorem        NO "looks correct"
```

The final authority is a fresh `lean` process on a file rebuilt from scratch,
exit code `0`, and `#print axioms` reporting nothing beyond
`propext`, `Classical.choice`, `Quot.sound`.

**V1 is not intended to solve open Erdős conjectures.** For an *open*
problem, success means a faithful, type-checked statement plus verified
surrounding mathematics — never a proof of the conjecture itself (see
[Open-problem guard](#open-problem-guard)).

## Status: V0.3

| Version | Milestone | State |
|---|---|---|
| V0.1 | LLM → Lean → error → repair | ✅ |
| V0.2 | structured diagnostics | ✅ |
| V0.3 | Mathlib / core retrieval + premise selection | ✅ |
| V0.4 | compile every candidate (samples / labelled tactics) | ✅ |
| V0.5 | beam / best-first search | primitives ready (node, DAG, scoring, pruning) |
| V0.6 | proof-state deduplication | ✅ (`state_hash`; used by the search DAG) |
| V0.7 | trajectory database | ✅ (JSONL; DB later) |
| V0.8 | multi-model ensemble | ✅ (`EnsembleModel`, `local:` provider) |
| V0.9 | benchmark + ablations | ✅ (`erdos-forge ablate`) |
| V1.0 | Erdős formalization agent (PDF → verified formalization) | analyzer + guard + statement validator ready |

What exists today:

- **Lean ground-truth layer** — `lake env`-resolved compiler, structured
  diagnostics (category, line, identifier, goals, suggested action),
  theorem/context parser, file assembler with safety options
  (`autoImplicit false`).
- **Verification firewall** — forbidden-construct scan, statement-faithfulness
  check, independent recompile, `declaration uses sorry` detection, axiom
  audit. The LLM never sees or controls it.
- **Open-problem guard + mathematical analyzer** — `status`/`kind` metadata;
  structured `ProblemAnalysis` (`prove` vs `formalize_only`) so an open
  conjecture is never treated as a theorem to prove.
- **Mathlib retrieval** — seed index of real core-Lean / common-Mathlib
  declarations, optional `erdos-forge index` scan of a built Mathlib tree,
  type-aware filter, rerank to 10, then the LLM. Unknown-identifier repair
  is routed to `retrieve_declaration`.
- **Repair controller** — retrieval on the first prompt, N candidate proofs
  per call (every distinct sample is compiled; Lean is the filter),
  extraction, early rejection, structured feedback + failure memory,
  bounded repairs, budgets.
- **Models** — OpenAI-compatible, Anthropic, local servers, ensembles
  (`ensemble:gpt,claude`), an offline *heuristic* baseline and a scripted mock.
- **Search primitives** — `ProofNode` / `ProofTree` DAG, state hashing,
  scoring, pruning. Beam / best-first is the next controller, not this one.
- **Benchmarks** — level 0 (core Lean), level 1 (narrow Mathlib imports),
  Erdős auxiliary (known facts around Problem 169); every reference proof is
  firewall-verified.
- **Evaluation** — kernel-verified solve rate plus compiler/token/retrieval
  metrics, JSON + Markdown reports, JSONL trajectories, ablation presets
  (`llm_only` · `llm_repair` · `llm_retrieval` · `llm_retrieval_repair`).

## Quickstart

Requirements: Python ≥ 3.11, [elan](https://github.com/leanprover/elan), and a
Lake project with a **built Mathlib** (see `workspace/lean_project/README.md`;
reusing an existing `formal-conjectures` checkout is the fastest route).

```bash
pip install -e ".[dev]"

# point at a built Lean project (or set project_dir in config/lean.yaml)
export ERDOS_FORGE_LEAN_PROJECT=/path/to/formal-conjectures      # bash
$env:ERDOS_FORGE_LEAN_PROJECT = "C:\path\to\formal-conjectures"   # PowerShell

erdos-forge doctor                                   # toolchain, project, compile time, API keys
erdos-forge check benchmarks/level0_core/NatArith.lean   # firewall on a whole file
erdos-forge retrieve "n + 0 = n" --core-only             # premise selection (no Lean needed)
erdos-forge analyze data/problems/erdos_169_conjecture.json
erdos-forge bench --split level0_core --model heuristic  # offline baseline
erdos-forge ablate --split level0_core --model heuristic --limit 20
erdos-forge bench --split level0_core --model gpt        # needs OPENAI_API_KEY
erdos-forge prove benchmarks/level1_mathlib/IntRatAlgebra.lean:am_gm_two_int --model claude
erdos-forge prove data/problems/erdos_169_conjecture.json   # open → guarded, statement check only
```

Model specs are aliases from `config/models.yaml` (`gpt`, `claude`, `local`,
`heuristic`) or inline `provider:model` strings (`openai:gpt-4.1`,
`anthropic:claude-sonnet-4-5`). Any OpenAI-compatible server (vLLM, Ollama,
OpenRouter) works through `OPENAI_BASE_URL`.

## The proof loop

```text
guard ──► retrieve ──► generate N ──► extract ──► scan ──► compile ──► diagnostics
                           ▲                                           │
                           └──────── repair (≤ N) ◄────────────────────┘
                                                                       │ ok
                                                                       ▼
                                                             verification firewall
```

1. **Guard + analyze.** Open conjectures are routed to statement checking only.
   The analyzer records `prove_vs_formalize` so the two jobs cannot be confused.
2. **Retrieve.** The statement (and later, unknown identifiers / remaining
   goals) is searched against the declaration index. The model sees at most
   `top_k` existing names — never a hallucinated `Nat.foo` as if it were real.
3. **Generate.** The model receives fixed imports, retrieved lemmas, the file
   context and the target statement, and must return the complete declaration
   verbatim (helper lemmas allowed before it). Every distinct sample / 
   `Candidate N:` block is compiled.
4. **Extract & scan.** Imports and repeated context are dropped; statement
   changes and forbidden constructs are rejected *before* spending a compile.
5. **Compile & diagnose.** Raw output becomes `LeanDiagnostic` records:

   ```python
   LeanDiagnostic(category="unknown_identifier", identifier="Nat.foo",
                  line=84, severity="error", likely_action="retrieve_declaration")
   ```

   Categories: unknown identifier · unknown tactic · type mismatch · unsolved
   goals (with parsed goals) · tactic failure · failed synthesis · coercion ·
   rewrite failure · termination · universe · parser · import · timeout.
6. **Repair.** A compact, structured summary plus category-specific hints,
   retrieved replacements for unknown identifiers, and failure-memory notes
   is fed back; at most `max_repairs` times (`config/search.yaml`).
7. **Firewall.** Independent recompile with `#print axioms`; only this
   component can report `verified`.

## Open-problem guard

```python
class ProblemStatus(Enum): OPEN, SOLVED, PARTIALLY_SOLVED, UNKNOWN
class TargetKind(Enum):    THEOREM, CONJECTURE, AUXILIARY
```

| kind         | status           | allowed                                        |
|--------------|------------------|------------------------------------------------|
| `conjecture` | `open`/`unknown` | statement elaboration check only (`statement_ok`) |
| `theorem`    | any              | proof search                                   |
| `auxiliary`  | any              | proof search                                   |

Independently of status, no candidate may add `axiom`s or alter the statement.

## Benchmarks

| Split | Level | Imports | Problems | Reference proofs |
|---|---:|---|---:|---|
| `level0_core` | 0 | none (core Lean 4) | 29 | verified |
| `level1_mathlib` | 1 | `Mathlib.Tactic.{Ring,Linarith,NormNum,Positivity}` | 13 | verified |
| `erdos_auxiliary` | 6 | `Mathlib.Data.Set.Basic` | 6 | verified |

Reference proofs are hidden from the prover. Add files to
`benchmarks/splits.json`; Erdős targets carry metadata in `data/problems/`.
Levels 2–5 (Mathlib composition, olympiad, solved `formal-conjectures`
entries, known Erdős theorems) are the next additions.

Headline metric: **kernel-verified solve rate**. Also reported: first-attempt
rate, repair success rate, compiler calls / LLM calls / tokens / wall-clock
per problem, outcome and error-category histograms. Reports land in
`reports/runs/<run-id>/{summary.json,report.md,trajectories.jsonl,proofs.lean.txt}`.

## Repository layout

```text
erdos_forge/
├── core/          agent, state, budget, events, guard, controller
├── lean/          compiler, diagnostics, goal parser, source, firewall, environment
├── models/        base, openai, anthropic, local, mock (+ heuristic), router
├── prover/        prompts, extract, repair, tactic candidates, ensemble
├── retrieval/     index, theorem search, semantic rank, premise selection, reranker
├── formalizer/    problem parser, mathematical analyzer, statement validator
├── search/        node, tree (DAG), scoring, pruning
├── lemma/         verified helper-lemma library
├── memory/        trajectories (JSONL), failure memory
└── evaluation/    benchmark runner, metrics, report, ablations
config/            lean.yaml · models.yaml · search.yaml · benchmark.yaml
benchmarks/        level0_core/ · level1_mathlib/ · erdos/ · splits.json
data/problems/     Erdős target metadata (status, kind, source, notes)
data/mathlib_index/  extra JSONL + optional Mathlib source cache
workspace/         lean_project/ (Lake project) · scratch/ (temporary .lean files)
tests/             unit tests (fake compiler) + `lean`-marked integration tests
```

## Tests

```bash
pytest -q -m "not lean"                                   # no Lean needed
pytest -q tests --lean-project /path/to/formal-conjectures  # + real-Lean integration
ERDOS_FORGE_TEST_MATHLIB=1 pytest -q tests -m mathlib ...   # slow Mathlib tests
```

## Performance notes

- `lake env lean` reloads the Lake workspace on every call (20–30 s on some
  machines). `erdos-forge` resolves `lake env` once and runs the toolchain's
  `lean` directly with that environment (~1–2 s for a core file); each compile
  is still a fresh process. Disable with `cache_lake_env: false`.
- `import Mathlib` loads thousands of `.olean` files; on a cold disk this can
  take many minutes. Keep imports narrow where the mathematics allows it, and
  calibrate `compile_timeout` with `erdos-forge doctor`.

## Research questions

> Can an autonomous system transform mathematical sources about Erdős problems
> into faithful Lean 4 formalizations and maximize the amount of surrounding
> known mathematics that is independently kernel-verified?

> Can reusable lemma discovery, premise retrieval, compiler feedback and
> proof-state search systematically increase the frontier of mathematics that
> autonomous Lean agents can formalize?

Ablations (same problems, timeout, compiler budget and retrieval index):

```bash
erdos-forge ablate --split level0_core --model gpt --presets llm_only llm_repair llm_retrieval llm_retrieval_repair
```

That is the comparison that answers *what actually makes autonomous Lean
theorem proving work better*, instead of claiming the agent is good. Search
width and lemma-discovery rows land when those controllers do.

## License

Apache-2.0.
