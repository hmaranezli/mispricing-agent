# Phase 6.1 — Option-B Serialization / Field-Shape Charter

> **This is a docs-only serialization/field-shape charter.** It architecturally pins the **physical at-rest
> format** and the **conceptual payload field-shape** of the Option-B event-level replay artifact family, while
> preserving the **1 physical record = 1 logical event** invariant. It **designs and builds nothing**: no reader,
> parser, IO mechanics, read loop, file-pointer logic, `enumerate()`, counters, or extraction. It authorizes NO
> runtime code, NO tests, NO lock-test edits, NO pytest, NO graphify, NO Python, NO imports, NO reader/parser/IO
> mechanics, NO B1 runtime implementation, NO B2 normalization change, NO log persistence/storage implementation,
> NO B4 scoring, NO S4 materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work. It is subordinate to
> `docs/handoff/phase6_1_option_b_event_level_replay_artifact_contract_amendment_charter.md`,
> `docs/handoff/phase6_1_replay_artifact_io_contract_amendment_decision_charter.md`,
> `docs/handoff/phase6_1_replay_artifact_venue_origin_identity_evidence_review_charter.md`,
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `30930bcb749cbb9c933491f929c95c3cc361e45b`

**External review note:** Gemini Quant/Red-Team verdict — `30930bc` Option-B event-level replay artifact contract
is **APPROVED**. The next step is the **serialization/field-shape** charter, **not** reader/IO design. The
**physical at-rest shape must be pinned before any reader can remain a dumb parser.** This charter pins that
shape.

---

## 1. Base / Dependency Chain

**Base commit:** `30930bcb749cbb9c933491f929c95c3cc361e45b`.

References:

- `…_option_b_event_level_replay_artifact_contract_amendment_charter.md` — pinned the family: **one physical
  record = one logical event**; INVALID batched/nested/multi-event/snapshot-container shapes; Silver identity =
  abstract tuple `(artifact-locator concept, physical-record-position concept)`; Gold overlay additive-only;
  existing reader frozen; blind carriage.
- `…_replay_artifact_io_contract_amendment_decision_charter.md` — selected Option B; identity is
  artifact-origin/I/O-intrinsic, never a runtime counter.
- `…_replay_artifact_venue_origin_identity_evidence_review_charter.md` — Gold/Silver hierarchy; snapshot-level
  disqualified; physical I/O evidence standard.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. What This Charter Pins (and what it does not)

This charter fixes, at **architecture level only**: (a) the **physical at-rest format family** of Option-B
artifacts, and (b) the **conceptual key-level payload field-shape** of each one-event record. It defines **no**
reader, parser, IO mechanic, byte/line strategy, value coercion, mapping, validation algorithm, or runtime. The
goal: pin the at-rest shape so that a **future, separately-authorized** reader can be a **dumb parser** under fixed
constraints.

---

## 3. Physical At-Rest Format — Line-Oriented Pin

- **Selected family: strict line-oriented text artifact (JSONL-style), where each physical line is exactly one
  event record.** One newline-delimited physical line ⇒ one logical event ⇒ one self-contained record payload.
- **Justification for JSONL-style selection:** line-orientation makes the **1:1 physical-record-to-event**
  invariant a property of the **physical medium** itself — a physical line is an indivisible at-rest unit and a
  natural artifact-origin position carrier (§ the future Silver `physical_record_position` concept). A keyed
  per-line object gives a self-describing payload without nesting. (Format *family* is pinned; concrete encoding
  details, escaping, and parser behavior remain a future reader charter.)
- **INVALID at-rest shapes (explicitly forbidden):** nested arrays, batched records, multi-event records, a single
  line carrying more than one event, an array-of-events in one line/object, and any **snapshot-container** record
  (the Option-A model). A physical line that is not exactly one event is **not** a valid Option-B record.

---

## 4. Medium vs. Payload Separation (binding)

The Silver identity tuple concepts **`(artifact_locator, physical_record_position)`** are **medium/IO-layer
metadata — NOT payload data.** They **MUST NOT** be serialized inside the per-line payload.

- The **artifact_locator** is a property of *which artifact* the line belongs to; the **physical_record_position**
  is a property of *where the line physically sits* in that artifact. Both are observed at the **IO layer** when
  the artifact is read — they are **not** authored into the record's content.
- Serializing them into the payload would (a) duplicate medium facts as forgeable payload, (b) invite a
  payload-authored counter masquerading as artifact-origin position (forbidden), and (c) break the artifact-origin
  guarantee. They remain **future IO-layer metadata**, carried by B1 from the medium, never read from the payload.

---

## 5. Forbidden Identity-in-Payload Fields (explicit)

The per-line payload **MUST NOT** contain any field that is, names, or implies an identity:

- `artifact_locator`, `physical_record_position`, `row_offset`, `read_index`, `read_offset`, `record_id`,
  `event_id`, `log_id`, `message_id`, `sequence_number`, `seq_no`, `uuid`, `hash`, `fingerprint`, or any
  identity/uniqueness-implying key.
- No payload field may be a synthesized identity (no concatenation, hash, UUID, random, counter, timestamp-as-ID,
  or payload fingerprint).

Identity is **never** in the payload. It is a medium fact (§4), borrowed at the IO layer by a future reader (not
designed here).

---

## 6. Passive Payload Field-Shape (conceptual / key-level only)

Each one-event payload may carry **only passive observation facts** needed downstream — at **conceptual key level
only**, no concrete schema, types, formats, or ordering:

- **gross magnitude / value** — the observed gross-edge magnitude (passive, the Phase 5 `GROSS_EDGE` magnitude
  concept).
- **unit** — the unit bound to that magnitude (passive).
- **venue** — the source venue (passive provenance).
- **pair** — the source pair/instrument (passive provenance).
- **observed_at_epoch_ms** — the source-observed market timestamp. **It remains a timestamp, NEVER identity**, and
  is never repurposed as the event key.
- **future cost-context evidence shape** — *only if strictly passive* (the future Cell-3 real-cost evidence
  shape), carried as passive observation; **not designed here** and **not required** by this charter. The minimal
  shape needs no cost field.

These are **observation facts**, carried for downstream passive scoring. **No** field is a decision, score, route,
or identity. **No** concrete field names beyond these conceptual keys, **no** types, **no** serialization details
are fixed here.

---

## 7. Tombstone Ban — Forbidden Payload Content (binding)

The payload MUST explicitly **reject** all actionability/intent/policy content. It MUST NOT carry (nor any future
reader accept): `edge_direction`, `staleness_threshold_ms`/staleness policy, capacity activation/`capacity` pass
tokens, Shadow Intent, execution intent, routing, sizing, order/trade intent, paper/live readiness, or **any**
actionability field. Tombstones honored: `edge_direction` and `staleness_threshold_ms` remain tombstoned; capacity
remains non-activatable. Payload is **passive observation only**.

---

## 8. Environment-Agnostic Locator Rule

The future **artifact_locator** (a medium fact, §4 — not designed here) MUST be **portable / relative /
environment-agnostic**. **Absolute machine paths are forbidden as durable identity** (they are process/host-local,
non-portable, and break replay determinism across environments). This charter fixes only this **constraint**; it
**does not** design locator derivation, path mechanics, or any reader behavior.

---

## 9. Gold Overlay Deferral

- A future **Gold** venue `sequence_number` / `message_id` remains **overlay-compatible** but is **NOT required or
  designed** in this payload.
- A Gold value may appear in the payload **only if** evidence proves it is a **raw passive venue fact** carried by
  the source (not synthesized). Absent such proof, **no** Gold field is authored here.
- **Gold must never replace or mutate** the Silver medium metadata (§4). It is additive overlay only. **No**
  priority/resolution algorithm is designed.

---

## 10. Reader Deferral & Downstream Blind Carriage

- **Reader deferral.** This charter designs **no** parser library, read loop, file-pointer logic, `enumerate()`,
  counter, byte/line offset arithmetic, or extraction mechanic. The Option-B reader/IO design is a **separate
  future charter**; it must remain a **dumb parser** of this pinned at-rest shape.
- **Blind carriage.** Once a future reader carries the payload facts and the medium identity tuple, **B1 / B2 / B3
  / Producer / Phase 5 / B4 / S1 must not** inspect, branch on, cast, normalize, mutate, derive, filter, or
  reinterpret the identity tuple — no `int↔str` coercion, no string formatting, no prefixing, no concatenation.
  Passive payload facts likewise flow under existing passive invariants; identity flows opaquely end-to-end.

---

## 11. S2 / Slice-0B Cascade — Remaining Blockers

- **S2 identity: still BLOCKED.** This charter pins the at-rest **shape** but **implements nothing** and **carries
  no evidence**. S2 stays BLOCKED until the Option-B family is **later carried as evidence** (real artifacts whose
  medium yields the `(artifact_locator, physical_record_position)` tuple). The opaque S2-owned slot stays
  **unfilled**.
- **Slice-0B field-level schema: still BLOCKED.** A field-level log schema may not be defined until S2 holds an
  authoritative **carried** borrowed identity source.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged. **This charter authorizes nothing executable.**

---

## 12. Still-Forbidden Work

- **No** reader/parser/IO mechanics, read loop, file-pointer logic, `enumerate()`, counter, offset arithmetic, or
  extraction design.
- **No** identity-in-payload field (§5); **no** serialization of `(artifact_locator, physical_record_position)`
  into the payload (§4); **no** minting (concatenation/hash/UUID/random/counter/timestamp-as-ID/fingerprint).
- **No** absolute-machine-path locator; **no** locator derivation mechanics.
- **No** concrete schema types, encoding/escaping spec, field ordering, or serialization details beyond the
  line-oriented family pin and conceptual key-level field-shape.
- **No** batched/nested/multi-event/snapshot-container at-rest shape (all INVALID, §3).
- **No** B2 normalization change/design; **no** value coercion, mapping, derivation, defaulting, calibration, or
  validation algorithm beyond field-shape constraints.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/order/actionability payload
  content (§7).
- **No** required/designed Gold field unless proven a raw passive venue fact; **no** Gold replacing/mutating
  Silver; **no** Gold/Silver priority algorithm.
- **No** timestamp-as-identity; **no** `observed_at_epoch_ms` repurposed as the event key.
- **No** downstream inspection/branch/cast/normalize/mutate/derive/filter/reinterpret of identity (blind carriage).
- **No** log persistence/storage implementation; **no** S4 materialization; **no** B4 scoring; **no** S5 runner;
  **no** Cell-3 route.
- **No** Slice-0B authorization; **no** S2 runtime/schema; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 13. Readiness Verdict

- **Option-B at-rest shape: PINNED (docs-only), UNBUILT.** Physical format = **strict line-oriented (JSONL-style),
  one physical line = one event**; INVALID nested/batched/multi-event/snapshot-container shapes; **medium vs.
  payload separated** (identity tuple is IO-layer metadata, never payload); **identity-in-payload fields
  forbidden**; **passive payload** = gross magnitude/value, unit, venue, pair, `observed_at_epoch_ms`
  (timestamp-not-identity), optional strictly-passive future cost-context shape; **tombstones rejected**;
  **environment-agnostic locator** constraint; **Gold overlay deferred/additive**; **reader deferred**; **blind
  carriage** continued.
- **S2 identity: BLOCKED** until the family is carried as evidence. **Slice-0B field-level schema: BLOCKED.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.**

---

## 14. Next Safe Step (recommendation only)

- A **separately-authorized docs-only Option-B reader / IO design charter** — designing a **dumb parser** of this
  pinned at-rest shape that (a) reads one physical line as one event payload, (b) observes the
  `(artifact_locator, physical_record_position)` tuple **from the medium** as artifact-origin metadata (never a
  runtime counter), and (c) carries both opaquely under blind-carriage — **still** under separate authorization,
  with the existing single-artifact snapshot reader staying frozen.
- Only after the Option-B family is **carried as evidence** may the **S2 identity slice** fill the opaque slot, and
  only then may a **Slice-0B field-level schema** charter be authorized (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency; relevant to the optional passive cost-context shape of §6).
- **No implementation is authorized by this charter.** The Option-B reader/IO design, the S2 identity fill, the 0B
  schema, S4 materialization, B4 scoring, S5 runner, durable persistence, the Cell-3 route, the Shadow Intent
  Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the Option-B event artifact's at-rest shape is pinned at architecture level — a **strict
line-oriented (JSONL-style) artifact where one physical line = one logical event** (nested/batched/multi-event/
snapshot-container shapes INVALID); the **Silver identity tuple `(artifact_locator, physical_record_position)` is
IO-layer medium metadata, never serialized into the payload**, and **no identity-implying field may appear in the
payload**; the **passive payload** carries only observation facts (gross magnitude/value, unit, venue, pair,
`observed_at_epoch_ms` as a timestamp-not-identity, plus an optional strictly-passive future cost-context shape),
with **all actionability tombstoned**, the **locator constrained to be environment-agnostic**, **Gold deferred as
an additive overlay**, and the **reader deferred** to a separate charter. It is **UNBUILT** and **designs no
reader/parser/runtime**; **S2 identity remains BLOCKED** and **Slice-0B schema remains BLOCKED** until the family
is carried as evidence; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is
authorized.**
