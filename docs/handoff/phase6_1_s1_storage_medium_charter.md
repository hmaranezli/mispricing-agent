# Phase 6.1 — S1 Storage-Medium Charter

> **This is a docs-only architecture charter.** It selects the **canonical durable medium** for the S1 audit trail
> and pins its **append-only ACID posture** and **hybrid schema strategy** at architecture level only. It **designs
> and builds nothing**: no runtime, no tests, no schema DDL, no adapter, no serialization encoding. It authorizes NO
> runtime code, NO tests, NO lock-test edits, NO frozen-component edits, NO analytics/reporting interface, NO
> live/paper/canary, NO execution/routing/actionability, NO production-readiness, NO Phase 6.2 work, NO pytest, NO
> graphify. It is subordinate to
> `docs/handoff/phase6_1_in_memory_pipeline_milestone_closeout_ratification.md`,
> `docs/handoff/phase6_1_s5_runner_in_memory_orchestration_runtime_closeout_ratification.md`, the S1 in-memory sink
> charter, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `2817948eebd05b0b775b9f159733d6abcb0bda01`

---

## 1. Base / Purpose

**Base commit:** `2817948eebd05b0b775b9f159733d6abcb0bda01`.

The Phase 6.1 in-memory pipeline milestone is **closed and ratified** (`2817948`): the passive flow is
contract-complete and demonstrated **in RAM** against the S1 **in-memory reference sink**. The single handed-off
gate is a durable S1 medium. This charter **architects the canonical durable audit trail** for the S1 sink —
selecting the medium, fixing its append-only ACID posture, and pinning a hybrid envelope+payload schema
**strategy** — **without** implementing it and **without** choosing the payload encoding (deferred, §9).

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Frozen Evidence (cited before any selection)

From source (frozen, unchanged):

- **`phase6_1/s1_in_memory_observation_sink.py`** — two frozen, methodless DTO families,
  `ObservationScoreRecord` and `ObservationHaltRecord`, over **one common five-field envelope**:
  `identity_evidence`, `observation_kind`, `provenance_timestamp`, `opaque_cost_context`, `family_payload`. The
  in-memory sink admits only an exact record whose `identity_evidence` is an exact `S2IdentityWiringCandidate`, and
  is an append-only instance-bound list with a `snapshot()` readback. **It is the in-memory reference substrate,
  never a storage-engine choice.**
- **`identity_evidence`** = `S2IdentityWiringCandidate(forwarded_payload_or_local_halt, artifact_locator,
  physical_record_position)` — the opaque Silver pair `(artifact_locator, physical_record_position)` borrowed by
  reference, never minted.
- **`family_payload` carries embedded Python object references** (not just scalars):
  - SCORE (`b4_passive_scoring.py:56-62`): `passive_score_magnitude` (str), **`score_basis_reference`** (the
    frozen `NetEdgeCalculationResult` **object**, by identity), `score_inputs_summary` (a `(venue, pair)` tuple of
    strs), `score_unit_context` (str), `score_family_descriptor` (str);
  - HALT (`s4_halt_materialization.py:71-75`): **`halt_origin_reference`** (the frozen halt-carrier **object**, by
    identity), `opaque_upstream_context` (`None`), `halt_family_descriptor` (str);
  - the envelope's **`opaque_cost_context`** is likewise an opaque object reference (the Cell-3 cost-context tuple
    on the pass path, `None` on the local-parse-halt path).
- **Lock-placement constraint (decisive):** `tests/test_phase6_1_forbidden_token_locks.py` (and its diagnostic-EV
  mirror) make **`sqlite3` a forbidden import root** and **`serialize`/`serialization`/`json`/`to_json`/`to_dict`/
  `pickle`/`shelve`** forbidden tokens/imports **for every `phase6_1/*.py` runtime module**. Therefore a
  SQLite-based durable adapter **cannot live inside the locked `phase6_1/` passive package** without a
  separately-chartered closed lock exception. See §7.

---

## 3. Canonical Medium Selection — SQLite (WAL) (binding)

**SQLite in WAL (write-ahead logging) mode is selected as the SOLE canonical durable medium for the S1
ingestion/audit layer.** It is a single-file, embedded, ACID, zero-server engine well-matched to a real-time,
write-heavy, event-by-event append sink, and WAL gives concurrent durable appends with crash-consistency and a
single recoverable file.

**Forbidden for this real-time S1 sink:** Parquet, CSV, Postgres/MySQL or any client-server RDBMS, key-value/NoSQL
stores, external/cloud services, message brokers, and any heavy database. (An **analytics mirror/export** — e.g. a
downstream Parquet/columnar copy — is a **separate future boundary**, §5, and is **not** the S1 ingestion medium.)

---

## 4. Append-Only ACID Trail (binding)

S1 durable storage is a **strictly append-only, monotonic, crash-consistent observation log**:

- **Primary requirement: ACID event-by-event insertion** — exactly one durable `INSERT` per recorded observation,
  committed transactionally so a crash leaves a consistent, recoverable log.
- **`UPDATE` and `DELETE` are FORBIDDEN** — observations are immutable once written; no edit, no tombstone, no
  compaction, no retention deletion in the canonical trail.
- **Monotonic append ordering** — the storage medium's **own intrinsic row order** (a SQLite `INTEGER PRIMARY KEY`
  rowid) provides the durable append sequence. This is **medium-intrinsic ordering** (the durable analog of the
  in-memory list's append index and of the reader's stream-intrinsic `physical_record_position`) — it is **NOT** a
  minted business/event identity and never replaces the opaque Silver pair, which remains the borrowed event
  identity.
- **WAL durability posture** — `journal_mode=WAL` with a `synchronous` setting chosen (in the field-shape/runtime
  charter) to guarantee per-event durability without sacrificing crash-consistency. (Exact PRAGMAs are deferred,
  §9.)

---

## 5. Analytics Ban (binding)

S1 durable storage is a **write-heavy durable sink, not an analytics database.** This charter designs **NO**
reporting interface, aggregation, GROUP BY/rollup, complex read API, query DSL, dashboard, materialized view,
index-for-analytics, or Parquet/columnar export. The only read surface contemplated is a **minimal append-order
replay/readback** mirroring the in-memory `snapshot()` (full-fidelity, in insertion order) for audit verification —
nothing analytic. Any analytics **mirror/export** is a **separate future boundary**, never folded into the S1
ingestion sink.

---

## 6. Hybrid Schema Discipline (binding, strategy only)

S1 must **NOT** fully flatten every frozen DTO field into dozens of typed SQLite columns. The canonical strategy is
a **small indexed audit envelope + a verbatim canonical payload**:

### 6a. Minimal indexed envelope (a few columns, for ordering / family / type / identity reference)
A small fixed set of columns sufficient for append-ordering and coarse audit filtering — conceptually:

- the **medium-intrinsic append sequence** (rowid `INTEGER PRIMARY KEY`, §4);
- **`observation_kind`** (`"SCORE"` / `"HALT"`) — the neutral equal-peer family marker, carried verbatim;
- a **family descriptor** column — the passive `score_family_descriptor` / `halt_family_descriptor`, carried
  verbatim (replay explainability only, never a decision/version);
- the **opaque Silver identity reference** — `artifact_locator` and `physical_record_position` carried **verbatim
  and opaque** (two separate inherited facts, never hashed/joined/collapsed into a synthetic key);
- the **`provenance_timestamp`** carried **opaquely** as a timestamp-only fact (never an identity, never a sort key
  that supersedes the medium-intrinsic append order).

These envelope columns are **carried verbatim**, never derived, normalized, or interpreted; they exist for durable
ordering and coarse audit reference, not analytics (§5).

### 6b. Verbatim canonical payload (one column, full content)
The **complete** `ObservationScoreRecord` / `ObservationHaltRecord` content — the full `family_payload` plus the
envelope fields not already in §6a — is stored as **one verbatim canonical payload value** (a single column),
**not** exploded into per-field columns. This preserves full fidelity for audit replay while keeping the schema
small and stable across both families.

### 6c. The unresolved payload-encoding question (handed to §9)
The §6b payload **embeds Python object references** (`score_basis_reference`, `halt_origin_reference`,
`opaque_cost_context` — §2). A durable text/blob payload cannot hold a live object by reference, so **how these
embedded frozen objects are durably captured** — i.e. the exact canonical payload **encoding** and the precise
projection of each embedded reference into durable form **without flattening (§6), without bypassing the frozen
factories, without adding semantic fields, and without deriving business/actionability meaning (§* below)** — is
the **central open question** this charter deliberately **does not resolve**. It is reserved for the field-shape
charter (§9).

---

## * Frozen DTO Respect (binding)

The durable adapter **conceptually maps** `ObservationScoreRecord` and `ObservationHaltRecord` **without** changing
their frozen definitions, **without** bypassing the B4/S4 factories that produce them, **without** adding semantic
fields, and **without** deriving any business/actionability meaning. It reads already-built records (e.g. via the
in-memory sink's `snapshot()` or a parallel durable record path) and persists them; it is a **separate durable
adapter**, never an edit to the frozen in-memory reference sink, which remains the in-memory substrate unchanged.

---

## 7. Lock-Placement & Package Boundary (binding)

Because `sqlite3` is a **forbidden import root** and `serialize`/`serialization`/`json`/`to_json`/`to_dict`/
`pickle` are **forbidden tokens** for every `phase6_1/*.py` runtime module (§2), the durable S1 adapter **MUST NOT**
live inside the locked `phase6_1/` passive package as-is. The canonical resolution is to place the durable adapter
in a **separate package** (e.g. a dedicated `phase6_1_persistence/` or `db/` module outside the passive lock
scope), so the passive package stays IO-free and lock-clean. A narrower alternative — a **separately-chartered,
closed per-basename lock exception** (mirroring the reader's closed `json` exception) admitting only `sqlite3` and a
single durable-serialization token for exactly one adapter basename — is **possible but secondary**; the **separate
package is preferred**. This charter **selects neither mechanism's details**; it only records that the placement
must be resolved (in §9's charter) before any runtime, since the in-memory sink and all passive modules stay
frozen and lock-clean.

---

## 8. Anti-Production Seal (binding)

This storage-medium design authorizes **NO** live trading, **NO** paper trading, **NO** canary, **NO** execution,
**NO** routing, **NO** order/sizing, **NO** actionability/intent/readiness, **NO** production-readiness, and **NO**
Phase 6.2 readiness. A durable audit trail of passive observations is a **record of what was observed**, never a
trigger to act. DRY_RUN posture and all constitution guardrails remain in force and untouched.

**Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit sites**;
`PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."

---

## 9. In-Memory Boundary Continuity & Precise State (binding)

- The **`2817948` state is preserved**: the **in-memory milestone is CLOSED + RATIFIED**, but **full Phase 6.1
  remains INCOMPLETE** until S1 durable storage is **designed, built, and ratified**. The in-memory reference sink
  is **not** durable storage.
- **Medium selected (docs-only): SQLite/WAL**, append-only ACID, hybrid envelope+payload **strategy** — **UNBUILT**.
  The exact schema DDL, envelope column types, payload **encoding** (incl. the §6c embedded-object-reference
  capture), PRAGMA/`synchronous` settings, and the §7 package placement are **all deferred**.
- **Phase 6.2: NOT ready.**

---

## 10. Still-Forbidden Work

- **No** runtime / tests / schema DDL / adapter / serialization encoding; **no** edit to the frozen in-memory sink
  or any frozen DTO/factory/component or lock test.
- **No** Parquet / CSV / Postgres / client-server RDBMS / NoSQL / external service / heavy DB for the S1 ingestion
  sink (§3); **no** analytics / reporting / aggregation / dashboard / export interface (§5).
- **No** `UPDATE` / `DELETE` / tombstone / compaction / retention-deletion in the canonical trail (§4); **no**
  minted business/event identity (the rowid is medium-intrinsic ordering only).
- **No** flattening of the full DTO into per-field columns (§6); **no** added semantic field; **no** derived
  business/actionability meaning; **no** factory bypass; **no** identity collapse of the Silver pair (§6a, §*).
- **No** placement of the SQLite adapter inside the locked `phase6_1/` package without resolving §7; **no**
  lock-exception authored here.
- **No** live / paper / canary / execution / routing / actionability / production durability claim (§8); **no**
  Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Next Safe Step

The evidence (the unresolved §6c payload-encoding of embedded object references, the §6a envelope column shapes,
and the §7 package-placement decision) shows the next gate is **design, not implementation**:

- A **separately-authorized S1 Durable Storage Field-Shape / Schema Charter** — fixing the exact append-only table
  schema (envelope columns + their types), the **canonical payload encoding** and the precise durable projection of
  each embedded frozen object reference (`score_basis_reference`, `halt_origin_reference`, `opaque_cost_context`)
  **without** flattening / factory-bypass / semantic addition / derived meaning, the WAL/`synchronous` PRAGMA
  posture, and the §7 package placement.
- **Only after** that field-shape/schema charter resolves the encoding may a **separately-authorized S1 durable
  storage runtime TDD slice** implement the append-only SQLite/WAL adapter (RED→GREEN, package-wide locks intact,
  frozen components untouched, append-only ACID, no analytics).
- **No implementation is authorized by this charter.** Full Phase 6.1 completion becomes claimable only after the
  durable S1 storage is designed, built, and ratified; Phase 6.2 readiness remains a later, separate determination.

**Conclusion:** the canonical durable medium for the S1 audit trail is selected — **SQLite in WAL mode**, the sole
medium for the real-time, write-heavy S1 ingestion sink (Parquet/CSV/Postgres/external/heavy DBs forbidden; any
analytics mirror is a separate boundary). S1 durable storage is a **strictly append-only, monotonic,
crash-consistent ACID log** (event-by-event `INSERT`; `UPDATE`/`DELETE` forbidden; medium-intrinsic rowid ordering,
never a minted identity). Its schema is a **hybrid**: a **small indexed envelope** (append sequence, `observation_kind`,
family descriptor, the opaque Silver identity reference, the opaque provenance timestamp — all verbatim) **plus a
single verbatim canonical payload** holding the full `ObservationScoreRecord` / `ObservationHaltRecord` content —
**not** a full per-field flattening. The frozen DTOs are **respected** (no definition change, no factory bypass, no
semantic field, no derived meaning); the durable adapter is a **separate adapter** over already-built records and
must live **outside** the locked `phase6_1/` package (since `sqlite3`/serialization are lock-forbidden there) or
under a separately-chartered closed lock exception. This design makes **NO** live/paper/canary/execution/routing/
actionability/production-readiness/Phase-6.2 claim; the **in-memory milestone stays closed** while **full Phase 6.1
remains incomplete** until durable S1 is designed, built, and ratified. The **central deferred question** is the
canonical payload **encoding** of the embedded frozen object references — reserved, with the schema DDL and package
placement, for a **separately-authorized S1 durable storage field-shape/schema charter**, then a runtime TDD slice.
**No executable work is authorized.**
