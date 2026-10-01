/-
Erdős Problem 169 — the OPEN conjecture, formalized only.

Let f(k) be the supremum of ∑_{n ∈ A} 1/n over sets A ⊆ ℕ⁺ with no k-term
arithmetic progression, and W(k) the two-colour van der Waerden number.
Is f(k) / log W(k) → ∞ ?

This file states the conjecture; it does not (and must not) prove it. The
`sorry` below is the placeholder every open target carries: the open-problem
guard routes this target to statement checking only and the verification
firewall rejects any file containing it.
-/
import Mathlib

open scoped ENNReal

namespace Erdos169

/-- A nonconstant k-term arithmetic progression contained in A. -/
def HasAP (A : Set ℕ) (k : ℕ) : Prop :=
  ∃ a d : ℕ, 0 < d ∧ ∀ i : ℕ, i < k → a + i * d ∈ A

/-- A is a set of strictly positive integers with no k-term progression. -/
def Admissible (A : Set ℕ) (k : ℕ) : Prop :=
  (∀ n ∈ A, 0 < n) ∧ ¬ HasAP A k

/-- The sum of reciprocals, with infinity permitted. -/
noncomputable def reciprocalSum (A : Set ℕ) : ℝ≥0∞ :=
  ∑' n : A, ((n.val : ℝ≥0∞)⁻¹)

/-- The extremal function from Problem 169. -/
noncomputable def f (k : ℕ) : ℝ≥0∞ :=
  ⨆ (A : Set ℕ) (_ : Admissible A k), reciprocalSum A

/-- Every two-colouring of {1, ..., N} contains a monochromatic k-AP. -/
def VanDerWaerdenProperty (k N : ℕ) : Prop :=
  ∀ c : ℕ → Fin 2, ∃ a d : ℕ,
    0 < a ∧ 0 < d ∧ (∀ i : ℕ, i < k → a + i * d ≤ N) ∧ (∀ i : ℕ, i < k → c (a + i * d) = c a)

/-- Least positive N with the two-colour van der Waerden property. -/
noncomputable def W (k : ℕ) : ℕ :=
  sInf {N : ℕ | 0 < N ∧ VanDerWaerdenProperty k N}

/-- log W(k), in ENNReal. -/
noncomputable def logW (k : ℕ) : ℝ≥0∞ :=
  ENNReal.ofReal (Real.log (W k : ℝ))

/-- Erdős Problem 169 (open): f(k) / log W(k) → ∞ as k → ∞. -/
theorem erdos_169 :
    Filter.Tendsto (fun k : ℕ => f (k + 3) / logW (k + 3)) Filter.atTop (nhds (⊤ : ℝ≥0∞)) := by
  sorry

end Erdos169
