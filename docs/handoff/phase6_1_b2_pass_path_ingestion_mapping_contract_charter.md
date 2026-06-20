# Phase 6.1 — B2 Pass-Path Ingestion Mapping Contract Charter

> **This is a docs-only design charter.** It conceptually designs the **standalone pass-path ingestion boundary**
> that consumes one Option-B `parsed_payload` **plus** one ratified `MarketProvenanceContext` and produces the exact
> `PublicRawSnapshotRecord` the frozen B2 replay normalizer requires — **without implementing it**. It **designs and
> builds nothing**: no runtime, no tests, no adapter, no schema. It authorizes NO runtime code, NO tests, NO schema/
> runtime/interface edits, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 /
> lock-tests, NO S5 runtime, NO storage, NO Cell-3/cost arithmetic, NO Phase 6.2 work, NO pytest, NO graphify. It is
> subordinate to
> `docs/handoff/phase6_1_market_provenance_context_runtime_dto_closeout_ratification.md`,
> `docs/handoff/phase6_1_d3_non_payload_provenance_supply_contract_charter.md`,
> `docs/handoff/phase6_1_b2_pass_path_ingestion_normalization_contract_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`, and `CLAUDE.md`; where any conflict arises,
> those govern.

**Base:** `75f53a4631809b6c1cb1a713556554d0cf35eddf`

---

## 1. Base / Purpose

**Base commit:** `75f53a4631809b6c1cb1a713556554d0cf35eddf`.

With the `MarketProvenanceContext` DTO now **BUILT + RATIFIED** (`52f21af`/`75f53a4`), this charter designs the
**standalone mapping boundary** that, given (payload + provenance), assembles the 14 caller arguments of the frozen
`make_public_raw_snapshot_record`. It defines the **explicit field mapping**, the **precision-safe string-carriage
rule**, and the **GROSS_EDGE labeling rule** — and it **honestly marks the one residual unresolved label-source** as
a blocker rather than fabricating it.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Frozen Boundary Seal

The Option-B payload shape, `MarketProvenanceContext`, `PublicRawSnapshotRecord`, the B2 normalizer
(`b2_normalization_contract` / `b2_replay_normalization`), B3, Producer, Phase 5, B4, S4, S1, and S5 docs remain
**absolutely FROZEN**. This charter proposes **no** interface change, widened accept, relaxed validator, refactor,
or behavior edit to any of them. The ingestion boundary is a **new, separate, downstream** mapping client that feeds
the existing frozen constructor **as-is** — every value it supplies is already a legal
`make_public_raw_snapshot_record` argument.

---

## 3. The Standalone Ingestion Boundary (concept only)

- Conceptually, the boundary is a **pure, stateless, deterministic mapping** from **two inputs** — one Option-B
  `parsed_payload` and one ratified `MarketProvenanceContext` — to **one** `PublicRawSnapshotRecord` (constructed via
  the frozen `make_public_raw_snapshot_record`).
- It is **standalone**, **not** S5 orchestration (§8): **no** loop, stream iteration, routing, retry, repair, EOF
  handling, cursor/checkpoint, storage, or pipeline trigger. One payload + one provenance ⇒ at most one record (or a
  structural ingestion halt / blocker if a required source is absent).
- It performs **no** business logic, numeric math, semantic repair, or identity handling beyond the explicit
  structural mapping defined below.

---

## 4. The 14-Field Mapping (every `make_public_raw_snapshot_record` caller argument)

Sources: **P** = Option-B `parsed_payload` (frozen §6 fields: gross magnitude, unit, venue, pair,
`observed_at_epoch_ms`); **E** = ratified `MarketProvenanceContext` (ten fields). No other source is permitted; no
fabrication.

| # | Caller argument | Source | Rule |
|---|-----------------|--------|------|
| 1 | `source_artifact` | **E** | `E.source_artifact`, verbatim str |
| 2 | `source_field` (record-level) | **E** | `E.source_field`, verbatim str |
| 3 | `venue` | **P** | `P.venue`, verbatim str |
| 4 | `pair` | **P** | `P.pair`, verbatim str |
| 5 | `base_asset` | **E** | `E.base_asset`, verbatim str — **not** parsed from `pair` (§9) |
| 6 | `quote_asset` | **E** | `E.quote_asset`, verbatim str — **not** parsed from `pair` (§9) |
| 7 | `instrument_id` | **E** | `E.instrument_id`, verbatim str |
| 8 | `venue_scope` | **E** | `E.venue_scope`, verbatim str |
| 9 | `venue_buy` | **E** | `E.venue_buy`, verbatim str |
| 10 | `venue_sell` | **E** | `E.venue_sell`, verbatim str |
| 11 | `retrieval_epoch_ms` | **E** | `E.retrieval_epoch_ms`, exact non-negative int, verbatim — **not** copied from `observed_at` (§9) |
| 12 | `observed_at_epoch_ms` | **P** | `P.observed_at_epoch_ms` → canonical unsigned-int str under the precision-safe rule §5 |
| 13 | `raw_snapshot_identity` | **E** | `E.raw_snapshot_identity`, verbatim str — Market Identity only, never S2 (§7) |
| 14 | `field_payload` | **P values + structural** | one GROSS_EDGE binding (§5–§6); **two binding labels residual-blocked** (§6) |

**Resolved: 13 of 14 caller arguments** (1–13) are fully mapped from {P, E} with **zero fabrication**. **Field 14**
is mapped **except** for two GROSS_EDGE binding labels (§6).

---

## 5. Precision-Safe String Carriage (binding)

The B2 contract carries magnitudes and `observed_at_epoch_ms` as **exact strings** (verbatim; no numeric parsing).
The boundary therefore performs **no** numeric math — **no** float, `Decimal`, rounding, scaling, arithmetic,
precision-changing reserialization, unit conversion, or business calculation. Two explicit, structural rules:

### 5a. Gross magnitude (and unit) — string-only, verbatim
- `P.gross_magnitude` and `P.unit` MUST arrive in `parsed_payload` as **exact non-empty `str`** and are carried
  **verbatim** into the GROSS_EDGE binding's `magnitude` / `unit` labels.
- **If the magnitude is not a `str`** (e.g. a JSON number that the frozen reader's `json.loads` already turned into a
  `float`/`int`), the boundary **MUST NOT** convert it: a decimal magnitude as a JSON number is **already
  float-parsed (lossy) at the medium**, and losslessness **cannot be guaranteed**. Per constraint 4, this is a
  **structural ingestion halt / blocker** — the boundary imports no `float`/`Decimal` and never coerces a numeric
  magnitude. (A lossless magnitude requires the artifact to author it as a JSON string.)

### 5b. `observed_at_epoch_ms` — verbatim str, or the single lossless integer carriage
- If `P.observed_at_epoch_ms` arrives as an **exact non-empty `str`**, it is carried **verbatim** (the frozen B2
  validator enforces canonical unsigned-int form and rejects non-canonical — the boundary never repairs).
- The **only** permitted numeric→string carriage is `non-negative int → canonical str`, applied **only** to
  `observed_at_epoch_ms` when it arrives as a **non-negative JSON `int`**: `str(non_negative_int)` is provably
  **lossless and canonical**. A **`float`** or any non-(`str`|non-negative-`int`) value ⇒ **structural halt** (a
  float epoch cannot be a canonical unsigned int; the boundary does no float handling).
- This integer carriage is **not** extended to the gross magnitude (§5a), which is decimal-bearing and string-only.

**Anti-copy.** `observed_at_epoch_ms` (P, #12) and `retrieval_epoch_ms` (E, #11) are sourced **independently**; the
boundary never copies one from the other. The frozen B2 anti-copy lock (`observed != str(retrieval)`) is enforced by
B2, never repaired here.

---

## 6. GROSS_EDGE Labeling & the Residual Label-Source Blocker (binding)

`field_payload` is **one** binding entry — a GROSS_EDGE binding — built as a tuple of `(label, value)` pairs. The B2
field-entry requires the labels `normalized_field_name`, `source_field`, `binding_role`, `magnitude`, `unit`
(`b2_replay_normalization.py:30-32`), with optional `zero_cost_evidence`. Their resolution:

- **`magnitude`** ← `P.gross_magnitude` (verbatim str, §5a). **Resolved.**
- **`unit`** ← `P.unit` (verbatim str). **Resolved.**
- **`binding_role`** ← the **structural constant** `"GROSS_EDGE"` (the existing B2 vocabulary applied structurally,
  constraint 5). It is **not** evaluated, thresholded, ranked, scored, classified, or derived from the magnitude.
  **Resolved.**
- **`zero_cost_evidence`** ← **absent / `None`** — the frozen contract requires a GROSS_EDGE binding to carry `None`
  here (`b2_normalization_contract.py:259-261`); the label is simply omitted. **Resolved** (no COST evidence, §6a).
- **`normalized_field_name`** ← **UNRESOLVED.** It is a required non-empty label that is **not** in `P` (payload §6
  carries no binding label) and **not** in the ratified ten-field `E` (the DTO field-shape charter §10 explicitly
  **deferred** binding-label sourcing to this ingestion decision). It must **not** be fabricated or inferred
  (constraints 3, 9).
- **`source_field` (binding-level)** ← **UNRESOLVED.** This is the binding's *raw source field* — **distinct** from
  the record-level `source_field` (#2). It is genuine source provenance, **not** in `P` and **not** in `E`, and it
  **must not** be inferred or reused from #2 (constraint 9 forbids inferring source fields). **Blocker.**

### 6a. COST / Cell-3 deferral
- `field_payload` contains **only** the single GROSS_EDGE binding. **No COST entry is built.** B3 requires exactly
  one GROSS_EDGE binding (it reads that binding's magnitude/unit); COST economics enter downstream via the
  Producer/B3 `cost_validity_contexts` argument, which is **not** a `PublicRawSnapshotRecord` field. **No** passive
  empty/opaque COST placeholder is defined here, and **no** cost/fee/Cell-3 arithmetic is implemented or invented.
  **COST remains separately gated.**

### 6b. Residual decision (separate, separately-gated)
Because **two GROSS_EDGE binding labels** (`normalized_field_name`, binding-level `source_field`) are **not
sourceable** from {payload, ratified `MarketProvenanceContext`} without fabrication/inference, the **label-source
rules are NOT fully resolved.** A **separate, separately-gated** decision is required: whether these labels are
(i) **ratifiable structural constants** of the single gross-edge binding (defensible for `normalized_field_name` as
a fixed structural name; **weak** for a *source_field* that is genuine provenance), or (ii) **additional supplied
provenance** — which would require a separately-chartered extension of `MarketProvenanceContext` or a distinct
passive binding-label provenance contract (the DTO is **frozen** here, §2). **This charter selects neither and
authorizes neither.**

---

## 7. Identity Segregation (binding)

`S2IdentityWiringCandidate` **completely bypasses** this ingestion mapping. The boundary **MUST NOT** import,
inspect, copy, derive, hash, stringify, collapse, route, or fall back to S2 identity, and carries **no** Silver
tuple. `raw_snapshot_identity` (#13) comes **only** from `MarketProvenanceContext` — Market Identity on a plane
strictly separate from S2 System/Silver Identity.

---

## 8. No Runner Smuggling (binding)

This boundary is a **standalone mapping contract**, **not** S5 orchestration. It contains **no** loop, stream
iteration, routing, retry, repair, EOF/exhaustion handling, cursor/checkpoint, storage, or pipeline trigger. A
future S5 may only **invoke** this boundary on one (payload, provenance) pair; the runner does **not** implement the
mapping internally.

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 10. No Semantic Repair (binding)

- **No** parsing `pair` into `base_asset`/`quote_asset` (#5/#6 from E); **no** canonicalizing `venue`; **no**
  inferring source fields (record-level or binding-level); **no** defaulting `UNKNOWN`/empty/synthetic values; **no**
  copying `retrieval_epoch_ms` from `observed_at_epoch_ms`. Any required source absent from {P, E} ⇒ **structural
  ingestion halt / blocker**, never a fabricated value.
- The only permitted structural conversions are §5b's lossless `non-negative int → canonical str` for
  `observed_at_epoch_ms`, and (when assembling `field_payload`) direct tuple construction of the binding entry from
  scalar values plus the `GROSS_EDGE` structural constant (with `list→tuple` applying only if a source value were
  itself a JSON array — the minimal gross binding uses scalars, so none is needed).

---

## 11. Still-Forbidden Work

- **No** edit / widen / relax / refactor of any frozen module (§2); **no** boundary-as-S5; **no** loop/stream/
  routing/retry/repair/EOF/cursor/storage/trigger (§8).
- **No** numeric math / float / Decimal / rounding / scaling / unit conversion / precision-changing reserialization
  (§5); **no** lossy magnitude coercion — string-only, halt otherwise (§5a).
- **No** fabrication/inference of `normalized_field_name` or binding-level `source_field`; **no** reuse of
  record-level `source_field` for the binding (§6, §10).
- **No** COST entry, passive cost placeholder, cost/fee math, or Cell-3 assembly (§6a); **no** capacity activation.
- **No** S2 identity import/inspect/derive/hash/stringify/collapse/fallback; **no** Silver tuple (§7).
- **No** `pair`-splitting, venue canonicalization, source-field inference, `UNKNOWN`/default/synthetic value, or
  `retrieval`←`observed` copy (§10).
- **No** evaluation/threshold/rank/score/classification/actionability from the magnitude (§6, constraint 5).
- **No** runtime/tests/schema/storage; **no** S5 runtime; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 12. Precise State

- **13 of 14** caller arguments are fully and explicitly mapped from {payload, ratified `MarketProvenanceContext`}
  with zero fabrication; the **precision-safe string-carriage rule is fully defined** (§5).
- **The label-source rules are NOT fully resolved**: the GROSS_EDGE binding's `normalized_field_name` and
  binding-level `source_field` remain a **residual blocker** (§6b). **Per constraint 10, a B2 ingestion runtime TDD
  slice is therefore NOT yet eligible** — it becomes eligible **only after** the §6b residual is resolved by a
  separate ratified decision.
- This charter **does not** authorize S5 runtime, Cell-3, or storage; **does not** complete the pass path; **does
  not** complete Phase 6.1; **does not** ready Phase 6.2. The halt path stays complete; the S1 sink stays a
  **test-only reference sink**.

---

## 13. Next Safe Step

- A **separately-authorized docs-only decision charter resolving §6b** — deciding whether the GROSS_EDGE binding's
  `normalized_field_name` and `source_field` are (i) ratified **structural constants** of the gross-edge binding, or
  (ii) **supplied provenance** via a separately-chartered `MarketProvenanceContext` extension / distinct binding-label
  provenance contract (DTO frozen here). Only after that resolves are the label-source rules complete.
- **Then** a **separately-authorized B2 ingestion runtime TDD slice** implementing this mapping (precision-safe
  string carriage; structural-halt on any missing field; no fabrication; no S2 identity; no runner logic).
- Independently: the **passive cost-context (Cell-3)** source for B3/Producer; the **S1 storage-medium** charter.
- Only after **both** the pass path (ingestion + label-source + cost-context) **and** the halt path are
  contract-complete does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** the standalone B2 pass-path ingestion boundary is designed as a **pure, stateless mapping** from one
Option-B `parsed_payload` **plus** one ratified `MarketProvenanceContext` to one exact `PublicRawSnapshotRecord` via
the frozen `make_public_raw_snapshot_record`, with **13 of 14** caller arguments fully mapped from {P, E} with **zero
fabrication** (venue/pair/observed_at from P; the ten provenance fields from E; record-level identity/provenance from
E). **Precision-safe string carriage** is fully defined: gross magnitude/unit are **string-only verbatim** (numeric
magnitude ⇒ structural halt, no float/Decimal), and `observed_at_epoch_ms` is verbatim str or the **single lossless**
`non-negative int → canonical str` carriage (float ⇒ halt). The `field_payload` is **one GROSS_EDGE binding** with
`magnitude`/`unit` from P, `binding_role="GROSS_EDGE"` as a structural constant, and `zero_cost_evidence` absent/None
per the frozen GROSS_EDGE rule; **no COST entry** is built (COST/Cell-3 separately gated, no placeholder invented).
**Identity Segregation** (S2 bypasses entirely; `raw_snapshot_identity` from E only), **No Runner Smuggling**
(standalone mapping, no loop/stream/routing/retry/EOF/cursor/storage), and **No Semantic Repair** (no `pair`-split,
no venue canonicalization, no source-field inference, no defaults, no `retrieval`←`observed` copy) all hold. **One
residual blocker stands**: the GROSS_EDGE binding's `normalized_field_name` and binding-level `source_field` are
**not sourceable** from {payload, ratified DTO} and **must not be fabricated** — so **the label-source rules are not
fully resolved and a B2 ingestion runtime TDD slice is NOT yet eligible** (constraint 10). Existing modules remain
**frozen**; this authorizes **no** runtime; the pass path is **not** contract-complete; **S5 runtime remains
ineligible**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
