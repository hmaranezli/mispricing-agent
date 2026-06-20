# Phase 6.1 — Option-B Reader / IO Design Charter

> **This is a docs-only reader/IO architecture charter.** It defines, at **architecture level only**, the IO
> mechanics and **output contract** for reading the pinned Option-B JSONL-style event-level replay artifact. It
> **designs and builds nothing**: no reader/parser code, no class/dataclass/interface implementation, no read
> loop, no file-pointer algorithm, no `enumerate()`, no extraction mechanic. It authorizes NO runtime code, NO
> tests, NO lock-test edits, NO pytest, NO graphify, NO Python, NO imports, NO reader/parser code, NO concrete
> class/dataclass/interface implementation, NO B1 runtime implementation, NO B2 normalization change, NO log
> schema/persistence/storage implementation, NO B4 scoring, NO S4 materialization, NO S5 runner, NO Cell-3 route,
> NO Phase 6.2 work. It is subordinate to
> `docs/handoff/phase6_1_option_b_serialization_field_shape_charter.md`,
> `docs/handoff/phase6_1_option_b_event_level_replay_artifact_contract_amendment_charter.md`,
> `docs/handoff/phase6_1_replay_artifact_io_contract_amendment_decision_charter.md`,
> `docs/handoff/phase6_1_replay_depth_artifact_reader_charter.md`,
> `docs/handoff/phase6_1_replay_depth_reader_io_lock_exception_amendment_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `d685b9575b9fa91680d4b73c51295e36ad45018f`

**External review note:** Gemini Quant/Red-Team verdict — `d685b95` Option-B Serialization / Field-Shape Charter
is **APPROVED**. The next step is the **Reader / IO Design Charter**. The reader must be a **dumb, blind,
deterministic physical parser** for the pinned JSONL-style line-oriented format. This charter defines that
boundary.

---

## 1. Base / Dependency Chain

**Base commit:** `d685b9575b9fa91680d4b73c51295e36ad45018f`.

References:

- `…_option_b_serialization_field_shape_charter.md` — pinned the at-rest shape: **strict line-oriented
  (JSONL-style), one physical line = one event**; Silver tuple `(artifact_locator, physical_record_position)` is
  **IO-layer medium metadata, never in payload**; identity-in-payload fields forbidden; passive payload only;
  tombstones rejected; environment-agnostic locator; Gold deferred/additive; reader deferred (to **this** charter).
- `…_option_b_event_level_replay_artifact_contract_amendment_charter.md` — 1:1 invariant; INVALID
  batched/nested/multi-event/snapshot-container shapes; blind carriage; existing reader frozen.
- `…_replay_artifact_io_contract_amendment_decision_charter.md` — identity is artifact-origin/I/O-intrinsic, never
  a runtime counter.
- `…_replay_depth_artifact_reader_charter.md` / `…_replay_depth_reader_io_lock_exception_amendment_charter.md` —
  the existing single-artifact snapshot reader: read-only, single-record, decide-nothing, **frozen**.

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. What This Charter Defines (and what it does not)

This charter fixes, at **architecture level only**: (a) the **Option-B reader's output contract** (the tripartite
envelope), (b) its **blind/dumb-parser** obligations, (c) its **intrinsic IO-pointer** identity rule, and (d) its
**malformed-line** boundary behavior — conceptually. It defines **no** reader code, class, interface, read loop,
file-pointer algorithm, parser library, `enumerate()`, byte/line strategy, or runtime. The aim: specify the
boundary so a **future, separately-authorized** reader implementation stays a **dumb parser** under fixed
constraints.

---

## 3. Reader Role — Dumb, Blind, Deterministic Physical Parser

The Option-B reader is a **physical parser**, not a participant. Conceptually it reads **one physical line** of a
pinned JSONL-style Option-B artifact and produces **one** output envelope per line. It:

- **Decides nothing.** It scores, ranks, routes, filters, gates, and interprets **nothing**.
- **Is blind.** It carries facts opaquely; it does not understand their meaning.
- **Is deterministic.** Re-reading the same artifact yields the same envelopes in the same order, with the same
  identity tuples (artifact-origin determinism).
- **Is read-only.** It performs no writes, no mutation of the artifact, no network/environment access beyond the
  caller-supplied artifact.

---

## 4. Tuple Emission Lock — Tripartite Output Envelope

The reader's output contract is an **indivisible tripartite envelope** per physical line:

> **( parsed_payload, artifact_locator, physical_record_position )**

Binding constraints:

- **No bare payloads.** The reader **MUST NOT** conceptually yield a plain payload dictionary/object alone. Every
  emitted unit is the **whole** envelope; the payload never travels without its medium identity.
- **Indivisible.** The three parts are emitted together as one unit; downstream may not strip the identity from
  the payload at the reader boundary.
- **Docs-level contract shape only.** This is a **conceptual** output-contract shape — **not** a Python class,
  dataclass, NamedTuple, interface, or any concrete type. No implementation is defined.
- **Medium identity rides alongside, not inside.** `artifact_locator` and `physical_record_position` are carried
  **beside** the payload (the envelope's 2nd/3rd parts), never serialized into `parsed_payload` (§7).

---

## 5. Blind Courier Locator Lock

- The reader **receives `artifact_locator` as an opaque, caller-supplied value** and carries it verbatim into the
  envelope.
- The reader **must not** derive, normalize, join, absolutize, resolve, parse, validate, inspect, or mutate the
  locator. It is a pass-through opaque token.
- **Absolute machine paths remain forbidden as durable identity** (environment-agnostic locator rule, prior
  charter). The reader does not enforce or repair this — it simply never derives or absolutizes; supplying a
  portable locator is the **caller's** contract obligation, not the reader's to compute.

---

## 6. Intrinsic IO-Pointer Lock — `physical_record_position`

- `physical_record_position` must be tied **only** to the **active physical IO stream's own record/line position**
  within the single artifact being read — an artifact-origin / I/O-intrinsic fact of *this* stream.
- **Forbidden:** global counters, application-level counters, cross-file counters, persisted counters, or any
  process-state ordinal. The position is **not** application state; it is a property of the physical stream.
- **No mechanics designed.** This charter does **not** design the file-pointer algorithm, line/byte offset
  strategy, `enumerate()` loop, read-loop, or any extraction mechanic. It fixes only the **semantic constraint**:
  the position is intrinsic to the active physical stream of one artifact, never a counter living outside it.
- **Coincidence is not identity.** A loop index that happens to track physical order is still a runtime counter;
  only the stream's own intrinsic record position qualifies, and only as an IO fact (not designed here).

---

## 7. Medium vs. Payload Preservation

- `artifact_locator` and `physical_record_position` remain **IO-layer metadata** — observed from the medium/
  stream, carried in the envelope's 2nd/3rd slots.
- They must **never** be read from, written into, or trusted from payload fields. The reader does **not** consult
  the payload for identity, and does **not** inject identity into the payload.
- **Payload-authored identity remains forbidden:** `row_offset`, `read_index`, `read_offset`, `event_id`,
  `record_id`, `log_id`, `message_id`, `sequence_number`, `uuid`, `hash`, `fingerprint`, or any identity/
  uniqueness-implying payload key. If such a field appears in a payload, it is **not** trusted as identity (the
  authoritative identity is always the medium-observed tuple).

---

## 8. Dumb Physical Parser — No Semantic Validation

- The reader may **conceptually** parse one physical line into a `parsed_payload` object (structural parse only).
- The reader **MUST NOT** perform any semantic/business validation or interpretation: **no** price validity, **no**
  magnitude coercion/parsing, **no** cost interpretation, **no** venue logic, **no** staleness/freshness policy,
  **no** unit math, **no** scoring, **no** mapping, **no** defaulting, **no** calibration. Field-shape was pinned
  by the serialization charter; the reader does not re-validate or transform it.
- All semantic meaning is downstream (B2 normalization / Phase 5 / B4), under their own existing invariants — **not
  designed here**.

---

## 9. Structural Fault Tolerance — Malformed-Line Behavior (conceptual)

- A **malformed physical line** (one that cannot be structurally parsed into a payload) **must not be hidden or
  silently dropped.** Silent loss would corrupt replay completeness and audit truth.
- The reader boundary **must preserve `artifact_locator` + `physical_record_position` for the bad line** — the
  identity of *where* the fault occurred is retained even when the payload cannot be parsed.
- The output for such a line **may be classified as a defensive structural-halt envelope family** (a recorded
  structural outcome carrying the medium identity), **but** this charter **MUST NOT** design a concrete halt
  class, schema, fields, or S4 materialization. Only the **conceptual** requirement is fixed: malformed lines
  surface as identity-preserving structural outcomes, never as silent drops.
- This mirrors the ratified pass/halt symmetry: a structural fault is a **recorded outcome of equal standing**,
  not an erased one. (How it is later materialized into the durable log is **S4**, separately gated.)

---

## 10. One-Line One-Event Continuity & Frozen Existing Reader

- **1:1 continuity.** The reader design preserves the pinned invariant: **one physical line = exactly one logical
  event.** It performs **no** batching, no nested-array expansion, no multi-event splitting/merging, and never
  treats a line as a snapshot container. One line in ⇒ one envelope out.
- **Existing reader frozen.** The existing single-artifact snapshot reader
  (`phase6_1/b1_replay_depth_artifact_reader.py`) and its closed 8-field single-snapshot contract remain **frozen
  and untouched**. The Option-B reader is a **separate future boundary**; **no retrofitting**, extending, or
  reshaping of the existing reader is authorized or implied.

---

## 11. Gold Overlay Deferral

- A future **Gold** venue `message_id` / `sequence_number` remains **separate overlay work**.
- The reader **must not invent, infer, derive, or prioritize** Gold identity. It carries only what the medium and
  caller supply (the Silver tuple) plus the opaque payload.
- **No** Gold/Silver priority or resolution algorithm is designed. Gold, if ever present, is additive overlay
  only and never replaces/mutates the Silver tuple.

---

## 12. S2 / Slice-0B Cascade — Remaining Blockers

- **S2 identity: still BLOCKED.** This charter defines the reader **boundary** but **implements nothing** and
  **carries no evidence**. S2 stays BLOCKED until this reader/IO boundary is **implemented and ratified as carrying
  evidence** (real envelopes whose medium yields the `(artifact_locator, physical_record_position)` tuple). The
  opaque S2-owned slot stays **unfilled**.
- **Slice-0B field-level schema: still BLOCKED.** It may not define an event-identity field until S2 holds an
  authoritative **carried** borrowed identity source.
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.** Unchanged. **This charter authorizes nothing executable.**

---

## 13. Still-Forbidden Work

- **No** reader/parser code, class/dataclass/NamedTuple/interface implementation, read loop, file-pointer
  algorithm, `enumerate()`, byte/line offset arithmetic, parser library, or extraction mechanic.
- **No** bare-payload emission; the envelope is indivisible (§4).
- **No** locator derivation/normalization/join/absolutization/parse/validation/mutation (§5); **no** absolute
  machine path as durable identity.
- **No** global/application/cross-file/persisted counter as `physical_record_position` (§6); **no** runtime counter
  or loop index as identity.
- **No** reading identity from / writing identity into the payload (§7); **no** trusting payload-authored
  identity fields.
- **No** semantic/business validation, coercion, mapping, defaulting, calibration, scoring, venue/staleness/cost
  logic (§8).
- **No** concrete halt class/schema/fields; **no** S4 materialization (§9).
- **No** batching/nesting/multi-event/snapshot-container handling (§10); **no** retrofit/unfreeze of the existing
  reader.
- **No** invented/inferred/prioritized Gold identity; **no** Gold/Silver priority algorithm (§11).
- **No** B2 normalization change; **no** log schema/persistence/storage; **no** B4 scoring; **no** S5 runner; **no**
  Cell-3 route.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Slice-0B authorization; **no** S2 runtime/schema; **no** Phase 6.1 completion claim; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 14. Readiness Verdict

- **Option-B reader/IO boundary: DEFINED (docs-only), UNBUILT.** Output contract = the **indivisible tripartite
  envelope `(parsed_payload, artifact_locator, physical_record_position)`**; reader is a **dumb, blind,
  deterministic physical parser** (no semantic validation); **locator** is opaque caller-supplied (never derived/
  absolutized); **`physical_record_position`** is intrinsic to the active physical stream (never a runtime/global/
  persisted counter); **medium vs. payload** preserved (identity never in payload; payload-authored identity
  forbidden); **malformed lines** surface as identity-preserving defensive structural-halt envelopes (no concrete
  halt class/S4 designed); **1:1 line-event** continuity held; **existing reader frozen**; **Gold deferred**.
- **S2 identity: BLOCKED** until this boundary is implemented and ratified as carrying evidence. **Slice-0B
  field-level schema: BLOCKED.**
- **Phase 6.1: INCOMPLETE; Phase 6.2: NOT ready.**

---

## 15. Next Safe Step (recommendation only)

- A **separately-authorized Option-B reader implementation slice (TDD)** — implementing, under this boundary, a
  read-only dumb parser that emits the tripartite envelope per physical line, observes `physical_record_position`
  from the active stream, carries the opaque `artifact_locator` verbatim, and surfaces malformed lines as
  identity-preserving structural-halt envelopes — **separately authorized**, test-first, with the existing
  single-artifact snapshot reader staying frozen, and **still** designing no concrete halt schema or S4
  materialization (those remain separately gated).
- Only after the Option-B reader is **implemented and ratified as carrying** the artifact-origin tuple may the
  **S2 identity slice** fill the opaque slot, and only then may a **Slice-0B field-level schema** charter be
  authorized (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The Option-B reader slice, the S2 identity fill, the 0B
  schema, the concrete structural-halt class, S4 materialization, B4 scoring, S5 runner, durable persistence, the
  Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the Option-B reader/IO boundary is defined at architecture level — a **dumb, blind, deterministic
physical parser** of the pinned JSONL-style artifact whose output contract is the **indivisible tripartite envelope
`(parsed_payload, artifact_locator, physical_record_position)`**; the **locator** is an opaque caller-supplied
value (never derived/absolutized; absolute machine paths forbidden as durable identity), the
**`physical_record_position`** is intrinsic to the active physical IO stream (never a global/application/cross-file/
persisted counter, never a loop index), **identity is medium metadata never read from or written into the
payload** (payload-authored identity fields forbidden), the reader performs **no semantic validation**, **malformed
lines surface as identity-preserving defensive structural-halt envelopes** (no concrete halt class or S4 designed),
the **1:1 line-event invariant** holds, the **existing snapshot reader stays frozen**, and **Gold remains a
deferred additive overlay**. It is **UNBUILT** and **designs no reader/parser/runtime**; **S2 identity remains
BLOCKED** and **Slice-0B schema remains BLOCKED** until the reader is implemented and ratified as carrying
evidence; Phase 6.1 remains **incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
