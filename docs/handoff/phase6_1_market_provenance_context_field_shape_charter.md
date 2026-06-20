# Phase 6.1 — MarketProvenanceContext Field-Shape Charter

> **This is a docs-only logical field-shape charter.** It formally defines the **logical field shape** of the
> `MarketProvenanceContext` envelope designed in `f85349c` — **conceptual obligations only**, no runtime, no schema,
> no persistence, no parsing, no validation algorithm, no helper methods. It **designs and builds nothing**. It
> authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO storage/persistence/serialization/
> indexing, NO parsing/validation logic, NO B2 ingestion runtime, NO S5 runtime, NO Cell-3/cost math, NO Phase 6.2
> work, NO pytest, NO graphify, NO edits to the Reader / S2 / B2 / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 /
> lock-tests. It is subordinate to
> `docs/handoff/phase6_1_d3_non_payload_provenance_supply_contract_charter.md`,
> `docs/handoff/phase6_1_b2_pass_path_ingestion_normalization_contract_charter.md`,
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`, and `CLAUDE.md`; where any conflict arises, those
> govern.

**Base:** `f85349c323dded74b4c13064c7ef1efff8a09ece`

---

## 1. Base / Dependency Chain

**Base commit:** `f85349c323dded74b4c13064c7ef1efff8a09ece`.

References:

- `…_d3_non_payload_provenance_supply_contract_charter.md` — designed `MarketProvenanceContext` as a **new passive
  non-payload provenance envelope** that travels **beside** the Option-B payload and supplies the ten non-payload
  `PublicRawSnapshotRecord` fields, with an explicit 1-to-1 mapping, supplied-not-generated, dual-identity strict
  segregation, no fabrication, and Cell-3/cost excluded. **This charter fixes that envelope's logical field shape.**
- `…_b2_pass_path_ingestion_normalization_contract_charter.md` — cited the frozen 14-field
  `make_public_raw_snapshot_record` caller contract (§10 maps the envelope side to it).
- `…_option_b_serialization_field_shape_charter.md` — the frozen Option-B payload (venue, pair,
  observed_at_epoch_ms, gross magnitude, unit; identity forbidden in payload). **Unchanged.**

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Current State

- `MarketProvenanceContext` is conceptually designed (`f85349c`) but its **field shape is undefined** — this charter
  defines its **logical attributes** only.
- The Option-B reader/payload, B2, `PublicRawSnapshotRecord`, B3, Producer, Phase 5, B4, S4, S1, and S5 docs remain
  **BUILT/RATIFIED and frozen**. The pass path is **contract-incomplete**; Phase 6.1 incomplete; Phase 6.2 not ready.
- This charter is **non-executable**: it adds no runtime, schema, parser, validator, or persistence.

---

## 3. Pure DTO Restriction (binding)

`MarketProvenanceContext` is defined as a **frozen, immutable, methodless passive metadata container** — a pure
data carrier and nothing else. At concept level:

- It is **pure data**: it holds the ten supplied provenance facts and exposes them by name. **Zero methods, zero
  math, zero logic.**
- It contains **NO** parsing logic, validation logic, business logic, score logic, cost logic, routing logic,
  derivation, normalization, coercion, defaulting, or helper/convenience methods. It neither validates nor
  transforms what it carries.
- Validation of the supplied values (type/shape) is **B2's** at construction of `PublicRawSnapshotRecord` — **not**
  this envelope's. The envelope **carries**; B2 (frozen) **checks** when it consumes the mapped values (§10). This
  charter defines **no** validator and **no** runtime types.

---

## 4. Exact Ten Envelope Fields (closed set; conceptual obligations only)

The envelope carries **exactly these ten** Logical Provenance Attributes — **no more, no fewer**, **no catch-all
dict, no arbitrary metadata bag, no `extra`/`details`/`raw` field**:

1. **`source_artifact`** — passive provenance: which source artifact the snapshot came from (supplied).
2. **`source_field`** — passive provenance: the source field reference (supplied).
3. **`base_asset`** — passive market-identity fact, **externally supplied** (§5 anti-parsing).
4. **`quote_asset`** — passive market-identity fact, **externally supplied** (§5 anti-parsing).
5. **`instrument_id`** — passive market-identity fact (supplied).
6. **`venue_scope`** — passive venue-provenance fact (supplied).
7. **`venue_buy`** — passive venue-provenance fact (supplied).
8. **`venue_sell`** — passive venue-provenance fact (supplied).
9. **`retrieval_epoch_ms`** — passive freeze-time provenance, **externally supplied** (§6 anti-clock).
10. **`raw_snapshot_identity`** — passive **Market Identity**, **externally supplied** (§7 dual-identity segregation).

These are **Logical Provenance Attributes** — **not** database columns, serialized keys, JSON structure, dataclass
fields, Python types, SQL/Parquet schemas, indexes, primary keys, or persistence formats. **No** concrete types,
formats, ordering, encoding, or serialization are fixed here.

### 4a. Closed-set discipline
- The set is **closed and minimal**: it carries **only** the ten non-payload fields the §10 mapping requires.
- It carries **NO** payload field (venue/pair/observed_at_epoch_ms/magnitude/unit stay in the payload, §10), **NO**
  GROSS_EDGE/COST binding label, **NO** identity-from-S2, **NO** cost field, and **NO** open key/value surface. Each
  attribute has a single, passive, declared purpose.

---

## 5. Anti-Parsing Seal (binding)

- **`base_asset` and `quote_asset` are externally-supplied provenance fields.** They are raw passive facts the
  source already states about itself.
- They **MUST NOT** be derived by splitting `pair`, parsing/tokenizing `pair`/`venue` strings, regex extraction,
  delimiter inference, or any string manipulation. The frozen B2 contract itself forbids splitting
  (`b2_normalization_contract.py:327-328`); this envelope honors that by carrying them as **independent supplied
  facts**. If the source does not supply them, they are a **blocker** (§7), never inferred.

---

## 6. Anti-Clock Temporal Seal (binding)

- **`retrieval_epoch_ms` is externally-supplied provenance** — the freeze/retrieval time the source/capture already
  recorded, carried verbatim beside the event.
- A future runtime constructing or consuming this envelope **MUST NOT** call any time/date/clock function, read the
  system or wall clock, use a default, **copy `observed_at_epoch_ms`**, or generate a timestamp internally.
  `retrieval_epoch_ms` and the payload's `observed_at_epoch_ms` remain **distinct, independently-supplied**
  timestamps; their distinctness is enforced by the frozen B2 anti-copy lock (`observed != str(retrieval)`), never
  repaired here. If `retrieval_epoch_ms` is not supplied, it is a **blocker** (§7).

---

## 7. Dual-Identity Segregation & No-Fabrication (binding)

### 7a. Dual-identity segregation
- **`raw_snapshot_identity` is strictly external Market/raw identity** — a raw passive fact of the source market
  snapshot, supplied by the envelope. It is a **different identity plane** from S2 Silver/System Identity.
- It **MUST NOT** duplicate, derive from, inspect, merge with, hash, stringify, collapse, or fall back to
  `S2IdentityWiringCandidate` or the Silver tuple `(artifact_locator, physical_record_position)`. S2 identity
  remains **parallel and separate**; the two planes never touch. The envelope carries **no** Silver tuple.

### 7b. No fabrication / no UNKNOWN
- **Every** field is **supplied** by the provenance envelope. **No** field may be `UNKNOWN`, empty, synthetic,
  fallback, default, placeholder, `UUID`, counter, hash, or fingerprint. A field the source does not supply remains
  a **structural blocker** (the future runtime structural-halts or stops/reports) — it is **never** invented.

---

## 8. Cell-3 / Cost Math Exclusion (binding)

- This charter defines **NO** computed cost, fee, `cost_validity_contexts`, Cell-3 derivation, COST payload field,
  or COST binding label. The envelope's ten fields are **provenance only** — they carry no cost magnitude and no
  cost evidence.
- **Cost handling remains separately gated.** `cost_validity_contexts` is a downstream B3/Producer concern; Cell-3
  remains an independent, separately-gated prerequisite (`f85349c` §8/§12).

---

## 9. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." Provenance is **not** a capacity decision.

---

## 10. B2 Mapping Compatibility (explanatory only — no ingestion runtime designed)

The ten fields are exactly the **envelope side** of the `f85349c` 1-to-1 mapping into the frozen 14-field
`make_public_raw_snapshot_record` caller contract. **Payload (P)** supplies 3 fields; **this envelope (E)** supplies
10; one field is **hybrid** (payload values + envelope labels):

| `PublicRawSnapshotRecord` field | Source | From this envelope? |
|---------------------------------|--------|---------------------|
| `venue` | **P** | no — payload |
| `pair` | **P** | no — payload |
| `observed_at_epoch_ms` | **P** | no — payload |
| `source_artifact` | **E** | **yes** (#1) |
| `source_field` | **E** | **yes** (#2) |
| `base_asset` | **E** | **yes** (#3) |
| `quote_asset` | **E** | **yes** (#4) |
| `instrument_id` | **E** | **yes** (#5) |
| `venue_scope` | **E** | **yes** (#6) |
| `venue_buy` | **E** | **yes** (#7) |
| `venue_sell` | **E** | **yes** (#8) |
| `retrieval_epoch_ms` | **E** | **yes** (#9) |
| `raw_snapshot_identity` | **E** | **yes** (#10) |
| `field_payload` | **P values + E labels** | the GROSS_EDGE binding **labels** are envelope-supplied per `f85349c` §6/§8; magnitude/unit are payload values |

- **Note on `field_payload` labels.** `f85349c` §6/§8 supply the GROSS_EDGE binding labels (`normalized_field_name`,
  the binding's `source_field`, `binding_role=GROSS_EDGE`) from the provenance side. This field-shape charter keeps
  the envelope's **closed ten-attribute** set (§4) and does **not** add binding-label attributes to the DTO; whether
  those passive labels are carried by `MarketProvenanceContext` or by a **separate** passive binding-label provenance
  contract is **deferred to the B2 ingestion contract decision** and **not fixed here**. This charter fixes **only**
  the ten provenance attributes; it designs **no** `field_payload` assembly.
- **This section is explanatory only.** It **does not** design or authorize the B2 ingestion runtime, the mapping
  function, or any assembly of `PublicRawSnapshotRecord`. It shows the ten attributes are **shape-compatible** with
  the envelope side of the frozen contract — nothing more.

---

## 11. Storage Ban (binding)

`MarketProvenanceContext` is an **in-memory, passive, ephemeral envelope shape only**. This charter makes **NO**
durable-storage, database, serialization, indexing, retention, cursor, checkpoint, run-state, or S5-state decision.
The envelope exists per-event, carried by reference; it is not persisted and owns no log.

---

## 12. Still-Forbidden Work

- **No** method/parse/validate/business/score/cost/route/derive/normalize/coerce/default logic on the DTO (§3);
  **no** helper methods.
- **No** field beyond the exact ten (§4); **no** catch-all dict / arbitrary metadata bag / open key-value surface;
  **no** payload field, GROSS_EDGE/COST label attribute, or S2 identity in the DTO (§4a, §7, §10).
- **No** `base_asset`/`quote_asset` derived by splitting/parsing `pair`/`venue` (§5).
- **No** clock/time/date call, default, `observed_at_epoch_ms` copy, or internal timestamp generation for
  `retrieval_epoch_ms` (§6).
- **No** derivation/merge/hash/stringify/collapse/fallback between Market Identity and S2 Silver/System Identity; **no**
  Silver tuple in the envelope (§7a).
- **No** `UNKNOWN`/empty/synthetic/fallback/default/UUID/counter/hash/placeholder for any field; missing ⇒ blocker
  (§7b).
- **No** computed cost/fee/`cost_validity_contexts`/Cell-3/COST field (§8); **no** capacity activation.
- **No** durable storage/DB/serialization/indexing/retention/cursor/checkpoint/S5-state (§11).
- **No** B2 ingestion runtime, mapping function, or `PublicRawSnapshotRecord` assembly (§10); **no** S5 runtime.
- **No** edits to Reader/S2/B2/B3/Producer/Phase5/B4/S4/S1/S5/lock-tests; **no** runtime/tests/schema.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Precise State

- This charter may make a **separately-authorized `MarketProvenanceContext` runtime DTO TDD slice eligible** (a
  frozen, methodless, ten-field passive container with exact-supplied fields and structural-halt on any missing
  one) — but **authorizes none here**.
- It **does not** authorize the B2 ingestion runtime, S5 runtime, Cell-3, or storage; **does not** complete the pass
  path; **does not** complete Phase 6.1; **does not** ready Phase 6.2.
- Still-separate prerequisites before the pass path is contract-complete: (a) the `MarketProvenanceContext` runtime
  DTO; (b) the B2 ingestion contract/runtime combining payload + provenance into `PublicRawSnapshotRecord`; (c) a
  passive cost-context (Cell-3) source for B3/Producer. The **S1 storage-medium** charter remains independently
  gated; the S1 sink stays a **test-only reference sink**.

---

## 14. Next Safe Step

- A **separately-authorized `MarketProvenanceContext` runtime DTO TDD slice** — implementing, **under this
  field-shape**, a frozen/immutable/methodless ten-field passive container (exact-supplied fields; no parse/validate/
  business/cost/identity logic; no clock; no fabrication; structural-halt/blocker on any missing field), test-first.
- Independently/subsequently: the **B2 ingestion contract** (payload + provenance → `PublicRawSnapshotRecord` via the
  `f85349c` §6 mapping, including the `field_payload` GROSS_EDGE label-source decision deferred in §10); the
  **passive cost-context (Cell-3)** source; and the **S1 storage-medium** charter. Each separately gated.
- Only after **both** the pass path (provenance DTO + ingestion + cost-context) **and** the halt path are
  contract-complete does an **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** `MarketProvenanceContext` is fixed at **logical-attribute level** as a **frozen, immutable,
methodless passive metadata container** carrying **exactly ten** supplied non-payload provenance attributes —
`source_artifact`, `source_field`, `base_asset`, `quote_asset`, `instrument_id`, `venue_scope`, `venue_buy`,
`venue_sell`, `retrieval_epoch_ms`, `raw_snapshot_identity` — with **no extra field, no catch-all dict, no methods,
and no logic**. **Anti-Parsing** (`base`/`quote` supplied, never split from `pair`), **Anti-Clock**
(`retrieval_epoch_ms` supplied, never clock-called/defaulted/copied), **Dual-Identity Segregation**
(`raw_snapshot_identity` is external Market Identity, never derived from/merged with S2 Silver/System Identity),
**No-Fabrication/No-UNKNOWN** (missing ⇒ structural blocker), **Cell-3/Cost Exclusion** (no cost/COST field),
**Storage Ban** (in-memory/passive shape only), and **B2 Mapping Compatibility** (the ten attributes are the
envelope side of the frozen 14-field mapping, explanatory only — no ingestion runtime designed) all hold. Existing
modules remain **frozen**; this authorizes **no** runtime; the pass path is **not** contract-complete; **S5 runtime
TDD remains ineligible**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is
authorized.**
