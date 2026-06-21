# Post-Phase 6.1 — Risk Audit & Phase 6.2 Readiness Charter

> **This is a docs-only risk-audit / readiness charter.** It maps the architectural risks, readiness
> prerequisites, and hard boundaries for a **future** Phase 6.2 Shadow Intent capability. It **implements nothing
> and authorizes nothing executable**: no runtime code, no tests, no lock-test edits, no frozen-component edits, no
> schema, no Phase 6.2 runtime, no pytest, no graphify. It makes **no** Phase 6.2 readiness/paper/live/production
> claim. It is subordinate to `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, every per-stage
> Phase 6.1 closeout charter, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `061bf1ba9bfed3bc2a83bf18bb376b2c2a8f031a`

---

## 1. Base / Purpose

**Base commit:** `061bf1ba9bfed3bc2a83bf18bb376b2c2a8f031a`.

Phase 6.1 (passive in-memory + durable audit substrate) is **COMPLETE + RATIFIED** (`061bf1b`). This charter is the
**audit** that must precede any Phase 6.2 planning: it enumerates the risks, the readiness prerequisites, and the
**hard boundaries** a future Phase 6.2 Shadow Intent state machine must respect. It **opens no Phase 6.2 work**; it
only clarifies what a future, separately-authorized Phase 6.2 field-shape charter would have to satisfy.

**No capacity validation and no capacity pass is claimed by this charter** (see §6).

---

## 2. Phase 6.1 Baseline (ratified starting point)

Per `061bf1b`, the starting state is:

- **Phase 6.1 passive in-memory + durable audit substrate: COMPLETE + RATIFIED** — Reader → S2 → B2 ingestion →
  B2 normalizer → Cell-3 → B3 → B4/S4 → S1 in-memory reference sink, with the isolated SQLite/WAL durable audit
  adapter; `SCORE` and `HALT` are equal-peer families.
- **Forbidden / not claimed:** production, live data, paper trading, canary, execution, order routing,
  actionability. Capacity gate deferred (0 emit sites). Multi-event context-supply, registries, and analytics
  export are **separate unbuilt boundaries**.
- **Phase 6.2: NOT ready.** This charter does not change that — it audits the path toward a future readiness
  decision.

---

## 3. Shadow Intent Isolation (binding boundary)

Phase 6.2, when/if authorized, is defined **only** as an **isolated shadow-intent state machine** — a passive,
observation-derived record of "what an intent *would* be" that **never acts**. It **MUST NOT**:

- connect to any real exchange, market data feed, or venue API;
- connect to any broker **paper-trading** API (paper is still a live-broker connection and is forbidden);
- perform or simulate order routing, order emission, order placement, or execution;
- expose any live actionability, trade trigger, or sizing/allocation surface;
- integrate with any production system or external service.

A shadow intent is a **diagnostic artifact** computed from already-recorded passive observations; it is inert. The
DRY_RUN posture and all constitution guardrails remain in force. Any feature that would let a shadow intent *cause
an action* is **out of scope for all of Phase 6.2 readiness** and would require its own, separately-gated,
human-authorized charter far beyond this audit.

---

## 4. Multi-Event Context / State Boundary Risk (binding boundary)

Tracking shadow intents **across time** (an intent opens, evolves, and resolves over multiple observed events)
requires a **multi-event context / state boundary** that Phase 6.1 deliberately does **not** provide (S5 is a dumb,
single-pass-event, stateless coordinator with no per-event context map).

- This **registry / resolver / state machine MUST be architected OUTSIDE the frozen Phase 6.1 pipeline.** It **must
  not** pollute S5 or any Phase 6.1 carrier: no per-event lookup/registry/cache/matching may be added to S5; no
  Phase 6.1 frozen DTO may gain a state/intent/lifecycle field; no Phase 6.1 module may import the Phase 6.2 state
  boundary.
- The dependency direction must stay one-way: **Phase 6.2 may read Phase 6.1 outputs; Phase 6.1 never knows about
  Phase 6.2.** The state boundary is a new top-level concern (analogous to how the durable adapter was quarantined
  in `phase6_1_s1_storage/`).
- **Risk:** state leakage / coupling that would make Phase 6.1 stateful or actionable. Mitigation: strict
  quarantine + read-only consumption of Phase 6.1 records.

---

## 5. S1 Replay Trust Boundary (binding)

Phase 6.2 state reconstruction **MUST** flow through the ratified **S1 SQLite/WAL audit trail** boundary — the
durable, append-only, monotonic record is the **single source of truth** for "what was observed." Specifically:

- shadow-intent state is **derived from the S1 audit replay** (append-order readback), never from live recomputation
  or a parallel hidden store;
- tests may use **temporary S1 audit fixtures** (temp SQLite DBs populated via the ratified adapter), but **ad-hoc
  synthetic bypasses of S1** — fabricating intent state directly, hand-rolling records that never passed through
  the S1 boundary, or reading from a non-S1 side channel — are **forbidden**;
- the S1 read surface stays **minimal append-order replay** (no query DSL/analytics, §7); Phase 6.2 consumes that
  replay and builds its own state externally.
- **Risk:** trust-boundary erosion (state diverging from the audited truth). Mitigation: S1-replay-only
  reconstruction + determinism checks (§9).

---

## 6. Capacity Lock (ratified)

**Capacity gates remain DEFERRED with exactly 0 emit sites.** `CapacityConstraintGate` stays non-activatable;
`PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated."
**Phase 6.2 readiness work MUST NOT create any execution, routing, order-emission, or capacity-activation surface**,
and must not add a capacity emit site. A shadow intent never consumes or asserts capacity.

---

## 7. Analytics Boundary (ratified)

Parquet, dashboards, analytics mirrors, reporting layers, query DSLs, and export systems remain **separate future
boundaries** and **MUST NOT** be smuggled into Phase 6.2 readiness. Phase 6.2 may read the minimal S1 append-order
replay; it may **not** introduce an analytics/reporting/export surface, nor may such a surface be justified "for
Phase 6.2 state." Any analytics is its own separately-gated boundary.

---

## 8. Integrity Maintenance (ratified)

Phase 6.1's **fail-fast vs structural-halt discipline is preserved end-to-end** into any Phase 6.2 reasoning:

- **Expected structural halts stay explicit** — `HALT` observations (materialized from
  `OptionBLocalParseHalt` / `BlockedPacket` via S4) are first-class equal peers in the audit trail and must be
  surfaced, never hidden, when reconstructing shadow state.
- **Unexpected runtime crashes must NOT be swallowed into shadow state** — raw exceptions
  (`B2PassPathIngestionValueError`/`TypeError`, `S5RunnerUnexpectedOutputError`, or any unexpected exception)
  remain hard fail-fast and must never be converted into a shadow intent, a synthetic halt, or a silently-absorbed
  state transition. A Phase 6.2 state machine that ingests the audit trail must treat a crash as a crash, not as a
  state.

---

## 9. Risk Inventory (the readiness prerequisites before any Phase 6.2 runtime)

Each item below is an **open risk** that a future, separately-authorized Phase 6.2 field-shape charter must resolve
**before** any Phase 6.2 runtime may be authorized. None is resolved here.

1. **Shadow intent schema** — the exact passive, frozen, methodless shape of a shadow intent (no actionability
   field, no order/size/route field); how it references the S1 observations it is derived from (by audited identity,
   never minted).
2. **State transitions** — the explicit, closed set of shadow-intent states and the exact-typed transition rules;
   no implicit/derived transitions.
3. **Lifecycle rules** — open/evolve/resolve/expire semantics defined over **observed** events only, with no clock
   manufacturing and no time-based action.
4. **Replay determinism** — reconstructing identical shadow state from the same S1 audit trail must be **byte/shape
   deterministic** (the durable payload is already deterministic, fixed-key canonical text).
5. **Idempotency** — replaying the same audited events any number of times yields the same state; no double-counting,
   no accumulation drift.
6. **Context supply** — the multi-event context/state boundary (§4): how per-intent context is supplied **outside**
   S5 without a Phase 6.1 registry/resolver, and without fabrication.
7. **Halt propagation** — how `HALT` peers propagate into shadow state (a halted observation never silently becomes
   a pass; §8); crash vs structural-halt distinction preserved.
8. **Auditability** — every shadow-state transition must be explainable from the S1 audit trail (the constitution's
   "why" requirement); no un-audited state.
9. **Capacity isolation** — proof that no shadow-intent path touches capacity, execution, routing, or order emission
   (§6); 0 emit sites preserved.
10. **No-actionability enforcement** — structural (lock-style) guarantees that no Phase 6.2 surface can become an
    action/trade/route/size/execution trigger; passive-only invariant enforced by tests/locks, not by convention.

Until **all ten** are resolved by separately-ratified design, **Phase 6.2 runtime is NOT eligible.**

---

## 10. No Readiness Smuggling (binding)

This charter clarifies future Phase 6.2 planning **only**. It claims **NO** Phase 6.2 runtime readiness, **NO**
paper readiness, **NO** live readiness, **NO** production readiness, and **NO** implementation authorization. It
adds no runtime surface, no test, no schema, and no scope. "Clearer planning" is **not** "readiness."

---

## 11. Precise State & Next Safe Step

- **Phase 6.1:** COMPLETE + RATIFIED (passive in-memory + durable audit substrate). **Phase 6.2: NOT ready** — the
  §9 risk inventory is entirely open.
- **Capacity:** deferred (0 emit sites). **Multi-event context/state boundary, registries/resolvers, analytics
  export:** separate unbuilt boundaries. **Production / live / paper / canary / execution / routing /
  actionability:** forbidden.
- **Next safe step (recommendation only):** a **separately-authorized Phase 6.2 Shadow Intent Field-Shape Charter**
  — a docs-only design that resolves (at least) §9.1–§9.3 (shadow intent schema, state transitions, lifecycle
  rules) as a **passive, isolated, non-actionable** shape derived from the S1 audit trail, **outside** the frozen
  Phase 6.1 pipeline, with the §3–§8 boundaries intact. **This charter does NOT open, draft, or perform that next
  step.**

**Conclusion:** Phase 6.1 stands **complete and ratified** as a passive in-memory + durable audit substrate; this
audit maps the path to a **possible future** Phase 6.2 **without** authorizing any of it. Phase 6.2 is admissible
**only** as an **isolated shadow-intent state machine** that never connects to exchanges, broker/paper APIs, order
routing, execution, or production; its cross-time **context/state boundary must live OUTSIDE** the frozen Phase 6.1
pipeline and must not pollute S5 or any Phase 6.1 carrier; its state must be reconstructed **only** through the
ratified **S1 audit-trail trust boundary** (no synthetic bypass); **capacity stays deferred at 0 emit sites**;
**analytics/export stay separate**; and Phase 6.1's **fail-fast vs structural-halt** discipline (equal-peer
`SCORE`/`HALT`; crashes never swallowed) is preserved. Ten readiness risks — **shadow intent schema, state
transitions, lifecycle rules, replay determinism, idempotency, context supply, halt propagation, auditability,
capacity isolation, and no-actionability enforcement** — remain **entirely open** and must be resolved by
separately-ratified design before any Phase 6.2 runtime is eligible. This charter makes **NO** readiness/paper/live/
production/implementation claim; the **only** next safe step is a separately-authorized **Phase 6.2 Shadow Intent
Field-Shape Charter**, **not opened here**. **No executable work is authorized.**
