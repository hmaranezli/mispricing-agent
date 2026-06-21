# Phase 6.2 — Duplicate-Root Guard, Root Non-Establishment & Context-First Precedence Micro-Correction Charter

> **This is a docs-only targeted micro-amendment charter.** It corrects **only** the remaining precedence and
> root-establishment contradictions in the predicate precedence chain (`f57d116`, `d7204d6`) — it does **NOT**
> redesign the predicate model. It **implements nothing and authorizes nothing executable**: no runtime code, no
> tests, no DTO, no loader, no state machine, no Phase 6.1 edits, no S1-adapter edits, no Gate A/B edits, no
> frozen-component edits, no prior-charter file edits, no Phase 6.2 runtime, no pytest, no graphify. It corrects
> prior charters **only** through the exact supersession map in §3. It makes **no** Phase 6.2 runtime/paper/live/
> production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_predicate_precedence_decimal_evidence_consistency_targeted_correction_charter.md`,
> `docs/handoff/phase6_2_evidence_intersection_classification_predicate_charter.md`, the Gate A/B charters
> (`5dc757c`, `1071067`, `474cc6f`), the source-boundary + amendment charters (`07135be`, `abd1b41`), the lifecycle
> charters (`e9995e7`, `999a109`), the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises,
> those govern **except** for the narrow, explicitly-mapped supersessions in §3.

**Base:** `f57d11623fa1160623b6a5f5432354e966d2aec6`

---

## 1. Base / Purpose

**Base commit:** `f57d11623fa1160623b6a5f5432354e966d2aec6`.

`f57d116` corrected the unit/expiry precedence and the decimal/timestamp/duplicate contracts, but left two ordering
defects: (1) its `a→j` per-record ordering places **absorbing-terminal self-loops, family validation, and kind
classification before the duplicate-root integrity guard**, so a terminal state could **absorb/hide** a duplicate-
root failure; and (2) it runs **full SCORE-family consistency before context equality** for every SCORE, so an
**unrelated** SCORE's family defect could **abort independent intent contexts**. Separately, `d7204d6` §4 says a
unit-mismatched directional root "**stays AUDIT_REPLAYED, awaiting a unit-comparable qualifying SCORE**," which
wrongly implies a slot can be re-rooted by a later SCORE. This charter repairs exactly those three points: a
**global duplicate-root guard runs first**, **context-shape precedes family validation**, and a **unit-mismatched
directional root is permanently non-established** (never re-rooted).

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Evidence-First Reaffirmation

- **`append_sequence` is the database primary key.** `phase6_1_s1_storage/s1_durable_sqlite_sink.py` DDL declares
  `append_sequence INTEGER PRIMARY KEY` and **no** `UNIQUE` constraint / index on `(artifact_locator,
  physical_record_position)`. **Duplicate Silver pairs are therefore physically possible** within one stored/replayed
  sequence.
- **A duplicate targeted pair is NOT claimed to prove database or replay corruption.** The durable trail is a valid
  append-only audit log; a recurring Silver pair is a legitimate physical possibility. It is classified **purely as
  a forbidden ambiguous duplicate-root under the Phase 6.2 reconstruction contract** — Phase 6.2 cannot
  deterministically choose which occurrence roots the intent, so it refuses (hard fail-fast), making **no** claim
  about S1 integrity.

---

## 3. Exact Supersession Map (binding)

| Charter / § | Exact quoted clause | Precise replacement |
|---|---|---|
| `f57d116` §4 | the `a→j` per-record ordering (absorbing terminal **a**, then non-SCORE/non-targeted-HALT **b**, then SCORE-family consistency **c**, then context **d** …) | Superseded by the **§5 A→E (with E.1–E.12) ordering**: a **global exact-manifest-target Silver-pair occurrence guard runs FIRST** (before absorbing-terminal self-loops, kind classification, HALT handling, family validation, context, timestamp, unit, magnitude); per-intent evaluation is reordered so **context-shape + equality precede SCORE-family consistency** (§6). |
| `f57d116` §5 | "A qualifying **root or later** SCORE that is **evaluated** must satisfy [full SCORE-family consistency]" applied **before** context equality for every SCORE | Superseded by **context-first** validation (§6): minimal `score_inputs_summary` **shape** validation first; full SCORE-family consistency is enforced **only** for a SCORE that is **context-equal** to ≥1 established intent (or is the first targeted root), **before** timestamp evaluation. |
| `d7204d6` §4 | "the intent stays `AUDIT_REPLAYED`, **awaiting a unit-comparable qualifying SCORE**; not fail-fast, not a halt" | Superseded by **§4 permanent non-establishment**: the first targeted occurrence is the **only** possible root; a unit-mismatched structurally-valid directional root makes the slot **permanently non-established** for the remainder of the replay — it **never awaits or accepts another root SCORE**, captures no context, tracks no later observations, and is validly frozen in `AUDIT_REPLAYED` at EOF. |

All other provisions of `f57d116`, `d7204d6`, and every earlier charter stand intact.

---

## 4. Root Unit-Mismatch Correction (binding)

The first targeted occurrence is the **only possible root occurrence** for that definition in that replay. For a
**structurally valid directional root SCORE with unit inequality** (`score_unit_context` ≠ `boundary_unit_context`):

- **no `INTENT_RECORDED` transition**;
- the slot **remains `AUDIT_REPLAYED`**;
- it becomes **permanently non-established** for the remainder of that replay;
- it **does not capture a comparison context** and **tracks no later observations**;
- **replay EOF leaves it validly frozen in `AUDIT_REPLAYED`** (valid audit state, not an error);
- it **never awaits or accepts another root SCORE**.

A **later occurrence of the targeted pair is a duplicate-root hard fail-fast** (§3 guard / `f57d116` §8) — it does
not "rescue" a non-established slot. **`INERT_STATE` root establishment remains unaffected by unit comparability**
(inert has no boundary/unit; a structurally valid inert root establishes `INTENT_RECORDED`).

---

## 5. Global Root Guard Separated From Per-Intent Predicates (binding)

For each replayed row, the **only** legal high-level sequence is:

- **A. Exact manifest-target Silver-pair occurrence guard** — does the row's exact `(artifact_locator,
  physical_record_position)` equal a sealed-manifest definition key? This is a **replay-step structural-integrity
  guard, not a lifecycle transition**, and runs **before** any absorbing-terminal self-loop, kind classification,
  HALT handling, family validation, context, timestamp, unit, or magnitude step.
- **B. If first targeted occurrence:** perform **root-establishment validation** for that definition (§7).
- **C. If duplicate targeted occurrence** (the exact pair already occurred in this replay): **immediate hard
  fail-fast and stop** — **regardless of SCORE/HALT/other kind and regardless of lifecycle state**. **A terminal
  state MUST NOT hide or absorb a duplicate-root integrity failure.**
- **D. Evaluate the row against previously established intent slots.** The **newly established slot (if B established
  one) MUST NOT evaluate its own root observation** (§8).
- **E. For each previously established slot:**
  1. absorbing terminal → **self-loop**;
  2. row `observation_kind` not `SCORE` → **irrelevant no-op**;
  3. validate `score_inputs_summary` **shape** (§6);
  4. determine **exact context equality**;
  5. context inequality → **irrelevant no-op**;
  6. **only for a context-equal SCORE:** validate **SCORE-family consistency** (§6);
  7. validate **timestamp** and `TIMESTAMP_DELTA`;
  8. `delta < 0` → **passive non-comparability**;
  9. `delta > duration` → **`INTENT_EXPIRED`**;
  10. in-window `INERT_STATE` → **no-op**;
  11. in-window directional **unit inequality** → **no crossing**;
  12. in-window directional **magnitude validation and crossing**.

**No other ordering is legal.** The duplicate-root guard (A/C) is global and strictly precedes all per-slot
evaluation (E).

---

## 6. Context-First Family Validation (binding)

Superseding `f57d116`'s rule that complete SCORE-family consistency runs before context equality for every SCORE:

- **Minimal `score_inputs_summary` structural validation is required first**, because context ownership cannot
  otherwise be classified.
- **Malformed / missing / not-exactly-two-text `score_inputs_summary` while established intents exist remains hard
  fail-fast** (relevance cannot be determined).
- Once context is **structurally valid**:
  - if **no** established intent has exact context equality → the SCORE is an **irrelevant no-op**, and its
    **family / timestamp / unit / magnitude fields are NOT evaluated** (an unrelated SCORE's family defect cannot
    abort an independent intent context);
  - if **one or more** established intents have exact context equality → **enforce the full SCORE-family consistency
    contract** (`f57d116` §5: row/payload `observation_kind == "SCORE"`; row/payload descriptor ==
    `"passive_net_edge_diagnostic"`; exact row↔payload agreement) **before timestamp evaluation**.

This keeps reconstruction **fail-fast where relevance holds** while preventing unrelated defects from aborting
independent contexts.

---

## 7. Targeted-Root Validation (binding)

- A **first targeted occurrence** must undergo the **complete root validation already pinned**: SCORE-family
  consistency, context-shape, timestamp, decimal, and (directional) unit validation (`d7204d6` §4, `f57d116` §5/§6/§7).
- **Targeted HALT / non-SCORE / malformed root remains reconstruction hard fail-fast** (`d7204d6` §4 / `f57d116`
  §9) — no transition, no synthetic terminal.
- **Root unit inequality is the SOLE passive non-establishment case** for a **structurally valid directional root**
  (§4): every other targeted-root defect is hard fail-fast, and a unit-mismatched directional root is the only one
  that passively (non-fail-fast) fails to establish and freezes in `AUDIT_REPLAYED`.

---

## 8. Multi-Intent Observation Rule (binding)

- **One S1 SCORE may simultaneously be** the **first root** for one definition **and** a **later context-comparable
  observation** for previously established intents.
- It may **establish at most its own targeted slot**.
- It **must never evaluate crossing/expiry against the newly established slot on the same replay step** (the root
  observation never transitions its own slot twice — `d7204d6` §7).
- **Updates to other established slots** (context-equal, per §5 E) **remain governed by the corrected per-intent
  precedence** (E.1–E.12), independently of the establishment in B.

---

## 9. Preserve (affirmed)

- **Expiry precedes unit/magnitude** after context and timestamp validity (`f57d116` §4 g before i/j; §5 E.9 before
  E.11/E.12).
- **Separate S1 / Gate B decimal contracts** (`f57d116` §7): S1 magnitude under Phase 5 lexis, boundary under Gate
  B, compared as exact `Decimal`, S1 lexis never Gate-B-normalized.
- **Timestamp authority and row/payload consistency** (`f57d116` §6): `provenance_timestamp` = audited
  `observed_at_epoch_ms`; append order = processing order; payload integer == row decimal text; non-monotonic.
- **`INTENT_RETIRED` reserved / unreachable**; **equality-only fallback unactivated**.
- **No** wall clock, S4 fallback, mutation/write-back, global state/registry/cache/singleton, actionability,
  capacity, or integration. **Capacity stays deferred at exactly 0 emit sites.** Phase 6.1 frozen, COMPLETE +
  RATIFIED. Crossing inequalities (`POSITIVE_EXPOSURE` ≥, `NEGATIVE_EXPOSURE` ≤, `INERT_STATE` none), `delta >
  duration` expiry, negative-delta non-comparability, and the terminal invariant (at most one terminal; open frozen
  at replay EOF valid) all stand.

---

## 10. Next Gate (ratified)

- **`f57d116` alone did NOT make runtime TDD eligible** — the duplicate-root precedence, context-first, and
  root-non-establishment contradictions above had to be corrected first. This charter closes them.
- **After this micro-correction, the next eligible gate is ONLY a separately-authorized docs-only "Phase 6.2
  Reconstruction Runtime TDD Planning & Slice Charter."** **Direct runtime implementation is NOT the immediate
  gate** — a planning/slice charter must precede any code.
- **This charter does NOT open, draft, or perform that planning charter** (or any runtime). **Phase 6.2 remains
  UNBUILT and NOT runtime-ready.** Phase 6.1 frozen, COMPLETE + RATIFIED; capacity deferred (0 emit sites);
  production / live / paper / canary / execution / routing / actionability forbidden.

**Conclusion:** the residual precedence and root-establishment contradictions are corrected through a targeted,
quote-anchored supersession map (§3) and nothing else. A **global exact-manifest-target Silver-pair occurrence
guard** now runs **first** for every replayed row — a **replay-step structural-integrity guard, not a lifecycle
transition** — strictly **before** absorbing-terminal self-loops, kind classification, HALT handling, family
validation, context comparison, timestamp, unit, or magnitude: the **first** targeted occurrence is recorded as the
single root and undergoes root establishment, while a **second** occurrence of the exact targeted pair in the same
replay is an **immediate hard fail-fast regardless of kind or lifecycle state**, and **a terminal state must not
hide or absorb that duplicate-root failure** (whole-replay re-execution in a fresh context remains deterministic/
idempotent; a duplicate is a forbidden ambiguous duplicate-root under the Phase 6.2 contract, **not** a claim of DB/
replay corruption). The **legal per-row sequence** is pinned as **A** target guard → **B** first-occurrence root
establishment → **C** duplicate hard fail-fast → **D** evaluate against previously established slots (the newly
established slot never evaluates its own root) → **E** per-slot precedence (E.1 absorbing self-loop; E.2 non-SCORE
no-op; E.3 context shape; E.4 context equality; E.5 inequality no-op; **E.6 SCORE-family consistency only for
context-equal SCOREs**; E.7 timestamp/`TIMESTAMP_DELTA`; E.8 `delta<0` non-comparability; E.9 `delta>duration`
expiry; E.10 in-window inert no-op; E.11 in-window directional unit≠ no crossing; E.12 in-window directional
magnitude + crossing), **no other ordering legal**. **Context-first family validation** ensures an unrelated SCORE's
family defect never aborts an independent context (minimal context shape first; unrelated context-unequal SCORE is a
no-op without family/timestamp/unit/magnitude evaluation; full family consistency enforced only when context-equal,
before timestamp), while malformed/not-two-scalar context with active intents stays **hard fail-fast**. A
**structurally valid directional root with unit inequality is permanently non-established** (stays `AUDIT_REPLAYED`,
captures no context, tracks nothing, frozen-valid at EOF, never re-rooted) — the **sole** passive non-establishment
case; every other targeted-root defect (HALT/non-SCORE/malformed) is hard fail-fast, and `INERT_STATE` establishment
is unaffected by units. One SCORE may be **both** the first root for its own definition **and** a later
context-comparable observation for other established intents, establishing **at most** its own slot and **never**
evaluating crossing/expiry against that newly established slot on the same step. Expiry-before-unit/magnitude,
separate S1/Gate B decimal contracts, timestamp authority, **reserved-unreachable `INTENT_RETIRED`**, **unactivated
equality-only fallback**, and all no-wall-clock / no-S4 / no-mutation / no-global-state / no-actionability /
no-capacity / no-integration provisions are **preserved**. **`f57d116` alone did not confer runtime eligibility**;
the next eligible gate is **only** a separately-authorized docs-only **"Phase 6.2 Reconstruction Runtime TDD Planning
& Slice Charter"** (not direct runtime implementation), **not opened here**. **Phase 6.2 remains UNBUILT and NOT
runtime-ready. No executable work is authorized.**
