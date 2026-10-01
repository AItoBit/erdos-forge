/-
Erdős Problem 169 — auxiliary structural facts (level 6: known mathematics
surrounding an open problem).

Problem 169 asks whether f(k) / log W(k) → ∞, where f(k) is the supremum of
reciprocal sums of k-AP-free sets of positive integers and W(k) the two-colour
van der Waerden number. The conjecture itself is OPEN and lives in the
formal-conjectures repository (`FormalConjectures/ErdosProblems/169.lean`,
`import Mathlib`). This file only fixes the combinatorial core needed to state
elementary, provable facts; the imports are deliberately light.
-/
import Mathlib.Data.Set.Basic

namespace Erdos169

/-- A nonconstant k-term arithmetic progression contained in A. -/
def HasAP (A : Set ℕ) (k : ℕ) : Prop :=
  ∃ a d : ℕ, 0 < d ∧ ∀ i : ℕ, i < k → a + i * d ∈ A

/-- A contains no nonconstant k-term arithmetic progression. -/
def APFree (A : Set ℕ) (k : ℕ) : Prop :=
  ¬ HasAP A k

/-- A progression remains a progression in a larger set. -/
theorem hasAP_mono {A B : Set ℕ} {k : ℕ} (hAB : A ⊆ B) (h : HasAP A k) : HasAP B k := by
  obtain ⟨a, d, hd, hmem⟩ := h
  exact ⟨a, d, hd, fun i hi => hAB (hmem i hi)⟩

/-- An initial segment of a progression is a shorter progression. -/
theorem hasAP_of_le {A : Set ℕ} {k l : ℕ} (hkl : k ≤ l) (h : HasAP A l) : HasAP A k := by
  obtain ⟨a, d, hd, hmem⟩ := h
  exact ⟨a, d, hd, fun i hi => hmem i (lt_of_lt_of_le hi hkl)⟩

/-- Avoiding k-term progressions implies avoiding longer progressions. -/
theorem apFree_of_le {A : Set ℕ} {k l : ℕ} (hkl : k ≤ l) (h : APFree A k) : APFree A l := by
  intro hl
  exact h (hasAP_of_le hkl hl)

/-- AP-freeness is inherited by subsets. -/
theorem apFree_mono {A B : Set ℕ} {k : ℕ} (hAB : A ⊆ B) (h : APFree B k) : APFree A k := by
  intro hA
  exact h (hasAP_mono hAB hA)

/-- Every nonempty set contains a 1-term progression. -/
theorem hasAP_one_of_nonempty {A : Set ℕ} (h : A.Nonempty) : HasAP A 1 := by
  obtain ⟨a, ha⟩ := h
  refine ⟨a, 1, Nat.one_pos, fun i hi => ?_⟩
  have : i = 0 := Nat.lt_one_iff.mp hi
  subst this
  simpa using ha

/-- The empty set is k-AP-free for every k ≥ 1. -/
theorem apFree_empty {k : ℕ} (hk : 1 ≤ k) : APFree (∅ : Set ℕ) k := by
  rintro ⟨a, d, _, hmem⟩
  exact hmem 0 hk

end Erdos169
