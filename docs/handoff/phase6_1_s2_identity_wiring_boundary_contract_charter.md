# Phase 6.1 — S2 Identity Wiring Boundary / Contract Charter

> **This is a docs-only contract-boundary charter.** It defines, **at contract level only**, the boundary for a
> future S2 identity wiring component that consumes the ratified `OptionBEventEnvelope` — **without implementing
> it**. It **designs and builds nothing**, modifies no reader, and writes no schema. It authorizes NO runtime
> code, NO tests, NO lock-test edits, NO schema/runtime/interface edits, NO reader modification, NO
> B1/B2/B3/Phase 5/producer modification, NO Slice-0B schema, NO B4 scoring, NO S4 materialization, NO S5 runner,
> NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_option_b_reader_to_s2_identity_wiring_planning_charter.md`,
> `docs/handoff/phase6_1_option_b_reader_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`,
> `docs/handoff/phase6_1_s2_identity_source_definition_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `bf074ad55b1d80da291d01e38eefee8335d131cb`

**External review note:** Gemini Quant/Red-Team verdict — `bf074ad` is **APPROVED**. The state **"S2 unblock
candidate available"** is correct; **S2 is NOT UNBLOCKED**. The next safe step is this docs-only S2 identity
wiring **boundary/contract** charter, **before** any runtime wiring TDD.

---

## 1. Base / Dependency Chain

**Base commit:** `bf074ad55b1d80da291d01e38eefee8335d131cb`.

References:

- `…_option_b_reader_to_s2_identity_wiring_planning_charter.md` — mapped the wiring topology: a future client
  consumes `OptionBEventEnvelope`, unpacks it once, routes payload toward B2 and the opaque Silver pair toward
  the S2 slot; identity path bypasses Phase 5/scoring/B4; pass/halt symmetry; "S2 unblock candidate available."
- `…_option_b_reader_tdd_closeout_ratification.md` — froze the reader island and its envelope contract; future
  S2 work consumes it **as a client**, never reshapes it.
- `…_s2_provenance_chain_locks_identity_planning_charter.md` / `…_s2_identity_source_definition_charter.md` —
  synthetic-identity ban; opaque, S2-owned identity slot; Silver composite `(artifact_locator,
  physical_record_position)`, borrowed not minted; reference-preservation ≠ durable identity.
- `…_s1_durable_passive_shadow_log_boundary_charter.md` — S1 owns the opaque identity slot; `observed_at_epoch_ms`
  is a timestamp, not identity.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- The Option-B reader is **BUILT + RATIFIED** (`5fece9f`, sealed `03c7fbf`): a frozen, isolated, stream-only
  physical parser emitting the immutable, non-dict tripartite `OptionBEventEnvelope(parsed_payload_or_local_halt,
  artifact_locator, physical_record_position)` per physical line.
- It is **not wired**: nothing consumes its envelope as carried evidence. The Silver tuple components are emitted
  but not carried.
- **S2 Identity: BLOCKED**; exact state **"S2 unblock candidate available"** (§7). The existing evaluation spine
  (Phase 5 passive socket, passive producer, Master B3) is **BUILT + RATIFIED** and **untouched**.

---

## 3. Frozen Reader, Client-Only (governing principle)

- The Option-B reader is a **frozen dependency**. The future wiring boundary may **only consume**
  `OptionBEventEnvelope`.
- **No** reader edit, refactor, parameter change, signature change, behavior change, widening, subclassing,
  wrapping, or monkeypatching is proposed or permitted. The wiring boundary is a **client**, never a boundary
  author.
- If the wiring ever appears to require a reader change, that is a signal to **stop and re-charter**, not to
  reshape the frozen island.

---

## 4. Contract Boundary Definition

The future wiring component is a **single, additive client boundary** sitting **downstream of the reader and
upstream of the existing spine**. Its contract (at boundary level only — **no** implementation, signature, type,
or schema fixed here):

- **Input:** exactly one `OptionBEventEnvelope`, consumed from the frozen reader as a client. (Per-envelope; the
  reader's stream iteration is the reader's own concern, untouched.)
- **Responsibility:** to **open the envelope once** (§5) and **route** its three parts down two separate paths
  (§6) — and **nothing else**. It is a router, not a computer: it normalizes nothing, derives nothing, scores
  nothing, decides nothing.
- **Outputs (two separate paths):** the **payload path** (toward B2 normalization) and the **identity path** (the
  opaque Silver pair toward the S2 identity/provenance slot).
- **Statelessness/passivity:** the boundary is passive and per-envelope; it holds no cross-envelope state, derives
  no aggregate, and emits no actionability.

This charter fixes the **boundary's role and constraints**, not its code, types, or interfaces.

---

## 5. Single Envelope-Unpacking Boundary

- There is **one and only one** architectural point at which `OptionBEventEnvelope` is opened: the wiring boundary
  of §4.
- **No downstream component** (B2, B3, the producer, Phase 5, B4, S1, S4, S5) may independently re-open,
  reinterpret, or re-derive identity from the envelope **or** from the payload. The envelope is unpacked exactly
  once, at the single boundary; thereafter, the payload and the identity pair travel as already-separated values.
- This single-unpacking rule is what keeps medium/payload separation and blind carriage intact end-to-end.

---

## 6. Dual-Path Handoff Map

At the single unpacking boundary, the three envelope parts are routed:

| Envelope part | Path | Rule |
|---|---|---|
| `parsed_payload_or_local_halt` (parsed payload) | **Payload path → B2 normalization** | Handed onward to the downstream normalization boundary **as-is**. The wiring boundary does **not** normalize it (§7-Normalization). |
| `parsed_payload_or_local_halt` (local parse-halt) | **Halt path (§8 symmetry)** | Carried as a halt outcome, never dropped, never routed into B2 math. |
| `artifact_locator` | **Identity path → S2 identity/provenance slot** | Carried **intact, opaque, indivisible** (§7-Opaque). |
| `physical_record_position` | **Identity path → S2 identity/provenance slot** | Carried **intact, opaque, indivisible** (§7-Opaque). |

- **Identity-path purity.** From unpacking to the S2 slot, the Silver pair touches **no** Phase 5 math, **no**
  net-edge/cost arithmetic, **no** B4 scoring, **no** business logic, and **no** semantic validation. It is a
  provenance channel only.
- **Medium/payload separation preserved.** Identity is taken **only** from the envelope's 2nd/3rd parts, **never**
  from inside the payload; payload-authored identity fields are never promoted.

---

## 7. Two Boundary Rules: Normalization & Opaque Tuple

### 7a. Explicit Normalization Boundary

- This wiring contract **DOES NOT perform B2 normalization.** It only **hands the parsed payload onward** to the
  downstream normalization boundary.
- It performs **no** payload mapping, coercion, defaulting, unit math, venue logic, freshness/staleness checks,
  or cost interpretation. Normalization is B2's, under B2's own ratified invariants — untouched here.

### 7b. Opaque Silver Tuple

- `artifact_locator` + `physical_record_position` must travel **intact, opaque, and indivisible**.
- **Forbidden:** hash, UUID, string concatenation, counter, timestamp-as-ID, payload fingerprint, cast,
  normalize, derive, fallback, or any synthetic event key.
- The tuple is **never collapsed** into a string or a durable generated ID. It remains a **pure pair of inherited
  facts** carried by reference.

---

## 8. Pass / Halt Symmetry

The boundary covers **both** envelope families equally:

- **Parsed-payload envelopes** — payload → B2 path; Silver pair → S2 slot.
- **Local parse-halt envelopes** (`OptionBLocalParseHalt`) — carried as a **halt outcome of equal standing**,
  never silently dropped and never routed into business math. **The malformed-line local halt preserves the same
  `(artifact_locator, physical_record_position)`** as any other envelope from that physical line — a halt event
  is identity-anchored exactly like a pass event.
- This charter **does NOT design or authorize S4 global halt materialization.** It fixes only that the local-halt
  envelope's identity pair is preserved and symmetric with the pass case. How a local parse-halt is ever
  materialized into a durable log is **S4's**, separately gated.

---

## 9. Blind Carriage & S2 State Precision

### 9a. Blind Carriage

- Once the identity pair enters the pipeline, **B1 / B2 / B3 / Producer / Phase 5 / B4 / S1 may only carry the
  identity reference blindly** — by reference, opaque.
- **No** inspect, branch, validate, mutate, normalize, fallback, or priority logic on the identity pair by any
  downstream boundary. It is never a decision input. The wiring boundary is the only component that touches the
  envelope, and it only **routes**.

### 9b. S2 State Precision

- **Exact state remains: "S2 unblock candidate available."**
- **S2 is NOT UNBLOCKED.** This charter does **not** declare S2 unblocked and does **not** fill the opaque S2
  slot. S2 becomes **UNBLOCKED only after** the future runtime wiring is **built, tested, and ratified** as
  actually **carrying** the Silver pair as pipeline evidence into the slot. A defined contract is not carried
  evidence.

---

## 10. Slice-0B Gate & Existing-Spine Isolation

- **Slice-0B field-level schema remains BLOCKED** until S2 identity wiring is **implemented and ratified.** This
  charter designs **no** log schema, **no** persistence, **no** serialization.
- **Existing spine untouched.** The Phase 5 passive socket, the passive producer, and the Master B3 client remain
  **frozen and unmodified**; this contract implies **no** change to them and **no** B4/runner readiness. The
  wiring boundary is additive and downstream.

---

## 11. Still-Forbidden Work

- **No** reader modification/refactor/parameter/behavior change/widening; **no** envelope contract change.
- **No** second envelope-unpacking point; **no** downstream re-open/reinterpret/re-derive of identity from
  envelope or payload.
- **No** B2 normalization/mapping/coercion/defaulting/unit-math/venue/staleness/cost interpretation in the wiring
  boundary.
- **No** minting from the identity pair (hash/UUID/concatenation/counter/timestamp-as-ID/fingerprint); **no**
  collapsing the tuple into a string or durable generated ID; **no** cast/normalize/derive/fallback.
- **No** routing of identity through Phase 5 math / scoring / B4 / semantic validation; **no** reading identity
  from the payload.
- **No** declaration that S2 is UNBLOCKED; **no** filling of the opaque S2 slot; **no** carried-evidence claim.
- **No** S4 global halt materialization design; **no** dropping/reclassifying local parse-halts.
- **No** downstream inspect/branch/validate/mutate/normalize/fallback/priority on the identity reference (blind
  carriage).
- **No** Slice-0B field-level schema; **no** log schema/persistence/serialization.
- **No** B1/B2/B3/Phase 5/producer modification; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 13. Next Safe Step

- A **separately-authorized S2 identity wiring runtime TDD slice** — implementing, under this contract boundary,
  the client that consumes one `OptionBEventEnvelope`, unpacks it at the single point, hands the parsed payload to
  the downstream normalization boundary, and carries the opaque, indivisible Silver pair toward the S2 slot, with
  pass/halt symmetry — test-first, reader and spine frozen, designing **no** S4 materialization and **no** 0B
  schema. After that slice is **built, tested, and ratified**, S2 may be reclassified from *unblock-candidate* to
  **UNBLOCKED** and the opaque slot filled.
- Only after S2 identity is **carried and ratified** may a **Slice-0B field-level schema** charter be authorized
  (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The runtime wiring slice, the S2 identity fill, the
  Slice-0B schema, S4 materialization, B4 scoring, the S5 runner, durable persistence, the Cell-3 route, the
  Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the S2 identity wiring boundary is defined at **contract level only** — a single, additive,
**client-only** boundary that consumes one ratified `OptionBEventEnvelope`, opens it at **exactly one** point, and
routes `parsed_payload_or_local_halt` toward **B2 normalization** (performing no normalization itself) while
carrying the **opaque, intact, indivisible Silver pair `(artifact_locator, physical_record_position)`** toward the
**S2 identity/provenance slot**, **bypassing all Phase 5 math, B4 scoring, business logic, and semantic
validation**, preserving **pass/halt symmetry** (local parse-halts keep the same locator + position, never
dropped), under strict **blind carriage**, with the reader and the existing spine **frozen and untouched**. The
exact state remains **"S2 unblock candidate available"** — **S2 is NOT UNBLOCKED** until the runtime wiring is
built, tested, and ratified as carrying the pair; **Slice-0B schema remains BLOCKED**; Phase 6.1 remains
**incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
