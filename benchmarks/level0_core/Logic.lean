/-
Level 0 — propositional and first-order logic in core Lean 4 (no Mathlib).
-/

theorem and_swap' (p q : Prop) (h : p ∧ q) : q ∧ p := by
  exact ⟨h.2, h.1⟩

theorem or_swap' (p q : Prop) (h : p ∨ q) : q ∨ p := by
  cases h with
  | inl hp => exact Or.inr hp
  | inr hq => exact Or.inl hq

theorem imp_trans' (p q r : Prop) (hpq : p → q) (hqr : q → r) : p → r := by
  intro hp
  exact hqr (hpq hp)

theorem not_not_intro' (p : Prop) (hp : p) : ¬¬p := by
  intro hn
  exact hn hp

theorem forall_and_split (α : Type) (p q : α → Prop) (h : ∀ x, p x ∧ q x) :
    (∀ x, p x) ∧ (∀ x, q x) := by
  exact ⟨fun x => (h x).1, fun x => (h x).2⟩

theorem exists_imp' (α : Type) (p q : α → Prop) (h : ∀ x, p x → q x) (hx : ∃ x, p x) :
    ∃ x, q x := by
  obtain ⟨x, hpx⟩ := hx
  exact ⟨x, h x hpx⟩

theorem iff_symm' (p q : Prop) (h : p ↔ q) : q ↔ p := by
  exact h.symm

theorem de_morgan_or (p q : Prop) (h : ¬(p ∨ q)) : ¬p ∧ ¬q := by
  exact ⟨fun hp => h (Or.inl hp), fun hq => h (Or.inr hq)⟩
