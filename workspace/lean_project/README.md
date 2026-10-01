# Lean workspace

`erdos-forge` compiles every candidate with `lake env lean <file>` executed
from a Lake project whose dependencies are already built. This directory is the
default project (`config/lean.yaml: project_dir`).

## Option A — build this project (downloads the Mathlib cache, several GB)

```bash
cd workspace/lean_project
lake exe cache get      # fetch pre-built Mathlib .olean files
lake build              # builds the (empty) root library
cd ../..
erdos-forge doctor
```

## Option B — reuse an existing Mathlib project (recommended if you have one)

Point the agent at any Lake project with a built Mathlib, e.g. a
`formal-conjectures` checkout:

```bash
# PowerShell
$env:ERDOS_FORGE_LEAN_PROJECT = "C:\path\to\formal-conjectures"
# bash
export ERDOS_FORGE_LEAN_PROJECT=/path/to/formal-conjectures

erdos-forge doctor
```

or pass `--lean-project PATH` to any command.

## Performance note

The whole of `import Mathlib` is loaded on every compile. On a warm SSD this is
10–30 s; on a cold disk it can take many minutes. Benchmarks therefore use
narrow imports (`Mathlib.Tactic.Ring`, `Mathlib.Data.Set.Basic`, ...) wherever
possible, and `erdos-forge doctor` reports the measured compile time for a
core-only file so you can calibrate `compile_timeout`.
