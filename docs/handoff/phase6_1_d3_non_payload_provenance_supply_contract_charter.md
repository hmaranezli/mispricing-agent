# Phase 6.1 — D3 Non-Payload Provenance-Supply Contract Charter

> **This is a docs-only design charter.** It conceptually defines a **separate non-payload provenance envelope**
> (`MarketProvenanceContext`) that can supply the missing `PublicRawSnapshotRecord` caller fields identified in
> `615329a` — **without changing the Option-B payload (D1 rejected) or B2 (D2 rejected)**. It **designs and builds
> nothing**: no runtime, no tests, no schema, no adapter. It authorizes NO runtime code, NO tests, NO schema/
> runtime/interface edits, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 /
> lock-tests, NO ingestion runtime, NO S5 runtime, NO storage, NO Cell-3 assembly, NO Phase 6.2 work, NO pytest, NO
> graphify. It is subordinate to
> `docs/handoff/phase6_1_b2_pass_path_ingestion_normalization_contract_charter.md`,
> `docs/handoff/phase6_1_pass_path_edge_contract_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `615329a4b9e8f55bedf5e9b97fb7388089739146`

---

## 1. Base / Purpose

**Base commit:** `615329a4b9e8f55bedf5e9b97fb7388089739146`.

The B2 ingestion blocker (`615329a` §6) classified three separate reconciliation options for the
payload↔`PublicRawSnapshotRecord` field mismatch: **D1** (enrich the Option-B payload), **D2** (a new B2 ingestion
shape), **D3** (a non-payload provenance-supply). This charter pursues **D3 only** and **explicitly rejects D1 and
D2** (constraint 2): it changes **nothing** in the Option-B payload, the Option-B serialization charter, the B2
normalizer, the `PublicRawSnapshotRecord` requirements, or any downstream interface. Instead it conceptually defines
a **new passive provenance envelope** that travels **beside** the payload and supplies exactly the fields the
payload cannot — as **supplied raw passive facts, never fabricated**.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Current State

- The frozen pass-path chain (Option-B reader → [missing ingestion] → B2 `PublicRawSnapshotRecord` → B2 normalizer →
  B3 → Producer → `PassiveShadowInput` → B4) is **contract-incomplete** at the ingestion edge (`615329a`).
- The Option-B payload (5 passive facts; identity forbidden) cannot satisfy the 14-field `PublicRawSnapshotRecord`
  caller contract. **This charter designs the conceptual container** that would carry the remaining fields beside the
  payload; it builds nothing and authorizes no runtime.
- All existing modules remain **BUILT/RATIFIED and frozen**. Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. Frozen Core Guarantee (D1 & D2 rejected)

- **No** change to the Option-B reader `parsed_payload` shape or the Option-B serialization/field-shape charter
  (D1 rejected).
- **No** change to the B2 normalizer logic, `make_public_raw_snapshot_record`, `PublicRawSnapshotRecord`
  requirements, the binding contract, or any downstream interface (D2 rejected).
- The fix is **purely additive and external**: a new sibling provenance container that an existing frozen
  constructor can already consume **as-is** (every field it supplies is already a legal `make_public_raw_snapshot_record`
  argument). No frozen validator is relaxed, widened, or edited.

---

## 4. The `MarketProvenanceContext` Envelope (conceptual)

`MarketProvenanceContext` is a **new, passive, immutable metadata container** defined **here at concept level only**
(no runtime class, no schema, no types, no serialization). Binding properties:

- **It is metadata that travels BESIDE the payload**, one provenance context per one Option-B event. It is supplied
  by the same source/capture that produced the event, carried by reference.
- **It is NOT the payload** (it is never serialized into, or read from, the Option-B per-line payload — the payload
  shape stays frozen, §3).
- **It is NOT S2 identity** (it never contains, derives from, or duplicates the Silver tuple
  `(artifact_locator, physical_record_position)` — §6, §7).
- **It is NOT S5 state** (it is not run-state, cursor, offset, checkpoint, or progress) and **NOT durable storage**
  (it is ephemeral, in-memory, per-event; this charter designs no persistence).
- **It carries only supplied raw passive provenance facts** — the non-payload `PublicRawSnapshotRecord` fields, each
  a passive observation of *what the source already is/was*, never a decision, score, route, or actionability.

**Conceptual contents (key-level only; no types/schema):** `source_artifact`, `source_field`, `base_asset`,
`quote_asset`, `instrument_id`, `venue_scope`, `venue_buy`, `venue_sell`, `retrieval_epoch_ms`,
`raw_snapshot_identity`, and the **passive binding labels** for the GROSS_EDGE field-entry (`normalized_field_name`,
`source_field` for the binding, `binding_role`) — see §6 and §8. Nothing else.

---

## 5. Supplied-Not-Generated & Dual-Identity Segregation (binding)

### 5a. Supplied, not generated
- Every provenance field — **including `retrieval_epoch_ms`** — is **supplied by the envelope** as a raw passive
  fact captured at the source/freeze moment and carried beside the event. The future B2 ingestion boundary and the
  S5 runner **MUST NOT** call clocks, read the system time, invent timestamps, default values, emit `UNKNOWN`/
  sentinel placeholders, or synthesize counters/UUIDs/hashes/IDs. They **receive** provenance; they never **make**
  it.

### 5b. Dual-identity strict segregation
- `raw_snapshot_identity` is **Market Identity** — a raw passive fact of the *source market snapshot*, supplied by
  the provenance envelope. It is a **different kind of identity** from S2 Silver/System Identity.
- It **MUST NOT** derive from, inspect, merge with, stringify, hash, collapse, or fall back to
  `S2IdentityWiringCandidate` or the Silver tuple. The two identity planes never touch: Market Identity flows in the
  provenance envelope; System (Silver) Identity flows separately through S2 (§7).
- **If a legitimate market/raw identity (or any required provenance field) is absent** from the envelope, the future
  runtime **MUST** produce a **local structural ingestion halt** or **stop/report a blocker** — it must **never**
  fabricate one or borrow S2 identity (§5a, §7).

---

## 6. Exact 1-to-1 Mapping Obligation (all 14 `PublicRawSnapshotRecord` caller fields)

Each `make_public_raw_snapshot_record` caller field is satisfied by **exactly one** explicit source — the Option-B
**payload** (P) or the **provenance envelope** (E) — with **no fabrication**:

| # | `PublicRawSnapshotRecord` field | Source | Mapping rule (passive, explicit, lossless) |
|---|---------------------------------|--------|---------------------------------------------|
| 1 | `source_artifact` | **E** | supplied passive str, verbatim |
| 2 | `source_field` | **E** | supplied passive str, verbatim |
| 3 | `venue` | **P** | payload venue, verbatim str |
| 4 | `pair` | **P** | payload pair, verbatim str |
| 5 | `base_asset` | **E** | supplied passive str, verbatim — **NOT parsed/inferred from `pair`** (§7) |
| 6 | `quote_asset` | **E** | supplied passive str, verbatim — **NOT parsed/inferred from `pair`** (§7) |
| 7 | `instrument_id` | **E** | supplied passive str, verbatim |
| 8 | `venue_scope` | **E** | supplied passive str, verbatim |
| 9 | `venue_buy` | **E** | supplied passive str, verbatim |
| 10 | `venue_sell` | **E** | supplied passive str, verbatim |
| 11 | `retrieval_epoch_ms` | **E** | supplied passive **non-negative int** (captured at source/freeze; never clock-called at ingestion §5a) |
| 12 | `observed_at_epoch_ms` | **P** | payload market timestamp → canonical unsigned-int **str** (explicit non-negative `int→str` only if the payload carries it as a JSON integer; else verbatim str). Independent of #11; the frozen anti-copy lock (`observed != str(retrieval)`) is enforced by B2, not repaired here |
| 13 | `raw_snapshot_identity` | **E** | supplied passive **Market Identity** str, verbatim — **never** from S2 (§5b) |
| 14 | `field_payload` | **P values + E labels** | one GROSS_EDGE field-entry: **magnitude** and **unit** from the payload (verbatim str); **`normalized_field_name`, `source_field`, `binding_role=GROSS_EDGE`** supplied by E (§8); assembled into the frozen tuple-of-`(label,value)` shape via the only permitted structural conversion `list→tuple` |

**Coverage:** all 14 fields are sourced — **3 from payload (P)** (venue, pair, observed_at), **10 from envelope (E)**,
**1 hybrid (field_payload: payload values + envelope labels)**. **Zero fields are fabricated, defaulted, inferred, or
clock-generated.** Any field that a real payload/envelope cannot supply at runtime stays a **blocker** (§5b, §7).

---

## 7. No Fabrication / No Guessing & Identity Isolation (binding)

- **No fabrication / no guessing.** Any field not sourceable from **either** the payload **or** the provenance
  envelope remains a **blocker** — the runtime structural-halts or stops/reports; it never infers or invents.
- **`base_asset` / `quote_asset` are NOT parsed from `pair`.** They are **supplied provenance facts** (E), ratified
  here as provenance — **not** guessed by splitting/parsing `pair`. The frozen contract itself forbids splitting
  (`b2_normalization_contract.py:327-328`); this charter honors that by sourcing them from E.
- **Identity Isolation.** `S2IdentityWiringCandidate` **bypasses** this provenance envelope and any future ingestion
  boundary **untouched**. The envelope **must not** carry, duplicate, or reconstruct the Silver tuple; the ingestion
  boundary processes **payload + provenance only** and never consumes/inspects/derives/stringifies/falls-back-to S2
  identity. Market Identity (E) and System/Silver Identity (S2) remain on **separate planes** (§5b).

---

## 8. Field-Payload Label Discipline (binding)

- The `field_payload` GROSS_EDGE entry's **structure** (labels/roles) is supplied as **passive source contract**
  only: `binding_role=GROSS_EDGE` and the binding's `normalized_field_name`/`source_field` are **supplied passive
  labels** (E), and `magnitude`/`unit` are **payload values** (P). The exact `binding_role` vocabulary
  (`{GROSS_EDGE, COST}`) is the frozen B2 contract's, used verbatim — never inferred.
- **No computation.** The boundary/envelope **MUST NOT** compute cost, edge, score, threshold, ranking, or any
  business meaning from these labels/values. A GROSS_EDGE binding is a **passive carrier** of an already-observed
  gross magnitude/unit; it asserts no profitability, direction, or decision.
- **COST bindings remain Cell-3 gated.** This charter defines **no** COST field-entry, no cost magnitude, and no
  cost-context assembly. `cost_validity_contexts` (a separate B3/Producer concern) stays **deferred**; **Cell-3
  remains separately gated.**

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." Provenance is **not** a capacity decision.

---

## 10. Runner Smuggling Ban & No Business Logic (binding)

- **Runner Smuggling Ban.** The S5 runner **MUST NOT** implement provenance construction or B2 ingestion internally.
  A future S5 may only **receive** a separately-ratified `MarketProvenanceContext` and **invoke** a separately-
  ratified ingestion boundary. Until **both** the provenance envelope **and** the ingestion boundary are
  runtime-built and ratified, **S5 runtime TDD remains ineligible**.
- **No business logic.** Neither the provenance envelope nor any future ingestion boundary may compute edge, score,
  ranking, actionability, routing, readiness, execution intent, venue decision, or threshold. They are **passive
  metadata carriage + structural field mapping** only.

---

## 11. Still-Forbidden Work

- **No** change to the Option-B payload/serialization charter (D1), B2 normalizer / `PublicRawSnapshotRecord` (D2),
  or any downstream interface (§3).
- **No** clock/timestamp/default/`UNKNOWN`/counter/UUID/hash/synthetic-ID generation; **no** fabrication/guessing of
  any provenance field (§5a, §7); **no** `pair`-splitting to source base/quote (§7).
- **No** derivation/merge/fallback between Market Identity and S2 Silver/System Identity (§5b); **no** envelope
  carriage/duplication of the Silver tuple (§7).
- **No** cost/edge/score/threshold/ranking/business computation; **no** COST field-entry; **no** Cell-3 assembly;
  **no** capacity activation (§8, §10).
- **No** S5-internal provenance/ingestion; **no** S5 runtime; **no** halt-only/partial runner (§10).
- **No** runtime/tests/schema/storage; **no** edits to Reader/S2/B2/B3/Producer/Phase5/B4/S4/S1/S5/lock-tests.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Precise State

- This charter may make a **future, separately-gated** `MarketProvenanceContext` runtime contract **and** a B2
  ingestion contract **eligible to be chartered** — but authorizes **neither** here.
- It **does not** authorize S5 runtime, **does not** complete the pass path, **does not** complete Phase 6.1, and
  **does not** ready Phase 6.2.
- The B2 ingestion boundary still requires the provenance envelope to exist as ratified runtime input; a **passive
  cost-context (Cell-3) source** for B3/Producer remains an **independent, separately-gated** prerequisite before the
  pass path is contract-complete. The **S1 durable storage medium** remains separately gated; the S1 sink stays a
  **test-only reference sink**.

---

## 13. Next Safe Step

- A **separately-authorized docs-only `MarketProvenanceContext` field-shape charter** — fixing, at logical-attribute
  level (storage-agnostic), the passive provenance fields of §4/§6 (each a supplied raw passive fact, no fabrication,
  no S2 identity, no business logic) — followed, once the envelope is ratified, by a **separately-authorized B2
  ingestion runtime TDD slice** that combines payload + provenance into an exact `PublicRawSnapshotRecord` via the
  §6 mapping (explicit `list→tuple` / non-negative `int→str` only; structural-halt on any missing field).
- Independently: the **passive cost-context (Cell-3)** source charter and the **S1 storage-medium** charter — each
  separately gated.
- Only after **both** the pass path (provenance + ingestion + cost-context) **and** the halt path are
  contract-complete does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** D3 is designed at concept level as a **new passive non-payload provenance envelope**,
`MarketProvenanceContext`, that travels **beside** the Option-B payload and supplies exactly the
`PublicRawSnapshotRecord` fields the payload cannot — **without touching the Option-B payload (D1 rejected) or B2 (D2
rejected)**. An explicit **1-to-1 mapping** sources all **14** caller fields with **zero fabrication**: **venue,
pair, observed_at_epoch_ms** from the payload; **source_artifact, source_field, base_asset, quote_asset,
instrument_id, venue_scope, venue_buy, venue_sell, retrieval_epoch_ms, raw_snapshot_identity** (plus the GROSS_EDGE
binding labels) from the envelope; and **field_payload** from payload magnitude/unit **values** plus envelope
labels — under the only permitted explicit conversions (`list→tuple`, non-negative `int→str` for
`observed_at_epoch_ms`). **Supplied-not-generated** (no clocks/defaults/UUIDs/synthetic IDs), **dual-identity strict
segregation** (Market Identity `raw_snapshot_identity` never derives from or merges with S2 Silver/System Identity),
**Identity Isolation** (S2 bypasses untouched; no Silver tuple in the envelope), **No Fabrication / No Guessing**
(missing field ⇒ structural-halt/blocker; `base`/`quote` supplied, never parsed from `pair`), **Field-Payload label
discipline** (passive GROSS_EDGE labels only; no cost/edge/score; COST + Cell-3 gated), **Runner Smuggling Ban**, and
**No Business Logic** all hold. Existing modules stay **frozen**; this authorizes **no** runtime; **S5 runtime TDD
remains ineligible**; the pass path is **not** contract-complete; Phase 6.1 remains **incomplete** and Phase 6.2
**not ready**. **No executable work is authorized.**
