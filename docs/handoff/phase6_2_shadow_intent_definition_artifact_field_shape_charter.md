# Phase 6.2 — Shadow Intent Definition Artifact Field-Shape Charter (Gate A)

> **This is a docs-only Gate A field-shape charter.** It pins the **exact closed logical field shape, logical
> scalar/container types, units, variants, and structural validation rules** for the sealed scenario-definition
> artifact. It **implements nothing and authorizes nothing executable**: no runtime code, no tests, no test
> execution, no lock-test edits, no frozen-component edits, no Phase 6.1 edits, no S1-adapter edits, no loader, no
> writer, no state machine, no predicate implementation, no container runtime, no Phase 6.2 runtime, no pytest, no
> graphify. It defines **NO** physical representation: no JSON/YAML/SQLite/Protobuf schema, no textual/byte
> encoding, no physical field order, no canonical sorting/normalization, no digest field/algorithm, no hashing, no
> cryptographic verification — **all physical representation and sealing verification remain Gate B.** It makes
> **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_source_authority_determinism_targeted_amendment_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_definition_artifact_source_boundary_charter.md`,
> `docs/handoff/phase6_2_multi_event_context_supply_shadow_state_boundary_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_lifecycle_state_transition_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_field_shape_charter.md`,
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `abd1b41289c740f7efc8a16fd5148cc7f320a312`

---

## 1. Base / Purpose

**Base commit:** `abd1b41289c740f7efc8a16fd5148cc7f320a312`.

The source-boundary charter (`07135be`) and its amendment (`abd1b41`) ratified the sealed scenario-definition
artifact as the **exclusive source of declared counterfactual assumptions** (orientation / passive boundary /
hypothetical-window declaration) and split the future design into **Gate A** (field-shape) then **Gate B**
(canonical-encoding & digest). This is **Gate A**: it pins the **exact closed logical shape** of that artifact — the
envelope, the closed two-variant definition union, the logical types, units, cardinality, the artifact-only
structural validation set, and the encounter-time cross-input contract — **without** fixing any physical
representation, byte encoding, ordering, normalization, or digest (Gate B).

**No capacity validation and no capacity pass is claimed by this charter** (see §15).

---

## 2. Evidence-First Silver-Pair Inspection (the logical target key, mapped)

**Inspected ratified evidence:**

- **`S2IdentityWiringCandidate`** (`phase6_1/s2_identity_wiring_candidate.py`): fields `artifact_locator: object`,
  `physical_record_position: object`, carried **verbatim, opaque, by reference** from the `OptionBEventEnvelope`
  (never hashed, concatenated, cast, derived, or collapsed).
- **`OptionBEventEnvelope`** origin: `artifact_locator` is caller-supplied opaque metadata carried verbatim;
  `physical_record_position` originates as `text_stream.tell()` (an `int` IO offset at origin).
- **S1 durable SQLite envelope** (`phase6_1_s1_storage/s1_durable_sqlite_sink.py`): columns `artifact_locator TEXT
  NOT NULL`, `physical_record_position TEXT NOT NULL`, written via `_opaque_text(...)` (str → verbatim str; int →
  `str(value)`; else canonical JSON).
- **S1 replay row surface** (the ratified minimal append-order `replay`, `b06d7ed` §5): the `SELECT` returns
  `artifact_locator` and `physical_record_position` as **TEXT** → Python **`str`** (`append_sequence` deliberately
  omitted; rowid containment, `b06d7ed` §6).
- **Ratified Silver-pair charters:** the opaque Silver pair is the borrowed event identity, **borrowed never
  minted**, and the `append_sequence` rowid is **never** a domain identity (`b06d7ed` §6; `999a109` §4).

**Mapping (unambiguous):** Phase 6.2 reconstruction consumes the **durable S1 SQLite/WAL audit replay** (the ratified
input per `999a109` §9 / `abd1b41` §6). At that replay-facing surface, **both** Silver-pair components are **opaque
text scalars** (`artifact_locator` verbatim text; `physical_record_position` the decimal-text rendering of the IO
offset). Therefore the artifact's logical target key is pinned as:

> **`OpaqueSilverPairKey`** — an ordered pair of **exactly two opaque logical text scalars**
> `(silver_artifact_locator_text, silver_physical_record_position_text)`, each preserving the **exact** corresponding
> durable S1 replay-row value **verbatim**.

The key is matched against replayed S1 records by **exact opaque text equality on both components**. It is **never**
coerced, parsed (the position is **not** re-read as an integer), arithmetically manipulated, normalized,
case-folded, split, concatenated, hashed, or used to invent identity. The pair is two separate opaque facts, not one
fused key. **The replay-facing pair types map unambiguously into logical opaque text targets; the §2 STOP condition
is NOT triggered.**

---

## 3. Exact Closed Artifact Envelope (binding)

One **frozen, methodless** logical artifact-envelope shape with **exactly these five fields and no extras**:

1. **`artifact_field_shape_version_reference`** — caller-supplied, stable, **opaque** logical schema-version
   reference (which field-shape version this artifact conforms to).
2. **`artifact_version_reference`** — caller-supplied, stable, **opaque** artifact-version reference (which version
   of *this* artifact lineage).
3. **`declarer_opaque_reference`** — caller-supplied, stable, **opaque** provenance reference (who/what declared the
   scenario).
4. **`predecessor_artifact_version_reference`** — **optional** opaque reference to **exactly one** predecessor
   artifact version; **structurally absent** for the first lineage member (see §3a — modeled by an explicit
   present/absent variant, never `null`/sentinel).
5. **`definitions_by_silver_pair`** — an **immutable finite logical map** keyed **only** by the exact
   `OpaqueSilverPairKey` of §2; values are the closed definition union of §6.

**No runtime-generated UUID, counter, timestamp, random token, rowid, field-hash, or surrogate identity may populate
any reference.** All four references are **caller-supplied and stable**. These references are **artifact / provenance
metadata only** and **MUST NOT** become an intent identity, a Silver identity, an ordering mechanism, an
actionability surface, or a runtime-lookup invention.

### 3a. Predecessor optionality (structural)

`predecessor_artifact_version_reference` is modeled as an explicit **present-with-one-opaque-reference OR
structurally-absent** option — **not** as a nullable field, sentinel, empty string, or fabricated default. The first
lineage member structurally carries no predecessor; later members carry exactly one opaque predecessor reference.

---

## 4. Opaque-Reference Discipline (binding)

The four opaque references (`artifact_field_shape_version_reference`, `artifact_version_reference`,
`declarer_opaque_reference`, `predecessor_artifact_version_reference`) obey:

- they are **never** semantically parsed, ranked, normalized, version-compared, or used to **infer behavior**;
- they **must not** carry credentials, secrets, personal data, endpoints, executable instructions, quantities,
  allocation, routing, or actionability;
- the future validator **must not** scan their text for trading vocabulary or derive semantics from their contents —
  it checks **only** that each is an opaque value of the expected logical type (and predecessor presence/absence);
- **producer responsibility and provenance policy** enforce the no-secret / no-PII rule; **runtime semantic
  inspection of reference contents is forbidden.**

---

## 5. Immutable Map Semantics (binding)

`definitions_by_silver_pair`:

- is **logically unordered** — physical entry order has **no semantic meaning** (canonical physical ordering is Gate
  B);
- an **empty** definition map is **valid**;
- each Silver pair has **zero or at most one** definition;
- **duplicate logical keys are structurally invalid** — **no** first-wins, last-wins, merge, overwrite, or
  deduplication (a duplicate is a pre-flight failure, §11);
- **banned:** sub-identities, ordinals, counters, generated IDs, hash-derived IDs, and rowid-as-domain-identity. The
  key is exactly the §2 `OpaqueSilverPairKey`, nothing else.

---

## 6. Closed Definition Sum Type (binding)

The map **value** is a **closed logical tagged union** with **exactly two variants** — no additional variants and no
additional fields:

**A. `DirectionalShadowIntentDefinition`** — exactly four fields:
- `exposure_orientation`
- `passive_boundary_magnitude`
- `boundary_unit_context`
- `hypothetical_window_duration_ms`

**B. `InertShadowIntentDefinition`** — exactly two fields:
- `exposure_orientation`
- `hypothetical_window_duration_ms`

Both variants are **frozen, methodless** logical DTOs. The union is **closed**: a value is exactly one of these two
variants; any third variant or any extra/unknown field is structurally invalid (§11).

---

## 7. Exact Orientation Contract (binding)

- `DirectionalShadowIntentDefinition.exposure_orientation` is **exactly one of**: `POSITIVE_EXPOSURE`,
  `NEGATIVE_EXPOSURE`.
- `InertShadowIntentDefinition.exposure_orientation` is **exactly**: `INERT_STATE`.
- **No enum value may be dropped, aliased, normalized, inferred from magnitude sign, or extended.** Orientation is a
  **declared** value, never derived from the boundary magnitude's sign or from any observed evidence.
- **`INERT_STATE` cannot produce directional crossing** (it declares no direction).
- **`InertShadowIntentDefinition` structurally has NO `passive_boundary_magnitude` and NO `boundary_unit_context`.**
  Their absence is modeled by the **variant's structure** — **not** by `null`, a sentinel, an ignored value, or a
  fabricated default. An inert definition that carried a boundary or unit field would be structurally invalid.

---

## 8. Exact Boundary Semantics (binding — `DirectionalShadowIntentDefinition` only)

- **`passive_boundary_magnitude`** has **logical exact-decimal semantics** (an exact base-10 decimal value).
  - **Native binary float / double is forbidden.**
  - **NaN, infinity, implicit rounding, locale parsing, coercive conversion, and sign-derived orientation are
    forbidden.**
  - Its **physical textual / byte representation remains Gate B** (this charter fixes the *logical* exact-decimal
    contract, not the encoding).
- **`boundary_unit_context`** is an **opaque logical unit token**.
  - It is compared **by exact equality only** against the S1 `score_unit_context` (the `family_payload.
    score_unit_context` of a SCORE record).
  - **No** normalization, conversion, FX conversion, case-folding, aliasing, or inferred equivalence.
  - **Unit mismatch remains passive not-comparable** — **no transition, NOT fail-fast, and NOT a Phase 6.1 halt**
    (consistent with `999a109` §7 and `abd1b41` §6).

---

## 9. Exact Hypothetical-Window Semantics (binding — both variants)

- **`hypothetical_window_duration_ms`** is an **exact non-negative integer** duration measured in **milliseconds**.
  - **`bool` is NOT an integer** for this contract (a boolean is structurally invalid here).
  - **Forbidden:** float, datetime, date range, interval object, absolute deadline, wall-clock reference, timer,
    scheduler, or current-time field. It is a **declared duration magnitude**, never a clock or an event.
- **Zero-duration validity is pinned structurally only** — a `0` duration is a structurally valid value; the **exact
  expiry inequality and transition behavior remain DEFERRED** to the Predicate Charter.
- The **anchor** remains the **qualifying root S1 provenance timestamp** (observed, from S1).
- The **comparison operand** remains a **later append-ordered S1 provenance timestamp** (observed, from S1).
- **Provenance timestamps are NOT assumed monotonic;** append order alone determines processing order
  (`abd1b41` §9).
- **Negative / out-of-order timestamp deltas must NEVER silently produce expiry;** the exact classification remains
  **DEFERRED** to the Predicate Charter. This charter pins only the **declared-duration field**, not the inequality.

---

## 10. No Observed Facts Inside Definitions (binding)

An artifact definition **MUST NOT** copy or carry **any** observed fact:

- observed score magnitude; observed S1 provenance timestamp; observed family payload; HALT payload; lifecycle
  state; hypothetical outcome; realized PnL; account / wallet / portfolio state; capacity result; or any
  execution / routing / action field.

A definition **references a Silver pair** (the §2 key) and **declares only the closed counterfactual geometry**
permitted by this charter (orientation, and — for the directional variant — a passive boundary magnitude + unit
token, plus a declared window duration). **S1 remains the exclusive observed-event source** (`abd1b41` §4).

---

## 11. Artifact-Only Pre-Flight Validation (binding)

Before any S1 record is consumed, future validation may check **only the artifact itself** — exactly this closed
set:

- exact **envelope type** and exact **five-field set** (no unknown fields);
- exact **logical map / container type** for `definitions_by_silver_pair`;
- exact **definition variant** (one of the closed two);
- exact **orientation membership** (§7);
- exact-**decimal** logical validity of `passive_boundary_magnitude` (directional only);
- exact **unit-token type** of `boundary_unit_context` (directional only);
- exact **non-negative integer** duration `hypothetical_window_duration_ms` (bool excluded);
- **opaque-reference types** (the four references, by type only — never by content, §4);
- **predecessor optionality** (present-with-one OR structurally-absent, §3a);
- **duplicate Silver-pair keys** (structurally invalid, §5);
- **absence of unknown fields and unknown variants** (closed-world).

**Pre-flight MUST NOT inspect, pre-scan, or validate against S1.** It is purely an artifact-shape check; any failure
is a `07135be` §10 pre-flight hard failure **before** any observation consumption.

---

## 12. Cross-Input Encounter Contract (binding)

When the ordered S1 replay **later** encounters a targeted Silver pair (a replayed record whose
`OpaqueSilverPairKey` matches a definition):

- **Exact qualifying SCORE record** — an exact `SCORE` observation carrying the required magnitude
  (`passive_score_magnitude`), unit (`score_unit_context`), and provenance timestamp: **eligible for later predicate
  classification** (the predicate itself is deferred).
- **Exact unit mismatch** (SCORE present, but `boundary_unit_context` ≠ `score_unit_context`): **passive
  not-comparable, no transition** (not fail-fast, not a Phase 6.1 halt).
- **HALT record, non-SCORE record, missing SCORE magnitude/unit, missing provenance timestamp, or malformed
  canonical SCORE evidence** for a **targeted** pair: a **cross-input binding failure at encounter-time** — **hard
  fail-fast before creating or mutating any shadow state for that pair**.
  - **No fallback to S4.** **No S1 or Phase 6.1 mutation.** **No synthetic intent, default value, or equality-only
    downgrade.**

If a definition's Silver pair is **never encountered** by replay EOF:

- it is a **valid dormant definition** — **no intent created, no error, no synthetic observation, no synthetic
  terminal** (consistent with `07135be` §9 unused-definition rule).

---

## 13. Sealing-Field Prohibition (binding)

The artifact envelope and **both** definition variants **MUST NOT** contain any of:

- `is_sealed`; a sealed flag; `digest`; `checksum`; `signature`; a canonical-bytes field; or any mutable
  validation-status field.

**Sealing is a source-lifecycle property** (from `abd1b41` / `07135be`): an artifact is sealed **before** the first
S1 record by the source lifecycle. **Durable canonical representation and seal verification belong exclusively to
Gate B.** A frozen logical DTO proves only **in-memory immutability**; it does **not** prove durable sealing — so no
seal/digest field is admitted into the logical shape.

---

## 14. Determinism Boundary (binding)

- **Logical interpretation is independent of map entry order** (§5).
- **Same valid logical artifact shape + same ordered S1 evidence ⇒ deterministically equivalent logical state**
  (per `abd1b41` §8).
- **Bit-identical / byte-identical output is NOT claimed** here (deferred to Gate B).
- **No** randomness, generated UUID, wall clock, environment-selected input, hidden state, singleton, mutable cache,
  or iteration-order dependency may influence logical interpretation.

---

## 15. Anti-Actionability & Quarantine (binding)

- The artifact is an **offline counterfactual scenario definition only**.
- **No** endpoint, credential, account identifier, venue connection, broker API, callback, emission hook, quantity,
  allocation, route, instruction, live flag, or production-risk control may appear in any field.
- **Capacity remains DEFERRED at exactly 0 emit sites.**
- **Phase 6.1 remains frozen, COMPLETE + RATIFIED.**
- **Phase 6.2 remains UNBUILT and NOT runtime-ready.**

---

## 16. Precise Post-Charter State (ratified)

This charter pins **only**:

- the **artifact envelope** (§3, the closed five fields);
- the **closed definition variants** (§6);
- the **logical fields and types** (§7–§9);
- **units** (§8);
- **cardinality** (§5);
- **artifact-only structural validation** (§11);
- the **encounter-time cross-input contract** (§12).

**Still unbuilt and unauthorized:** physical **encoding**; **canonical bytes**; **sorting / normalization**;
**content digest and verification**; the **artifact loader / writer**; the **predicate runtime**; the **state
machine**; the **shadow container runtime**; and **any executable integration**.

- **Phase 6.1:** frozen, COMPLETE + RATIFIED. **Capacity:** deferred (0 emit sites). **Production / live / paper /
  canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (unchanged):** at most one terminal per intent; open frozen non-terminal state at replay EOF
  is valid audit state.

---

## 17. Next Safe Gate

- **Gate B — Phase 6.2 Shadow Intent Definition Artifact Canonical-Encoding & Digest Charter** (docs-only): durable
  format, canonical byte representation, ordering / normalization rules, content digest, and artifact-reference
  verification — **no runtime implementation**.
- **This charter does NOT open, draft, implement, or authorize Gate B.** **No runtime TDD becomes eligible from Gate
  A alone.**

**Conclusion:** the sealed scenario-definition artifact's **logical field shape** is pinned (Gate A, docs-only). The
**logical target key** is `OpaqueSilverPairKey` — an ordered pair of **two opaque text scalars**
(`silver_artifact_locator_text`, `silver_physical_record_position_text`) preserving the durable S1 replay-row Silver
pair **verbatim**, matched by **exact opaque text equality**, never coerced/parsed/normalized/invented. The **frozen,
methodless envelope** carries **exactly five** fields — `artifact_field_shape_version_reference`,
`artifact_version_reference`, `declarer_opaque_reference`, **optional** `predecessor_artifact_version_reference`
(structurally present-one-or-absent, never null/sentinel), and the **immutable finite** `definitions_by_silver_pair`
map — all references **caller-supplied, stable, opaque** (no UUID/counter/timestamp/random/rowid/hash/surrogate;
never an intent/Silver/ordering/actionability/lookup identity; never semantically parsed or content-scanned). The map
is **logically unordered**, may be **empty**, holds **0..1** definition per pair, and **rejects duplicates**
structurally (no merge/first/last-wins). The value is a **closed two-variant tagged union**:
**`DirectionalShadowIntentDefinition`** {`exposure_orientation` ∈ {`POSITIVE_EXPOSURE`,`NEGATIVE_EXPOSURE`},
`passive_boundary_magnitude` (logical exact-decimal; no binary float/NaN/inf/rounding/locale/sign-derived),
`boundary_unit_context` (opaque unit token; exact-equality vs `score_unit_context`; no normalization; mismatch =
passive not-comparable), `hypothetical_window_duration_ms` (exact non-negative integer ms; bool excluded;
zero-valid structurally; inequality deferred)} and **`InertShadowIntentDefinition`** {`exposure_orientation` =
`INERT_STATE`, `hypothetical_window_duration_ms`} — the inert variant **structurally lacks** boundary/unit fields
(not null/sentinel; INERT_STATE produces no directional crossing). Definitions **carry no observed fact** (no
magnitude/timestamp/family/HALT/lifecycle/outcome/PnL/account/capacity/execution field); **S1 stays the exclusive
observed-event source**. **Artifact-only pre-flight** validates exactly the §11 closed set and **never inspects S1**.
At **encounter-time**: a qualifying SCORE pair is eligible for later predicate classification; a unit mismatch is a
passive no-op; a HALT/non-SCORE/missing-magnitude-or-unit/missing-timestamp/malformed-SCORE on a **targeted** pair is
a **hard fail-fast cross-input binding failure** (no S4 fallback, no S1/Phase-6.1 mutation, no synthetic
intent/default/equality-downgrade); an **unencountered** definition is a **valid dormant** definition (no intent, no
error, no synthetic anything). **No sealing/digest/checksum/signature/canonical-bytes/validation-status field** is
admitted (sealing + durable representation belong to Gate B). Determinism is **logical equivalence only** (no
bit/byte claim; no randomness/clock/env/hidden-state/cache/iteration-order dependence). The artifact is
**offline-only** with **no** endpoint/credential/connection/callback/emission/quantity/route/live flag; **capacity
stays deferred at 0 emit sites**; **Phase 6.1 stays frozen, COMPLETE + RATIFIED**. **Phase 6.2 remains UNBUILT and
NOT runtime-ready**; the **only** next safe step is the separately-authorized **Gate B — Phase 6.2 Shadow Intent
Definition Artifact Canonical-Encoding & Digest Charter**, **not opened here**. **No executable work is authorized.**
