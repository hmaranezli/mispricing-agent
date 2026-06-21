# Phase 6.2 — Multi-Event Context-Supply & Shadow-State Boundary Charter

> **This is a docs-only boundary/architecture charter.** It pins the **isolated downstream per-intent
> shadow-state container** — how cross-time shadow intents are held and how passive evidence intersections are
> classified against the ratified S1 audit replay — for a **future** Phase 6.2 capability. It **implements nothing
> and authorizes nothing executable**: no runtime code, no tests, no lock-test edits, no frozen-component edits, no
> container module, no state machine, no resolver/registry, no Phase 6.2 runtime, no pytest, no graphify. It makes
> **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_shadow_intent_lifecycle_state_transition_charter.md`,
> `docs/handoff/phase6_2_shadow_intent_field_shape_charter.md`,
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `e9995e7096cf1b5a322d92e8ce6f72f8f4b1f9a2`

---

## 1. Base / Purpose

**Base commit:** `e9995e7096cf1b5a322d92e8ce6f72f8f4b1f9a2`.

The lifecycle charter (`e9995e7`) pinned the closed state set and the exact legal transition table, but left **two**
prerequisites open: (a) the **cross-time container** that holds per-intent shadow state across replayed events, and
(b) the **bounded classification predicates** that recognize each observed trigger class from audited evidence. This
charter pins **(a) the isolated downstream per-intent state container** and **(b) the passive-evidence-intersection
classification boundary** under which those predicates may later be specified — so a future, separately-authorized
reconstruction runtime has an unambiguous, non-actionable target. It resolves the **context-supply / shadow-state
boundary** prerequisite (`a9ed9f4` §9.6 context supply, partially §9.2/§9.7) **only**; everything else stays open
and unauthorized.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Terminal Invariant Correction (binding)

The lifecycle charter (`e9995e7`, §4) stated that "an intent ends in **exactly one** terminal." That phrasing is
**hereby corrected** as too strong. The precise, ratified invariant is:

> **AT MOST ONE terminal state per intent — not exactly one.**

Consequences:

- An intent that reaches `INTENT_EXPIRED` or `INTENT_RETIRED` has **exactly one** terminal and is absorbed there
  (no cross-terminal, no revival — the §4 monotone/absorbing shape of `e9995e7` is unchanged).
- An intent that is still in a **non-terminal** state (`AUDIT_REPLAYED`, `INTENT_RECORDED`, or
  `HYPOTHETICAL_CONDITION_MET`) **when S1 replay stops** legitimately reaches **zero** terminals. The state machine
  **freezes** at end-of-replay (per `e9995e7` §2), and a frozen **open** non-terminal state is **valid audit
  state — NOT an error, NOT an incomplete record, NOT a defect**. It faithfully records "this is as far as the
  audited evidence carried this intent."
- The container therefore MUST tolerate, surface, and replay **open frozen** intents exactly as it surfaces
  terminated ones. It MUST NOT fabricate a synthetic terminal, force-expire, force-retire, or otherwise "complete"
  an open intent to satisfy a count. Manufacturing a terminal at replay EOF is **forbidden** (it would be a
  fabricated, un-audited transition, violating `a9ed9f4` §8 and `e9995e7` §2).

The legal transition table of `e9995e7` §4 stands intact; **only** the "exactly one terminal" wording is relaxed to
"at most one terminal," and "open frozen at replay EOF" is affirmed as valid.

---

## 3. Isolated Downstream Per-Intent State Container (binding)

The multi-event context is defined **strictly** as an **isolated downstream Phase 6.2 per-intent state container**:
a passive store that holds, per shadow intent, its current lifecycle state (from the `e9995e7` closed set) and the
by-reference audited evidence links it was derived from. It is the cross-time memory the lifecycle needs, and it is
**isolated**:

- It MUST live in an **isolated downstream Phase 6.2 boundary/package** (e.g. a future `phase6_2_shadow_intent/`
  package, analogous to the quarantined `phase6_1_s1_storage/`). No Phase 6.1 module imports it.
- Its dependency on S1 is **strictly one-way and read-only** (§9): it consumes the ratified S1 append-order replay
  and nothing else.
- It **MUST NOT mutate, write back to, delete from, reshape, re-factory, or attach state to**: the S1 durable
  adapter, the S1 audit records, S5, any Phase 6.1 carrier/DTO, or any frozen record. No Phase 6.1 DTO gains a
  lifecycle/intent/state/context field; S5 gains no per-event lookup/registry/cache/matching surface (it stays a
  dumb, single-pass, stateless coordinator).
- It holds **only** inert per-intent bookkeeping: lifecycle state + by-reference audited evidence links + a
  firewalled `HYPOTHETICAL_OUTCOME` projection (per `e9995e7` §6). It carries no endpoint, credential, connection,
  callback, or emission surface.

It records and classifies; it never acts.

---

## 4. Deterministic Per-Intent Keying (binding)

State tracking is **strictly per-intent**, keyed **only** by **ratified S1 Silver/audit references** already
recorded in the append-only trail:

- The per-intent key is the **opaque Silver identity pair** as recorded in the S1 audit envelope —
  (`artifact_locator`, `physical_record_position`) — carried **verbatim and opaque, borrowed never minted**.
- **FORBIDDEN keying surfaces:** no **global mutable identity registry**; no **domain identity invention** (no
  synthesizing a new intent id, hash-of-fields, sequence counter, or surrogate key); no **rowid-as-domain-identity**
  (the S1 `append_sequence` is medium-intrinsic append ordering only — per the S1 closeout `b06d7ed` §6 it is never
  returned and never a domain identity, and this container MUST NOT promote it to one).
- The container is a **keyed-by-audited-reference** lookup, not a registry that issues identities. It discovers
  intents from replay; it never allocates them. Two replays of the same audited trail key the same intents to the
  same slots (this underwrites the `e9995e7` §3 determinism/idempotency end-to-end).

---

## 5. Anti-Global-State Seal (binding)

The container holds **per-intent** state **only**. It MUST NOT aggregate, roll up, net, or sum per-intent states
into any **global / portfolio / account-level** structure. **Explicitly forbidden** aggregate surfaces:

- `wallet`, `account balance`, `realized PnL`, `portfolio`, `exposure book`, `position book`, net exposure,
  aggregate risk, or any **production-risk** / firm-level state;
- any "total" / "net" / "book" view that converts a collection of inert per-intent counterfactuals into a single
  actionable or balance-like quantity.

Each shadow intent is an **independent, isolated, inert bookkeeping slot**. `HYPOTHETICAL_OUTCOME` stays a
**per-intent counterfactual projection** (per `e9995e7` §6), never summed into a realized/aggregate result. There is
no global mutable state of any kind beyond the per-intent keyed store of §4.

---

## 6. Passive Evidence Intersection Vocabulary (binding)

Condition classification — how the container recognizes which `e9995e7` §4 trigger class a replayed observation
belongs to — is named with **passive evidence-intersection vocabulary** for any **newly defined** Phase 6.2 name,
field, or value, e.g.:

- **`EVIDENCE_INTERSECTION`** — the passive observation that an intent's already-recorded reference and a later
  audited observation's already-recorded value occupy a comparable evidentiary relation;
- **`PASSIVE_EVIDENCE_CROSSING`** — the direction-aware boundary relation defined in §7 (audited evidence crossing
  a passive boundary), classified counterfactually;
- **`TIMESTAMP_DELTA`** — the difference between two **already-recorded** audited provenance/evidence timestamps,
  used only for §8 expiry classification.

**Banned newly minted vocabulary** (case-insensitive, consistent with the package-wide token locks and `ef26f59`
§3 / `e9995e7` §5): `TRIGGER`, `EXECUTE`/`EXECUTION`, `ACTION`, `MATCH`, `ORDER`, `TRADE`, `BUY`, `SELL`,
`ROUTE`/`ROUTING`, `FILL`, `CANCEL` (and the already-banned `SUBMIT`/`PENDING`/`FILLED`/`CANCELLED`/`ROUTED`/
`EXECUTED`/`SIZING`/`ALLOCATION`/`SIGNAL`/`PAPER`/`LIVE`). The classification names a **passive evidentiary
intersection**, never an action. **Historical S1 audit evidence is read verbatim** and is **never** censored,
normalized, or rewritten to satisfy this vocabulary — the append-only trail is immutable and its payload strings are
consumed opaquely.

---

## 7. Bounded Comparison Semantics (binding)

The container may perform **only** the passive evidence comparisons strictly needed to classify
`HYPOTHETICAL_CONDITION_MET` or `INTENT_EXPIRED` (the `e9995e7` §4 trigger classes). The permitted comparison
surface is **bounded** to:

- **Equality / evidentiary intersection** — whether an intent's already-recorded reference and a later audited
  observation's already-recorded value are in the comparable relation (`EVIDENCE_INTERSECTION`).
- **Direction-aware boundary crossing** (`PASSIVE_EVIDENCE_CROSSING`), defined per the intent's passive
  `exposure_orientation` (`ef26f59` §6):
  - `POSITIVE_EXPOSURE` — classified when **audited evidence ≥ passive boundary**;
  - `NEGATIVE_EXPOSURE` — classified when **audited evidence ≤ passive boundary**;
  - `INERT_STATE` — no directional crossing defined.

These comparisons are **counterfactual bookkeeping only**. Both operands are **already-recorded audited values read
verbatim from S1**; the "passive boundary" is the intent's **own already-recorded** hypothetical reference, never a
live-computed or fabricated threshold. The comparison MUST NOT produce: advice, a ranking, a tradeable/actionable
threshold, a sizing/allocation, a decision, an instruction, or any value that converts an observation into an
action. It classifies a lifecycle trigger class and **nothing else**. Per `e9995e7` §6, the comparison classifies
transitions; it does **not** let `HYPOTHETICAL_OUTCOME` drive transitions (no outcome-threshold smuggling).

---

## 8. Expiry From Audited Evidence Only (binding)

`INTENT_EXPIRED` may be classified **only** from **audited S1 provenance/evidence timestamps** via `TIMESTAMP_DELTA`
— the difference between an intent's **already-recorded** hypothetical-window reference timestamp and a later
**replayed** observation's **already-recorded** `provenance_timestamp`, both read verbatim from S1. **Explicitly
forbidden:** **no wall-clock**, **no system-time `now()`**, **no scheduler**, **no timer/cron**, **no polling
loop**, **no system-time timeout**, and **no spontaneous (zero-observation) expiry**. Expiry is an
**audited-evidence event** surfaced by the next replayed observation — never a clock event. If replay stops before
such an observation arrives, the intent stays **open and frozen** (per §2), which is valid audit state, not an
expiry. Audited-observation order is the sole clock (`e9995e7` §2).

---

## 9. S1 Read-Only Replay Trust (binding)

The container reads **only** from the ratified S1 SQLite/WAL audit-replay boundary (minimal append-order readback,
per `b06d7ed` §5) — the durable, append-only, monotone trail is the **single source of truth**. Specifically:

- per-intent state is **derived from the S1 audit replay**, never from live recomputation, a parallel hidden store,
  or a non-S1 side channel;
- future tests **may** use **temporary S1 audit fixtures** (temp SQLite DBs populated via the ratified adapter), but
  **ad-hoc synthetic bypasses of S1** — hand-rolled intents/records that never flowed through the S1 boundary, or
  reading from a non-S1 side channel — are **forbidden**;
- the S1 read surface stays **minimal append-order replay** (no query DSL / analytics / filter / aggregation /
  export, per `b06d7ed` §5); the container consumes that replay and builds its own state **externally** in the
  downstream boundary.

The dependency is strictly one-way: **Phase 6.2 reads S1; S1 / Phase 6.1 never know about Phase 6.2.**

---

## 10. Capacity & Integration Ban (binding)

- **Capacity:** remains **DEFERRED with exactly 0 emit sites**; `CapacityConstraintGate` stays non-activatable;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred and is never read as "capacity validated." No
  container path references, consumes, or asserts capacity, and none adds an emit site.
- **Integration ban:** **NO** broker / exchange / paper-trading / market-data / venue API; **NO** execution,
  routing, order-emission, actionability, or integration hook / callback may be designed here or implied. The
  container is inert per-intent bookkeeping over audited evidence.

---

## 11. No Semantic Smuggling (binding)

The container holds **passive per-intent lifecycle state + by-reference audited evidence + a firewalled
counterfactual projection** and nothing else. It MUST NOT calculate or carry: executable advice, tradeable
thresholds, trade/route/size decisions, ranking, realized (real) PnL, account/portfolio balance, business
actionability, or any value that converts observation into instruction. The bounded comparisons of §7 classify a
lifecycle trigger class; they decide, rank, threshold-for-action, and instruct **nothing**. The future container and
its classification predicates are **dumb carriers + bounded passive classifiers with structural guards only**.

---

## 12. Precise Post-Charter State (ratified)

- **Phase 6.2: UNBUILT and NOT runtime-ready.** This charter pins **only** the context-supply / shadow-state
  boundary (§3), the deterministic per-intent keying (§4), the anti-global-state seal (§5), the passive
  evidence-intersection classification vocabulary and bounded comparison semantics (§6–§8), and corrects the
  terminal invariant (§2).
- **Still open / unauthorized:** the concrete per-intent state-container runtime, the exact-typed classification
  predicate implementations, the reconstruction state machine, replay-determinism/idempotency **mechanics in code**,
  and the remaining `a9ed9f4` §9 risk-inventory items not closed by design here. **Any runtime / state-machine /
  container TDD requires separate authorization.**
- **Phase 6.1:** COMPLETE + RATIFIED (unchanged). **Capacity:** deferred (0 emit sites). **Production / live /
  paper / canary / execution / routing / actionability:** forbidden.
- **Terminal invariant (corrected):** **at most one** terminal per intent; **open frozen non-terminal state at
  replay EOF is valid audit state**, never an error.

---

## 13. Next Safe Step

The boundary evidence (the container shape, keying, anti-global seal, and the bounded passive-classification
vocabulary are pinned, but the **exact-typed classification predicates** and the **concrete container runtime** are
still absent) shows the next gate is the **final predicate-specification design**, not implementation:

- A **separately-authorized Phase 6.2 Evidence-Intersection Classification Predicate Charter** — a docs-only design
  fixing, per `e9995e7` §4 trigger class, the **exact-typed, bounded, non-actionable** recognition predicate
  (the `EVIDENCE_INTERSECTION` / `PASSIVE_EVIDENCE_CROSSING` equality + direction-aware boundary relations of §7 and
  the `TIMESTAMP_DELTA` expiry rule of §8), all derived **only** from already-recorded audited S1 evidence, under
  the §5/§7/§11 firewalls, in the isolated downstream Phase 6.2 boundary.
- Only after that predicate charter (closing the last open `a9ed9f4` §9 design items) may a **separately-authorized
  Phase 6.2 shadow-intent reconstruction runtime / state-machine / container TDD slice** be considered. **This
  charter does NOT open, draft, or perform either step.**

**Conclusion:** the Phase 6.2 multi-event context is pinned (docs-only) as an **isolated downstream per-intent
shadow-state container** — quarantined in a future Phase 6.2 boundary, **one-way and read-only from the ratified S1
audit replay**, **keyed strictly by the opaque Silver audit reference** (no global mutable registry, no domain
identity invention, no rowid-as-domain-identity), holding **only** inert per-intent lifecycle state and by-reference
audited evidence with a **firewalled counterfactual `HYPOTHETICAL_OUTCOME`**, and **never** aggregating into a
wallet / balance / realized-PnL / portfolio / exposure-book / production-risk state. Condition classification uses
**passive evidence-intersection vocabulary** (`EVIDENCE_INTERSECTION`, `PASSIVE_EVIDENCE_CROSSING`,
`TIMESTAMP_DELTA`; `TRIGGER`/`EXECUTE`/`ACTION`/`MATCH`/`ORDER`/`TRADE`/`BUY`/`SELL`/`ROUTE`/`FILL`/`CANCEL`
**banned** for new names, historical S1 evidence read verbatim), with **bounded comparison semantics** — equality /
evidentiary intersection and direction-aware boundary crossing (`POSITIVE_EXPOSURE`: audited evidence ≥ passive
boundary; `NEGATIVE_EXPOSURE`: audited evidence ≤ passive boundary) — that are **counterfactual bookkeeping only**
and produce **no advice, ranking, actionable threshold, or executable decision**. `INTENT_EXPIRED` is classified
**only** from **audited S1 timestamps via `TIMESTAMP_DELTA`** (no wall-clock, scheduler, polling, or system-time
timeout). The **terminal invariant is corrected** to **at most one terminal per intent**, with **open frozen
non-terminal state at replay EOF affirmed as valid audit state, not an error**. **Capacity stays deferred at 0 emit
sites**; **no broker/exchange/paper/market-data/venue/execution/routing/order-emission integration** is designed.
**Phase 6.2 remains UNBUILT and NOT runtime-ready**; the **only** next safe step is a separately-authorized **Phase
6.2 Evidence-Intersection Classification Predicate Charter**, **not opened here**. **No executable work is
authorized.**
