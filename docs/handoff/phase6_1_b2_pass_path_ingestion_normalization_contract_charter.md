# Phase 6.1 — B2 Pass-Path Ingestion-Normalization Contract Charter (Docs-Only BLOCKER)

> **This is a docs-only, evidence-first contract charter that resolves to a BLOCKER.** It attempts to design the
> pass-path ingestion boundary that would transform an Option-B Reader `parsed_payload` into the exact
> `PublicRawSnapshotRecord` required by the frozen B2 replay normalizer — and, on the evidence, **records why the
> required field set cannot be mapped without fabrication and STOPS** (per the request's constraints 3 and 5). It
> **designs and builds nothing**: no runtime, no tests, no adapter, no schema. It authorizes NO runtime code, NO
> tests, NO schema/runtime/interface edits, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 /
> S1 / S5 / lock-tests, NO ingestion adapter, NO S5 runtime, NO storage, NO Cell-3 assembly, NO Phase 6.2 work, NO
> pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_pass_path_edge_contract_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_s5_runner_planning_charter.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `ce78ad8b31c6a782533c552b4812f130a2e2440d`

---

## 1. Base / Purpose

**Base commit:** `ce78ad8b31c6a782533c552b4812f130a2e2440d`.

The pass-path edge charter (`ce78ad8`) classified the missing pass-path work as a **B2/pass-path ingestion-
normalization** contract decision: parsed payload → exact `PublicRawSnapshotRecord`. This charter performs that
decision **evidence-first**, inspecting the exact `PublicRawSnapshotRecord` contract and the exact Option-B payload
field-shape **before** defining any mapping, exactly as constraint 3 requires.

**Verdict (this charter): BLOCKER.** The frozen `PublicRawSnapshotRecord` requires a **14-field** caller contract;
the pinned Option-B payload supplies only a **5-field passive** set and **forbids identity in the payload**. ~9 of
the 14 required fields are **unsourceable** from `parsed_payload` without fabrication, and one (`raw_snapshot_identity`)
is **structurally forbidden** in the payload *and* walled off by Identity Segregation. Per constraints 3 and 5, the
mapping is **not definable**; the missing reconciliation is classified below as **separate, separately-gated**
contract decisions.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Evidence A — the exact `PublicRawSnapshotRecord` caller contract (frozen)

From `phase6_1/b2_normalization_contract.py` :: `make_public_raw_snapshot_record(...)` (lines 309-347) and its
validators, the **14 caller-supplied fields** and their exact rules are:

| # | Field | Exact contract rule (cited) |
|---|-------|-----------------------------|
| 1 | `source_artifact` | exact non-empty `str` (`_require_str`, l.334) |
| 2 | `source_field` | exact non-empty `str` (l.335) |
| 3 | `venue` | exact non-empty `str` (l.336) |
| 4 | `pair` | exact non-empty `str` (l.337) |
| 5 | `base_asset` | exact non-empty `str`; **"never split, projected, or computed here"** (l.327-328, 338) |
| 6 | `quote_asset` | exact non-empty `str` (l.339) |
| 7 | `instrument_id` | exact non-empty `str` (l.340) |
| 8 | `venue_scope` | exact non-empty `str` (l.341) |
| 9 | `venue_buy` | exact non-empty `str` (l.342) |
| 10 | `venue_sell` | exact non-empty `str` (l.343) |
| 11 | `retrieval_epoch_ms` | exact **non-negative `int`** — the system freeze time (`_require_non_negative_int`, l.344) |
| 12 | `observed_at_epoch_ms` | **canonical unsigned-int `str`** — source-observed market time (`_require_canonical_unsigned_int_str`, l.345) |
| 13 | `raw_snapshot_identity` | exact non-empty `str` (l.346) |
| 14 | `field_payload` | **tuple-only** (`_require_tuple_only`, l.347); each entry a tuple of labeled `(label, value)` str pairs carrying required labels `normalized_field_name`/`source_field`/`binding_role`/`magnitude`/`unit`, `binding_role ∈ {GROSS_EDGE, COST}` (l.231), values exact non-empty `str` (`b2_replay_normalization.py:30-92`) |

**Cross-field anti-copy lock (l.353-357):** `observed_at_epoch_ms` **must not equal** `str(retrieval_epoch_ms)` —
the source-observed market time and the retrieval/freeze time are **distinct, independently-supplied** timestamps.
`retrieval_epoch_ms` therefore **cannot** be derived from `observed_at_epoch_ms`.

`cost_validity_contexts` is **NOT** a field of `PublicRawSnapshotRecord`; it is a separate B3/Producer argument.
Per constraint 6, because this record type does **not** require a cost slot, **no zero/opaque cost placeholder is
defined here** (Cell-3 remains separately gated and untouched).

---

## 3. Evidence B — the exact Option-B `parsed_payload` field-shape (frozen)

From `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md` §6 (and §4-5, §7), the pinned per-event
payload carries **only** these passive observation facts, and **nothing else**:

- **gross magnitude / value**, **unit**, **venue**, **pair**, **`observed_at_epoch_ms`** (a timestamp, never the
  key).
- An **optional, not-required, not-designed** future strictly-passive cost-context shape (the minimal payload needs
  no cost field).

And it **explicitly forbids** (binding):

- **Any identity field in the payload** (§4 medium-vs-payload separation; §5 forbids `…_id`/`record_id`/`uuid`/
  `hash`/`fingerprint`/`sequence_number`/etc. and any identity/uniqueness-implying key).
- All actionability/intent/policy content (§7 tombstone ban).

So the payload's sourceable set is: **venue, pair, observed_at_epoch_ms, gross magnitude, unit** — five passive
facts, with **identity deliberately absent**.

---

## 4. Field-by-Field Reconciliation (the mismatch)

Mapping `parsed_payload` → the 14-field `PublicRawSnapshotRecord`:

| Required field | Sourceable from Option-B payload? | Note |
|----------------|-----------------------------------|------|
| `venue` | ✅ yes (verbatim str) | payload §6 |
| `pair` | ✅ yes (verbatim str) | payload §6 |
| `observed_at_epoch_ms` | ✅ yes (str; if carried as a JSON number, an explicit **number→string** conversion §5a) | payload §6 |
| `field_payload` (magnitude/unit **values**) | ⚠️ values yes, but the required **B2 labels/roles** (`binding_role=GROSS_EDGE`, `normalized_field_name`, `source_field`) are **not** in the payload | labeling = normalization (forbidden) |
| `source_artifact` | ❌ **no** — not in payload | unsourceable |
| `source_field` | ❌ **no** — not in payload | unsourceable |
| `base_asset` | ❌ **no** — not in payload; splitting `pair` is **contract-forbidden** (l.327-328) and is semantic repair | unsourceable |
| `quote_asset` | ❌ **no** — same as above | unsourceable |
| `instrument_id` | ❌ **no** — not in payload | unsourceable |
| `venue_scope` | ❌ **no** — not in payload | unsourceable |
| `venue_buy` | ❌ **no** — not in payload | unsourceable |
| `venue_sell` | ❌ **no** — not in payload | unsourceable |
| `retrieval_epoch_ms` | ❌ **no** — a distinct freeze-time `int`; not in payload; anti-copy lock forbids reusing `observed_at`; reading a clock is forbidden (stateless/deterministic, no fabrication) | unsourceable |
| `raw_snapshot_identity` | ❌ **no** — required str, but identity-in-payload is **forbidden** (§5), and Identity Segregation (constraint 7) forbids pulling it from the S2 medium identity | **doubly blocked** |

**Result: ~9 of 14 required fields are unsourceable**, plus the `field_payload` labels are unsourceable. Constraint
5 forbids fabricating any of them; constraints 4/9 forbid splitting/labeling/semantic-repair to manufacture them.
**The mapping is not definable.**

---

## 5. The Explicit Conversions That WOULD Apply (and why they are insufficient)

For completeness, the Strict Explicit Coercion Protocol that **would** govern the *sourceable* fields (constraint 4)
is recorded — but it cannot rescue the blocker:

### 5a. Permitted explicit structural conversions (only where the frozen contract demands them)
- **`list → tuple`** for `field_payload` and its nested entries: JSON arrays deserialize to Python `list`, but
  `_require_tuple_only` (l.347) demands `tuple`. An explicit, **lossless, recursive** `list→tuple` is the only
  conversion the contract structurally necessitates here.
- **`number → string`** for `observed_at_epoch_ms` **iff** the payload carries it as a JSON integer: the contract
  requires a **canonical unsigned-int string**, and `str(non_negative_int)` is exactly canonical and lossless. (A
  negative or non-integer value is **not** repaired — it fails the frozen validator.)

### 5b. Forbidden everywhere
- **No** hidden coercion, lossy conversion, rounding, unit math, defaulting, semantic repair, `pair` splitting,
  binding-role inference, or clock reads. Where a value's type/shape does not already satisfy the frozen validator,
  the boundary **fails fast** — it never repairs.

### 5c. Why insufficient
These conversions only serve `observed_at_epoch_ms` and the structural form of `field_payload`. They do **nothing**
for the ~9 unsourceable fields (§4). Even a flawless coercion protocol cannot supply a field the payload does not
contain. **The blocker stands.**

---

## 6. Verdict & Classification of the Separate Decisions

**BLOCKER.** The Option-B payload field-shape (5 passive facts, identity forbidden) and the frozen
`PublicRawSnapshotRecord` caller contract (14 fields incl. distinct freeze-time int, full market-identity
decomposition, source provenance, and an identity str) are **structurally mismatched**. Reconciling them is **not**
a thin ingestion adapter and is **not decided here**. The missing work is one or more **separate, separately-gated**
decisions — each of which would itself require its own charter and ratification:

- **(D1) Option-B payload enrichment decision** — whether the Option-B serialization/field-shape contract should be
  (separately, by its own charter) extended to carry the additional **passive provenance** B2 demands
  (source_artifact/source_field, base/quote/instrument/venue_scope/venue_buy/venue_sell, a distinct retrieval/freeze
  epoch) **only if** each is a genuine raw passive fact of the source — never fabricated. *(The Option-B charter is
  frozen here; this is not authorized.)*
- **(D2) B2 raw-snapshot ingestion-shape decision** — whether a B2-side raw-snapshot contract appropriate to the
  Option-B passive payload is warranted. *(B2 is frozen here; not authorized.)*
- **(D3) Non-payload provenance-supply decision** — where the non-payload required fields (a freeze-time
  `retrieval_epoch_ms`, market-identity decomposition, source provenance, and `raw_snapshot_identity`) legitimately
  originate **without fabrication** and **without breaching Identity Segregation** (constraint 7) — noting that
  `raw_snapshot_identity` is directly in tension with the Option-B identity-in-payload ban and the S2 medium-identity
  wall.

This charter **selects none** of D1/D2/D3 and **authorizes none**. It records the mismatch and STOPS.

---

## 7. Binding Seals

- **Existing Boundary Seal.** The Reader, B2 (`b2_normalization_contract` / `b2_replay_normalization`),
  `PublicRawSnapshotRecord`, B3, Producer, Phase 5, B4, S4, S1, and the S5 docs remain **absolutely FROZEN**. This
  charter proposes **no** interface change, widened accept, relaxed validator, refactor, or behavior edit to any of
  them. The fix is a **new, separately-ratified** decision (§6), never a loosening of a frozen component.
- **Strict Explicit Coercion Protocol.** Recorded in §5a (only `list→tuple` and non-negative `int→str` where the
  frozen contract demands), with **no** hidden/lossy/rounding/unit-math/defaulting/semantic-repair coercion (§5b).
- **No-Fabrication.** Missing/unknown payload fields are **never** invented. A future runtime that cannot map a
  required field under the ratified contract must produce a **local structural ingestion halt** or **stop/report a
  blocker** — never a fabricated value (§4, constraint 5).
- **Identity Segregation.** Any future ingestion boundary processes **payload only**; `S2IdentityWiringCandidate`
  **bypasses it completely**. The boundary must **not** consume, inspect, copy, route, mint, hash, collapse, derive,
  stringify, or fall back on identity — and specifically may **not** source `raw_snapshot_identity` from the medium
  identity.
- **No Runner Smuggling.** The S5 runner must **not** implement this transformation internally. A future S5 may only
  **invoke** a separately-ratified ingestion boundary. Until such a boundary is **runtime-built and ratified**, **S5
  runtime TDD remains ineligible**.
- **No Business Logic.** Any future ingestion boundary must **not** compute edge, score, ranking, actionability,
  routing, readiness, execution intent, venue decision, or threshold. It is structural field mapping only.
- **No Partial Runner.** A halt-only/partial S5 runtime stays **unauthorized**; **both** pass and halt paths must be
  contract-complete first. The pass path is **not** contract-complete (this blocker), so S5 runtime stays ineligible.

---

## 8. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 9. Precise State

- This charter **does not** make the pass path contract-complete, **does not** authorize S5 runtime, **does not**
  make a B2 ingestion runtime TDD slice eligible, **does not** complete Phase 6.1, and **does not** ready Phase 6.2.
- It may make a **future, separately-gated** Option-B payload-enrichment / B2 ingestion-shape / provenance-supply
  decision (§6) eligible to be **chartered** — but authorizes **none** here.
- The **S1 durable storage medium** and the **real-cost Cell-3** assembly remain **separately gated** and
  **unbuilt/unbound**; the S1 sink stays a **test-only reference sink**.

---

## 10. Still-Forbidden Work

- **No** ingestion adapter from `parsed_payload` into `PublicRawSnapshotRecord` (the mapping is not definable, §4);
  **no** fabrication/defaulting/semantic-repair/`pair`-splitting/binding-role-inference of any unsourceable field
  (§4-5).
- **No** edit / widen / relax / refactor of the Reader, S2, B2, B3, Producer, Phase 5, B4, S4, S1, S5, or lock-tests
  (§7).
- **No** identity consumption/inspection/derivation/stringify/fallback by any future boundary; **no** sourcing of
  `raw_snapshot_identity` from the medium (§7).
- **No** S5-internal translation; **no** S5 runtime; **no** halt-only / partial runner (§7).
- **No** zero/opaque cost placeholder here (the record needs no cost slot, §2); **no** Cell-3 assembly; **no**
  capacity activation.
- **No** business logic (edge/score/ranking/actionability/routing/readiness/execution/venue-decision/threshold, §7).
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Next Safe Step

- A **separately-authorized docs-only decision** among **§6 D1/D2/D3** — most naturally beginning with whether the
  Option-B serialization payload should carry the additional **passive provenance** B2 requires (D1, as raw passive
  facts only, never fabricated), and/or where a freeze-time `retrieval_epoch_ms` and a non-payload
  `raw_snapshot_identity` legitimately originate (D3) without breaching Identity Segregation. Each is its own
  charter, separately gated.
- Only **after** the payload↔record field set is reconciled by a ratified decision can a **B2 ingestion runtime TDD
  slice** become eligible; only after **that** (and a passive cost-context source for B3/Producer) is the pass path
  contract-complete and an **S5 runtime TDD slice** eligible. The **S1 storage-medium** charter remains
  independently gated.
- **No implementation is authorized by this charter.**

**Conclusion:** evidence-first inspection shows the frozen `make_public_raw_snapshot_record` requires **14**
caller-supplied fields (incl. a distinct non-negative-int `retrieval_epoch_ms`, full market-identity decomposition
`base_asset`/`quote_asset`/`instrument_id`/`venue_scope`/`venue_buy`/`venue_sell`, `source_artifact`/`source_field`,
a `raw_snapshot_identity` str, and a tuple-only labeled `field_payload`), with an **anti-copy lock** keeping
`observed_at_epoch_ms` distinct from `retrieval_epoch_ms`; whereas the pinned Option-B `parsed_payload` carries only
**five** passive facts (gross magnitude, unit, venue, pair, `observed_at_epoch_ms`) and **forbids identity in the
payload**. **~9 of the 14 required fields — plus the `field_payload` B2 labels — are unsourceable** from the payload
without fabrication, and `raw_snapshot_identity` is **doubly blocked** (forbidden in payload **and** walled off by
Identity Segregation). The only explicit conversions the frozen contract would permit (`list→tuple`, non-negative
`int→str` for `observed_at_epoch_ms`) cannot supply absent fields. **Therefore no ingestion mapping is definable;
this charter is a BLOCKER**, classifying the reconciliation as **separate, separately-gated** decisions (Option-B
payload enrichment / B2 ingestion-shape / non-payload provenance-supply), authorizing none. The **Existing Boundary
Seal**, **No-Fabrication**, **Identity Segregation**, **No Runner Smuggling**, **No Business Logic**, and **No
Partial Runner** all hold; existing modules stay **frozen**; **S5 runtime TDD remains ineligible**; Phase 6.1
remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
