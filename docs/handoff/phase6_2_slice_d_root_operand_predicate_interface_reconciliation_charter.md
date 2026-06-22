# Phase 6.2 — Slice-D Root-Operand Predicate-Interface Reconciliation Charter

> **This is a docs-only interface-reconciliation charter.** It resolves the sealed Slice-A root-evidence vs sealed
> Slice-D predicate-operand incompatibility by **reopening exactly two** Slice-D public predicate interfaces and
> pinning their corrected **asymmetric** shapes. It **implements nothing and authorizes nothing executable**: no
> runtime code, no tests, no fixtures, no `atomic_replay_step.py`, no `reconstruction.py`, no lock edits, no
> prior-charter edits, no generated files, no pytest, no graphify, and no commit beyond this single docs file. It
> does **not** amend, rebase, delete, or rewrite history. It authorizes **no** runtime implementation; the Slice-D
> runtime correction is a separate, later, human-authorized TDD task. It is subordinate to the full Phase 6.2 chain —
> the planning / atomicity / precedence / duplicate-root / lifecycle / multi-event / Gate A/B charters, the sealed
> Slice-A lifecycle-slot / dual-snapshot chain (`85de568`→`38eccce`→`9fc7749`→`01331ec`, runtime `2f2990a`), the
> Slice-C `s1_evidence_projection.py` and Slice-D `classification_predicates.py` runtimes, the Slice-E exact-shape
> charter chain (`85d1ba6`→`ff92ad0`→`90bb5d3`), and `CLAUDE.md` — and where any conflict arises, those govern
> **except** for the two interface corrections this charter is expressly authorized to ratify (§3–§6).

**Base:** `90bb5d3878e682c02261b5eaa7a1623b4eb8477c`

---

## 1. Base / Purpose

**Base commit:** `90bb5d3878e682c02261b5eaa7a1623b4eb8477c`.

The Slice-E pre-flight implementation gate proved a **ratified-chain technical contradiction**: the sealed Slice-D
predicates `context_equals` and `classify_timestamp_window` require the **root** comparison operand to be a Slice-C
projection carrier (`ScoreContextProjection` / `ScoreTimestampProjection`), but the sealed Slice-A lifecycle slot
stores the established root as **Slice-A** carriers (`EstablishedRootContext` + `provenance_anchor_timestamp_text:
str`), and `logical_model` is the import **leaf** that can never hold Slice-C carriers, while Slice-C carriers are
**factory-only** (built only from a real `sqlite3.Row`, never synthesizable from stored scalars, and never from the
unavailable root row). The root operand therefore can never be presented to those two predicates without a forbidden
fabricated row, inverse hydration, registry, or duplicated logic.

This charter resolves the contradiction by making the two predicates **asymmetric**: the **root** operand becomes the
exact Slice-A carrier the slot actually stores, while the **observed** operand remains the exact Slice-C projection
of the current row. **Slice E remains BLOCKED**; this charter authorizes no runtime implementation.

**No capacity validation and no capacity pass is claimed by this charter.**

---

## 2. Quote-Anchored Supersession Map (binding)

The two old **symmetric** (Slice-C-root) interfaces are **superseded and invalid**.

| Sealed `classification_predicates.py` site | Old symmetric interface (superseded) | New asymmetric interface (this charter) |
|---|---|---|
| `def context_equals(*, root_context, observed_context)` (line 209), `_require_carrier(root_context, ScoreContextProjection)` (line 212) | `context_equals(*, root_context: ScoreContextProjection, observed_context: ScoreContextProjection) -> bool` | `context_equals(*, root_context: EstablishedRootContext, observed_context: ScoreContextProjection) -> bool` (§4) |
| `def classify_timestamp_window(*, anchor, comparison, duration_ms)` (line 231), `_require_carrier(anchor, ScoreTimestampProjection)` (line 237), `anchor_text = _require_canonical_timestamp(_slot(anchor, "provenance_timestamp"))` (line 239) | `classify_timestamp_window(*, anchor: ScoreTimestampProjection, comparison: ScoreTimestampProjection, duration_ms: int)` | `classify_timestamp_window(*, anchor: str, comparison: ScoreTimestampProjection, duration_ms: int)` (§5) |

**No overload, union, compatibility branch, optional operand, alternate callable, adapter, synthetic row, registry,
cache, or second execution path is legal.** Each predicate has exactly one signature and one execution path; the old
symmetric calls must be **rejected**, not accepted via a fallback.

---

## 3. Strict Replacement — Exact New Signatures (binding)

```python
context_equals(
    *,
    root_context: EstablishedRootContext,
    observed_context: ScoreContextProjection,
) -> bool

classify_timestamp_window(
    *,
    anchor: str,
    comparison: ScoreTimestampProjection,
    duration_ms: int,
)
```

- `EstablishedRootContext` is the Slice-A carrier (`logical_model`); `ScoreContextProjection` /
  `ScoreTimestampProjection` are the Slice-C carriers (`s1_evidence_projection`). Slice D already imports both
  modules, so the new root-operand types introduce **no** new dependency edge and **no** leaf violation
  (`logical_model` stays the leaf; Slice D depends on Slice A and Slice C, never the reverse).
- The corrected `classify_timestamp_window` retains its existing return domain
  (`WINDOW_NON_COMPARABLE` / `WINDOW_IN_WINDOW` / `WINDOW_EXPIRED`).

---

## 4. Context Contract (binding)

- `root_context` must be an **exact `EstablishedRootContext`** from Slice A (consumer-boundary check
  `type(root_context) is EstablishedRootContext`, else `PREDICATE_WRONG_CARRIER_TYPE`).
- `observed_context` must remain an **exact `ScoreContextProjection`** from Slice C (unchanged full consumer-boundary
  forgery/text validation, including its `score_inputs_summary` exact-tuple/arity-2/non-blank revalidation).
- **Fully revalidate the root** at the Slice-D consumer boundary: populated **and** missing-slot `object.__new__`
  forgeries of `EstablishedRootContext`, and both exact-`str` non-blank fields `source_venue_context_text` and
  `source_pair_context_text` (read through the missing-slot-safe `_slot` helper; malformed/blank →
  `PREDICATE_INVALID_TEXT`).
- **Blank semantics are exactly Python `str.strip()`** (Slice-A `9fc7749`): a scalar is blank **iff**
  `value.strip() == ""`; **`U+200B` is accepted** (non-blank) exactly as Slice A pins it; empty / ASCII whitespace /
  NBSP / EM SPACE / IDEOGRAPHIC SPACE are blank and rejected. No broader Unicode/zero-width category is consulted.
- **Comparison is byte-for-byte and position-for-position:** `root_context.source_venue_context_text` vs
  `observed_context.score_inputs_summary[0]`, and `root_context.source_pair_context_text` vs
  `observed_context.score_inputs_summary[1]` — exact `str` equality, **no normalization, trim, coercion, case
  folding, tuple synthesis, or Slice-C carrier construction.**
- Returns `True` iff both positional scalar pairs are byte-exact equal, else `False`.

---

## 5. Timestamp Contract (binding)

- `anchor` must be an **exact `str`** holding the Slice-A `provenance_anchor_timestamp_text`. It is validated against
  the **exact ASCII grammar `"0" | [1-9][0-9]*`** — **no** `int()`, `Decimal`, `float`, Unicode decimal digits,
  sign, fraction, exponent, whitespace, or leading zero — purely lexically (malformed → the existing
  `PREDICATE_INVALID_CANONICAL_TIMESTAMP`). This matches the established `_require_canonical_timestamp` ASCII-digit
  semantics, now applied to a **bare `str`** rather than a `ScoreTimestampProjection` slot.
- `comparison` remains an **exact `ScoreTimestampProjection`** from Slice C with full consumer-boundary forgery
  validation (exact carrier type; populated/missing-slot; its `provenance_timestamp` revalidated as canonical
  timestamp text → `PREDICATE_INVALID_CANONICAL_TIMESTAMP`).
- `duration_ms` retains the exact contract: an exact `int`, **non-`bool`**, within `[0, 2^63-1]` (else
  `PREDICATE_INVALID_DURATION`).
- **Lexical arithmetic is preserved** (length-then-lexicographic compare; exact digit addition; no `int()` on
  timestamp text), and the existing truth table is preserved **unchanged**:
  `delta < 0 → WINDOW_NON_COMPARABLE`; `0 ≤ delta ≤ duration → WINDOW_IN_WINDOW`; `delta > duration → WINDOW_EXPIRED`
  — including arbitrarily long (≥ 5000-digit) timestamps and the **inclusive** `delta == duration → WINDOW_IN_WINDOW`
  boundary.

---

## 6. Deterministic Validation / Error Precedence (binding)

For each predicate the fixed order is:

1. **Validate the root / anchor operand** (`EstablishedRootContext` for context; the bare canonical-`str` `anchor`
   for timestamp) — including forgery/missing-slot/text/grammar.
2. **Validate the observed Slice-C carrier and the reached field** (`ScoreContextProjection.score_inputs_summary` /
   `ScoreTimestampProjection.provenance_timestamp`) with the existing full forgery/text validation.
3. **Validate `duration_ms`** (timestamp classification only).
4. **Perform the equality / lexical arithmetic.**

The first failing step determines the reason; the order is deterministic and independent of iteration.

### 6.1 Closed `ClassificationPredicateError` reason mappings (existing vocabulary, unchanged)

| Failure | Reason |
|---|---|
| wrong exact operand type (root `EstablishedRootContext`, observed `ScoreContextProjection`/`ScoreTimestampProjection`) | `PREDICATE_WRONG_CARRIER_TYPE` |
| missing root or observed slot (`object.__new__` forgery) | `PREDICATE_FORGED_OR_MISSING_SLOT` |
| malformed / blank context scalar (root field or observed summary element) | `PREDICATE_INVALID_TEXT` |
| malformed anchor `str` or comparison `provenance_timestamp` | `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| invalid `duration_ms` (non-int, bool, out of `[0, 2^63-1]`) | `PREDICATE_INVALID_DURATION` |

**No raw `AttributeError`, `TypeError`, `ValueError`, or foreign exception may escape for contract-invalid
operands;** `BaseException` / `MemoryError` / `KeyboardInterrupt` / `SystemExit` / `GeneratorExit` / unrelated faults
are **never** broadly caught. (No new reason constant is introduced; the five existing constants suffice.)

---

## 7. No-Bridge / No-Invention Seal (binding)

- The private Slice-C makers `_make_score_context` and `_make_score_timestamp` **remain private**. **Slice E must not
  import or call them.** **No public bridge maker is created.**
- **No fabricated replay row, inverse hydration, carrier conversion, Slice-A→Slice-C up-conversion, slot-shape
  change, registry, cache, or duplicated predicate/arithmetic logic is permitted** anywhere.
- The reconciliation is **purely** the asymmetric operand-type correction of §3–§5: the root operand becomes the
  Slice-A carrier the slot already stores; nothing is synthesized.

---

## 8. Legal / Illegal Operand Matrices (binding)

### 8.1 `context_equals`

| `root_context` | `observed_context` | Outcome |
|---|---|---|
| exact `EstablishedRootContext`, both non-blank scalars | exact `ScoreContextProjection`, valid summary | ✅ `bool` (byte/position-exact) |
| `ScoreContextProjection` (old symmetric root) | any | ❌ `PREDICATE_WRONG_CARRIER_TYPE` |
| any non-`EstablishedRootContext` (str/tuple/None) | any | ❌ `PREDICATE_WRONG_CARRIER_TYPE` |
| forged `EstablishedRootContext` missing a scalar slot | any | ❌ `PREDICATE_FORGED_OR_MISSING_SLOT` |
| `EstablishedRootContext` with blank/`""`/whitespace scalar | any | ❌ `PREDICATE_INVALID_TEXT` |
| `EstablishedRootContext` with `U+200B` scalar | valid observed | ✅ accepted (non-blank), byte-exact compared |
| valid root | non-`ScoreContextProjection` / forged / blank-summary observed | ❌ `PREDICATE_WRONG_CARRIER_TYPE` / `PREDICATE_FORGED_OR_MISSING_SLOT` / `PREDICATE_INVALID_TEXT` |

### 8.2 `classify_timestamp_window`

| `anchor` | `comparison` | `duration_ms` | Outcome |
|---|---|---|---|
| exact canonical `str` (`"0"`/`[1-9][0-9]*`) | exact `ScoreTimestampProjection`, canonical | exact int in range | ✅ `WINDOW_*` |
| `ScoreTimestampProjection` (old symmetric anchor) | any | any | ❌ `PREDICATE_WRONG_CARRIER_TYPE` |
| non-`str` anchor (int/None/Decimal) | any | any | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| anchor `"00"`/`"-1"`/`"1.0"`/`"1e3"`/`" 1"`/Unicode-digit/`""` | any | any | ❌ `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| valid anchor | non-`ScoreTimestampProjection` / forged / non-canonical `provenance_timestamp` | valid | ❌ `PREDICATE_WRONG_CARRIER_TYPE` / `PREDICATE_FORGED_OR_MISSING_SLOT` / `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| valid anchor | valid comparison | non-int / bool / out-of-range | ❌ `PREDICATE_INVALID_DURATION` |

## 9. Complete Populated / Missing-Slot Forgery Matrix (binding)

| Forgery | Predicate | Reason |
|---|---|---|
| `object.__new__(EstablishedRootContext)`, no slots | `context_equals` root | `PREDICATE_FORGED_OR_MISSING_SLOT` |
| `EstablishedRootContext` venue set, pair slot missing | `context_equals` root | `PREDICATE_FORGED_OR_MISSING_SLOT` |
| `EstablishedRootContext` populated with blank/non-str scalar | `context_equals` root | `PREDICATE_INVALID_TEXT` |
| `object.__new__(ScoreContextProjection)`, no slot | `context_equals` observed | `PREDICATE_FORGED_OR_MISSING_SLOT` |
| `ScoreContextProjection` populated with non-2-tuple / blank element | `context_equals` observed | `PREDICATE_INVALID_TEXT` |
| `object.__new__(ScoreTimestampProjection)`, no slot | `classify_timestamp_window` comparison | `PREDICATE_FORGED_OR_MISSING_SLOT` |
| `ScoreTimestampProjection` populated with non-canonical text | `classify_timestamp_window` comparison | `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |
| bare `anchor` non-canonical/non-str | `classify_timestamp_window` anchor | `PREDICATE_INVALID_CANONICAL_TIMESTAMP` |

---

## 10. Future Targeted Slice-D RED → GREEN Requirements (for the later runtime correction — NOT opened here)

The separately-authorized Slice-D runtime correction must prove, RED→GREEN, editing only
`classification_predicates.py` and `tests/test_phase6_2_classification_predicates.py`:

1. **Old symmetric calls are rejected:** `context_equals(root_context=<ScoreContextProjection>, …)` →
   `PREDICATE_WRONG_CARRIER_TYPE`; `classify_timestamp_window(anchor=<ScoreTimestampProjection>, …)` →
   `PREDICATE_WRONG_CARRIER_TYPE`.
2. **Only the new asymmetric contracts succeed:** `context_equals(root_context=<EstablishedRootContext>,
   observed_context=<ScoreContextProjection>)`; `classify_timestamp_window(anchor=<canonical str>,
   comparison=<ScoreTimestampProjection>, duration_ms=<int>)`.
3. **Full root forgery matrix** (§9); the §8 operand matrices; the §6 precedence; the five error mappings.
4. **Preserved behavior:** byte/position-exact context equality incl. `U+200B`; the NON_COMPARABLE / IN_WINDOW /
   EXPIRED truth table incl. ≥5000-digit timestamps and inclusive `delta == duration`; lexical arithmetic; no `int()`.
5. **Static AST requirements:** in the corrected predicates — **no** import or call of `_make_score_context` /
   `_make_score_timestamp` (or any Slice-C maker); **no** fabricated replay row; **no** overload/union/second path;
   **no** duplicated comparison/arithmetic logic (the existing single lexical-arithmetic helpers are reused, not
   re-coded); and the new root operand types resolve to `EstablishedRootContext` (Slice A) / bare `str`.

All other Slice-D tests/behaviors stay unchanged.

---

## 11. Preserved Unchanged (affirmed)

- **All other Slice-D predicate APIs and behavior**: `silver_pair_intersects`, `unit_comparable`,
  `classify_directional_crossing`, and the `classify_timestamp_window` return domain / lexical arithmetic.
- **Strict field independence and non-inspection**: each predicate inspects only its own narrow inputs; none invokes
  another as a hidden prerequisite.
- **Exact Silver-pair, unit, magnitude, orientation, Unicode-decimal (Phase-5 magnitude lexis), crossing, and
  timestamp-arithmetic contracts** are untouched (the timestamp **anchor source type** is the only timestamp change).
- **Slice-A `logical_model` leaf direction** (stdlib-only; no Phase-6.2 sibling imports) and the Slice-C factory-only
  carrier discipline.
- **All Slice-E API / result / error / lookup / duplicate / atomicity charters through `90bb5d3`** (the Slice-E
  signature, `AtomicReplayStepResult`, `AtomicReplayStepError(reason, message)`/`.reason`, the ten-reason vocabulary,
  the single manifest `M[key]` lookup, duplicate semantics, identity/atomicity, exclusions). This charter only fixes
  the Slice-D operand interface that those Slice-E comparisons depend on.

---

## 12. Precise Post-Charter State (ratified)

- **Slice-D runtime is built, but its affected root-operand interface (`context_equals`, `classify_timestamp_window`)
  is hereby REOPENED and pending a separate targeted runtime correction.** The other Slice-D predicates remain
  ratified.
- **Slice E is NOT eligible** until **both** this charter **and** the subsequent Slice-D runtime correction are
  independently reviewed and ratified.
- **Slice F/G remain blocked. Capacity remains 0. Phase 6.2 remains INCOMPLETE and NOT runtime-ready;** execution /
  routing / actionability / live / paper / canary behavior remain **forbidden.** Phase 6.1 frozen, COMPLETE +
  RATIFIED.

---

## 13. Unresolved Items

- **None.** Both operand interfaces are pinned asymmetrically and exactly; the root operand is the Slice-A carrier the
  slot already stores; the observed operand stays Slice-C; the error vocabulary is the existing closed five; no
  bridge, fabricated row, conversion, or duplicated logic is introduced; and the leaf direction is preserved.

**Conclusion:** the sealed Slice-A-root-evidence vs sealed Slice-D-predicate-operand contradiction is resolved
(docs-only) by making exactly two Slice-D predicates **asymmetric** — `context_equals(*, root_context:
EstablishedRootContext, observed_context: ScoreContextProjection) -> bool` and `classify_timestamp_window(*, anchor:
str, comparison: ScoreTimestampProjection, duration_ms: int)` — superseding the invalid symmetric Slice-C-root
interfaces with **no** overload / union / compatibility branch / optional operand / alternate callable / adapter /
synthetic row / registry / cache / second path. The root operand becomes the exact Slice-A carrier the lifecycle slot
already stores (`EstablishedRootContext`; the canonical `provenance_anchor_timestamp_text` as a bare `str` under the
ASCII `"0" | [1-9][0-9]*` grammar with no `int()`), fully revalidated (populated/missing-slot forgeries; exact
non-blank `str` fields under Python `str.strip()` semantics incl. `U+200B` acceptance), while the observed operand
remains the exact Slice-C `ScoreContextProjection` / `ScoreTimestampProjection` with its existing full forgery/text
validation; comparison stays byte/position-exact with no normalization/trim/coercion/case-fold/tuple-synthesis/
carrier-construction, timestamp classification preserves lexical arithmetic and the NON_COMPARABLE / IN_WINDOW /
EXPIRED truth table (≥5000-digit; inclusive `delta == duration`), and the deterministic precedence
(root/anchor → observed → duration → compute) maps failures to the existing closed
`PREDICATE_WRONG_CARRIER_TYPE` / `PREDICATE_FORGED_OR_MISSING_SLOT` / `PREDICATE_INVALID_TEXT` /
`PREDICATE_INVALID_CANONICAL_TIMESTAMP` / `PREDICATE_INVALID_DURATION` with no raw/foreign exception escape and no
broad catch. The private `_make_score_context` / `_make_score_timestamp` stay private and uncalled by Slice E; no
public bridge maker, fabricated row, inverse hydration, carrier conversion, slot-shape change, or duplicated logic is
permitted; all other Slice-D predicates, field independence, the Slice-A leaf direction, and the Slice-E charter
chain through `90bb5d3` are **preserved**. **Slice-D's root-operand interface is reopened pending a separate targeted
runtime correction; Slice E is NOT eligible until this charter and that correction are independently ratified; Slice
F/G blocked; capacity 0; Phase 6.2 INCOMPLETE and NOT runtime-ready. No executable work is authorized.**
