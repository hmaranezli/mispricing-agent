# Phase 6.1 S2 — Identity Source Definition Charter

> **This is a docs-only classification charter.** It classifies the **authoritative external identity source** for
> future shadow-log events **using repo evidence only**, and — finding none carried — returns **BLOCKED/DEFERRED**
> without minting identity. It **designs and builds nothing** and **invents no source**. It authorizes NO runtime,
> NO tests, NO lock-test edits, NO Python, NO imports, NO schema/runtime/interface edits, NO log field-level
> schema, NO persistence/storage/serialization design, NO B4 scoring, NO S4 materialization, NO S5 runner, NO
> Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `f9bcd6cc5b415214ef4d0b3b9298de413a17db5b`

**External review note:** Gemini Quant/Red-Team verdict — `f9bcd6c` S2 Provenance Chain Locks charter **APPROVED**;
Slice-0B schema **remains BLOCKED**; next step is to **classify the authoritative external identity source
without minting identity**. This charter is that classification.

---

## 1. Base / Dependency Chain

**Base commit:** `f9bcd6cc5b415214ef4d0b3b9298de413a17db5b`.

References:

- `…_s2_provenance_chain_locks_identity_planning_charter.md` — banned synthetic identity; separated reference
  preservation from durable identity; pinned the **opaque, S2-owned** identity slot and left it **unfilled**;
  deferred the identity **source** to this charter.
- `…_s1_durable_passive_shadow_log_boundary_charter.md` — S1 owns the opaque identity slot; `observed_at_epoch_ms`
  is a timestamp, **not** identity.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Borrow, Do Not Mint (governing principle)

Durable identity must be **inherited as an external fact** from B1 ingestion / venue origin / replay-artifact
metadata. The system **MUST NOT** generate, calculate, hash, concatenate, increment, count, randomize, or
otherwise **mint** identity. If no authoritative external source is already carried, identity is **BLOCKED/
DEFERRED** — it is **not** invented to fill the gap.

---

## 3. Evidence Inventory Inspected (read-only)

A repo sweep of the B1/B2 carriers (`phase6_1/b1_depth_source_contract.py`,
`phase6_1/b2_normalization_contract.py`) for origin-identity metadata
(`sequence_number`, `message_id`, `seq_no`, `msg_id`, `row_offset`, `read_index`, `offset`, `event_id`,
`record_id`) returned **no matches** — none of these fields exist anywhere in the carriers.

The identity-adjacent fields that **are** carried on `PublicRawSnapshotRecord`:

- `raw_snapshot_identity` — a per-snapshot exact non-empty **string** carried verbatim (fixtures use labels such
  as `"replay-fixture-0001"`).
- `source_artifact`, `source_field` — provenance strings.
- `retrieval_epoch_ms`, `observed_at_epoch_ms` — **timestamps** (provenance/context, **not** identity).

No venue-provided sequence/message identifier and no replay-artifact row/read index is present as origin metadata.

---

## 4. Permitted Source Classes (per constraint)

Only these may ever serve as durable identity, and **only if already carried**:

- **(C1)** Venue/exchange-provided `sequence_number` / `message_id`, if already carried.
- **(C2)** Replay-artifact `row_offset` / `read_index`, **only** if already carried by the replay artifact as
  deterministic origin metadata.
- **(C3)** A **pure tuple of inherited facts only** — multi-part identity composed of already-carried authoritative
  origin facts, with **no string concatenation and no synthetic key construction**.

---

## 5. Candidate Source Classification (evidence-based)

| Candidate | Class | Repo evidence | Verdict |
|---|---|---|---|
| Venue `sequence_number` / `message_id` | C1 | **Not carried** anywhere in B1/B2 | **ABSENT** |
| Replay-artifact `row_offset` / `read_index` | C2 | **Not carried** anywhere in B1/B2 | **ABSENT** |
| `raw_snapshot_identity` (carried string) | (candidate C3 component) | Carried, but **(a)** not evidenced as authoritative external origin metadata (fixtures look like internal labels), and **(b)** **snapshot-level, not event-level** — one snapshot can yield multiple shadow events | **DEFERRED** (unproven authority; insufficient granularity alone) |
| Pure inherited-fact tuple | C3 | Would require ≥1 authoritative origin fact **plus** an authoritative **event-discriminator**; neither is carried/evidenced | **BLOCKED** (no inherited facts to compose; must not invent a discriminator) |
| `observed_at_epoch_ms` / `retrieval_epoch_ms` | — (timestamp) | Carried, but a **timestamp is never identity** (§ ban) | **REJECTED as identity** |
| Hash / `id()` / counter / concatenation | — (synthetic) | Forbidden by S2 provenance locks | **FORBIDDEN** |

**No candidate is AVAILABLE.** The two permitted authoritative classes (C1, C2) are **ABSENT**; the only carried
identity-adjacent value (`raw_snapshot_identity`) is **DEFERRED** (authority unproven and snapshot-level, so
insufficient as an event identity on its own); a composed tuple (C3) is **BLOCKED** for lack of carried inherited
facts and an authoritative event-discriminator.

---

## 6. `raw_snapshot_identity` Disposition

`raw_snapshot_identity` is **not ratified** as the event identity source by this charter, because:

- **Authority unproven.** Repo evidence does not establish it as an externally-supplied venue/artifact origin
  fact; current values resemble internal/test labels. Treating it as authoritative would be **assuming**, not
  borrowing.
- **Wrong granularity.** It identifies a **raw snapshot**, not a **shadow log event**. Score events (B4) and
  materialized-halt events (S4) are **downstream** of a snapshot and can be multiple per snapshot; the snapshot
  identity cannot, alone, distinguish them.

It is recorded only as a **DEFERRED candidate *component*** of a future inherited-fact tuple — usable **only if**
(a) its authoritativeness as external origin metadata is separately proven, **and** (b) an authoritative,
already-carried **event-level discriminator** exists to complete the tuple. This charter **does not** invent that
discriminator and **does not** concatenate, hash, or otherwise transform `raw_snapshot_identity`.

---

## 7. Standing Locks (restated, binding)

- **No hashing.** SHA/MD5/`hashlib`/`hash(payload)` or any payload-derived fingerprint as identity is **banned**.
- **No timestamp identity.** `observed_at_epoch_ms` (and `retrieval_epoch_ms`) remain timestamp/provenance
  context, **never** identity.
- **Blind carriage.** B2 / B3 / Producer / Phase 5 / B4 / S1 may carry identity/provenance **blindly** (by
  reference); they may **not** inspect, derive, reinterpret, or modify it.
- **No minting** of any kind (generate/calculate/hash/concatenate/increment/count/randomize).

---

## 8. Pass / Halt Symmetry

Whatever authoritative identity source is **eventually** ratified must apply **equally** to future **B4 score
events** and future **S4 materialized-halt events** (structural and semantic/math families). Neither family may
use a weaker or different identity source; both inherit the same external origin identity under the same rules.
This charter designs neither B4 scoring nor S4 materialization.

---

## 9. S1 / S2 Boundary & Slice-0B Gate

- **S1 owns** the opaque identity slot (held by reference, never inspected).
- **S2 classifies** the authoritative source — and here finds **none carried**, so the slot's source remains
  **DEFERRED**.
- **Slice-0B field-level schema remains BLOCKED.** It may not proceed: a field-level schema cannot responsibly
  define an event-identity field while the authoritative source is ABSENT/DEFERRED (defining one would force
  minting — forbidden). **No 0B schema design is authorized.**

---

## 10. Still-Forbidden Work

- **No** minting of identity (generate/calculate/hash/concatenate/increment/count/randomize); **no** `event_id`/
  `log_id` formula; **no** filling of the opaque slot.
- **No** promotion of `raw_snapshot_identity` to ratified identity; **no** transformation/concatenation of it.
- **No** timestamp-as-identity; **no** hash/`id()`/counter identity.
- **No** log field-level schema; **no** persistence/storage/serialization/database/file design.
- **No** S4 materialization; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** inspection/derivation/modification of carried identity/provenance by any boundary (blind carriage only).
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no**
  7.x/8.x work.

---

## 11. Readiness Verdict

- **Authoritative identity source: ABSENT → verdict BLOCKED/DEFERRED.** No venue sequence/message identifier and
  no replay-artifact row/read index is carried; `raw_snapshot_identity` is a DEFERRED, unratified candidate
  component only. Preferred **BLOCKED/DEFERRED** over inventing a source.
- **Slice-0B field-level schema: remains BLOCKED.** It may **not** proceed until an authoritative external
  identity source is **carried** and ratified.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged.

---

## 12. Next Safe Step (recommendation only)

- A **separately-authorized docs-only decision** on **whether B1 ingestion / the replay artifact can supply an
  authoritative deterministic origin identity** — i.e. evidence-check whether the replay artifact format carries
  (or can be authorized to carry, as a **B1 ingestion-contract** matter) a deterministic `row_offset`/`read_index`,
  or whether venue metadata carries a `sequence_number`/`message_id`. Identity must be **ingested at the source
  (B1)**, **borrowed not minted**, and proven by evidence — **or** remain BLOCKED. This charter recommends that
  the identity source be resolved at **B1 ingestion**, not downstream, because only B1 touches origin metadata.
- Only after an authoritative source is **carried and ratified** may a **Slice-0B field-level schema** charter be
  authorized (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The B1 origin-identity decision, the 0B schema, S4
  materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the authoritative external identity source is **ABSENT** in current repo evidence → **BLOCKED/
DEFERRED** (nothing minted, nothing invented); **Slice-0B schema remains BLOCKED**; Phase 6.1 remains
**incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
