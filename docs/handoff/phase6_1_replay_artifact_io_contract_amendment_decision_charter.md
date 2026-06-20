# Phase 6.1 — Replay Artifact / IO Contract Amendment Decision Charter

> **This is a docs-only architecture-decision charter.** It decides, **at architecture level only**, whether the
> replay artifact / IO contract should be amended to carry deterministic **event-level** origin identity, and which
> contract family should own it. It **designs and builds nothing**: no field names, no serialization, no
> extraction mechanics, no runtime. It authorizes NO runtime code, NO tests, NO lock-test edits, NO pytest, NO
> graphify, NO Python, NO imports, NO schema/runtime/interface edits, NO B1 runtime implementation, NO
> replay-reader implementation, NO B2 normalization change, NO log field-level schema, NO persistence/storage/
> serialization implementation, NO B4 scoring, NO S4 materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2
> work. It is subordinate to
> `docs/handoff/phase6_1_replay_artifact_venue_origin_identity_evidence_review_charter.md`,
> `docs/handoff/phase6_1_b1_replay_artifact_identity_source_decision_charter.md`,
> `docs/handoff/phase6_1_s2_identity_source_definition_charter.md`,
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `bf66adec65e1fe08a0d451f1c6b8c8f68f699889`

**External review note:** Gemini Quant/Red-Team verdict — `bf66ade` **ABSENT/BLOCKED** is **APPROVED**: the current
replay reader is single-artifact `json.load` → one record with a closed 8-field contract, so no event-level
`row_offset`/`read_index` currently exists. The identity knot must be resolved **at the replay artifact / IO
contract boundary** before S2 identity, Slice-0B schema, B4, S4, or S5 can proceed. This charter makes that
architecture-level decision.

---

## 1. Base / Dependency Chain

**Base commit:** `bf66adec65e1fe08a0d451f1c6b8c8f68f699889`.

References:

- `…_replay_artifact_venue_origin_identity_evidence_review_charter.md` — read-only evidence: Gold (venue
  sequence/message id) ABSENT; Silver (replay row_offset/read_index) ABSENT (closed single-artifact contract
  exposes no artifact-origin row order); snapshot-level DISQUALIFIED; no committed replay/sample artifact.
- `…_b1_replay_artifact_identity_source_decision_charter.md` — authoritative identity must live at the **source
  contract boundary**; **B1 runtime is a blind courier**.
- `…_s2_identity_source_definition_charter.md` — synthetic-identity ban; opaque S2-owned slot, unfilled.
- `…_replay_depth_artifact_reader_charter.md` / `…_replay_depth_reader_io_lock_exception_amendment_charter.md` —
  the single allowlisted IO module: read-only, **single-artifact**, decide-nothing, verbatim-carry.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. The Decision This Charter Makes

The evidence chain established that **no event-level identity exists today** and that resolving it requires a
**contract-boundary change**, not a downstream fix. The open architecture question: **should the replay artifact /
IO contract be amended to carry event-level origin identity, and if so, which contract family owns it?** This
charter evaluates Options A/B/C and **selects a direction**. It authorizes **no** amendment, field, format, or
code — only the architectural direction that a **future, separately-authorized** amendment charter would follow.

---

## 3. Governing Constraints (binding on any selected direction)

- **Borrow, do not mint.** No UUID, hash, random, counter, timestamp-as-ID, payload fingerprint, string
  concatenation, or `event_id`/`log_id` formula. Identity is an inherited external origin fact.
- **Composite identity mandate.** A bare `row_offset`/`array_index` alone is **not** globally sufficient. Any
  Silver identity must be a **pure tuple of inherited facts** — conceptually `(artifact_locator,
  artifact_order_position)` — **not** a concatenated synthetic string. **No concrete field names or serialization
  are defined here.**
- **Strict extraction boundary.** Identity must be an **artifact-origin fact exposed by the IO/replay contract**.
  **Runtime business-logic counters are forbidden** as identity. **No extraction mechanics are designed here** —
  ownership and constraints only.
- **Gold/Silver optionality.** Gold venue `sequence_number`/`message_id` remains **preferred if ever available**;
  any Silver `(artifact_locator, position)` must be **forward-compatible with future Gold without breaking
  replay**. **No runtime priority algorithm is designed here.**
- **Granularity.** Identity must be **event-/row-/message-level**; snapshot-level `raw_snapshot_identity`/
  `depth_snapshot_identity` remains **insufficient as sole identity** (deferred tuple-component only).
- **No normalization creep.** **No** B2 modification/design; **no** mapping, value coercion, cost logic, scoring,
  or Phase 5 behavior.
- **Blind courier.** B1 may only **carry** an inherited identity; B2/B3/Producer/Phase 5/B4/S1 may only **carry it
  blindly** — no inspection, branching, derivation, mutation, or fallback.

---

## 4. Artifact-Origin Fact vs. Runtime Counter (the decisive test)

The crux of every option is whether the position is an **artifact-origin fact** or a **runtime counter**:

- **Artifact-origin fact (permitted).** A deterministic, reproducible property of how the artifact **physically
  stores** the data — e.g. the ordinal of an element within an artifact-stored ordered array, or the physical
  line/record position within a physical-record file. Re-reading the same artifact always yields the same value;
  it exists **independent of the reader**.
- **Runtime counter (forbidden).** A process-local variable the reader increments while iterating (`i += 1`, an
  enumeration index treated as identity). It is reader state, not artifact state; it simulates identity and is
  banned (Anti-Counter Firewall of the prior charters).

A position may serve as Silver identity **only** when the **contract** authoritatively defines it as an
artifact-origin fact — never when it is merely the reader's loop variable that happens to coincide with order.

---

## 5. Option A — Amend the Existing Single-Artifact JSON Contract

**Shape.** Extend the current one-record artifact to contain an **ordered event/depth array**; derive identity
from the **artifact-origin array position** of each element, composited as `(artifact_locator, array_position)`.

**Assessment.**

- Array position *can* be an artifact-origin fact (the array literally stores elements in order; element *N* is
  stable on re-read).
- **But** the current artifact is, by its frozen contract, **one snapshot = one record** (closed 8-field,
  `json.load` of a single mapping, unknown keys fail fast). Retrofitting an ordered array **overloads** a
  contract whose entire ratified meaning is "one physical artifact carries exactly one depth snapshot." It would
  require **unfreezing and re-shaping** the single-artifact reader/contract, and risks the **array-index ↔
  runtime-counter ambiguity** (§4) precisely because the snapshot contract was never designed around physical
  record ordering.
- **Verdict: REJECTED as the primary direction.** It conflates a snapshot contract with an event-stream contract
  and disturbs a frozen boundary to do so. (Not forbidden in principle — array position *is* artifact-origin — but
  architecturally the wrong home for event-level identity.)

---

## 6. Option B — Define a Separate Event-Level Replay Artifact Family

**Shape.** A **distinct** replay artifact family of **physical-record** form (JSONL/CSV/stream-like), where **each
physical record is exactly one replay/loggable event**. Identity is the artifact-origin composite
`(artifact_locator, physical_record_position)` — the locator naming the artifact and the physical row/offset/read
position naming the event within it.

**Assessment.**

- **Native event-level granularity.** One physical record = one event is exactly the required granularity (§3);
  no snapshot-to-event fan-out problem.
- **Artifact-origin by construction.** Physical record position (line/record ordinal or byte offset) is a
  deterministic property of the physical artifact, reproducible on replay — an artifact-origin fact, **not** a
  runtime counter, **provided the contract defines it as such** (§4).
- **Preserves the frozen single-artifact reader.** A new family leaves the existing single-snapshot reader/
  contract **untouched and frozen**; no unfreezing required.
- **Composite-compliant & Gold-forward-compatible.** Identity is a pure tuple `(artifact_locator,
  physical_record_position)` (no concatenation); a future Gold venue `message_id`, if ever ingested, can ride the
  same event records without breaking the Silver tuple or replay.
- **Verdict: SELECTED architectural direction** — the correct contract family to **own** event-level origin
  identity.

---

## 7. Option C — Remain BLOCKED/DEFERRED

**Assessment.** Reserved for the case where **no** family can be justified without minting. That case does **not**
hold: Option B carries identity as a genuine artifact-origin fact without minting, concatenation, or runtime
counters. **Verdict: NOT TAKEN** for the *architectural direction* (Option B is justifiable). **However**, Option
C's posture **still governs all executable work**: until the Option-B amendment is **separately authored and
ratified**, no identity is actually carried, so S2 and Slice-0B remain BLOCKED (§9).

---

## 8. Selected Direction & Future Identity Source

- **Selected architectural direction: Option B** — a **separate event-level replay artifact family** (physical
  one-record-per-event form) **owns** the authoritative event-level origin identity. Option A is **rejected**
  (overloads the frozen single-snapshot contract); Option C is **not taken** as the direction (B is justifiable
  without minting) but its **no-executable-work** posture remains in force until B is built and ratified.
- **Future identity source:** a **Silver composite** — the pure inherited-fact tuple **`(artifact_locator,
  physical_record_position)`** (artifact locator + physical row/offset/read position), **not** array index of the
  existing snapshot artifact, **not** a bare offset alone, **not** a runtime counter, **not** snapshot-level
  labels. **Gold** (venue `sequence_number`/`message_id`) remains the **preferred** source **if ever available**
  and must be **forward-compatible** with the Silver tuple without breaking replay. **No concrete field names,
  serialization, or priority algorithm are defined here.**

---

## 9. Implications for S2 Identity & Slice-0B Schema

- **S2 identity: still BLOCKED.** The decision **selects a valid source family** (the unblock precondition), but
  **no source is carried yet** — the Option-B amendment is unbuilt. The opaque S2-owned identity slot stays
  **unfilled** until that amendment is separately authored, ratified, and actually carries the tuple.
- **Slice-0B field-level schema: still BLOCKED.** It may not define an event-identity field until S2 holds an
  authoritative **borrowed** source (the carried Option-B tuple). Defining one now would force minting.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged. **This decision authorizes nothing executable.**

---

## 10. Still-Forbidden Work

- **No** minting (generate/calculate/hash/concatenate/increment/count/randomize/fingerprint); **no** `event_id`/
  `log_id` formula; **no** filling of the opaque S2 slot.
- **No** runtime/loop counter or enumeration index as identity; **no** array index of the existing snapshot
  artifact as identity.
- **No** concrete field names, serialization format, file format spec, or extraction/reader mechanics for the
  Option-B family.
- **No** amendment of the existing single-artifact reader/contract; **no** unfreezing of frozen B1/reader
  boundaries.
- **No** B2 normalization change/design; **no** mapping/coercion/cost/scoring/Phase-5 behavior.
- **No** timestamp-as-identity; **no** `id()`/memory identity; **no** promotion of snapshot-level labels to sole
  identity.
- **No** log field-level schema; **no** persistence/storage/serialization implementation.
- **No** S4 materialization; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** Gold/Silver runtime priority algorithm.
- **No** downstream inspection/derivation/mutation/reinterpretation/fallback of carried identity (blind courier).
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** S2 runtime/schema; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 11. Readiness Verdict

- **Architectural direction: SELECTED — Option B** (separate event-level replay artifact family owns identity);
  **future source = Silver composite `(artifact_locator, physical_record_position)`**, Gold venue message-id
  preferred-if-available and forward-compatible. Option A REJECTED; Option C not taken as direction.
- **S2 identity: BLOCKED** (family selected, source not yet carried). **Slice-0B field-level schema: BLOCKED.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.**

---

## 12. Next Safe Step (recommendation only)

- A **separately-authorized docs-only Option-B replay event-artifact contract amendment charter** — defining, at
  contract level, that the new event-artifact family carries the artifact-origin `(artifact_locator,
  physical_record_position)` tuple as a borrowed, immutable, deterministic, verbatim-carried identity (meeting the
  §3 constraints and the prior §9 minimum-evidence standard), **still designing no concrete fields, serialization,
  reader mechanics, or runtime** until a subsequent, separately-authorized slice. Only that amendment can move
  Silver from ABSENT to AVAILABLE.
- Only after the amendment is **carried and ratified** may the **S2 identity slice** fill the opaque slot, and only
  then may a **Slice-0B field-level schema** charter be authorized (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The Option-B amendment, the S2 identity fill, the 0B
  schema, S4 materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the identity knot is resolved **in direction only** — **Option B** (a separate event-level
replay artifact family) is selected to **own** authoritative event-level origin identity, sourced as the Silver
composite **`(artifact_locator, physical_record_position)`** (borrowed, not minted), with **Gold** venue
message-id preferred-if-available and forward-compatible; **Option A is rejected** and **Option C is not taken** as
the direction. No source is yet carried, so **S2 identity remains BLOCKED** and **Slice-0B schema remains
BLOCKED**; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
