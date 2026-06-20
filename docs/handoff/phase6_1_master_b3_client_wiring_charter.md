# Phase 6.1 Master B3 — Client Wiring Charter

> **This is a docs-only architecture-mapping charter.** It maps how a future Master B3 will act as a
> **dumb-pipe client** connecting B2 passive normalized evidence to the **frozen** passive producer boundary. It
> **designs and builds nothing**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python, NO
> interface/schema/runtime edits, NO B2/B3 runtime/schema/carrier changes, NO passive producer changes, NO Phase
> 5 runtime amendment, NO Master B3 wiring implementation, NO B4 scoring design/math, NO durable shadow logs, NO
> Shadow Intent Envelope, NO `edge_direction` reopening, NO `staleness_threshold_ms` reopening, NO capacity
> activation, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_passive_producer_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_passive_producer_implementation_charter.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md`, and `CLAUDE.md`;
> where any conflict arises, those govern.

**Base:** `fc3aed0a0154a8e03008e6a9a64d070e294f79ef`

---

## 1. Base / Dependency Chain

**Base commit:** `fc3aed0a0154a8e03008e6a9a64d070e294f79ef`.

References:

- `…_passive_producer_tdd_closeout_ratification.md` — froze the producer; **B3 client-only rule**, identity
  forwarding, downstream AST invariants, anti-monkeypatch seal, zero-cost extensibility (all RATIFIED).
- `…_passive_producer_implementation_charter.md` — producer contract.
- `…_master_b3_remaining_blockers_reclassification_v2_readiness_audit.md` — Master B3 BLOCKED; producer was the
  critical path.

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Why This Charter Exists

With the passive producer BUILT + RATIFIED, Master B3 is the next track: a **dumb-pipe client** that reads B2
passive normalized evidence and calls `produce_passive_shadow_input`, surfacing the producer's output unchanged.
Before any B3 TDD slice, B3's role, allowed/forbidden behavior, the producer-client contract, and the
sync/stateless invariants must be **fixed in docs** so the future slice cannot drift into scoring, state,
concurrency, actionability, or boundary mutation. This charter fixes them and implements nothing. It also
**honestly surfaces** the one open adaptation concern (B2-evidence → producer-input shape) and bounds it.

---

## 3. Evidence Inventory Inspected (read-only)

- **Producer (frozen)** — `phase6_1/passive_producer.py`:
  `produce_passive_shadow_input(*, gross_edge_value, gross_edge_unit, cost_validity_contexts, source_venue,
  source_pair, observed_at_epoch_ms)`. Keyword-only, exact-typed; returns a `PassiveShadowInput` on a pass or a
  defensive carrier (e.g. `BlockedPacket`) by identity.
- **Handoff (built)** — `phase6_1/passive_shadow_input.py`: requires an exact `NetEdgeCalculationResult`, exact
  non-empty `source_venue`/`source_pair`, an exact **non-negative `int`** `observed_at_epoch_ms`, and
  `capacity_pass_reference` deferred `None`.
- **B2 normalized evidence (built, read-only here)** — `phase6_1/b2_normalization_contract.py`:
  `NormalizedEvidenceMaterial` references a `PublicRawSnapshotRecord` (carrying `venue`, `pair`,
  `observed_at_epoch_ms` as a **canonical unsigned-int string**, etc.) and a tuple of
  `NormalizedEvidenceFieldBinding` (each with `binding_role ∈ {GROSS_EDGE, COST}`, a `unit_bound_magnitude`
  carrying `magnitude`/`unit` strings, optional `zero_cost_evidence` and `cost_component_provenance_reference`).
- **Producer cost input** — the producer requires exact Phase 5 `ObservableCostValidityContext` items; **B2 does
  not carry that type** (it carries B2 cost bindings). This is the adaptation surface noted in §9.

---

## 4. B3 Role Classification

Master B3 is classified as a **stateless, synchronous, deterministic dumb-pipe client / thin adapter**. Its only
job per invocation: read exact-typed passive B2 evidence, extract by **exact field-read** the producer's required
inputs (with value-preserving, non-derived adaptation where a type shape differs), call
`produce_passive_shadow_input`, and **return the producer's output unchanged**. It is a **conduit**, never a
calculator, scorer, owner, or boundary author. It holds no state and makes no decision.

---

## 5. B3 Allowed Behavior

- **Call the producer.** B3 may call `produce_passive_shadow_input` with exactly its keyword-only parameters.
- **Exact field-read extraction (no derivation).** B3 may read, by exact field access from exact-typed passive
  B2 evidence: the gross-edge `magnitude`/`unit` (from the `GROSS_EDGE`-role binding's `unit_bound_magnitude`),
  and `venue`/`pair` (from the raw snapshot). These are pure reads — never split, projected, computed, or
  inferred.
- **Value-preserving adaptation (bounded, non-temporal).** Where the producer/handoff requires a different *type
  shape* than B2 carries (notably `observed_at_epoch_ms`: B2 canonical unsigned-int **string** → handoff exact
  **int**), B3 may perform a **value-preserving lexical conversion only** — no arithmetic, no rounding, no
  temporal interpretation, no clock. This is an adaptation, not a derivation or policy. (Its exact mechanism is
  left to the future TDD slice under the locks; nothing is designed here.)
- **Identity forwarding.** B3 must return/surface the producer's output **as-is** (the `PassiveShadowInput` on a
  pass, or the defensive carrier on a non-pass), by identity.

---

## 6. B3 Forbidden Behavior

- **No boundary mutation.** B3 must not modify, widen, subclass, wrap, monkeypatch, or reinterpret the producer
  or the Phase 5 passive socket (B3 client-only rule, RATIFIED).
- **No scoring/actionability.** No B4 `ShadowScore`, diagnostic-EV math, ranking, logging, calibration,
  thresholding, routing, sizing, execution, or intent emission.
- **No tombstone reopening.** No `edge_direction`, `staleness_threshold_ms`, capacity activation, Shadow Intent,
  order/sizing/execution intent, or actionability field — neither read-as-policy nor synthesized.
- **No loose input.** No `*args`/`**kwargs`/`dict`/blob/unbounded mapping/raw payload; exact-typed evidence only.
- **No derivation.** No economic derivation, no cost/gross inference, no pair-split, no venue-scope inference.
- **No state, no concurrency** (§8).
- **No output transformation.** No unpack/mutate/copy/re-instantiate/wrap of the producer output (§ identity
  forwarding).

---

## 7. Producer-Client Contract

- B3 calls `produce_passive_shadow_input(gross_edge_value=…, gross_edge_unit=…, cost_validity_contexts=…,
  source_venue=…, source_pair=…, observed_at_epoch_ms=…)` and **only** that producer entry. It calls neither the
  Phase 5 socket factories nor `calculate_net_edge` directly, nor `make_passive_shadow_input` directly — the
  producer owns that orchestration.
- All field validation remains delegated to the producer/socket/handoff factories; B3 re-validates nothing and
  fabricates nothing.
- B3 surfaces the producer's exact return value by identity; on a defensive non-pass it surfaces that carrier and
  performs no wrapping (mirroring the producer's own discipline).

---

## 8. Sync / Stateless Invariants

- **Strictly synchronous & deterministic.** No `async`/`await`, threading, multiprocessing, queues, event loops,
  callbacks, background workers, timers, or scheduler behavior. One call in → one call out.
- **Stateless.** No buffering, caching, memoization, previous-frame comparison, rolling windows, delta
  computation, or cross-frame derivation. Each invocation is an **isolated pass-through event** from B2-shaped
  evidence to a single producer call. No instance/module mutable state is retained between calls.

These are to be proven by AST/structure tests in the future slice (§10).

---

## 9. Cell-3 Separation & Zero-Cost Deferral

- **Cost-context assembly is a SEPARATE, deferred concern.** The producer requires exact Phase 5
  `ObservableCostValidityContext` items; **B2 does not carry that type**. Assembling cost contexts from B2 cost
  bindings is a distinct mapping (Cell-3-adjacent) and is **out of scope here**. The minimal B3 client wiring
  must **not** invent it by derivation.
- **Zero-cost deferral preserved.** The minimal critical path uses a **zero-valued cost context** and must not
  require real Cell-3 costs. The **empty cost tuple remains invalid**. The zero-valued cost context is a
  temporary deferral state (not a permanent assumption); the B3 wiring contract must stay ready to forward real
  B2-originated cost contexts once the separate Cell-3 / cost-assembly route is built.
- **No Cell-3 design.** This charter neither designs nor requires the Cell-3 route.

---

## 10. Future TDD Test Requirements (for a separately-authorized slice)

A future Master B3 client wiring TDD slice must prove:

- **Client call** — B3 calls `produce_passive_shadow_input` exactly as a client (no direct socket/handoff/math
  calls).
- **Identity preserved** — B3 returns the producer's exact output by identity (pass and defensive non-pass);
  no unpack/mutate/copy/re-instantiate/wrap.
- **No producer / Phase 5 modification** — producer and Phase 5 files untouched by the slice.
- **AST locks** — no toxic imports (actionable gross-edge gate carriers, directional-intent symbols, Shadow
  Intent, capacity-activation, freshness-policy modules); no `time`/`datetime`/clock; no `isinstance`; no
  `Protocol`/`Any`/`dict`-blob/duck typing; no `async`/`await`/threading/multiprocessing/queue/event-loop.
- **Stateless** — no module/instance mutable state, cache, buffer, window, delta, or memoization.
- **Tombstone token absence** — no `edge_direction`/`staleness`/`capacity`/Shadow-Intent/B4/logging tokens.
- **Cell-3 absent/deferred** — no real cost-context assembly; the zero-valued cost context path holds; empty
  tuple rejected.
- **Fixture purity** — passive-only fixtures built from scratch; no actionable carrier reused.

---

## 11. What This Does and Does Not Unblock

- **Does:** fix B3's dumb-pipe client contract, allowed/forbidden behavior, sync/stateless invariants, the
  producer-client contract, and the future-slice test requirements; honestly surface the cost-context assembly
  adaptation as deferred.
- **Does NOT:** implement or wire B3; design the B2→producer adaptation runtime; build cost-context assembly;
  touch B2/B3/producer/Phase 5; do any B4/logging/Phase 6.2.

**Master B3 remains UNBUILT and BLOCKED** as a runtime artifact after this docs-only charter.

---

## 12. Remaining Blockers

- **Master B3 client wiring — UNBUILT.** Now docs-bounded (this charter); a separate TDD slice would implement
  the dumb-pipe client under §4–§10.
- **B3 router-only Cell-3 cost-type pass-through / cost-context assembly — UNBUILT (separate/parallel).** Needed
  only for real-cost wiring; the minimal path uses the zero-valued cost context.

Tombstoned: `edge_direction`, `staleness_threshold_ms`. Built: B2 carriers (incl. cost-type provenance),
`PassiveShadowInput`, passive pre-net-edge carrier + Union, passive producer.

---

## 13. Still-Forbidden Work

- **No** B3 implementation/mock/code/test; **no** producer/Phase 5/B2 edit; **no** boundary
  mutation/widening/subclassing/wrapping/monkeypatch.
- **No** scoring/diagnostic-EV/ranking/threshold/durable-log/calibration; **no** routing/sizing/execution/intent.
- **No** `edge_direction`/`staleness`/capacity/Shadow-Intent reopening; **no** actionability field.
- **No** `*args`/`**kwargs`/dict-blob/loose input; **no** derivation; **no** economic inference.
- **No** `async`/threading/multiprocessing/queue/event-loop/callback/scheduler; **no** state/cache/buffer/window/
  delta/memoization.
- **No** clock/time read; **no** temporal policy; **no** Cell-3 route design or real cost-context assembly.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** weakening of the producer, Phase 5 passive socket, or B2 passive carrier invariants; **no** Phase 6.2
  readiness claim; **no** 7.x/8.x work.

---

## 14. Next Safe Step

- A **separately-authorized Master B3 client wiring TDD slice** — a new Phase 6.1 module + tests implementing the
  **dumb-pipe client** under §4–§10 (exact field-read extraction, value-preserving epoch adaptation,
  zero-cost-deferred context, identity forwarding), with AST/structure tests proving the §10 locks — **requiring
  its own explicit authorization** before any runtime. This charter finds **no remaining docs blocker** for that
  minimal dumb-pipe slice; the real-cost B2 cost-context assembly remains a **separate** deferred concern.
- The B3 router-only Cell-3 cost-type pass-through / cost-context assembly may be separately authorized at any
  time (parallel), required only for real-cost wiring.
- **No implementation is authorized by this charter.** Master B3 wiring, the Cell-3 route, B4 scoring, durable
  logs, Phase 5/producer modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x
  remain separately gated.
