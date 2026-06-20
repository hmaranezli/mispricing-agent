# Phase 6.1 — B1 / Replay Artifact Authoritative Identity Source Decision Charter

> **This is a docs-only decision charter.** It decides **where** the authoritative **event-level** identity
> source must live so that S2 can **borrow** identity without minting it — using repo/contract evidence only.
> Finding no event-level source currently carried, it returns **BLOCKED/DEFERRED** and **invents no source**. It
> **designs and builds nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO pytest, NO graphify,
> NO Python, NO imports, NO schema/runtime/interface edits, NO B1 runtime implementation, NO replay-reader
> implementation, NO log field-level schema, NO persistence/storage/serialization design, NO B4 scoring, NO S4
> materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work. It is subordinate to
> `docs/handoff/phase6_1_s2_identity_source_definition_charter.md`,
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `a86782e71ce4523421617fdc4be29e37180f743b`

**External review note:** Gemini Quant/Red-Team verdict — the `a86782e` **BLOCKED/DEFERRED** status is **STRONGLY
APPROVED**: the system correctly refused to mint synthetic identity and correctly rejected snapshot-level
`raw_snapshot_identity` as insufficient for event-level durable provenance. This charter is the **next safe step**
recommended there: decide **where** an authoritative event-level identity source must live — at the **replay
artifact contract boundary** or the **venue/B1 origin contract boundary** — and re-confirm, by evidence, whether
any such source is currently carried.

---

## 1. Base / Dependency Chain

**Base commit:** `a86782e71ce4523421617fdc4be29e37180f743b`.

References:

- `…_s2_identity_source_definition_charter.md` — classified candidate identity sources from repo evidence and
  found the two permitted authoritative classes (venue `sequence_number`/`message_id`; replay
  `row_offset`/`read_index`) **ABSENT**; `raw_snapshot_identity` **DEFERRED** (authority unproven, snapshot-level);
  verdict **BLOCKED/DEFERRED**. Recommended resolving the source **at B1 ingestion**, borrowed and evidence-proven.
- `…_s2_provenance_chain_locks_identity_planning_charter.md` — banned synthetic identity; separated in-process
  reference preservation from durable identity; pinned the **opaque, S2-owned** identity slot and left it
  **unfilled**.
- `…_s1_durable_passive_shadow_log_boundary_charter.md` — S1 owns the opaque identity slot held by reference;
  `observed_at_epoch_ms` is a timestamp, **not** identity.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. The Question This Charter Answers

The S2 identity charter established **what** may serve as identity (borrowed external origin facts only) and found
none carried. The open question it deferred is **where the authoritative source must be defined** — so that, when
one ever exists, S2 borrows it from a single, contract-fixed origin rather than improvising it downstream. This
charter answers the **location/ownership** question and re-confirms the evidence; it does **not** build, read, or
extract anything.

---

## 3. Contract-First Resolution (governing principle)

Authoritative event-level identity must be **defined at a contract boundary that owns origin facts** — namely:

- the **Replay Artifact Contract Boundary** (the replay artifact's own deterministic origin metadata), or
- the **venue / B1 origin contract boundary** (an externally-supplied venue/exchange origin identifier).

**B1 runtime is only a blind courier.** It may *carry* an inherited identity that the contract already defines;
it may **not** *originate*, *improvise*, *compute*, or *assign* identity. Identity is a property of the **source
contract**, not of the act of reading. If the contract does not carry it, B1 runtime **must not** fabricate it to
fill the gap (see §5, §7).

---

## 4. Borrow, Do Not Mint (restated, binding)

Identity must be **inherited as an external origin fact**. The system **MUST NOT** generate, calculate, hash,
concatenate, increment, count, randomize, fingerprint, or otherwise **mint** identity. Specifically forbidden as
identity: **UUID/`uuid4`**, **hash/`hashlib`/SHA/MD5/payload fingerprint**, **random/PRNG/nonce**, **counter/
auto-increment/sequence invented at the sink or in a loop**, **timestamp-as-ID** (`observed_at_epoch_ms`/
`retrieval_epoch_ms` are timestamps, never keys), **string concatenation** into a composite key, and any other
**`event_id`/`log_id` uniqueness formula**.

---

## 5. Anti-Counter Firewall (explicit)

A **runtime loop counter is not authoritative provenance.** In-memory stateful counters used to *simulate*
identity — e.g. `i = 0; … i += 1`, an enumeration index, a read-loop ordinal, a "row number" computed while
iterating, or any per-process incrementing variable — are **explicitly banned** as the identity source. Such a
counter is process-local, non-deterministic across runs, and indistinguishable from minting. Position/ordering
that is **authentically part of the replay artifact contract** (see §6, class **B**) is a *contract fact*, not a
runtime counter; only the former may ever qualify, and only if the **contract** carries it.

---

## 6. Candidate Source Location Classification (evidence-based)

Repo evidence inspected read-only (no extraction designed):

- **`phase6_1/b1_depth_source_contract.py`** carries: `depth_source_field`, `depth_source_artifact`,
  `depth_source_contract`, `depth_observed_at_epoch_ms`, `depth_retrieval_epoch_ms`, and **`depth_snapshot_identity`**
  (snapshot-level). It carries **no** `sequence_number`/`message_id`/`row_offset`/`read_index`/`event_id`/
  `record_id`.
- **`phase6_1/b2_normalization_contract.py`** carries: `source_artifact`, `source_field`, `venue`, `pair`,
  `retrieval_epoch_ms`, `observed_at_epoch_ms`, and **`raw_snapshot_identity`** (snapshot-level). It carries
  **no** sequence/message/offset/record identifier.

| Candidate location | Owning boundary | Repo evidence | Verdict |
|---|---|---|---|
| **A. Venue / B1 origin message ID** (`sequence_number` / `message_id`) | venue / B1 origin contract | **Not carried** anywhere in B1/B2 | **ABSENT** |
| **B. Replay artifact `row_offset` / `read_index`** (immutable artifact-origin fact) | replay artifact contract | **Not carried** anywhere in B1/B2 | **ABSENT** |
| **C. `raw_snapshot_identity`** (and B1's `depth_snapshot_identity`) | B2 / B1 carrier (snapshot-level) | Carried, but **snapshot-level**, and authority as external origin metadata **unproven** (fixtures resemble internal labels); one snapshot may yield multiple shadow events | **DISQUALIFIED as sole event identity** — DEFERRED tuple-component only |
| **D. No currently carried event-level source** | — | A and B ABSENT; C insufficient | **CURRENT STATE** |

---

## 7. Row-Offset Lock

Replay `row_offset` / `read_index` is permitted as identity **only** when treated as an **immutable
artifact-origin fact that belongs to the replay artifact contract** — i.e. the artifact *itself* deterministically
carries it as origin metadata. It may **not** be **invented downstream**, computed by a reader, or synthesized
from a read loop (§5). This charter **does not** design extraction code, file-reader mechanics, parsing, or any
read path; it only fixes that **if** such a fact is ever carried, it must be **defined in and owned by the replay
artifact contract** and merely **carried** by B1.

---

## 8. Granularity Mandate

Identity must be **event-level / row-level / message-level** — sufficient to distinguish each discrete shadow
observation event. **Snapshot-level** labels (`raw_snapshot_identity`, `depth_snapshot_identity`) remain
**disqualified as the sole durable event identity**, because score events (B4) and materialized-halt events (S4)
are **downstream of, and can be multiple per,** a single snapshot. They may **only** remain **possible tuple
components** of a future inherited-fact identity **if** their authoritativeness is later separately proven **and**
an authoritative event-level discriminator (class A or B) is carried to complete the tuple. This charter neither
proves their authority nor invents a discriminator, and performs **no** concatenation/hashing/transformation of
them.

---

## 9. Blind Carriage (restated, binding)

- **B1 may carry** the inherited identity once a contract defines one — by reference, as an opaque origin fact.
- **B2 / B3 / Producer / Phase 5 / B4 / S1 may carry it blindly only** — they may **not** inspect, parse, format,
  derive, mutate, reinterpret, compare lexically, or apply any **fallback** to it.
- No boundary may substitute a different or weaker identity, and none may compute one when the contract omits it
  (omission ⇒ BLOCKED, never improvisation).

---

## 10. Decision & Blocker Status

- **Location decision (ownership).** The authoritative event-level identity source **belongs to the source
  contract boundary** — the **Replay Artifact Contract Boundary** (for replay-origin `row_offset`/`read_index`,
  class **B**) **or** the **venue / B1 origin contract boundary** (for venue `sequence_number`/`message_id`,
  class **A**). It does **not** belong to, and must **not** be improvised inside, **B1 runtime**, which is a
  **blind courier**. Of the two, the source must be the one that authentically carries the origin fact; per
  current evidence **neither** carries it.
- **Evidence verdict.** Current state is **D — no currently carried event-level source.** Classes A and B are
  **ABSENT**; class C is **snapshot-level / unproven** and disqualified as sole identity. Therefore the
  authoritative event-level identity source is **BLOCKED/DEFERRED**. Nothing is minted; no source is pretended.
- **S2 identity: BLOCKED.** S2 cannot borrow an event-level identity until a contract (replay artifact or
  venue/B1 origin) authoritatively carries one and it is ratified.
- **Slice-0B field-level schema: BLOCKED.** It remains blocked until S2 has an authoritative **borrowed**
  identity source; defining an identity field now would force minting (forbidden). **No 0B schema is authorized.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged.

---

## 11. Still-Forbidden Work

- **No** minting of identity (generate/calculate/hash/concatenate/increment/count/randomize/fingerprint); **no**
  `event_id`/`log_id` formula; **no** filling of the opaque S2 slot.
- **No** loop counter / enumeration index / read-ordinal used as identity (Anti-Counter Firewall, §5).
- **No** promotion of `raw_snapshot_identity`/`depth_snapshot_identity` to sole event identity; **no**
  transformation/concatenation/hashing of them.
- **No** timestamp-as-identity; **no** `id()`/memory identity as durable identity.
- **No** B1 runtime implementation; **no** replay-reader/extraction/file-reader/parsing design.
- **No** log field-level schema; **no** persistence/storage/serialization/database/file design.
- **No** S4 materialization; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** downstream inspection/derivation/mutation/reinterpretation/fallback of carried identity (blind carriage
  only, §9).
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no**
  7.x/8.x work.

---

## 12. Readiness Verdict

- **Authoritative event-level identity source: location decided (source contract boundary — replay artifact or
  venue/B1 origin; never improvised in B1 runtime), but currently ABSENT → BLOCKED/DEFERRED.** No venue
  sequence/message ID and no replay `row_offset`/`read_index` is carried; snapshot-level labels are disqualified
  as sole identity.
- **S2 identity: BLOCKED** until the source contract authoritatively carries an event-level origin identity and it
  is ratified.
- **Slice-0B field-level schema: BLOCKED** until S2 has an authoritative borrowed identity source.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged.

---

## 13. Next Safe Step (recommendation only)

- A **separately-authorized docs-only Replay Artifact / Venue Origin Contract evidence-review** — establishing,
  by inspection of the **actual replay artifact contract and any venue origin contract**, whether either *can be
  authorized to carry* a deterministic, immutable event-level origin identity (replay `row_offset`/`read_index`
  as an artifact-contract fact, or venue `sequence_number`/`message_id`). If yes, a subsequent charter may
  **ratify** that contract-defined source (still designing no runtime/reader). If neither carries nor can be
  authorized to carry one, the source remains **BLOCKED/DEFERRED** — never minted.
- Only after an authoritative **borrowed** source is **carried and ratified** may the **S2 identity slice** fill
  the opaque slot, and only then may a **Slice-0B field-level schema** charter be authorized (under the S1
  boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The replay/venue contract evidence-review, the S2 identity
  fill, the 0B schema, S4 materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route, the
  Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the authoritative event-level identity source **must live at the source contract boundary** (replay
artifact contract or venue/B1 origin contract) and **never be improvised inside B1 runtime, which is a blind
courier**; per current repo evidence **no such event-level source is carried** (classes A and B ABSENT;
snapshot-level class C disqualified as sole identity) → **BLOCKED/DEFERRED** (nothing minted, nothing invented).
**S2 identity remains BLOCKED**; **Slice-0B schema remains BLOCKED**; Phase 6.1 remains **incomplete** and
Phase 6.2 **not ready**. **No executable work is authorized.**
