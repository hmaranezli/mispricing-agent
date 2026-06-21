# Phase 6.2 — Gate A Predecessor Option-Sum Targeted Correction Charter

> **This is a docs-only targeted correction charter.** It corrects **only** the predecessor-optionality
> contradiction in the Gate A field-shape charter (`5dc757c`) — it does **NOT** redesign or reopen the rest of Gate
> A. It **implements nothing and authorizes nothing executable**: no runtime code, no tests, no test execution, no
> lock-test edits, no frozen-component edits, no Phase 6.1 edits, no S1-adapter edits, no encoding/digest decisions,
> no loader, no writer, no predicate, no state machine, no container runtime, no Phase 6.2 runtime, no pytest, no
> graphify. It **edits no previous charter file**; it corrects `5dc757c` **only** through the exact clause-by-clause
> supersession map in §2. It makes **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate
> to `docs/handoff/phase6_2_shadow_intent_definition_artifact_field_shape_charter.md`,
> `docs/handoff/phase6_2_source_authority_determinism_targeted_amendment_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_source_boundary_charter.md`, the earlier Phase 6.2
> charters, the S1 durable-storage charters, and `CLAUDE.md`; where any conflict arises, those govern **except** for
> the narrow, explicitly-mapped clause supersessions in §2.

**Base:** `5dc757cfdec364df4f6fed947d0f2611af28abaa`

---

## 1. Base / Purpose

**Base commit:** `5dc757cfdec364df4f6fed947d0f2611af28abaa`.

Gate A (`5dc757c`) pinned the artifact envelope as having **"exactly these five fields and no extras"** (§3 line 78),
**including** `predecessor_artifact_version_reference` as field 4 — yet simultaneously described that field as
**"optional"** and **"structurally absent for the first lineage member"** (§3 field 4, §3a, §11, conclusion), and
counted **"four opaque references"** (§4). These are **contradictory**: a field that can be *structurally absent*
cannot coexist with a *fixed five-field arity*, and the reference count is wrong because the predecessor field does
**not** always carry an opaque reference.

This charter repairs **only** that contradiction: the envelope **always** has exactly five fields (the predecessor
field is **always structurally present**), and its **value** is a **closed option-sum** (`NoPredecessor |
PredecessorReference`) — never an omission, null, or sentinel. The reference-count language is corrected accordingly.
**Every other Gate A decision is preserved unchanged** (§9).

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Evidence-First Supersession Map (the affected clauses, quoted)

All affected clauses were located and quoted **unambiguously**; the §2 STOP condition is **not** triggered. This
charter supersedes **only** the rows below.

| `5dc757c` § | Exact quoted clause | Precise replacement |
|---|---|---|
| §3, field 4 | "**`predecessor_artifact_version_reference`** — **optional** opaque reference to **exactly one** predecessor artifact version; **structurally absent** for the first lineage member (see §3a — modeled by an explicit present/absent variant, never `null`/sentinel)." | "`predecessor_artifact_version_reference` — **always structurally present** (field 4 of an invariant five-field envelope); its **value** is exactly one closed `PredecessorArtifactVersionOption` variant (`NoPredecessor` \| `PredecessorReference`, §4). It is **never** omitted, null, or sentinel." |
| §3a (whole section) | "`predecessor_artifact_version_reference` is modeled as an explicit **present-with-one-opaque-reference OR structurally-absent** option … The first lineage member structurally carries no predecessor; later members carry exactly one opaque predecessor reference." | The field is **always present**; the **first lineage member** carries the **`NoPredecessor`** variant (zero payload fields), **later members** carry the **`PredecessorReference`** variant (exactly one `opaque_reference`). "Structurally-absent" is withdrawn — absence is modeled by the **`NoPredecessor` variant value**, not by field omission (§4, §5). |
| §3, "all four references" | "**No runtime-generated UUID … may populate any reference.** All **four** references are **caller-supplied and stable**." | The **three** directly-reference-carrying envelope fields (`artifact_field_shape_version_reference`, `artifact_version_reference`, `declarer_opaque_reference`) are caller-supplied and stable; the **predecessor field carries an option value** whose `PredecessorReference` variant carries **one** caller-supplied, stable `opaque_reference`. The no-runtime-generated rule applies to **every** carried opaque reference (§6). |
| §4, "four opaque references" | "The **four** opaque references (`artifact_field_shape_version_reference`, `artifact_version_reference`, `declarer_opaque_reference`, `predecessor_artifact_version_reference`) obey:" | "Three envelope fields **directly carry** opaque references … and the predecessor field carries an **option value** (`NoPredecessor` → no reference; `PredecessorReference` → one `opaque_reference`). Every **carried** opaque reference obeys the discipline below." (§6) |
| §11, predecessor validation | "**predecessor optionality** (present-with-one OR structurally-absent, §3a)" | "**predecessor field always present**; its value is **exactly one** closed option variant — `NoPredecessor` (zero payload fields) **or** `PredecessorReference` (exactly one `opaque_reference`); unknown variants or extra fields invalid (§7)." |
| §11, "the four references" | "**opaque-reference types** (the **four** references, by type only — never by content, §4)" | "**opaque-reference types** — the **three** direct envelope references plus, when the predecessor value is `PredecessorReference`, its single inner `opaque_reference` — checked by **type only**, never by content (§6, §7)." |
| Conclusion | "**methodless envelope** carries **exactly five** fields — … **optional** `predecessor_artifact_version_reference` (structurally present-one-or-absent, never null/sentinel)" | "**methodless envelope** carries **exactly five** fields, **always** — … `predecessor_artifact_version_reference` **always present**, valued by the closed `NoPredecessor \| PredecessorReference` option-sum (never omission/null/sentinel)." |

**Affirmed (NOT superseded):** `5dc757c` §3 line 78 "**exactly these five fields and no extras**" is **correct and
reaffirmed** — the five-field arity is invariant; only the *false "can be absent" gloss* on field 4 is removed.

---

## 3. Preserved Exact Five-Field Envelope (binding)

The artifact envelope **always** has exactly these five logical fields, in every artifact, for every lineage member:

1. `artifact_field_shape_version_reference`
2. `artifact_version_reference`
3. `declarer_opaque_reference`
4. `predecessor_artifact_version_reference`
5. `definitions_by_silver_pair`

**The predecessor field (4) is ALWAYS structurally present. The envelope never changes between four and five
fields.** Arity is fixed at five.

---

## 4. Closed Predecessor Option-Sum Type (binding)

The **logical type** of `predecessor_artifact_version_reference` is pinned as exactly:

```
PredecessorArtifactVersionOption =
    NoPredecessor
  | PredecessorReference
```

**Exact variants (closed — no third variant):**

- **A. `NoPredecessor`** — **zero payload fields**; used **only** for the **first lineage member**.
- **B. `PredecessorReference`** — **exactly one payload field**: `opaque_reference`. `opaque_reference` is
  **caller-supplied, stable**, and subject to the existing opaque-reference discipline (`5dc757c` §4, as corrected
  in §6).

The field's *value* is always exactly one of these two closed variants; the field itself is never missing.

---

## 5. Null / Sentinel / Omission Prohibition (binding)

The predecessor field **MUST NOT** be represented logically by any of:

- field omission; `null` / `None`; empty string; `false` / `true`; zero; the strings `"NONE"`, `"ROOT"`, or **any**
  string sentinel; a fabricated default; a runtime-generated UUID; or a self-reference.

**`NoPredecessor` is a real, closed logical variant — NOT a sentinel value.** "No predecessor" is expressed by the
*variant*, never by a magic value or a missing field.

---

## 6. Reference-Discipline Correction (binding)

Correcting the prior "four opaque references" language:

- **Three envelope fields ALWAYS directly carry opaque references:** `artifact_field_shape_version_reference`,
  `artifact_version_reference`, `declarer_opaque_reference`.
- **`predecessor_artifact_version_reference` ALWAYS carries an OPTION value:** `NoPredecessor` carries **no** opaque
  reference; `PredecessorReference` carries **exactly one** `opaque_reference`.

**All carried opaque references** (the three direct ones plus, when present, the `PredecessorReference.
opaque_reference`) remain: **caller-supplied; stable; semantically uninterpreted** (never parsed/ranked/normalized/
content-scanned, `5dc757c` §4); **never** an intent / Silver / ordering / actionability identity; and **never**
runtime-generated. The no-secret / no-PII producer-responsibility rule (`5dc757c` §4) is unchanged.

---

## 7. Pre-Flight Validation Correction (binding)

Future Gate A artifact-only validation must require:

- **exact five-field envelope, always;**
- **predecessor field present, always;**
- predecessor **value is exactly one closed option variant** (`NoPredecessor` or `PredecessorReference`);
- **`NoPredecessor` has zero payload fields;**
- **`PredecessorReference` has exactly one `opaque_reference`;**
- **unknown variants or extra fields are invalid** (closed-world).

**No S1 access occurs during this validation** (artifact-only, `5dc757c` §11 unchanged in that respect).

---

## 8. Gate B Separation (binding)

- **Do NOT** define a physical discriminator field; **do NOT** define JSON tags, bytes, field order, null encoding,
  variant encoding, canonical sorting, digest, checksum, or signature.
- **Gate B** may later define a **physical canonical discriminator** for the two logical variants **without** adding
  a new domain field to Gate A (the discriminator is an encoding artifact, not a sixth envelope field or a third
  predecessor field).
- This correction **must not** preselect a runtime implementation technique or language construct (no tagged-class,
  enum, `Optional[...]`, union-library, or serialization choice is implied — only the **closed logical option-sum**
  is pinned).

---

## 9. Preserved Remainder of Gate A (affirmed, unchanged)

All other `5dc757c` decisions remain **unchanged**:

- the `OpaqueSilverPairKey` mapping (two opaque text scalars, verbatim, exact opaque equality);
- the **unordered, immutable, finite** logical `definitions_by_silver_pair` map;
- **0..1** definition cardinality per Silver pair (duplicates structurally invalid; no merge/first/last-wins);
- the **closed `DirectionalShadowIntentDefinition` / `InertShadowIntentDefinition`** variants;
- the **three-member orientation vocabulary** (`POSITIVE_EXPOSURE` / `NEGATIVE_EXPOSURE` / `INERT_STATE`);
- **exact-decimal** `passive_boundary_magnitude` semantics (no binary float/NaN/inf/rounding/locale/sign-derived);
- **unit exact-equality** for `boundary_unit_context` vs `score_unit_context` (no normalization);
- **exact non-negative integer-ms** `hypothetical_window_duration_ms` (bool excluded; inequality deferred);
- **`INERT_STATE` structural boundary/unit absence** (variant structure, not null/sentinel);
- **artifact-only pre-flight** (never touches S1);
- the **encounter-time SCORE / HALT cross-input contract** (qualifying SCORE eligible; unit mismatch = passive
  no-op; HALT/non-SCORE/missing/malformed on a targeted pair = hard fail-fast; no S4 fallback / no mutation / no
  synthetic);
- **dormant definitions** (unencountered = valid, no intent, no error, no synthetic anything);
- the **sealing-field prohibition** (no `is_sealed`/digest/checksum/signature/canonical-bytes/validation-status);
- **logical determinism only** (no bit/byte claim);
- **anti-actionability and quarantine**;
- **all Gate B deferrals**.

Only the predecessor-optionality clauses of §2 are corrected; nothing else is reopened or redesigned.

---

## 10. Precise Post-Correction State (ratified)

- **Gate A predecessor contradiction: CLOSED** (every affected clause mapped in §2).
- **Gate A field shape: PINNED + CORRECTED** (docs-only).
- **Gate B** becomes eligible as the next separately-authorized design gate (§11).
- **Phase 6.2: UNBUILT and NOT runtime-ready.** **No runtime TDD becomes eligible.**
- **Phase 6.1:** frozen, **COMPLETE + RATIFIED**.
- **Capacity:** deferred at exactly **0 emit sites**.
- **Production / live / paper / canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (unchanged):** at most one terminal per intent; open frozen non-terminal state at replay EOF
  is valid audit state.

---

## 11. Next Safe Gate

- **Gate B — Phase 6.2 Shadow Intent Definition Artifact Canonical-Encoding & Digest Charter** (docs-only): durable
  format, canonical byte representation, ordering / normalization rules, content digest, artifact-reference
  verification, **and** the physical canonical discriminator for the two predecessor-option variants — **no runtime
  implementation**.
- **This charter does NOT open, draft, or perform Gate B.** **No runtime TDD becomes eligible from Gate A (as
  corrected) alone.**

**Conclusion:** the Gate A predecessor-optionality contradiction is **resolved** through a targeted, quote-anchored
supersession map (§2) and nothing else. The artifact envelope **always** has **exactly five** logical fields, with
`predecessor_artifact_version_reference` **always structurally present** (the envelope never varies between four and
five fields). Its **value** is a **closed option-sum** `PredecessorArtifactVersionOption = NoPredecessor |
PredecessorReference` — `NoPredecessor` (zero payload fields, first lineage member) or `PredecessorReference`
(exactly one caller-supplied, stable `opaque_reference`); **no third variant**, and **never** field omission / null /
empty-string / boolean / zero / `"NONE"` / `"ROOT"` / any sentinel / fabricated default / runtime UUID /
self-reference (`NoPredecessor` is a **real closed variant**, not a sentinel). The reference count is corrected to
**three** envelope fields that **directly** carry opaque references plus the predecessor field's **option value**
(zero or one inner `opaque_reference`); all carried references stay caller-supplied, stable, semantically
uninterpreted, non-identity/order/actionability, and never runtime-generated. Pre-flight requires the **always-five**
envelope, the **always-present** predecessor field, exactly **one** closed option variant with the correct payload
arity, and rejects unknown variants/extra fields — **without touching S1**. Gate B (not this charter) will define
the **physical canonical discriminator** for the two variants **without** adding any Gate A domain field, and no
runtime construct is preselected here. **All other Gate A decisions are preserved unchanged** (§9). **Capacity stays
deferred at 0 emit sites; Phase 6.1 stays frozen, COMPLETE + RATIFIED.** The contradiction is **CLOSED**; **Phase 6.2
remains UNBUILT and NOT runtime-ready**; the **only** next safe step is the separately-authorized **Gate B — Phase
6.2 Shadow Intent Definition Artifact Canonical-Encoding & Digest Charter**, **not opened here**. **No executable
work is authorized.**
