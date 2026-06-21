# Phase 6.2 — Negative-Evidence Case Isolation & Relevance-Harness Micro-Correction Charter

> **This is a docs-only targeted micro-amendment charter.** It corrects **only** case overlap, subvariant closure,
> single-fault isolation, and relevance-scoped poison semantics in the negative-evidence fixture-boundary charter
> (`b4368fd`) — it does **NOT** redesign the fixture architecture. It **implements nothing**: no runtime, no tests,
> no fixture code, no package, no adapter, no database, no Slice A, no pytest, no graphify, no prior-charter file
> edits. It is exactly one docs file and corrects `b4368fd` **only** through the supersession map in §2. It makes
> **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_negative_evidence_fixture_boundary_charter.md`,
> `docs/handoff/phase6_2_reconstruction_runtime_tdd_planning_slice_charter.md`, and the full Phase 6.2 chain, the S1
> durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern **except** for the narrow,
> explicitly-mapped supersessions in §2.

**Base:** `b4368fd72ab2a833cd44d76d420dcd92eb340181`

---

## 1. Base / Purpose

**Base commit:** `b4368fd72ab2a833cd44d76d420dcd92eb340181`.

`b4368fd` authorized the quarantined negative-evidence fixture mechanism but left three defects: (1) Case 7
`INVALID_PROVENANCE_TIMESTAMP` included "**row/payload-inconsistent**," which **overlaps** Case 3
`ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT` (one fixture could belong to two top-level cases); (2) "exactly one invariant
malformed **where practical**" is too loose — an incidental second defect could let a test pass on the **wrong**
rejection branch; and (3) the **universal poison** wording ("HardFailure only … its only valid effect is to be
rejected") wrongly implies a raw negative row must fail in **every** lifecycle/context, contradicting the ratified
relevance-scoped precedence (terminal / non-established / context-unequal / lazy-field evaluation). This charter
fixes exactly those: an **absolute single-fault rule**, **exact non-overlap** (Case 3 owns all timestamp
disagreement; Case 7 stays mutually consistent), **closed subvariants**, and a **harness-scoped (relevance-scoped)
poison invariant**. The fixture architecture is otherwise preserved.

**No capacity validation and no capacity pass is claimed by this charter** (see §15).

---

## 2. Exact Supersession Map (binding)

| `b4368fd` § | Quoted clause | Precise replacement |
|---|---|---|
| §11 | "For each closed case, **exactly one required invariant is malformed where practical**" | **Absolute single-fault rule** (§3): every fixture case **MUST** violate **exactly one** named invariant; every other field/invariant **MUST** remain valid and canonical enough to reach that exact rejection branch; **no incidental second defect**; a test reaching a different/earlier failure does **not** prove the case and **MUST fail**. "Where practical" is removed. |
| §11 | "**`INVALID_PROVENANCE_TIMESTAMP`** (7) is **negative, non-integer, or row/payload-inconsistent** per its selected case" | **Case 7 = consistent invalids only** (§8): exactly `CONSISTENT_NEGATIVE_TIMESTAMP` and `CONSISTENT_NON_INTEGER_TIMESTAMP`; **every row/payload-inconsistent option is REMOVED from Case 7** (it belongs solely to Case 3, §5). |
| §8 / §9 | universal poison: "**expected result is `HardFailure` only**"; "its only valid effect is to be rejected" (read as: a negative row must HardFailure in every possible lifecycle/context) | **Relevance-scoped rejection law** (§10) + **harness-scoped poison invariant** (§12): a raw fixture expects `HardFailure` **only inside an authorized rejection harness** (§11) that makes its named invariant **required**; outside such a harness, relevance-scoped no-op/terminal behavior is valid and **must not** be mislabeled as fixture failure. |
| conclusion | clauses implying "every invalid row necessarily dies unconditionally" / "exactly one … where practical" | re-stated under the absolute single-fault rule, exact non-overlap, and harness-scoped poison (§3, §5, §10–§13). |

All other `b4368fd` provisions (real `sqlite3.Row` representation, tests-only location/import isolation, adapter-only
successful evidence, no production fixture awareness, deferred implementation) stand intact (§15).

---

## 3. Absolute Single-Fault Rule (binding)

Replacing "where practical":

- **Every fixture case MUST violate exactly one named invariant.**
- **Every other field/invariant MUST remain valid and canonical enough to reach that exact rejection branch.**
- **No incidental second defect is permitted.**
- **A test that reaches a different earlier failure does not prove the intended case and MUST fail** (the test
  asserts the **specific** ratified `HardFailure` category, not merely "some failure").

---

## 4. Preserved Seven Top-Level Cases (binding)

Exactly these seven top-level categories, unchanged — **no eighth category**:

1. `ROW_PAYLOAD_OBSERVATION_KIND_DISAGREEMENT`
2. `ROW_PAYLOAD_FAMILY_DESCRIPTOR_DISAGREEMENT`
3. `ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT`
4. `MALFORMED_CANONICAL_JSON`
5. `MALFORMED_SCORE_INPUTS_SUMMARY`
6. `INVALID_S1_DECIMAL_LEXIS`
7. `INVALID_PROVENANCE_TIMESTAMP`

---

## 5. Exact Non-Overlap (binding)

- **Case 3 (`ROW_PAYLOAD_TIMESTAMP_DISAGREEMENT`) owns ALL row/payload timestamp disagreement.**
- **Case 7 (`INVALID_PROVENANCE_TIMESTAMP`) MUST have row and payload mutually consistent.**
- **Every row/payload-inconsistent option is REMOVED from Case 7.**
- **No fixture / subvariant may belong to two top-level cases** (the seven cases are a strict partition of the
  authorized negative space).

---

## 6. Closed Context Subvariants (binding)

`MALFORMED_SCORE_INPUTS_SUMMARY` (Case 5) has **exactly** these closed subvariants, each with **one fixed malformed
shape**:

- `MISSING_SCORE_INPUTS_SUMMARY` — the `score_inputs_summary` key is absent from an otherwise-valid SCORE payload;
- `WRONG_ARITY_SCORE_INPUTS_SUMMARY` — present but a fixed wrong arity (one fixed shape, e.g. a single-element
  list);
- `NON_TEXT_SCORE_INPUTS_SUMMARY_ELEMENT` — present, two elements, but one is a fixed non-text scalar.

**No arbitrary list, callback, payload map, random arity, or caller-selected malformed value.**

---

## 7. Closed Decimal Subvariants (binding)

`INVALID_S1_DECIMAL_LEXIS` (Case 6) has **exactly** these closed subvariants, each using **one fixed internal
invalid string** that violates the Phase 5 S1 lexis `^-?\d+(\.\d+)?$`:

- `LEADING_PLUS_DECIMAL` (e.g. a fixed `"+1"`-form);
- `EXPONENT_DECIMAL` (e.g. a fixed `"1e3"`-form);
- `WHITESPACE_PADDED_DECIMAL` (e.g. a fixed `" 1 "`-form);
- `EMPTY_DECIMAL_TEXT` (the empty string);
- `NON_DECIMAL_TEXT` (a fixed non-numeric token).

**Phase-5-VALID forms MUST NOT be classified invalid:** leading zeros, trailing fractional zeros, and negative zero
are **accepted** by the Phase 5 lexis and are **not** fixtures here. **The caller cannot supply arbitrary decimal
text.**

---

## 8. Closed Timestamp Subvariants (binding)

`INVALID_PROVENANCE_TIMESTAMP` (Case 7) has **exactly**:

- `CONSISTENT_NEGATIVE_TIMESTAMP`;
- `CONSISTENT_NON_INTEGER_TIMESTAMP`.

For **each** subvariant: the **row `provenance_timestamp` and the payload `provenance_timestamp` represent the SAME
invalid value** (the row text is the canonical decimal text of the payload value); **no disagreement exists** (that
is Case 3); and **all other fields are valid**. The fault is solely the value's invalidity (negative / non-integer),
never an inconsistency.

---

## 9. Exact Fixed Constructions (binding)

Deterministic, fixed constructions (no arbitrary malformed payload authoring):

- **observation-kind disagreement (1):** row kind and payload kind are each **individually valid tokens** but
  **unequal**; all score fields otherwise valid.
- **family disagreement (2):** row and payload family descriptors are each **individually valid text** but
  **unequal**; observation kinds and all other fields valid.
- **timestamp disagreement (3):** row and payload timestamps are each **individually valid non-negative integer
  representations** but **unequal**.
- **malformed JSON (4):** one **fixed truncated-object** JSON form for `canonical_text_payload`; row columns
  otherwise valid.
- **context / decimal / timestamp cases (5/6/7):** **only the selected named invariant** (the chosen subvariant) is
  malformed; everything else valid and canonical.

---

## 10. Relevance-Scoped Rejection Law (binding)

Correcting the universal-poison interpretation:

- **A raw negative fixture is NOT inherently required to fail in every lifecycle/context.**
- **Production relevance rules remain authoritative** (`457d279` row-start snapshot / terminal relevance; `f57d116`
  context-first; expiry-before-unit/magnitude).
- **Fields that production correctly does NOT inspect** — for terminal, permanently-non-established, context-unequal,
  expired-before-magnitude, or otherwise irrelevant observations — **MUST remain uninspected.**
- **Negative fixtures MUST NOT be used to force validation of fields outside the ratified precedence** (no fixture
  may "smuggle" an inspection that production legitimately skips).

---

## 11. Authorized Rejection Harnesses (binding)

A negative fixture expects `HardFailure` **only** when used in a harness that makes its named invariant **required**:

- **Slice C direct boundary test:** invoke the **exact** required projection/validation operation for that case (the
  field is directly demanded by the operation under test).
- **Slice E/F targeted-root harness:** the fixture's Silver pair is the **first manifest-target occurrence**,
  forcing **complete root validation** (which demands the named field).
- **Slice E/F later-observation harness:** at least one **row-start slot is established / non-terminal and
  context-equal**, and the timestamp/unit/window preconditions **force evaluation of the selected field**.

Refinements:

- For **`INVALID_S1_DECIMAL_LEXIS`** in a later-observation harness: the intent must be **directional**, **context
  equal**, **timestamp in-window**, and **unit equal** — so that **magnitude validation is actually reached**.
- For **`MALFORMED_SCORE_INPUTS_SUMMARY`**: **at least one established non-terminal slot must require relevance
  classification** (so context is actually parsed).

---

## 12. Harness-Scoped Poison Invariant (binding)

**Only inside an authorized rejection harness** (§11), the fixture's poison invariant holds:

- **expected result is the exact ratified `HardFailure` category**;
- **no** `NextShadowSnapshot`;
- **no** `NextSeenTargetPairs` commit;
- **no** lifecycle transition or partial proposal;
- **no** S4 conversion or successful projection.

**Outside such a harness, relevance-scoped no-op / terminal behavior remains VALID and MUST NOT be mislabeled as
fixture failure** (e.g. a malformed-context fixture against a row whose only established slots are terminal is a
legitimate no-op, not a fixture defect).

---

## 13. Slice C Clarification (binding)

- **Slice C proves the projector rejects a malformed field ONLY when that exact projection/validation operation is
  invoked.**
- **Slice C does NOT override terminal relevance, context relevance, expiry precedence, or lazy field evaluation
  owned by Slice E/F.**
- **Do NOT claim every invalid row necessarily dies unconditionally at Slice C** — the projector inspects a field
  only when that field's projection/validation is actually demanded.

---

## 14. Closed Builder API (binding)

The future helper plans:

- **one top-level case selector** (over the seven cases of §4);
- a **subvariant selector required only for Cases 5, 6, and 7** (the closed subvariants of §6/§7/§8);
- **exact type / membership validation** of the selected case + subvariant;
- **no** omitted / default / random subvariant;
- **no** arbitrary payload / raw SQL / column / value callback.

**Cases 1–4 accept no subvariant** (each is a single fixed construction, §9).

---

## 15. Preserve (affirmed)

- **real `sqlite3.Row` via one parameterized in-memory `SELECT`** (the six aliases; no table; no temp/production DB;
  no `CREATE/INSERT/UPDATE/DELETE/DROP`; no adapter mutation/private-connection access; no monkeypatch / mock /
  **fake**-Row / dict substitution; no private SQL-constant import; no network/persistent state);
- **tests-only location** (`tests/fixtures/phase6_2_negative_evidence_rows.py`) and **import isolation** (production
  never imports tests/fixtures; static import-direction lock);
- **adapter-only successful evidence** (`record_observation` + ratified replay; no hand-rolled successful row);
- **no production fixture awareness** (same production rejection path; no test-only flag/branch/env/alternate
  parser);
- **fixture implementation deferred to Slice C RED**;
- **all Phase 6.2 precedence, atomicity, no-synthetic-success, and scope prohibitions** (no wall clock, S4 fallback,
  mutation, global state, actionability, capacity, integration; capacity deferred at 0 emit sites; Phase 6.1 frozen,
  COMPLETE + RATIFIED).

---

## 16. Status & Next Gate (ratified)

- **`b4368fd`'s fixture architecture is preserved**, but its **overlapping vocabulary** (Case 7 vs Case 3) and
  **universal-poison wording** required correction; this charter supplies the **absolute single-fault rule**,
  **exact non-overlap**, **closed subvariants**, and the **relevance/harness-scoped poison invariant**.
- **The fixture blocker is CLOSED.**
- **The first executable gate is the separately-authorized Slice A — Logical Model TDD** (no S1 dependency, needs no
  fixture). **This charter does NOT implement Slice A.** Fixture implementation remains **deferred to Slice C RED**.
- **Phase 6.2 remains UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0
  emit sites); production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** the negative-evidence fixture vocabulary is corrected to a **strict partition** of seven top-level
cases with an **absolute single-fault rule** (every fixture violates **exactly one** named invariant; all else valid
and canonical enough to reach that exact branch; **no incidental second defect**; a test hitting a different/earlier
failure **must fail**). **Case 3 owns all row/payload timestamp disagreement** and **Case 7 is consistent-invalids
only** (`CONSISTENT_NEGATIVE_TIMESTAMP`, `CONSISTENT_NON_INTEGER_TIMESTAMP` — row and payload represent the same
invalid value, no disagreement, all else valid), with **every row/payload-inconsistent option removed from Case 7**
and **no fixture in two cases**. `MALFORMED_SCORE_INPUTS_SUMMARY` has exactly `MISSING` / `WRONG_ARITY` /
`NON_TEXT_ELEMENT`; `INVALID_S1_DECIMAL_LEXIS` has exactly `LEADING_PLUS` / `EXPONENT` / `WHITESPACE_PADDED` /
`EMPTY` / `NON_DECIMAL` (each a fixed invalid string; Phase-5-valid leading zeros / trailing fractional zeros /
negative zero are **not** invalid; caller supplies no arbitrary text) — all via a **closed case + subvariant
selector** (subvariant required only for Cases 5/6/7; Cases 1–4 take none; no callback/raw-SQL/column/value input).
The **universal poison** wording is replaced by a **relevance-scoped rejection law** + **harness-scoped poison
invariant**: a raw fixture expects the exact `HardFailure` **only inside an authorized harness** (Slice C direct
boundary op; Slice E/F targeted-root forcing full root validation; Slice E/F later-observation with an established
non-terminal context-equal slot whose preconditions force the selected field — decimal needing directional /
context-equal / in-window / unit-equal; context needing an established non-terminal slot that requires relevance);
**outside** such a harness, relevance-scoped no-op/terminal behavior is **valid and not a fixture failure**, and
fixtures **may not force inspection of fields production legitimately skips**. **Slice C** rejects a malformed field
**only when that exact operation is invoked** and **does not** override terminal/context relevance, expiry
precedence, or lazy evaluation owned by Slice E/F. The **real `sqlite3.Row` in-memory representation**, **tests-only
location + import isolation**, **adapter-only successful evidence**, **no production fixture awareness**, **deferred
Slice C RED implementation**, and **all Phase 6.2 precedence / atomicity / no-synthetic-success / scope
prohibitions** are **preserved**. **Blocker: CLOSED.** The **first executable gate is the separately-authorized
Slice A — Logical Model TDD** (not implemented here). **Phase 6.2 remains UNBUILT and NOT runtime-ready. No
executable work is authorized.**
