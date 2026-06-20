# Phase 6.1 — Option-B Reader → S2 Identity Wiring Planning Charter

> **This is a docs-only planning charter.** It architecturally maps **how** the ratified `OptionBEventEnvelope`
> output could become **carried S2 identity evidence** in a future, separately-authorized wiring slice — **without
> implementing it**. It **designs and builds nothing**, modifies no reader, and writes no schema. It authorizes
> NO runtime code, NO tests, NO lock-test edits, NO Python/schema/runtime/interface edits, NO reader
> modification, NO B1/B2/B3/Phase 5/producer modification, NO Slice-0B schema, NO B4 scoring, NO S4
> materialization, NO S5 runner, NO Cell-3 route, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_option_b_reader_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_option_b_reader_io_design_charter.md`,
> `docs/handoff/phase6_1_s2_provenance_chain_locks_identity_planning_charter.md`,
> `docs/handoff/phase6_1_s2_identity_source_definition_charter.md`,
> `docs/handoff/phase6_1_s1_durable_passive_shadow_log_boundary_charter.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `03c7fbf1cd58ccad55221cf7766121c8a57fd746`

**External review note:** Gemini Quant/Red-Team verdict — `03c7fbf` reader closeout is **APPROVED**. The reader is
**BUILT + RATIFIED** but still an **isolated island**; **S2 Identity remains BLOCKED**; the reader provides an
**unblock candidate, not wired evidence**. This charter is the docs-only wiring plan.

---

## 1. Base / Dependency Chain

**Base commit:** `03c7fbf1cd58ccad55221cf7766121c8a57fd746`.

References:

- `…_option_b_reader_tdd_closeout_ratification.md` — froze the reader as a stream-only island; permanent output
  contract `OptionBEventEnvelope(parsed_payload_or_local_halt, artifact_locator, physical_record_position)`;
  medium identity alongside, never inside, the payload; **future S2 work must consume the reader as a client,
  never reshape it**.
- `…_s2_provenance_chain_locks_identity_planning_charter.md` — synthetic-identity ban; opaque, S2-owned identity
  slot; reference-preservation ≠ durable identity; pass/halt provenance symmetry.
- `…_s2_identity_source_definition_charter.md` / `…_option_b_*` chain — Silver composite
  `(artifact_locator, physical_record_position)`, borrowed not minted; Gold venue id additive-only.
- `…_s1_durable_passive_shadow_log_boundary_charter.md` — S1 owns the opaque identity slot; `observed_at_epoch_ms`
  is a timestamp, not identity.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Current State

- The Option-B reader is **BUILT + RATIFIED** (`5fece9f`, sealed by `03c7fbf`): a frozen, isolated, stream-only
  physical parser emitting the immutable, non-dict tripartite `OptionBEventEnvelope` per physical line.
- It is **not wired** to anything: B1, B2, B3, the passive producer, Phase 5, S1, S2, B4, S4, S5 neither call it
  nor are called by it. It emits the **Silver tuple components** but nothing **carries** them as evidence.
- **S2 Identity: BLOCKED** — see §6. The reader is an **S2 unblock candidate**, not carried S2 identity evidence.
- The existing evaluation spine (Phase 5 passive socket, passive producer, Master B3) is **BUILT + RATIFIED** and
  **untouched**; it does not depend on, and is not modified by, any wiring contemplated here.

---

## 3. Client-Only Consumption (governing principle)

- The Option-B reader is a **frozen dependency**. A future wiring slice may **only consume** its public output
  (`OptionBEventEnvelope`).
- **No** modification, widening, refactor, rename, parameter change, signature change, subclassing, wrapping,
  monkeypatching, or behavior change to the reader or its envelope is proposed or permitted. Wiring is a
  **client**, never a boundary author.
- If wiring ever appears to need a reader change, that is a signal to **stop and re-charter**, not to reshape the
  frozen island.

---

## 4. Proposed Topological Wiring Boundary

A future, separately-authorized **wiring component** (a new client module; **not** designed here) would sit
**downstream of the reader and upstream of the existing spine**, with this topology:

```
  Option-B artifact (caller-injected text stream)
            │
            ▼
  [ Option-B reader ]  ── frozen island; yields one OptionBEventEnvelope per physical line
            │
            ▼
  [ future WIRING client ]  ── opens the envelope exactly once (the single unpacking point, §5)
        ├───────────────► parsed_payload_or_local_halt ──► (toward B2 normalization, existing spine)
        └───────────────► (artifact_locator, physical_record_position) ──► (toward the S2 identity/provenance slot)
```

- The wiring client is the **single topological owner** of envelope unpacking. No other component opens the
  envelope.
- The two outputs travel **separate paths**: the **payload path** toward B2 normalization / the existing
  evaluation spine; the **identity path** toward the S2 opaque identity slot.
- The **identity path MUST bypass** business math, Phase 5 arithmetic, scoring, and B4 entirely. Identity is never
  an arithmetic input and never a scoring input.

---

## 5. Envelope Unpacking Map

The wiring client opens `OptionBEventEnvelope` at **exactly one** topological point and routes its three parts:

| Envelope part | Destination path | Rule |
|---|---|---|
| `parsed_payload_or_local_halt` (parsed payload case) | toward **B2 normalization** (existing spine) | Carried as the passive observation payload; the existing spine normalizes/evaluates it under its own ratified invariants. Wiring performs **no** normalization itself. |
| `parsed_payload_or_local_halt` (local parse-halt case) | toward the **halt-carrying** path (§7 symmetry) | A malformed-line `OptionBLocalParseHalt` is carried as a halt outcome, **not** dropped, **not** routed into B2 math. |
| `artifact_locator` | toward the **S2 identity/provenance slot** | Carried **intact and opaque** (§6). Never normalized/cast/derived. |
| `physical_record_position` | toward the **S2 identity/provenance slot** | Carried **intact and opaque** (§6). Never normalized/cast/derived. |

- **Opaque carriage seal.** The Silver tuple components travel **intact and opaque**: **no** hashing, UUID, string
  concatenation, counter, timestamp-as-ID, payload fingerprint, normalization, casting, or derivation; and the
  tuple is **never collapsed into a synthetic key**. The two components remain a **pure pair of inherited facts**.
- **Identity-path purity.** From unpacking to the S2 slot, the identity pair touches **no** Phase 5 arithmetic,
  **no** net-edge/cost math, **no** scoring, and **no** B4. It is a provenance channel, not a compute channel.
- **Medium/payload separation preserved.** Identity is read **only** from the envelope's 2nd/3rd parts, **never**
  from inside `parsed_payload`; payload-authored identity fields are never promoted (the reader already guarantees
  this; wiring must not undo it).

---

## 6. Identity State Precision — S2 Classification

- **Exact state: "S2 unblock candidate available."** The reader emits the Silver tuple components, so an
  authoritative, borrowed, event-level identity **source candidate** now exists at the boundary.
- **S2 is NOT UNBLOCKED.** This charter does **not** declare S2 unblocked. S2 becomes **UNBLOCKED only after** the
  future runtime wiring is **built, tested, and ratified** as actually **carrying** the tuple as pipeline evidence
  into the opaque S2 identity slot. Planning a path is not carrying evidence.
- The opaque S2-owned identity slot stays **unfilled** until that ratified wiring exists.

---

## 7. Pass / Halt Symmetry

Planning covers **both** envelope families equally:

- **Parsed-payload envelopes** — the payload flows toward B2/normalization; the identity pair flows toward the S2
  slot.
- **Local parse-halt envelopes** (`OptionBLocalParseHalt`) — carried as a **halt outcome of equal standing**,
  **never** silently dropped and **never** routed into business math. **The malformed-line halt identity MUST
  preserve the same `(artifact_locator, physical_record_position)`** as any other envelope from that physical line
  — a halt event is identity-anchored exactly like a score event.
- This charter **does NOT design S4 global halt materialization** — only that, whatever S4 later does, the
  local-halt envelope's identity pair is preserved and symmetric with the pass case. How a local parse-halt is
  ever materialized into a durable log is **S4's**, separately gated.

---

## 8. Blind-Carriage Downstream

- Once the identity pair enters the pipeline, **B1 / B2 / B3 / Producer / Phase 5 / B4 / S1 may only carry the
  identity reference blindly** — by reference, opaque.
- **No** inspection, branching, validation, mutation, reinterpretation, casting, or fallback of the identity pair
  by any downstream boundary. It is never a decision input.
- This preserves the ratified blind-carriage invariant end-to-end; the wiring client is the only component that
  *touches* the envelope, and it only **routes** (never derives).

---

## 9. Slice-0B Gate & Existing-Spine Isolation

- **Slice-0B field-level schema remains BLOCKED** until S2 identity wiring is **implemented and ratified**. This
  charter designs **no** log schema and **no** persistence.
- **Existing spine untouched.** The Phase 5 passive socket, the passive producer, and the Master B3 client remain
  **frozen and unmodified**; this plan implies **no** change to them and **no** B4/runner readiness. The wiring
  client is additive and downstream; it does not reach into or alter the spine.

---

## 10. Still-Forbidden Work

- **No** reader modification/widening/refactor/rename/parameter/behavior change; **no** envelope contract change.
- **No** minting from the identity pair (hash/UUID/concatenation/counter/timestamp-as-ID/payload-fingerprint);
  **no** collapsing the tuple into a synthetic key; **no** normalization/casting/derivation of either component.
- **No** declaration that S2 is UNBLOCKED; **no** filling of the opaque S2 slot; **no** carried-evidence claim.
- **No** routing of identity through Phase 5 arithmetic / scoring / B4; **no** reading identity from the payload.
- **No** S4 global halt materialization design; **no** dropping/reclassifying local parse-halts.
- **No** downstream inspection/branch/validation/mutation/fallback of the identity reference (blind carriage).
- **No** Slice-0B field-level schema; **no** log schema/persistence design.
- **No** B1/B2/B3/Phase 5/producer modification; **no** B4 scoring; **no** S5 runner; **no** Cell-3 route.
- **No** `edge_direction`/staleness/capacity/Shadow Intent/execution/routing/sizing/actionability content.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 11. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 12. Next Safe Step

- A **separately-authorized docs-only S2 identity wiring boundary/contract charter** — pinning, at contract level,
  the future wiring client's input (one `OptionBEventEnvelope`, consumed as a frozen-reader client), its single
  unpacking point, the opaque identity-pair carriage into the S2 slot, and the pass/halt symmetry — **still**
  designing no runtime, no schema, and no S4 materialization. Only after that is ratified may a **runtime wiring
  TDD slice** be authorized, after which S2 may be reclassified from *unblock-candidate* to *UNBLOCKED* and the
  opaque slot filled.
- Only after S2 identity is **carried and ratified** may a **Slice-0B field-level schema** charter be authorized
  (under the S1 boundary and S2 locks).
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; Phase-6.2 fidelity dependency).
- **No implementation is authorized by this charter.** The wiring boundary/contract, the runtime wiring slice, the
  S2 identity fill, the Slice-0B schema, S4 materialization, B4 scoring, the S5 runner, durable persistence, the
  Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.

**Conclusion:** the ratified `OptionBEventEnvelope` can, in a **future client-only wiring slice**, become carried
S2 identity evidence by unpacking the envelope at a **single topological point** and routing
`parsed_payload_or_local_halt` toward B2 normalization while carrying the **opaque, intact Silver pair
`(artifact_locator, physical_record_position)`** toward the S2 identity/provenance slot — **bypassing all Phase 5
math, scoring, and B4**, preserving **pass/halt symmetry** (local parse-halts keep the same locator + position,
never dropped), and keeping the reader and the existing spine **frozen and untouched** under strict **blind
carriage**. The exact state is **"S2 unblock candidate available"** — **S2 is NOT UNBLOCKED** until the wiring is
built, tested, and ratified as carrying the tuple; **Slice-0B schema remains BLOCKED**; Phase 6.1 remains
**incomplete** and Phase 6.2 **not ready**. **No executable work is authorized.**
