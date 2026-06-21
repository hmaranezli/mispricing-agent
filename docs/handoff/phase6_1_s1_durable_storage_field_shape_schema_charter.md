# Phase 6.1 — S1 Durable Storage Field-Shape & Schema Charter

> **This is a docs-only schema/field-shape charter.** It pins the **exact physical SQLite/WAL schema**, the
> **durable projection strategy** for embedded object references, the **PRAGMA posture**, and the **package
> placement** for the durable S1 sink. It **designs and builds nothing**: no runtime, no tests, no migration, no
> adapter code. It authorizes NO runtime code, NO tests, NO lock-test edits, NO frozen-component edits, NO analytics
> interface, NO live/paper/canary, NO execution/routing/actionability, NO production-readiness, NO Phase 6.2 work,
> NO pytest, NO graphify. It is subordinate to `docs/handoff/phase6_1_s1_storage_medium_charter.md`,
> `docs/handoff/phase6_1_in_memory_pipeline_milestone_closeout_ratification.md`, the S1 in-memory sink charter, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `83ed6f019e015302350dbe7a8f46bc81137bec15`

---

## 1. Base / Purpose

**Base commit:** `83ed6f019e015302350dbe7a8f46bc81137bec15`.

The S1 Storage-Medium Charter (`83ed6f0`) selected **SQLite/WAL**, an append-only ACID posture, and a hybrid
envelope+payload **strategy**, while deferring the exact schema, the embedded-object-reference encoding, the PRAGMA
settings, and the package placement. This charter **pins all four** so that a future, separately-authorized runtime
TDD slice has an unambiguous, fabrication-free target.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Evidence-First Schema Inspection (frozen fields cited before naming columns)

From source (frozen, unchanged):

- **`phase6_1/s1_in_memory_observation_sink.py`** — `ObservationScoreRecord` and `ObservationHaltRecord` share the
  exact **five-field envelope**: `identity_evidence`, `observation_kind`, `provenance_timestamp`,
  `opaque_cost_context`, `family_payload`. `identity_evidence` must be an exact `S2IdentityWiringCandidate`.
- **`phase6_1/s2_identity_wiring_candidate.py`** — `S2IdentityWiringCandidate(forwarded_payload_or_local_halt,
  artifact_locator, physical_record_position)`; the opaque Silver pair `(artifact_locator,
  physical_record_position)` is borrowed by reference, never minted.
- **SCORE `family_payload`** (`b4_passive_scoring.py:56-62`): `passive_score_magnitude` (str, = `net_edge_value`),
  `score_basis_reference` (the frozen `NetEdgeCalculationResult` **object**), `score_inputs_summary` (a
  `(source_venue, source_pair)` tuple of strs), `score_unit_context` (str, = `net_edge_unit`),
  `score_family_descriptor` (str). Envelope: `observation_kind="SCORE"`, `provenance_timestamp =
  observed_at_epoch_ms`, `opaque_cost_context` = the Cell-3 cost-context tuple (**object**).
- **HALT `family_payload`** (`s4_halt_materialization.py:71-75`): `halt_origin_reference` (the frozen halt-carrier
  **object** — `OptionBLocalParseHalt` / `B3PassiveClientWiringError` / `BlockedPacket`), `opaque_upstream_context`
  (`None`), `halt_family_descriptor` (str). Envelope: `observation_kind="HALT"`, `provenance_timestamp = None`,
  `opaque_cost_context` = `None` (parse-halt) or the cost tuple (blocked path).
- **`NetEdgeCalculationResult`** (the `score_basis_reference` object, `net_edge_calculator_boundary.py:48-64`) is
  **all evidentiary scalar strings**: `component_name`, `origin_component`, `origin_result_status`, `status`,
  `gross_edge_value`, `gross_edge_unit`, `total_cost_value`, `total_cost_unit`, `net_edge_value`, `net_edge_unit`,
  `cost_component_count`, `source_contract`, `source_artifact`, `source_field`, `calculation_method`,
  `boundary_version` — projectable to text without resurrection.

**No invented fields.** Every column/projection below is **directly supported** by the frozen records above or the
medium charter — there is **no** fabricated `timestamp`/`venue`/`pair`/etc. that the records do not carry.
(`provenance_timestamp` and the `(venue, pair)` of `score_inputs_summary` are present **only** because the frozen
records carry them.)

---

## 3. Quarantine Package Placement (binding)

The durable adapter **MUST** live in a **new, isolated top-level package, `phase6_1_s1_storage/`** — **outside** the
pure-logic `phase6_1/` package. The pure `phase6_1/` package stays **completely ignorant** of `sqlite3`, disk I/O,
the canonical-text-payload encoding module, and durable persistence; it imports nothing from `phase6_1_s1_storage/`.
The durable adapter imports the frozen DTO **types** from `phase6_1` **read-only** (to admit/project them) and never
edits them. Because the package-wide forbidden-token / forbidden-import locks scan only `phase6_1/*.py`, the
separate `phase6_1_s1_storage/` package may use `sqlite3` and a durable text-encoding without tripping those locks
and **without** any lock-exception edit. (A per-basename lock exception inside `phase6_1/` is **rejected** in favour
of this clean quarantine.)

---

## 4. Durable Projection, Not Object Preservation (binding)

Embedded live Python object references — `score_basis_reference`, `halt_origin_reference`, and the
`opaque_cost_context` tuple — **MUST NOT** be preserved, pickled, marshalled, restored, or treated as a live
identity. They are **irreversibly projected** into **canonical textual evidence / opaque structural strings**
containing **only evidentiary facts**, with **no** semantic derivation, **no** actionability, and **no** object
resurrection. The durable record is an **audit shadow** of what was observed, not a rehydratable object graph.

Projection rules (per embedded reference):

- **`score_basis_reference`** (`NetEdgeCalculationResult`) → a deterministic text projection of its **evidentiary
  scalar fields** (§2 list: status, gross/total-cost/net values+units, cost_component_count, source_*,
  calculation_method, component/boundary names) — copied **verbatim** as strings, never recomputed or interpreted.
- **`halt_origin_reference`** (one of the three frozen carriers) → an **opaque structural stringification**: the
  carrier's exact **type name** plus its **evidentiary content** carried verbatim as text (e.g.
  `OptionBLocalParseHalt` → its `raw_line`; `BlockedPacket` → its evidentiary scalar fields; a wiring error → its
  type name and message text). The object is never resurrected and its type is recorded as a label, not a live
  class.
- **`opaque_cost_context`** (the Cell-3 `ObservableCostValidityContext` tuple, or `None`) → a deterministic text
  projection of the context's **evidentiary scalar facts** (`cost_component_type`, `signed_decimal_value`, `unit`,
  `zero_cost_evidence`, `validity_assertion_type`, `valid_from_epoch_ms`, `valid_until_epoch_ms`, `source_*`), or an
  explicit **null marker** when `None`.

All projection is **lossy-by-design** for object identity (irreversible) and **lossless** for the evidentiary text
facts it copies; it derives no new meaning.

---

## 5. Exact Hybrid SQLite DDL (binding)

A **single append-only table** with a tiny audit envelope plus **exactly one** `canonical_text_payload` column —
**no** full DTO flattening into per-field columns:

```sql
CREATE TABLE IF NOT EXISTS s1_observation_audit_log (
    append_sequence          INTEGER PRIMARY KEY,   -- medium-intrinsic monotonic rowid (append order); NOT an event identity
    observation_kind         TEXT    NOT NULL,      -- 'SCORE' | 'HALT', carried verbatim (the neutral equal-peer family marker)
    family_descriptor        TEXT    NOT NULL,      -- score_family_descriptor | halt_family_descriptor, verbatim (replay explainability)
    artifact_locator         TEXT    NOT NULL,      -- opaque Silver locator, verbatim
    physical_record_position TEXT    NOT NULL,      -- opaque Silver position, verbatim opaque string (never interpreted/sorted)
    provenance_timestamp     TEXT,                  -- opaque timestamp-only fact, verbatim; NULL allowed (HALT carries None)
    canonical_text_payload   TEXT    NOT NULL       -- full deterministic canonical-text projection of the whole record (§6)
);
```

- **Seven columns only** (one PK + five tiny envelope columns + one payload) — the §2 sixteen-field
  `NetEdgeCalculationResult` and the full `family_payload` live **inside** `canonical_text_payload`, never exploded
  into columns.
- `append_sequence` is the **medium-intrinsic** monotonic rowid (the durable analog of the in-memory append index
  and the reader's stream-intrinsic position); it is **NOT** a minted business/event identity. The borrowed event
  identity remains the opaque Silver pair (`artifact_locator`, `physical_record_position`).
- `physical_record_position` and `provenance_timestamp` are stored as **verbatim opaque TEXT** (value-preserving
  stringification only) and are **never** numerically interpreted or used as a sort key — `append_sequence` is the
  sole ordering.
- **No secondary indexes** are created (an index on kind/family/timestamp would be analytics-oriented, §8). The PK
  rowid is the only index, used solely for append-order replay/readback.

### 5a. `canonical_text_payload` encoding
`canonical_text_payload` holds a **deterministic canonical-text encoding** (a JSON-text document with a **fixed,
stable key order** for reproducibility) of the **complete** record projection of §6, produced by the
`phase6_1_s1_storage/` encoder. The encoding is byte-stable for identical input (audit reproducibility) and is
**write-only canonical evidence** — never parsed back into live objects.

---

## 6. Canonical Payload Projection Content (binding)

`canonical_text_payload` projects the **whole** record (envelope + identity + family) as evidentiary text:

**Common (both families):** `observation_kind`; `family_descriptor`; `identity_evidence` →
`{artifact_locator, physical_record_position}` (opaque Silver pair, verbatim) plus an opaque projection of
`forwarded_payload_or_local_halt`; `provenance_timestamp` (verbatim string, or null marker); `opaque_cost_context`
→ the §4 cost projection or null marker.

**SCORE-only:** `passive_score_magnitude` (verbatim); `score_unit_context` (verbatim); `score_inputs_summary` →
`[source_venue, source_pair]` (verbatim strings); `score_basis_projection` → the §4 `NetEdgeCalculationResult`
scalar-field text projection.

**HALT-only:** `halt_origin_projection` → the §4 carrier stringification (`carrier_type` label + evidentiary
content); `opaque_upstream_context` → null marker.

No field is added beyond what the frozen records carry; no value is derived, normalized, or interpreted.

---

## 7. Append-Only Seal (binding)

The schema and adapter are **strictly append-only and monotonic**: **exactly one ACID `INSERT` per observation**,
committed transactionally. **`UPDATE` and `DELETE` are FORBIDDEN** — no edit, tombstone, compaction, or
retention-deletion in the canonical trail; no column is mutable; no design implies mutable state. An **optional**
runtime hardening (a `BEFORE UPDATE`/`BEFORE DELETE` trigger that `RAISE(ABORT, ...)`s) **may** be added by the
runtime slice purely to enforce immutability — it is a safeguard, not analytics, and is not mandated here.

---

## 8. PRAGMA Posture (binding)

- **`PRAGMA journal_mode = WAL;`** — mandated (write-ahead logging; concurrent durable appends, single recoverable
  file, crash-consistency).
- **`PRAGMA synchronous = FULL;`** — **mandated** for this audit sink. From an audit-safety perspective, `FULL`
  fsyncs the WAL on every commit, so each committed observation is durable even across an OS crash or power loss.
  The charter **deliberately does NOT choose `NORMAL`**: in WAL mode `NORMAL` is crash-safe against application
  crashes and never corrupts the database, but a power-loss/OS-crash can lose the **most recent** unsynced
  transaction(s) — unacceptable for an evidentiary audit trail where the last record matters. **Documented
  tradeoff:** `FULL` reduces write throughput (an fsync per commit); this is **accepted** because per-event
  durability of the audit record outweighs throughput for a passive shadow sink.
- Other PRAGMAs (e.g. `busy_timeout` for concurrent writers) are **deferred** to the runtime slice; none may relax
  the WAL + `synchronous=FULL` durability posture.

---

## 9. Analytics Ban & Anti-Production Seal (binding)

- **Analytics ban:** **no** reporting layer, dashboard, query DSL, complex read API, aggregation/rollup,
  materialized view, Parquet/columnar export, analytics mirror, or **extra analytics index**. Only a **minimal
  append-order replay/readback** (full-fidelity, in `append_sequence` order, mirroring the in-memory `snapshot()`)
  may exist, purely for audit verification.
- **Anti-production:** this charter authorizes **NO** live trading, paper trading, canary, execution, routing,
  order/sizing, actionability/intent/readiness, production-readiness, or Phase 6.2 readiness. A durable audit trail
  records what was observed; it never triggers action. DRY_RUN and all constitution guardrails remain in force.
- **Capacity invariant unchanged:** `CapacityConstraintGate` stays deferred / non-activatable with **0 emit sites**;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."

---

## 10. Vocabulary Safety (binding)

This charter uses **canonical text payload encoding**, **durable projection**, and **opaque structural
stringification**. The future runtime lives in `phase6_1_s1_storage/` (outside the lock scope, §3), so its use of
`sqlite3` and a text encoding creates **no** token-lock collision. The pure `phase6_1/*.py` runtime surfaces stay
**free** of `sqlite3`/serialization/encoding tokens — no `phase6_1/` module gains any storage/encoding reference,
import, or name from this design.

---

## 11. Precise State & Next Safe Step

- **Schema, projection, PRAGMA posture, and package placement: PINNED (docs-only), UNBUILT.** Exact DDL (§5),
  embedded-reference projection (§4, §6), `journal_mode=WAL` + `synchronous=FULL` (§8), and the
  `phase6_1_s1_storage/` quarantine (§3) are now unambiguous.
- The **`2817948`/`83ed6f0` state is preserved**: in-memory milestone **CLOSED**, **full Phase 6.1 INCOMPLETE**
  until durable S1 is built and ratified. **Phase 6.2: NOT ready.**
- **Next safe step:** a **separately-authorized S1 durable storage runtime TDD slice** — implementing the
  `phase6_1_s1_storage/` append-only SQLite/WAL adapter exactly per §3–§8 (RED→GREEN; one ACID `INSERT` per
  observation; `UPDATE`/`DELETE` forbidden; the §6 canonical-text projection with irreversible object-reference
  stringification; `WAL` + `synchronous=FULL`; minimal append-order readback only; package-wide locks intact;
  frozen components and the in-memory reference sink untouched), plus its closeout/ratification. **No** runtime is
  authorized here.

**Conclusion:** the durable S1 SQLite/WAL schema is pinned — a **single append-only table** `s1_observation_audit_log`
with a **tiny indexed envelope** (`append_sequence` medium-intrinsic rowid, `observation_kind`, `family_descriptor`,
the opaque Silver pair `artifact_locator`/`physical_record_position`, the opaque `provenance_timestamp`) **plus
exactly one** `canonical_text_payload` column holding a **deterministic canonical-text projection** of the whole
`ObservationScoreRecord`/`ObservationHaltRecord` (no per-field flattening). Embedded live object references
(`score_basis_reference`, `halt_origin_reference`, `opaque_cost_context`) are **irreversibly projected** into
canonical textual evidence / opaque structural strings — evidentiary facts only, **never** pickled, resurrected, or
treated as live identity, with no derived/actionable meaning. The sink is **strictly append-only** (one ACID
`INSERT`; `UPDATE`/`DELETE` forbidden; `append_sequence` is medium-intrinsic ordering, not a minted identity), runs
under **`WAL` + `synchronous=FULL`** (audit-safety bias; documented throughput tradeoff), bans all analytics, and is
**quarantined** in a new `phase6_1_s1_storage/` package so the pure `phase6_1/` package stays ignorant of
`sqlite3`/persistence/encoding. This authorizes **NO** live/paper/canary/execution/routing/actionability/
production-readiness/Phase-6.2 work; the in-memory milestone stays closed; **full Phase 6.1 remains INCOMPLETE**
until the durable S1 runtime is built and ratified. **Next safe step:** a separately-authorized S1 durable storage
runtime TDD slice. **No executable work is authorized.**
