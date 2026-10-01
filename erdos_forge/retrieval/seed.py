"""Curated core-Lean + common-Mathlib declarations that retrieval can use offline.

Names are real Lean 4 / Mathlib identifiers. The seed is intentionally small
enough to load instantly and large enough that unknown-identifier repair can
point at a genuine alternative instead of inventing ``Nat.foo``.
"""

from __future__ import annotations

from erdos_forge.retrieval.mathlib_index import Declaration


def _d(
    name: str,
    signature: str,
    *,
    kind: str = "theorem",
    docstring: str = "",
    source_file: str = "",
    requires_mathlib: bool = False,
    tags: tuple[str, ...] = (),
) -> Declaration:
    ns = name.rsplit(".", 1)[0] if "." in name else ""
    return Declaration(
        name=name,
        signature=signature,
        kind=kind,
        namespace=ns,
        docstring=docstring,
        source_file=source_file,
        tags=list(tags),
        requires_mathlib=requires_mathlib,
    )


def seed_declarations() -> list[Declaration]:
    return [
        # Nat — arithmetic
        _d("Nat.add_comm", "Nat.add_comm (n m : Nat) : n + m = m + n", docstring="Addition is commutative.", tags=("nat", "add")),
        _d("Nat.add_assoc", "Nat.add_assoc (n m k : Nat) : n + m + k = n + (m + k)", tags=("nat", "add")),
        _d("Nat.add_zero", "Nat.add_zero (n : Nat) : n + 0 = n", tags=("nat", "add")),
        _d("Nat.zero_add", "Nat.zero_add (n : Nat) : 0 + n = n", tags=("nat", "add")),
        _d("Nat.succ_add", "Nat.succ_add (n m : Nat) : n.succ + m = (n + m).succ", tags=("nat", "add")),
        _d("Nat.add_succ", "Nat.add_succ (n m : Nat) : n + m.succ = (n + m).succ", tags=("nat", "add")),
        _d("Nat.add_left_comm", "Nat.add_left_comm (n m k : Nat) : n + (m + k) = m + (n + k)", tags=("nat", "add")),
        _d("Nat.add_right_comm", "Nat.add_right_comm (n m k : Nat) : n + m + k = n + k + m", tags=("nat", "add")),
        _d("Nat.mul_comm", "Nat.mul_comm (n m : Nat) : n * m = m * n", docstring="Multiplication is commutative.", tags=("nat", "mul")),
        _d("Nat.mul_assoc", "Nat.mul_assoc (n m k : Nat) : n * m * k = n * (m * k)", tags=("nat", "mul")),
        _d("Nat.mul_zero", "Nat.mul_zero (n : Nat) : n * 0 = 0", tags=("nat", "mul")),
        _d("Nat.zero_mul", "Nat.zero_mul (n : Nat) : 0 * n = 0", tags=("nat", "mul")),
        _d("Nat.mul_one", "Nat.mul_one (n : Nat) : n * 1 = n", tags=("nat", "mul")),
        _d("Nat.one_mul", "Nat.one_mul (n : Nat) : 1 * n = n", tags=("nat", "mul")),
        _d("Nat.succ_mul", "Nat.succ_mul (n m : Nat) : n.succ * m = n * m + m", tags=("nat", "mul")),
        _d("Nat.mul_succ", "Nat.mul_succ (n m : Nat) : n * m.succ = n * m + n", tags=("nat", "mul")),
        _d("Nat.left_distrib", "Nat.left_distrib (n m k : Nat) : n * (m + k) = n * m + n * k", tags=("nat", "mul", "add")),
        _d("Nat.right_distrib", "Nat.right_distrib (n m k : Nat) : (n + m) * k = n * k + m * k", tags=("nat", "mul", "add")),
        _d("Nat.mul_add", "Nat.mul_add (n m k : Nat) : n * (m + k) = n * m + n * k", tags=("nat", "mul", "add")),
        _d("Nat.add_mul", "Nat.add_mul (n m k : Nat) : (n + m) * k = n * k + m * k", tags=("nat", "mul", "add")),
        _d("Nat.pow_zero", "Nat.pow_zero (n : Nat) : n ^ 0 = 1", tags=("nat", "pow")),
        _d("Nat.pow_succ", "Nat.pow_succ (n m : Nat) : n ^ m.succ = n ^ m * n", tags=("nat", "pow")),
        _d("Nat.pow_one", "Nat.pow_one (n : Nat) : n ^ 1 = n", tags=("nat", "pow")),
        _d("Nat.pow_two", "Nat.pow_two (n : Nat) : n ^ 2 = n * n", tags=("nat", "pow")),
        _d("Nat.pow_add", "Nat.pow_add (a m n : Nat) : a ^ (m + n) = a ^ m * a ^ n", tags=("nat", "pow")),
        # Nat — order
        _d("Nat.le_refl", "Nat.le_refl (n : Nat) : n ≤ n", tags=("nat", "le")),
        _d("Nat.le_trans", "Nat.le_trans {n m k : Nat} : n ≤ m → m ≤ k → n ≤ k", tags=("nat", "le")),
        _d("Nat.le_antisymm", "Nat.le_antisymm {n m : Nat} : n ≤ m → m ≤ n → n = m", tags=("nat", "le")),
        _d("Nat.le_of_lt", "Nat.le_of_lt {n m : Nat} : n < m → n ≤ m", tags=("nat", "lt", "le")),
        _d("Nat.lt_of_lt_of_le", "Nat.lt_of_lt_of_le {n m k : Nat} : n < m → m ≤ k → n < k", tags=("nat", "lt", "le")),
        _d("Nat.lt_of_le_of_lt", "Nat.lt_of_le_of_lt {n m k : Nat} : n ≤ m → m < k → n < k", tags=("nat", "lt", "le")),
        _d("Nat.lt_trans", "Nat.lt_trans {n m k : Nat} : n < m → m < k → n < k", tags=("nat", "lt")),
        _d("Nat.lt_irrefl", "Nat.lt_irrefl (n : Nat) : ¬ n < n", tags=("nat", "lt")),
        _d("Nat.lt_succ_self", "Nat.lt_succ_self (n : Nat) : n < n.succ", tags=("nat", "lt")),
        _d("Nat.le_succ", "Nat.le_succ (n : Nat) : n ≤ n.succ", tags=("nat", "le")),
        _d("Nat.succ_le_succ", "Nat.succ_le_succ {n m : Nat} : n ≤ m → n.succ ≤ m.succ", tags=("nat", "le")),
        _d("Nat.zero_le", "Nat.zero_le (n : Nat) : 0 ≤ n", tags=("nat", "le")),
        _d("Nat.not_succ_le_zero", "Nat.not_succ_le_zero (n : Nat) : ¬ n.succ ≤ 0", tags=("nat", "le")),
        _d("Nat.succ_ne_zero", "Nat.succ_ne_zero (n : Nat) : n.succ ≠ 0", tags=("nat")),
        _d("Nat.le_add_right", "Nat.le_add_right (n m : Nat) : n ≤ n + m", tags=("nat", "le", "add")),
        _d("Nat.le_add_left", "Nat.le_add_left (n m : Nat) : n ≤ m + n", tags=("nat", "le", "add")),
        _d("Nat.add_le_add_left", "Nat.add_le_add_left {n m : Nat} (h : n ≤ m) (k : Nat) : k + n ≤ k + m", tags=("nat", "le", "add")),
        _d("Nat.add_le_add_right", "Nat.add_le_add_right {n m : Nat} (h : n ≤ m) (k : Nat) : n + k ≤ m + k", tags=("nat", "le", "add")),
        _d("Nat.mul_le_mul_left", "Nat.mul_le_mul_left (k : Nat) {n m : Nat} (h : n ≤ m) : k * n ≤ k * m", tags=("nat", "le", "mul")),
        _d("Nat.dvd_iff_mod_eq_zero", "Nat.dvd_iff_mod_eq_zero {a b : Nat} : a ∣ b ↔ b % a = 0", tags=("nat", "dvd")),
        _d("Nat.mod_eq_of_lt", "Nat.mod_eq_of_lt {a b : Nat} (h : a < b) : a % b = a", tags=("nat", "mod")),
        _d("Nat.div_mul_le_self", "Nat.div_mul_le_self (m n : Nat) : m / n * n ≤ m", tags=("nat", "div")),
        # List
        _d("List.length_nil", "List.length_nil {α : Type _} : [].length = 0", tags=("list", "length")),
        _d("List.length_cons", "List.length_cons {α : Type _} (a : α) (as : List α) : (a :: as).length = as.length + 1", tags=("list", "length")),
        _d("List.length_append", "List.length_append {α : Type _} (as bs : List α) : (as ++ bs).length = as.length + bs.length", tags=("list", "length", "append")),
        _d("List.length_map", "List.length_map {α β : Type _} (f : α → β) (l : List α) : (l.map f).length = l.length", tags=("list", "map")),
        _d("List.length_reverse", "List.length_reverse {α : Type _} (l : List α) : l.reverse.length = l.length", tags=("list", "reverse")),
        _d("List.length_replicate", "List.length_replicate {α : Type _} (n : Nat) (a : α) : (List.replicate n a).length = n", tags=("list", "replicate")),
        _d("List.append_nil", "List.append_nil {α : Type _} (as : List α) : as ++ [] = as", tags=("list", "append")),
        _d("List.nil_append", "List.nil_append {α : Type _} (as : List α) : [] ++ as = as", tags=("list", "append")),
        _d("List.append_assoc", "List.append_assoc {α : Type _} (as bs cs : List α) : as ++ bs ++ cs = as ++ (bs ++ cs)", tags=("list", "append")),
        _d("List.reverse_reverse", "List.reverse_reverse {α : Type _} (as : List α) : as.reverse.reverse = as", tags=("list", "reverse")),
        _d("List.reverse_append", "List.reverse_append {α : Type _} (as bs : List α) : (as ++ bs).reverse = bs.reverse ++ as.reverse", tags=("list", "reverse")),
        _d("List.map_nil", "List.map_nil {α β : Type _} (f : α → β) : [].map f = []", tags=("list", "map")),
        _d("List.map_cons", "List.map_cons {α β : Type _} (f : α → β) (a : α) (as : List α) : (a :: as).map f = f a :: as.map f", tags=("list", "map")),
        _d("List.map_append", "List.map_append {α β : Type _} (f : α → β) (l₁ l₂ : List α) : (l₁ ++ l₂).map f = l₁.map f ++ l₂.map f", tags=("list", "map")),
        _d("List.mem_cons_self", "List.mem_cons_self {α : Type _} (a : α) (as : List α) : a ∈ a :: as", tags=("list", "mem")),
        _d("List.mem_cons", "List.mem_cons {α : Type _} {a b : α} {l : List α} : a ∈ b :: l ↔ a = b ∨ a ∈ l", tags=("list", "mem")),
        _d("List.mem_append", "List.mem_append {α : Type _} {a : α} {s t : List α} : a ∈ s ++ t ↔ a ∈ s ∨ a ∈ t", tags=("list", "mem")),
        # Logic
        _d("And.intro", "And.intro {a b : Prop} (left : a) (right : b) : a ∧ b", kind="def", tags=("logic", "and")),
        _d("And.left", "And.left {a b : Prop} (h : a ∧ b) : a", tags=("logic", "and")),
        _d("And.right", "And.right {a b : Prop} (h : a ∧ b) : b", tags=("logic", "and")),
        _d("And.comm", "And.comm {a b : Prop} : a ∧ b ↔ b ∧ a", tags=("logic", "and")),
        _d("Or.inl", "Or.inl {a b : Prop} (h : a) : a ∨ b", kind="def", tags=("logic", "or")),
        _d("Or.inr", "Or.inr {a b : Prop} (h : b) : a ∨ b", kind="def", tags=("logic", "or")),
        _d("Or.comm", "Or.comm {a b : Prop} : a ∨ b ↔ b ∨ a", tags=("logic", "or")),
        _d("Iff.intro", "Iff.intro {a b : Prop} (mp : a → b) (mpr : b → a) : a ↔ b", kind="def", tags=("logic", "iff")),
        _d("Iff.mp", "Iff.mp {a b : Prop} (h : a ↔ b) : a → b", tags=("logic", "iff")),
        _d("Iff.mpr", "Iff.mpr {a b : Prop} (h : a ↔ b) : b → a", tags=("logic", "iff")),
        _d("Iff.symm", "Iff.symm {a b : Prop} (h : a ↔ b) : b ↔ a", tags=("logic", "iff")),
        _d("Not.intro", "Not.intro {a : Prop} (h : a → False) : ¬a", kind="def", tags=("logic", "not")),
        _d("Exists.intro", "Exists.intro {α : Sort _} {p : α → Prop} (w : α) (h : p w) : ∃ x, p x", kind="def", tags=("logic", "exists")),
        # Int / order — Mathlib
        _d("sq_nonneg", "sq_nonneg {α : Type _} [LinearOrderedRing α] (x : α) : 0 ≤ x ^ 2", requires_mathlib=True, tags=("algebra", "sq"), source_file="Mathlib.Algebra.Order.Ring.Basic"),
        _d("Int.mul_pos", "Int.mul_pos {a b : ℤ} (ha : 0 < a) (hb : 0 < b) : 0 < a * b", requires_mathlib=True, tags=("int", "mul"), source_file="Mathlib.Data.Int.Order.Basic"),
        _d("Int.sq_nonneg", "Int.sq_nonneg (n : ℤ) : 0 ≤ n * n", requires_mathlib=True, tags=("int", "sq")),
        _d("mul_le_mul_of_nonneg_left", "mul_le_mul_of_nonneg_left {α} [MulLeftMono α] {a b c : α} (h : b ≤ c) (a0 : 0 ≤ a) : a * b ≤ a * c", requires_mathlib=True, tags=("algebra", "le")),
        _d("add_le_add", "add_le_add {α} [AddLeftMono α] [AddRightMono α] {a b c d : α} : a ≤ b → c ≤ d → a + c ≤ b + d", requires_mathlib=True, tags=("algebra", "le")),
        _d("le_add_of_nonneg_right", "le_add_of_nonneg_right {α} [AddRightMono α] [AddZeroClass α] {a b : α} (hb : 0 ≤ b) : a ≤ a + b", requires_mathlib=True, tags=("algebra", "le")),
        _d("div_le_iff₀", "div_le_iff₀ {α} [GroupWithZero α] [MulLeftMono α] {a : α} (hb : 0 < b) {c : α} : a / b ≤ c ↔ a ≤ c * b", requires_mathlib=True, tags=("algebra", "div")),
        # Set / combinatorics — Mathlib (Erdős-adjacent)
        _d("Set.mem_setOf", "Set.mem_setOf {α : Type _} {p : α → Prop} {a : α} : a ∈ {x | p x} ↔ p a", requires_mathlib=True, tags=("set"), source_file="Mathlib.Data.Set.Basic"),
        _d("Set.subset_def", "Set.subset_def {α : Type _} {s t : Set α} : s ⊆ t ↔ ∀ x, x ∈ s → x ∈ t", requires_mathlib=True, tags=("set")),
        _d("Set.Subset.trans", "Set.Subset.trans {α} {a b c : Set α} : a ⊆ b → b ⊆ c → a ⊆ c", requires_mathlib=True, tags=("set")),
        _d("Set.Finite.subset", "Set.Finite.subset {α} {s t : Set α} (ht : t.Finite) (h : s ⊆ t) : s.Finite", requires_mathlib=True, tags=("set", "finite")),
        _d("Set.Infinite.mono", "Set.Infinite.mono {α} {s t : Set α} (h : s ⊆ t) : s.Infinite → t.Infinite", requires_mathlib=True, tags=("set", "infinite")),
        _d("Nat.not_dvd_of_pos_of_lt", "Nat.not_dvd_of_pos_of_lt {a b : Nat} (h1 : 0 < b) (h2 : b < a) : ¬ a ∣ b", tags=("nat", "dvd")),
        _d("Nat.le_of_dvd", "Nat.le_of_dvd {m n : Nat} (h : 0 < n) : m ∣ n → m ≤ n", tags=("nat", "dvd", "le")),
    ]
