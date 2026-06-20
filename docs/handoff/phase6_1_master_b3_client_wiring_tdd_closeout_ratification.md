# Phase 6.1 Master B3 Client Wiring TDD — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It ratifies and permanently seals the **completed**
> Phase 6.1 Master B3 minimal dumb-pipe client wiring TDD slice (commit `7f13171`). It **builds and designs
> nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python, NO interface/schema/runtime
> edits, NO B2/B3 runtime/schema/carrier changes, NO passive producer changes, NO Phase 5 runtime amendment, NO
> Master B3 wiring change, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope, NO
> `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity activation, NO Phase 6.2 work, NO
> pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_master_b3_client_wiring_charter.md`,
> `docs/handoff/phase6_1_passive_producer_tdd_closeout_ratification.md`, and `CLAUDE.md`; where any conflict
> arises, those govern.

**Base:** `7f13171ec1496002fcbb6f665bfc6df2f5edb866`

---

## 1. Base / Dependency Chain

**Base commit:** `7f13171ec1496002fcbb6f665bfc6df2f5edb866`.

References:

- `…_master_b3_client_wiring_charter.md` — mapped B3 as a stateless, synchronous dumb-pipe client (locks
  implemented by this slice).
- `…_passive_producer_tdd_closeout_ratification.md` — froze the producer; B3 client-only rule, identity
  forwarding, AST invariants, anti-monkeypatch seal (all RATIFIED).

**Implemented commit under closeout:** `7f13171` (parent `b2a11f6`).

**No capacity validation and no capacity pass is claimed by this charter** (see §14).

---

## 2. Why This Closeout Exists

The Master B3 minimal client is implemented and green; it joins B2 passive normalized evidence to the frozen
passive producer. Before any further track (real-cost Cell-3 assembly, B4 scoring, logs), B3's guarantees must be
**frozen as ratified invariants** so no later step can mutate the client boundary, smuggle actionability/state/
concurrency, read a clock, or break identity forwarding or error-domain separation. This charter records the
proof and seals those invariants; it advances nothing executable.

---

## 3. Evidence Inventory Inspected (read-only)

- **`phase6_1/b3_passive_client_wiring.py`** — defines `wire_passive_shadow_input(*, normalized_evidence_material,
  cost_validity_contexts)` and the error class `B3PassiveClientWiringError`. It exact-field-reads the one
  `GROSS_EDGE` binding's `unit_bound_magnitude.magnitude`/`.unit`, the raw snapshot's `venue`/`pair`, and the
  provenance `observed_at_epoch_ms`; performs a strict lexical `str.isdigit()` guard → `int()`; calls
  `produce_passive_shadow_input` once; returns its output unchanged. Imports only
  `phase6_1.b2_normalization_contract` (the `NormalizedEvidenceMaterial` type) and `phase6_1.passive_producer`.
  No Phase 5 import; no clock; no try/except; no concurrency; no `isinstance`.
- **`tests/test_phase6_1_b3_passive_client_wiring.py`** — real pass/defensive integration + monkeypatched-producer
  adapter isolation + AST locks; passive-only fixtures built from scratch.
- **Untouched:** `phase5/net_edge_calculator_boundary.py`, `phase6_1/passive_producer.py`,
  `phase6_1/passive_shadow_input.py`, all B2 files — no edits in this slice.

---

## 4. Ratified B3 Runtime Surface

**BUILT + RATIFIED at `7f13171`:** the single public entry `wire_passive_shadow_input(*,
normalized_evidence_material, cost_validity_contexts)` (and its `B3PassiveClientWiringError`) in
`phase6_1/b3_passive_client_wiring.py` — a stateless, synchronous, deterministic dumb-pipe client. **Frozen:** any
change to its signature, behavior, or boundary requires **separate authorization**.

---

## 5. Ratified Test Proof

- **RED:** `ModuleNotFoundError: No module named 'phase6_1.b3_passive_client_wiring'` — feature genuinely missing.
- **GREEN:** **307 passed** across the targeted suite
  (`tests/test_phase6_1_b3_passive_client_wiring.py`, `tests/test_phase6_1_passive_producer.py`,
  `tests/test_phase6_1_passive_shadow_input.py`, `tests/test_phase6_1_b2_normalization_contract.py`).
  **No broad pytest.**
- **Changed-file scope (exactly two):** `phase6_1/b3_passive_client_wiring.py`,
  `tests/test_phase6_1_b3_passive_client_wiring.py`. **No edits** to Phase 5, `passive_producer.py`,
  `passive_shadow_input.py`, or B2.
- **Branch coverage:** real pass path (`net_edge_value == "12.34"`, epoch `int`, venue/pair) and real defensive
  path (incompatible units → `BlockedPacket` by identity); adapter isolation (call-once with extracted fields;
  pass/defensive identity forwarding; producer-not-called on invalid epoch / missing-`GROSS_EDGE` / non-material
  input).
- **AST locks (green):** keyword-only signature; no `isinstance`; no `Protocol`/`Any`; clock-blind (no
  `time`/`datetime`/clock); no `async`/threading/multiprocessing/queue/concurrency; no `try`/`except`; no toxic
  actionable imports/tokens; producer-only (no `phase5` import; no direct `calculate_net_edge`/handoff/socket
  calls); stateless (UPPERCASE constants only).

---

## 6. Producer-Only Client Rule (RATIFIED)

B3 calls **only** `produce_passive_shadow_input`. It has **no** Phase 5 import, makes **no** direct
`calculate_net_edge` call, and calls **neither** `make_passive_shadow_input` **nor** the passive socket factories
directly. B3 may **not** modify, widen, subclass, wrap, monkeypatch, or reinterpret the producer or Phase 5
socket boundaries. B3 is a **client**, never a boundary author.

---

## 7. Identity Forwarding (RATIFIED)

B3 returns the producer's output **unchanged, by exact identity** — both the `PassiveShadowInput` (pass) and the
`BlockedPacket`/defensive carrier (non-pass). B3 **never** wraps, copies, mutates, re-instantiates, hides, or
drops producer outputs. Proven by `is`-identity assertions and a "producer output forwarded" recorder test.

---

## 8. Lexical Epoch Adaptation (RATIFIED)

The `observed_at_epoch_ms` adaptation is frozen as a **structural lexical adaptation only**: an exact-`str` check
plus `str.isdigit()` guard → `int()`. There is **no** `datetime` parsing, **no** timezone adjustment, **no**
float conversion, **no** clock read, and **no** temporal policy/branching. A non-`str` or non-digit value fails
fast (§10/§11); a value-preserving integer is produced otherwise.

---

## 9. AST / Stateless / Synchronous Invariants (RATIFIED)

Frozen and AST-proven for the B3 module:

- **No clock/time** — no `time`/`datetime`/`calendar` import; no `now`/`utcnow`/`monotonic`/`perf_counter`/etc.
- **No concurrency** — no `async`/`await`/async-for/async-with; no `asyncio`/threading/multiprocessing/queue/
  `concurrent`/`sched`.
- **Exact typing** — no `isinstance`, `Protocol`, `Any`, `dict`/blob, unbounded mapping, or duck typing.
- **No toxic imports/tokens** — no `GrossEdgeObservation`, `edge_direction`, Shadow Intent, capacity-activation,
  freshness-policy, `ShadowScore`, or diagnostic-EV tokens.
- **No `try`/`except`** — no swallowing/conversion of failures.
- **Stateless / synchronous** — module-level names are UPPERCASE constants only; no cache, buffer, memoization,
  previous-frame comparison, rolling window, delta, or cross-frame derivation. **One invocation = one isolated
  pass-through event.**

---

## 10. Pre-Producer Defensive Shield (RATIFIED — as built)

B3 owns **structural/extraction** failures: a non-`NormalizedEvidenceMaterial` input, a missing/ambiguous
`GROSS_EDGE` binding (count ≠ 1), or a non-canonical provenance epoch. On any of these, B3 **short-circuits
before calling the producer**, raising a typed, explicit **`B3PassiveClientWiringError`** — the producer is
**not** called, and nothing is **silently dropped or swallowed**. Proven by `pytest.raises` plus a "producer not
called" recorder assertion on all three structural failure cases.

> **Honest divergence note (no runtime change here):** the client-wiring charter's §9 phrased this shield as
> short-circuiting "into a `BlockedPacket`/equivalent." The **as-built** shield is a **typed fail-fast exception**
> (`B3PassiveClientWiringError`), **not** a returned `BlockedPacket` carrier. This closeout ratifies the
> **actually-built and tested** behavior (typed exception, producer-not-called, never swallowed). Whether
> structural halts should instead be **materialized as a returned defensive carrier** is a **separate, unbuilt
> question** requiring its own authorization; it is **not** claimed as done here. The "must not throw
> pipeline-crashing exceptions" intent is satisfied to the extent that the failure is a **typed, catchable,
> explicit** contract error (not an arbitrary/untyped crash and not a silent drop).

---

## 11. Error Domain Separation (RATIFIED)

- **B3 owns structural halts only** — type/shape/extraction failures (§10), surfaced as
  `B3PassiveClientWiringError` before the producer is reached.
- **The producer owns semantic/math halts only** — e.g. incompatible units or other Phase 5 defensive math
  carriers (`BlockedPacket`), which arise **inside** the producer's `calculate_net_edge` path.
- **B3 must not reclassify** producer semantic/math halts: it forwards them verbatim by identity (§7), never
  re-labeling a `BlockedPacket` as a structural error or vice versa.
- **The producer is never asked to handle B3 structural extraction failures**: those are short-circuited before
  the producer call. The two error domains stay cleanly separated.

---

## 12. Opaque Cost Pass-Through (RATIFIED)

`cost_validity_contexts` is **opaque** to B3. B3 may **only forward the tuple by identity** into the producer. B3
is **forbidden** to unpack, inspect, iterate over, branch on, score, normalize, or derive from the cost context
contents. Proven by the recorder test asserting the exact tuple object is forwarded (`is`), and by the
producer-only/no-derivation AST locks. The minimal path supplies a **zero-valued cost context** (temporary
deferral, not a permanent economic assumption); the **empty cost tuple remains invalid** (rejected downstream);
real-cost Cell-3 assembly is a **separate, deferred** concern.

---

## 13. Remaining Separate Work

- **Real-cost Cell-3 cost-context assembly** (B2 cost bindings → Phase 5 `ObservableCostValidityContext`) —
  UNBUILT, separate/parallel; required only for real-cost wiring. The minimal B3 path stays on the zero-valued
  cost context.
- **B4 passive shadow scoring** (`ShadowScore` / diagnostic EV) — UNBUILT, future, separately authorized.
- **Durable shadow logs** — UNBUILT, future, separately authorized.
- **Phase 6.2** and 7.x/8.x — out of scope, separately gated.

Tombstoned: `edge_direction`, `staleness_threshold_ms`. **BUILT + RATIFIED:** B2 carriers (incl. cost-type
provenance), Phase 5 passive socket + Union, passive producer, `PassiveShadowInput`, and now the Master B3
minimal dumb-pipe client.

---

## 14. Still-Forbidden Work

- **No** change to the ratified B3 surface (§4) or its boundary; **no** producer/socket modification/wrap/
  subclass/monkeypatch.
- **No** Phase 5 import in B3; **no** direct `calculate_net_edge`/handoff/socket call; **no** new math.
- **No** clock/time/`datetime`/float/timezone in the epoch adaptation; **no** temporal policy.
- **No** `isinstance`/`Protocol`/`Any`/dict-blob/duck typing; **no** `async`/threading/multiprocessing/queue/
  scheduler/callback; **no** `try`/`except` swallowing; **no** module state/cache/buffer/window/delta/memoization.
- **No** cost-context unpacking/inspection/iteration/derivation; **no** real-cost Cell-3 assembly.
- **No** reclassification of producer semantic/math halts; **no** routing of B3 structural failures into the
  producer.
- **No** B4 scoring/diagnostic-EV/ranking/threshold/durable log/calibration; **no** Shadow Intent Envelope; **no**
  actionability/routing/sizing/execution/intent emission.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** reopening of `edge_direction`, `staleness_threshold_ms`, or cost vocabulary values; **no** weakening of
  the producer, Phase 5 socket, or B2 passive carrier invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 15. Next Safe Step

- A **separately-authorized track** — choose one: (a) a docs-only decision on whether B3 structural halts should
  be **materialized as a returned defensive carrier** vs. the current typed-exception shield (reconciling §10's
  divergence note); (b) the **router-only Cell-3 cost-type / real-cost cost-context assembly** charter; or (c) a
  **B4 passive shadow scoring** planning charter. Each is docs-first and separately gated.
- **No implementation is authorized by this charter.** Cell-3 assembly, B4 scoring, durable logs, Phase 5/
  producer/B3 modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain
  separately gated.

**Conclusion:** the Master B3 minimal dumb-pipe client is **BUILT + RATIFIED**; the Phase 5 passive socket and
the passive producer remain **BUILT + RATIFIED**; the Cell-3 route remains **separate/parallel**; B4 passive
scoring, durable logs, and Phase 6.2 remain future, separately-authorized work. **No executable work is
authorized.**
