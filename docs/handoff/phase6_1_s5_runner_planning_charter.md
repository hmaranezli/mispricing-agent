# Phase 6.1 — S5 Runner Planning Charter

> **This is a docs-only planning charter.** It conceptually defines the **S5 runner orchestration boundary** that will
> sequence the already-ratified frozen passive components (Option-B reader → S2 identity wiring → {B4 score path | S4
> halt path} → S1 reference sink) — **without implementing it**. It **designs and builds nothing**: no runtime, no
> tests, no schema, no storage. It authorizes NO runtime code, NO tests, NO schema/runtime/interface edits, NO edits
> to the Option-B reader / `S2IdentityWiringCandidate` / B3 / B4 / S4 / the S1 reference sink / the lock-tests, NO
> durable storage/persistence, NO Cell-3 assembly, NO actionability/trade/order/execution logic, NO Phase 6.2 work,
> NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_s4_halt_materialization_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_b4_passive_scoring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s1_in_memory_reference_sink_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_s2_identity_wiring_runtime_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_option_b_reader_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any conflict arises,
> those govern.

**Base:** `40613dd7416ae3a3b2d7cb9f6d2b4534ddce2997`

---

## 1. Base / Dependency Chain

**Base commit:** `40613dd7416ae3a3b2d7cb9f6d2b4534ddce2997`.

The frozen components S5 will sequence (all **BUILT + RATIFIED**, consumed as clients, never modified):

- **Option-B reader** — `read_option_b_event_stream(*, text_stream, artifact_locator)` yields one
  `OptionBEventEnvelope(parsed_payload_or_local_halt, artifact_locator, physical_record_position)` per physical
  line; the payload slot holds either a structurally-parsed payload **or** an `OptionBLocalParseHalt`.
- **S2 identity wiring** — `route_option_b_envelope_to_s2_identity_candidate(*, envelope)` maps one envelope to one
  `S2IdentityWiringCandidate(forwarded_payload_or_local_halt, artifact_locator, physical_record_position)`,
  pass/halt symmetric, identity-blind.
- **B4 passive scorer** — `build_passive_observation_record(*, pass_handoff, identity_evidence,
  opaque_cost_context)` consumes an exact `PassiveShadowInput` pass handoff and returns one
  `ObservationScoreRecord`.
- **S4 halt materializer** — `materialize_passive_halt_record(*, halt_source, identity_evidence,
  opaque_cost_context)` consumes one exact authorized halt carrier (`OptionBLocalParseHalt` /
  `B3PassiveClientWiringError` / `BlockedPacket`) and returns one `ObservationHaltRecord`.
- **S1 reference sink** — `S1InMemoryObservationSink.record_observation(record)` admits an exact
  `ObservationScoreRecord` / `ObservationHaltRecord` (whose identity is an exact `S2IdentityWiringCandidate`) and
  appends it; `snapshot()` returns an immutable tuple. **Test-only, in-memory; no persistence.**

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Current State

- **Both observation paths are green and equal-peer** at component level: B4 → `ObservationScoreRecord` → S1, and
  S4 → `ObservationHaltRecord` → S1. **No runner wires them end-to-end.** This charter **plans** the S5 boundary; it
  builds nothing.
- The S1 sink is the **contract target** the runner will deposit both families into. It remains a **test-only
  reference sink** — storage medium undecided. Phase 6.1 incomplete; Phase 6.2 not ready.

---

## 3. S5 Runner Boundary Definition (orchestration-only)

S5 is, at boundary level only:

- A **pure orchestration boundary** — it **sequences existing frozen components** and moves their outputs along the
  fixed topology. It is glue, not a participant in evaluation.
- **It computes nothing of its own.** S5 **MUST NOT** compute scores, materialize halts, normalize/parse/coerce
  payloads, mint/inspect/derive identity, read or interpret halt-carrier contents, interpret cost context, or write
  durable storage. Every value it moves is **already produced** by a ratified component and carried **by reference**.
- **It is not the sink and not any layer.** S5 calls the reader, S2, B4, S4, and S1; it **is** none of them, **wraps**
  none of them, and **reshapes** none of them. It owns no log (S1 records).

---

## 4. Conceptual Topology & The Pass/Halt Discriminator

The runner's conceptual per-event sequence (synchronous, one event fully handled before the next — §7):

1. **Read** one `OptionBEventEnvelope` from the Option-B reader.
2. **Wire** that envelope through S2 to one `S2IdentityWiringCandidate` (S2 handles pass and halt **identically**;
   the opaque Silver pair and the forwarded payload are carried intact).
3. **Discriminate pass vs halt by EXACT TYPE only** of the candidate's `forwarded_payload_or_local_halt` slot:
   - if it is an **exact** `OptionBLocalParseHalt` → the **halt path** (§5);
   - otherwise → the **pass/score path** (§5, subject to the contract gap in §6).
   This discriminator is a **single exact-type tag read** (`type(...) is OptionBLocalParseHalt`), **not** content
   inspection: the runner never reads the carrier's fields/args/message, never stringifies/`repr`s it, and never
   reads the identity slots (`artifact_locator` / `physical_record_position`). It reads **only** which structural
   path a frozen object already belongs to.
4. **Deposit** the single record the chosen leaf produces into the S1 reference sink, by reference.

The runner carries the **whole** `S2IdentityWiringCandidate` onward as `identity_evidence` for whichever leaf runs;
it unpacks only the `forwarded_payload_or_local_halt` slot to hand the carrier to S4 on the halt path. The identity
slots are **never** read, copied, or derived (§8).

---

## 5. Equal-Peer Routing (binding)

- **Pass outputs** → B4 → `ObservationScoreRecord` → S1.
- **Halt outputs** → S4 → `ObservationHaltRecord` → S1.
- **Neither family may be dropped, ranked, prioritized, ordered-by-importance, retried, deduplicated, filtered,
  sampled, throttled, or treated as actionability.** Both are equal-peer passive observation events; the runner
  deposits **every** produced record into S1 with **no** precedence between families and **no** judgement about
  which matters more. A halt is not "more urgent" than a score; a score is not privileged over a halt.

---

## 6. Pass-Path Contract Gap / Stop-on-Missing-Boundary (binding honesty)

- **The halt path is contract-complete today.** A candidate whose forwarded payload is an exact
  `OptionBLocalParseHalt` can be handed **as-is** to S4 (`halt_source=<that OptionBLocalParseHalt>`,
  `identity_evidence=<the candidate>`), which already accepts it → `ObservationHaltRecord` → S1. No new edge is
  required for halts.
- **The pass/score path has a KNOWN, UNRESOLVED contract gap.** The Option-B reader's non-halt payload is a
  **structurally-parsed payload** (e.g. a `json.loads` result), whereas **B4 consumes an exact `PassiveShadowInput`**
  pass handoff. There is **no ratified frozen edge** that turns a reader-parsed payload into a `PassiveShadowInput`,
  and the existing producer/B3/B2 chain consumes **`NormalizedEvidenceMaterial`**, not an Option-B parsed payload.
- **The runner MUST NOT bridge this gap by inventing an adapter.** Normalizing, coercing, mapping, defaulting, or
  constructing a `PassiveShadowInput` from a parsed payload is **forbidden** (it would breach §3's no-normalization
  rule and the constitution's anti-fabrication rule). The runner is orchestration-only.
- **Stop-on-missing-boundary.** Because this connecting contract is **absent/ambiguous**, the future S5 **runtime**
  slice must, on the pass path, **stop and report the exact blocker** rather than invent the adapter. The precise
  pass-path wiring (whether via a separately-chartered reader-payload → `PassiveShadowInput` edge, or by feeding S5
  pre-produced `PassiveShadowInput` handoffs from an upstream stage) is a **separate, future contract decision** and
  is **NOT decided here**. This planning charter **surfaces** the gap; it does not paper over it.
- More generally: if **any** needed component contract is absent or ambiguous at runtime-slice time, the runner must
  **stop and report a blocker**, never invent adapters, stubs, or fabricated inputs.

---

## 7. Determinism Lock (binding)

- S5 is **strictly synchronous, sequential, single-threaded.** It reads one event, fully handles it, deposits its
  one record, then proceeds to the next — a single deterministic pass over the input stream.
- **Explicitly banned:** `asyncio` / `async` / `await` / event loops; `threading` / `multiprocessing` / thread or
  process pools; `queue`/work queues; background workers/daemons; timers/schedulers/clocks; parallel fan-out,
  concurrency, batching-for-parallelism, prefetch, or speculative execution. No wall-clock dependence and no
  ordering nondeterminism: the same input stream yields the same sequence of S1 deposits.

---

## 8. Identity Preservation (binding)

- S5 carries the **existing** `S2IdentityWiringCandidate` into B4/S4 as `identity_evidence`, **by reference, whole
  and unmodified.**
- S5 **MUST NOT** mint, hash, collapse, derive, concatenate, cast, fingerprint, stringify, inspect, normalize, or
  fall back on identity. The opaque Silver pair stays **indivisible**; the runner never reads or rewrites
  `artifact_locator` / `physical_record_position`. Identity flows through untouched.

---

## 9. Crash Boundary (binding)

- S5 **MUST NOT** catch raw Python/programmer exceptions — e.g. `TypeError`, `KeyError`, `AttributeError`,
  `AssertionError`, `ImportError`, `ValueError`, or any unexpected exception — and **MUST NOT** wrap them into S4
  halts, into `ObservationHaltRecord`s, or into any record. Such a runner crash is a **hard, fail-fast crash** that
  propagates unchanged.
- **S4 is only for the three specific ratified structural halt carriers** (`OptionBLocalParseHalt` /
  `B3PassiveClientWiringError` / `BlockedPacket`) that an upstream component **already observed and emitted**. A
  programmer error, a contract violation, or an unexpected exception is **not** a structural halt and must **never**
  be laundered into the halt family. The runner does not convert crashes into observations.

---

## 10. EOF / Exhaustion Boundary (binding)

- **Natural reader exhaustion is a passive stop condition** — not an error, not a halt, not a readiness signal, and
  not an actionability event. When the input stream is exhausted (the Option-B reader's generator ends), the runner
  **stops cleanly**.
- S5 **MUST NOT** create a synthetic EOF record, an end-of-stream marker, a "done"/"ready" observation, a sentinel
  halt, or any manufactured record at exhaustion. It simply ceases; the S1 sink holds exactly the records the real
  events produced.

---

## 11. No Durability / Ephemeral State (binding)

- **S1 remains the test-only in-memory reference sink.** S5 introduces **no** persistence.
- S5 **MUST NOT** save read cursors, stream offsets, checkpoints, run state, progress, resume points, or observation
  state to any file, database, queue, cache, or external store. **All runner state is ephemeral / in-memory** and
  vanishes when the pass ends. No file/DB/network IO of any kind.

---

## 12. No Retry / Repair / Actionability (binding)

- **No retry/repair/self-heal.** S5 **MUST NOT** retry a failed component, re-read, patch malformed data, synthesize
  missing identity/context, reconstruct broken records, or recover. A component either produces its one record or
  the relevant boundary rule applies (halt carrier → S4; crash → fail-fast §9; exhaustion → clean stop §10).
- **No actionability.** S5 **MUST NOT** emit or imply any trade, order, route, execution, readiness, verdict,
  recommendation, sizing, allocation, capacity activation, paper/live/canary, or "should act" semantics. It moves
  passive observations into a passive log and does nothing else.

---

## 13. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." The runner activates no capacity gate.

---

## 14. Still-Forbidden Work

- **No** runtime/tests/schema/storage; **no** edits to the reader / S2 / B3 / B4 / S4 / S1 / lock-tests; **no**
  S5-as-any-layer; **no** wrap/widen/reshape of any frozen component.
- **No** score computation, halt materialization, payload normalization/parsing/coercion, identity
  minting/inspection/derivation/stringify/fallback, halt-carrier content inspection, or cost-context interpretation
  in the runner.
- **No** invented pass-path adapter (§6); **no** fabricated `PassiveShadowInput`; **no** adapter/stub for any
  absent/ambiguous contract — **stop and report the blocker** instead.
- **No** async/threading/multiprocessing/queue/worker/event-loop/timer/parallel fan-out (§7); **no** nondeterminism.
- **No** dropping/ranking/prioritizing/retrying/deduplicating/filtering/sampling either family (§5).
- **No** catching/wrapping of raw programmer exceptions into S4 halts or any record (§9); **no** crash-to-observation
  laundering.
- **No** synthetic EOF/end/ready/sentinel record (§10).
- **No** durable storage / cursors / offsets / checkpoints / run state / file / DB / network IO (§11).
- **No** retry/repair/self-heal/recover/synthesis (§12); **no** trade/order/route/execution/readiness/verdict/
  recommendation/sizing/capacity-activation/paper/live/canary actionability (§12).
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 15. Precise Scope / Status

- This planning charter may make a **separately-authorized S5 runtime TDD slice eligible**, but it **does not** make
  Phase 6.1 complete and **does not** make Phase 6.2 ready.
- The **S1 durable storage medium** and the **real-cost Cell-3** assembly remain **separately gated** and
  **unbuilt/unbound**. The S1 sink stays a **test-only reference sink**.
- The **pass-path contract gap (§6) is an open, separately-gated contract decision** that the runtime slice must
  resolve or stop-and-report; it is **not** resolved here.

---

## 16. Next Safe Step

- A **separately-authorized S5 boundary/contract charter** (or, if the pass-path edge of §6 is first resolved by its
  own contract decision, a **separately-authorized S5 runtime TDD slice**) — implementing a strictly synchronous,
  sequential, single-threaded runner that reads the Option-B stream, wires each envelope through S2, discriminates
  pass vs halt by **exact type only**, routes pass → B4 → `ObservationScoreRecord` and halt → S4 →
  `ObservationHaltRecord`, deposits every record into the S1 reference sink by reference, preserves identity
  untouched, fail-fast-crashes on programmer errors (never laundering them into halts), stops cleanly on exhaustion
  (no synthetic EOF), holds only ephemeral in-memory state, and **stops and reports** any absent/ambiguous contract
  rather than inventing an adapter — test-first, no durability, no actionability, no async/parallelism.
- Independently/subsequently: the **S1 storage-medium** charter (inheriting the ratified S1 interface) and the
  **real-cost Cell-3** assembly. Each separately gated.
- **No implementation is authorized by this charter.** The S5 runtime, the pass-path edge resolution, the storage
  medium, durable persistence, the Cell-3 route, the Shadow Intent Envelope, capacity activation, Phase 6.2, and
  7.x/8.x remain separately gated.

**Conclusion:** S5 is conceptually pinned as a **pure orchestration boundary** that **sequences frozen components**
(Option-B reader → S2 → {B4 score path | S4 halt path} → S1 reference sink) **synchronously, sequentially, and
single-threaded** (no async/threading/multiprocessing/queue/event-loop/timer/parallel fan-out), discriminating pass
vs halt by **exact type only** (no content inspection), routing the two families as **equal peers** (neither
dropped, ranked, prioritized, retried, nor treated as actionability), carrying the **existing**
`S2IdentityWiringCandidate` identity **untouched** (no mint/hash/collapse/derive/stringify/inspect/fallback),
**fail-fast-crashing** on raw programmer exceptions (never laundering them into S4 halts — S4 is only for the three
ratified structural carriers), **stopping cleanly** on natural reader exhaustion (no synthetic EOF record), holding
**only ephemeral in-memory state** (no durable storage / cursors / offsets / checkpoints; S1 stays the test-only
reference sink), and **never retrying/repairing/self-healing** or emitting any actionability. The runner **computes,
normalizes, materializes, and persists nothing** — it moves already-produced records by reference. The **halt path
is contract-complete today**, but the **pass/score path has an open contract gap** (reader-parsed payload →
`PassiveShadowInput`) that the runner **must not** adapt around and that the runtime slice must **resolve separately
or stop-and-report**. This planning may make an S5 runtime slice **eligible** but **does not** complete Phase 6.1 or
ready Phase 6.2; the **S1 storage medium** and **Cell-3** remain **separately gated**. It is **UNBUILT** and
**designs no runtime/schema/storage**; existing modules remain **frozen**. **No executable work is authorized.**
