/-
Level 0 — lists in core Lean 4 (no Mathlib).
-/

theorem length_append' (α : Type) (xs ys : List α) :
    (xs ++ ys).length = xs.length + ys.length := by
  simp

theorem reverse_reverse' (α : Type) (xs : List α) : xs.reverse.reverse = xs := by
  simp

theorem map_length' (α β : Type) (f : α → β) (xs : List α) : (xs.map f).length = xs.length := by
  simp

theorem length_cons' (α : Type) (x : α) (xs : List α) : (x :: xs).length = xs.length + 1 := by
  rfl

theorem mem_cons_self' (α : Type) (x : α) (xs : List α) : x ∈ x :: xs := by
  simp

theorem append_nil' (α : Type) (xs : List α) : xs ++ [] = xs := by
  simp

theorem length_replicate' (α : Type) (n : Nat) (x : α) : (List.replicate n x).length = n := by
  simp
