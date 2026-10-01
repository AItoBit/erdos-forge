/-
Level 1 — elementary algebra and order over ℤ / ℚ / ℕ with Mathlib's core
tactics. Imports are kept narrow on purpose: `import Mathlib` takes minutes
on a cold machine, these take well under a minute.
-/
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Positivity

theorem sq_nonneg_int (x : ℤ) : 0 ≤ x ^ 2 := by
  positivity

theorem add_sq_int (a b : ℤ) : (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2 := by
  ring

theorem sub_sq_int (a b : ℤ) : (a - b) ^ 2 = a ^ 2 - 2 * a * b + b ^ 2 := by
  ring

theorem cube_succ_int (a : ℤ) : (a + 1) ^ 3 = a ^ 3 + 3 * a ^ 2 + 3 * a + 1 := by
  ring

theorem two_mul_le_rat (a b : ℚ) (h : a ≤ b) : 2 * a ≤ a + b := by
  linarith

theorem rat_lt_mid (a b : ℚ) (h : a < b) : a < (a + b) / 2 := by
  linarith

theorem pow_ten_rat : (2 : ℚ) ^ 10 = 1024 := by
  norm_num

theorem div_rat : (7 : ℚ) / 2 = 3.5 := by
  norm_num

theorem am_gm_two_int (a b : ℤ) : 2 * a * b ≤ a ^ 2 + b ^ 2 := by
  nlinarith [sq_nonneg (a - b)]

theorem sq_sum_bound_int (a b : ℤ) : (a + b) ^ 2 ≤ 2 * (a ^ 2 + b ^ 2) := by
  nlinarith [sq_nonneg (a - b)]

theorem int_mul_pos' (a b : ℤ) (ha : 0 < a) (hb : 0 < b) : 0 < a * b := by
  positivity

theorem nat_sq_ge_four (n : ℕ) (h : 2 ≤ n) : 4 ≤ n ^ 2 := by
  nlinarith

theorem rat_abs_free (x : ℚ) (hx : 0 ≤ x) (hy : x ≤ 1) : x ^ 2 ≤ x := by
  nlinarith
