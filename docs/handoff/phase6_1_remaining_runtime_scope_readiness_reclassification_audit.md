# Phase 6.1 Remaining Runtime Scope — Readiness Reclassification Audit

> **This is a docs-only topological/readiness audit.** It maps the remaining runtime steps for Phase 6.1 now that
> the Phase 5 passive socket, the passive producer, and the Master B3 minimal client are BUILT + RATIFIED. It
> **designs and builds nothing** — only blocker classification and sequencing. It authorizes NO runtime, NO
> tests, NO lock-test edits, NO Python, NO schema/runtime/interface edits, NO B3 refactor, NO top-level
> runner/wrapper, NO B4 scoring design/math, NO shadow-log schema/persistence design, NO Cell-3 runtime/design,
> NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_master_b3_client_wiring_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_master_b3_client_wiring_charter.md`,
> `docs/handoff/phase6_1_passive_producer_tdd_closeout_ratification.md`,
> `docs/handoff/phase6_1_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md`,
> `docs/handoff/phase5_to_live_canary_roadmap.md`, the shadow-scoring TDD planning charter, and `CLAUDE.md`; where
> any conflict arises, those govern.

**Base:** `09bce9bf1d7b5cf662c609dadcc0a5ee259941d0`

---

## 1. Base / Dependency Chain

**Base commit:** `09bce9bf1d7b5cf662c609dadcc0a5ee259941d0`.

References:

- `…_master_b3_client_wiring_tdd_closeout_ratification.md` — B3 minimal client BUILT + RATIFIED; recorded the
  `B3PassiveClientWiringError` divergence as a ratified behavior + unresolved integration question.
- `…_passive_producer_tdd_closeout_ratification.md` / `…_phase5_passive_pre_net_edge_carrier_tdd_closeout_ratification.md`
  — producer and Phase 5 passive socket BUILT + RATIFIED.
- `…_shadow_scoring_tdd_planning.md` — pipeline **B1→B2→B3→B4 passive shadow scoring**; remaining slices **0A**
  (handoff type — pinned via `PassiveShadowInput`), **0B** (durable passive shadow artifact/`ShadowObservation`),
  **0C** (provenance chain locks); B4 consumes **only** the typed passed non-halt handoff and **must not** consume
  halt carriers.
- `…_phase5_to_live_canary_roadmap.md` — gating/sequencing; Phase 6.2 = calibration.

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Built + Ratified Components

- **Phase 5 passive socket** — `PassiveGrossEdgeMagnitude` / `PassivePreNetEdgeCalculationInput` + additive
  exact-typed Union at `calculate_net_edge` (single math source).
- **Passive producer** — `produce_passive_shadow_input` (arranger; emit-not-score; identity pass-through).
- **`PassiveShadowInput` handoff** — Slice-0A typed carrier (references `NetEdgeCalculationResult` by identity).
- **Master B3 minimal client** — `wire_passive_shadow_input` (stateless, synchronous dumb pipe; producer-only;
  identity forwarding; lexical epoch adaptation; structural fail-fast `B3PassiveClientWiringError`).
- **B2 normalized-evidence carriers** — incl. the ratified passive `cost_component_provenance_reference`.

These are frozen; this audit changes none of them.

---

## 3. Tombstoned / Excluded Items

- **`edge_direction`** — external intent; NOT NECESSARY for the passive path (tombstoned).
- **`staleness_threshold_ms`** — downstream temporal policy/calibration; NOT NECESSARY for B3/passive routing
  (tombstoned).
- **Capacity activation** — `CapacityConstraintGate` non-activatable, 0 emit sites; `capacity_pass_reference`
  stays `None`/deferred.

None of these is part of the remaining Phase 6.1 runtime scope.

---

## 4. Remaining Runtime Scope Map (topological)

Downstream of the built B1→B2→B3 pass/halt outputs, the still-unbuilt runtime steps are:

- **(S1) Durable passive shadow artifact / log** — the durable, **replayable** record of passive outcomes
  (Slice 0B). This is the **keystone**: Phase 6.1 completion is defined (roadmap/Phase-6.2 gate) by producing
  durable replayable shadow logs.
- **(S2) Provenance chain locks** — replay snapshot → normalized evidence → Phase 5 gate → shadow record
  (Slice 0C).
- **(S3) B4 passive shadow scoring** — consumes the **pass handoff only** (`PassiveShadowInput`), produces
  `ShadowObservation` / `ShadowScore` (passive, diagnostic).
- **(S4) Halt materialization / exception routing** — both the producer's **semantic/math halt** (`BlockedPacket`,
  forwarded by B3) and B3's **structural halt** (`B3PassiveClientWiringError`) must be **materialized** into the
  durable log for *complete* shadow logging (the log must record valid scores **and** halts). Currently a halt is
  either an identity-forwarded carrier or a raised typed error — neither is yet recorded.
- **(S5) Top-level passive runner / wrapper** — the orchestrator that drives B1→B2→B3→(B4) and routes scored
  observations **and** materialized halts into the durable log. None exists yet.

All of S1–S5 are **UNBUILT**. This audit designs none of them.

---

## 5. B3 Structural Failure Divergence Classification

- **Ratified behavior (not a bug).** B3 raises a typed, explicit `B3PassiveClientWiringError` on structural/
  extraction failures (non-material input, missing/ambiguous `GROSS_EDGE` binding, non-canonical epoch); the
  producer is not called and nothing is swallowed. **B3 remains frozen as built; this is not relabeled as a
  defect.**
- **Unresolved integration question.** For *complete* shadow logging (S4), structural halts must eventually be
  **materialized** (recorded), but the as-built shield surfaces them as a **raised exception**, not a recorded
  carrier. The architectural decision space (mapped only — **not** solved/designed here):
  - **Option A — top-level runner materializes.** A future runner/wrapper (S5) catches the typed
    `B3PassiveClientWiringError` and materializes/logs it as a structural-halt record. **B3 stays frozen** (no
    refactor) — consistent with the frozen-B3 lock.
  - **Option B — B3 carrier-refactor.** A future, separately-authorized change makes B3 *return* a structural-halt
    carrier instead of raising. This **requires** unfreezing/refactoring B3 (separate authorization; disfavored by
    the frozen-B3 lock unless explicitly chosen).
  - **Option C — BLOCKED/DEFERRED pending log architecture.** The choice between A and B depends on the (unbuilt)
    durable-log record model (S1); until that exists, the decision is **DEFERRED**.
- **Classification verdict:** **DEFERRED pending the durable-log architecture (S1).** Option A is the only path
  that preserves the frozen-B3 ratification without a separate refactor; Option B is available only via separate
  authorization. **No option is selected or designed here.**

---

## 6. B4 vs Shadow-Log Boundary

- **B4 scores valid passive results only.** B4 consumes the **pass handoff** (`PassiveShadowInput`) and produces
  `ShadowObservation`/`ShadowScore`. It **must not** consume halt carriers (`BlockedPacket`/`NoEligibleHaltPacket`)
  nor B3 structural errors.
- **Shadow logging is a separate sink.** The durable log (S1) must eventually record **both** valid scores **and**
  materialized halts (S4). B4 is therefore **one producer of log entries** (scores); halt materialization is a
  **distinct** producer of log entries (halts). **B4 ≠ shadow log.**
- **Designed nowhere here:** no B4 math, no diagnostic-EV formula, no log schema, no persistence mechanism.

---

## 7. Cell-3 Real-Cost Route Classification

- **Structural completion vs. real-cost completion are distinct.**
  - **Minimal zero-valued-cost path:** the pipeline is structurally complete and **replayable** with a zero-valued
    cost context (net edge = gross over the existing math); the durable log can record net-edge outcomes
    regardless of cost source.
  - **Real-cost completeness:** economically-meaningful shadow scoring (net edge after *real* costs) requires
    real B2-originated cost contexts assembled into Phase 5 `ObservableCostValidityContext` — the Cell-3 route.
- **Classification verdict:** real-cost Cell-3 assembly is **NOT required for the structural Phase 6.1 runtime +
  durable-log completion** (the minimal zero-cost path suffices to produce a complete, replayable passive log);
  it is **separate/parallel**. However, it is a **fidelity prerequisite for economically-meaningful shadow data**
  that **Phase 6.2 calibration** will ultimately depend on. It is therefore **separate/parallel for Phase 6.1
  structural completion, and a fidelity dependency for trustworthy Phase 6.2 calibration.** **Cell-3 is not
  designed here.**

---

## 8. Phase 6.1 Readiness Verdict — **NOT READY / INCOMPLETE**

Phase 6.1 is **not complete**: although B1→B3 carriers/clients and the producer are BUILT + RATIFIED, the
**durable replayable shadow log (S1)** — the defining completion artifact — **does not yet exist**, and neither do
provenance chain locks (S2), B4 scoring (S3), halt materialization (S4), or the top-level runner (S5). Per the
"do not claim complete unless every runtime/log prerequisite is satisfied" rule, the verdict is **NOT READY**.
(The *upstream evaluation spine* B1→B3+producer is ready; the *scoring + durable-logging tail* is not.)

---

## 9. Phase 6.2 Gate Statement

**Phase 6.2 (calibration) cannot be claimed ready.** Phase 6.2 is gated on Phase 6.1 producing **durable,
replayable shadow logs** (S1) — which do not yet exist. No Phase 6.2 readiness is claimed; Phase 6.2 remains
separately gated behind the entire S1–S5 tail (and, for trustworthy calibration inputs, the real-cost Cell-3
fidelity dependency of §7).

---

## 10. Exact Remaining Blocker List

1. **(S1) Durable passive shadow artifact / log** (Slice 0B) — UNBUILT. **Keystone / completion-defining.**
2. **(S2) Provenance chain locks** (Slice 0C) — UNBUILT.
3. **(S3) B4 passive shadow scoring** (`ShadowObservation`/`ShadowScore`) — UNBUILT.
4. **(S4) Halt materialization / exception routing** (semantic `BlockedPacket` + structural
   `B3PassiveClientWiringError` → log) — UNBUILT; **DEFERRED pending S1** (§5).
5. **(S5) Top-level passive runner / wrapper** (orchestrate B1→B4; route scores + halts to the log) — UNBUILT.
6. **(Separate/parallel) Real-cost Cell-3 cost-context assembly** — UNBUILT; fidelity dependency for Phase 6.2,
   not required for S1 structural completion (§7).

Tombstoned/out of scope: `edge_direction`, `staleness_threshold_ms`, capacity activation.

---

## 11. Recommended Sequence (recommendation only — nothing designed)

In dependency order (each separately authorized; docs-first):

1. **S1 — durable passive shadow log architecture** (Slice 0B planning, then slice). *Keystone:* it defines the
   record model for both scores and materialized halts, and is the Phase-6.2 completion gate.
2. **S2 — provenance chain locks** (Slice 0C).
3. **Exception-routing decision** (§5 Option A vs B) — now resolvable **because** the log record model exists;
   Option A (runner materializes; B3 stays frozen) is the frozen-B3-preserving path.
4. **S3 — B4 passive shadow scoring** slice (pass handoff → `ShadowObservation`/`ShadowScore`).
5. **S5 — top-level passive runner** that drives B1→B4 and routes scored observations **and** materialized halts
   into the durable log.
6. **(Parallel, any time) Real-cost Cell-3 assembly** — independent of S1–S5 structurally; needed before
   Phase-6.2 calibration is economically trustworthy.

Then a separate **Phase 6.2 gate review** once durable replayable logs exist.

Rationale for ordering: S1 is the keystone that unblocks the exception-routing decision and gives B4/the runner a
sink; sequencing it first removes the dependency that gates S3/S4/S5. Cell-3 is decoupled and therefore parallel.

---

## 12. Still-Forbidden Work

- **No** B3 refactor; **no** relabeling of the typed `B3PassiveClientWiringError` shield as a bug.
- **No** design/implementation of the durable log/schema/persistence, provenance locks, B4 math/scoring, halt
  materialization, top-level runner, or Cell-3 route.
- **No** selection or design of the exception-routing option (A/B/C) here.
- **No** B2/B3/producer/Phase 5/`passive_shadow_input` runtime/schema change; **no** test/lock-test edit.
- **No** reopening of `edge_direction`/`staleness_threshold_ms`/cost vocabulary values; **no** capacity
  activation; **no** Shadow Intent Envelope; **no** actionability/routing/sizing/execution.
- **No** Phase 6.1 completion claim while S1–S5 are unbuilt; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized docs-only Durable Passive Shadow Log (Slice 0B) architecture charter** (S1) — the
  keystone record model for valid scores **and** materialized halts, replayable and deterministic — **designing no
  runtime** until that authorization. Resolving S1 also unblocks the §5 exception-routing decision.
- Independently, the **real-cost Cell-3 cost-context assembly** charter may be separately authorized at any time
  (parallel; fidelity dependency for Phase 6.2).
- **No implementation is authorized by this charter.** S1–S5, the Cell-3 route, B4 scoring, durable logs,
  Phase 5/producer/B3 modification, the Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x
  remain separately gated.

**Conclusion:** Phase 6.1 is **NOT complete** (durable replayable shadow logs do not yet exist); **Phase 6.2 is
NOT ready**. The evaluation spine (Phase 5 socket + producer + B3 minimal client) is **BUILT + RATIFIED**; the
scoring + durable-logging tail (S1–S5) and the parallel real-cost Cell-3 fidelity route remain **separately-gated,
evidence-grounded blockers** — preferred as **BLOCKED/DEFERRED** over any design invention here. **No executable
work is authorized.**
