/-
Level 0 — natural-number arithmetic in core Lean 4 (no Mathlib).
Reference proofs are hidden from the prover; they only certify that every
statement is provable with the given imports.
-/

theorem add_zero_right (n : Nat) : n + 0 = n := by
  rfl

theorem zero_add_left (n : Nat) : 0 + n = n := by
  simp

theorem add_comm' (a b : Nat) : a + b = b + a := by
  omega

theorem le_add_right' (a b : Nat) : a ≤ a + b := by
  omega

theorem double_le (a b : Nat) (h : a ≤ b) : 2 * a ≤ 2 * b := by
  omega

theorem succ_ne_zero' (n : Nat) : n + 1 ≠ 0 := by
  omega

theorem mul_comm' (a b : Nat) : a * b = b * a := by
  exact Nat.mul_comm a b

theorem lt_of_lt_of_le' (a b c : Nat) (h₁ : a < b) (h₂ : b ≤ c) : a < c := by
  omega

theorem mod_two_cases (n : Nat) : n % 2 = 0 ∨ n % 2 = 1 := by
  omega

theorem exists_gt' (n : Nat) : ∃ m, n < m := by
  exact ⟨n + 1, Nat.lt_succ_self n⟩

theorem sq_eq_mul (n : Nat) : n ^ 2 = n * n := by
  exact Nat.pow_two n

/-- Triangular numbers, defined by recursion. -/
def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => (n + 1) + sumTo n

theorem sumTo_zero : sumTo 0 = 0 := by
  rfl

theorem sumTo_ge (n : Nat) : n ≤ sumTo n := by
  cases n with
  | zero => simp [sumTo]
  | succ n => simp [sumTo]

theorem sumTo_formula (n : Nat) : 2 * sumTo n = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ n ih =>
    simp only [sumTo]
    rw [Nat.mul_add, ih]
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul]
    omega
