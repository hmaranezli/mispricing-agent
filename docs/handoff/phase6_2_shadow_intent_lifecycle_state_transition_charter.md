# Phase 6.2 — Shadow Intent Lifecycle & State-Transition Charter

> **This is a docs-only lifecycle/transition charter.** It pins the **exact legal state-transition table** and the
> **invariants** for inert Phase 6.2 shadow intents, driven solely by sequential S1 audit replay. It **implements
> nothing and authorizes nothing executable**: no runtime code, no tests, no lock-test edits, no frozen-component
> edits, no state machine, no Phase 6.2 runtime, no pytest, no graphify. It makes **no** Phase 6.2 runtime/paper/
> live/production readiness claim. It is subordinate to `docs/handoff/phase6_2_shadow_intent_field_shape_charter.md`,
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `ef26f599c6a5d3021feb340992b41419e4d50aa8`

---

## 1. Base / Purpose

**Base commit:** `ef26f599c6a5d3021feb340992b41419e4d50aa8`.

The Phase 6.2 field-shape charter (`ef26f59`) pinned the inert shadow-intent shape and the five passive lifecycle
states. This charter pins the **exact legal transitions** between those states and the **determinism / idempotency
/ read-only / no-clock** invariants — so a future, separately-authorized reconstruction runtime has an unambiguous,
non-actionable target. It resolves the transition-rules prerequisite only; everything else stays open and
unauthorized.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Strict Observed-Event-Driven Transitions (binding)

Every transition is triggered **exclusively** by consuming the **next sequential observation from the ratified S1
SQLite/WAL audit replay** (append-order readback). There is:

- **NO** system-clock action, **NO** timer / scheduler / cron behavior, **NO** polling loop, **NO** wall-clock
  timeout, and **NO** spontaneous (zero-observation) transition.
- A "window lapse" / "expiry" is determined **only** from **audited evidence** — e.g. a later replayed observation
  whose **already-recorded** `provenance_timestamp` (read verbatim from S1) lies beyond the intent's
  **already-recorded** hypothetical window — never from the current wall clock.
- **If S1 replay stops, the shadow state machine FREEZES.** No further transition occurs until and unless more
  audited observations are replayed. The machine has no independent heartbeat.

The replay is the **sole** clock: lifecycle time is audited-observation order, nothing else.

---

## 3. Replay Determinism & Idempotency (binding)

- **Determinism:** the lifecycle is a **pure function of the audited observation sequence**. Replaying the exact
  same S1 audit trail yields the **exact same** shadow-intent states and the same hypothetical-outcome projections,
  every time. No randomness, no clock, no external/hidden state.
- **Idempotency:** re-processing the same audited events (in whole or by re-replay) produces the same final state —
  no double-counting, no accumulation drift. This is structurally guaranteed by §4's **monotone progression +
  absorbing terminals + no-op self-loops**.
- **No side effects:** reconstruction reads S1 and computes inert state in the downstream Phase 6.2 boundary only;
  it writes nothing back, emits nothing, and integrates with nothing (§7, §8, §9).

---

## 4. Exact Legal Transition Table (binding)

The **only** states are the five ratified passive states. **`AUDIT_REPLAYED` is the initial (reconstruction-
bootstrap) state** of every shadow-intent lifecycle slot derived from replay. `INTENT_EXPIRED` and `INTENT_RETIRED`
are **absorbing terminals**. The trigger of every transition is the next sequential S1 replay observation,
classified **only** from already-recorded audited evidence (§2); the exact recognition predicate per trigger class
is a bounded, non-actionable classification **deferred** to a later runtime charter under the §6/§9 firewall — this
charter fixes the **states and their legal edges**.

| # | From state | Observed trigger class (from S1 replay, evidence-only) | To state |
|---|------------|--------------------------------------------------------|----------|
| 1 | `AUDIT_REPLAYED` | evidence establishes the shadow intent | `INTENT_RECORDED` |
| 2 | `AUDIT_REPLAYED` | evidence does not establish this intent (irrelevant) | `AUDIT_REPLAYED` (self, no-op) |
| 3 | `INTENT_RECORDED` | evidence the hypothetical condition holds | `HYPOTHETICAL_CONDITION_MET` |
| 4 | `INTENT_RECORDED` | evidence the hypothetical window lapsed | `INTENT_EXPIRED` |
| 5 | `INTENT_RECORDED` | evidence of passive close-out / retirement | `INTENT_RETIRED` |
| 6 | `INTENT_RECORDED` | evidence irrelevant to this intent | `INTENT_RECORDED` (self, no-op) |
| 7 | `HYPOTHETICAL_CONDITION_MET` | evidence the hypothetical window lapsed | `INTENT_EXPIRED` |
| 8 | `HYPOTHETICAL_CONDITION_MET` | evidence of passive close-out / retirement | `INTENT_RETIRED` |
| 9 | `HYPOTHETICAL_CONDITION_MET` | evidence sustaining the met condition / irrelevant | `HYPOTHETICAL_CONDITION_MET` (self, no-op) |
| 10 | `INTENT_EXPIRED` | any observation | `INTENT_EXPIRED` (absorbing self, no-op) |
| 11 | `INTENT_RETIRED` | any observation | `INTENT_RETIRED` (absorbing self, no-op) |

**Any transition not explicitly listed above is FORBIDDEN.** In particular:

- **No regression / backward edge:** `HYPOTHETICAL_CONDITION_MET → INTENT_RECORDED`, `INTENT_RECORDED →
  AUDIT_REPLAYED`, and any `→ AUDIT_REPLAYED` from a non-initial state are **forbidden**.
- **No terminal revival:** `INTENT_EXPIRED → *` and `INTENT_RETIRED → *` (to any other state) are **forbidden** —
  terminals are absorbing.
- **No cross-terminal:** `INTENT_EXPIRED ↔ INTENT_RETIRED` is **forbidden**; an intent ends in **exactly one**
  terminal.
- **Monotone lifecycle:** the only legal forward path is
  `AUDIT_REPLAYED → INTENT_RECORDED → (HYPOTHETICAL_CONDITION_MET)? → (INTENT_EXPIRED | INTENT_RETIRED)`, with
  no-op self-loops permitted at every non-absorbing state.

This monotone, absorbing-terminal shape is what makes the lifecycle **deterministic and idempotent** (§3) over any
replay of the same audited sequence.

---

## 5. Tombstoned Vocabulary Preservation (binding)

No active lifecycle term is introduced. **Banned** (for any newly defined Phase 6.2 state/name/value):
`PENDING`, `FILLED`, `CANCELLED`, `SUBMITTED`, `ROUTED`, `EXECUTED`, `ORDER`, `TRADE`, `BUY`, `SELL`, and all
actionability/execution vocabulary (consistent with `ef26f59` §3 and the package-wide token locks). The closed
state set is exactly `{AUDIT_REPLAYED, INTENT_RECORDED, HYPOTHETICAL_CONDITION_MET, INTENT_EXPIRED,
INTENT_RETIRED}`. **Historical S1 audit evidence is read verbatim and must NOT be censored, normalized, or
rewritten** to satisfy this vocabulary — the append-only audit trail is immutable and its recorded payload strings
are consumed opaquely.

---

## 6. Hypothetical Outcome Firewall (binding)

`HYPOTHETICAL_OUTCOME` is defined **strictly** as a **counterfactual difference / projection over audited S1
evidence** — e.g. the difference between an intent's already-recorded hypothetical reference and a later audited
observation's already-recorded value, both read verbatim from S1. It is **NOT**, and may never be treated as:
realized PnL, wallet balance, account state, executable advice, a ranking, a threshold, or an actionability signal.

- It is computed (in a future runtime) **only** as an inert projection at condition/terminal states; it **does not
  drive transitions** (transitions are evidence-classified per §4, not outcome-threshold-driven), preventing any
  threshold/decision smuggling.
- It carries **no** instruction and authorizes **no** action.

---

## 7. S1 Read-Only Dependency (binding)

The lifecycle / state-transition layer **may read** from the ratified S1 audit-replay boundary (minimal append-order
readback) and **MUST NOT**: write back to S1, mutate or delete S1 records, alter any Phase 6.1 data, or **attach
lifecycle state to any Phase 6.1 DTO**. S1 stays append-only and immutable; shadow state lives **only** in the
downstream Phase 6.2 boundary. The dependency is strictly one-way: **Phase 6.2 reads S1; S1 / Phase 6.1 never know
about Phase 6.2.**

---

## 8. Phase 6.1 Quarantine & Capacity / Integration Ban (binding)

- **Quarantine:** state-transition logic, lifecycle context, registries, resolvers, and shadow state MUST remain in
  an **isolated downstream Phase 6.2 boundary/package** (analogous to the quarantined `phase6_1_s1_storage/`). They
  MUST NOT pollute S5, the S1 durable adapter, any Phase 6.1 carrier/DTO, or the frozen records; no Phase 6.1 module
  imports Phase 6.2.
- **Capacity:** remains **DEFERRED with exactly 0 emit sites**; no lifecycle path references, consumes, or asserts
  capacity, and none adds an emit site.
- **Integration ban:** **NO** broker / exchange / paper-trading / market-data / venue API, **NO** execution,
  routing, order-emission, or integration hook may be designed here or implied. The state machine is inert
  bookkeeping over audited evidence.

---

## 9. Precise Post-Charter State (ratified)

- **Phase 6.2: UNBUILT and NOT runtime-ready.** This charter pins **only** the lifecycle transition table (§4) and
  its invariants (§2, §3, §5–§8).
- **Still open / unauthorized:** the exact trigger-classification predicates, the multi-event **context-supply /
  shadow-state boundary** runtime, the reconstruction state machine, and the remaining `a9ed9f4` §9 risk-inventory
  items. **Any runtime / state-machine TDD requires separate authorization.**
- **Phase 6.1:** COMPLETE + RATIFIED (unchanged). **Capacity:** deferred (0 emit sites). **Production / live /
  paper / canary / execution / routing / actionability:** forbidden.

---

## 10. Next Safe Step

The lifecycle evidence (transitions pinned, but the trigger predicates and the cross-time state container still
absent) shows the next gate is the **context/state boundary design**, not implementation:

- A **separately-authorized Phase 6.2 Multi-Event Context-Supply & Shadow-State Boundary Charter** — a docs-only
  design of the isolated downstream container that holds per-intent shadow state across replayed events (the
  registry/resolver/state-store), strictly **one-way from S1 replay**, with the exact trigger-classification
  predicates bounded under the §6/§9 firewall, and the §7/§8 quarantine intact.
- Only after that (and the bounded trigger predicates) is resolved may a **separately-authorized Phase 6.2
  shadow-intent reconstruction runtime/state-machine TDD slice** be considered. **This charter does NOT open,
  draft, or perform either step.**

**Conclusion:** the inert Phase 6.2 shadow-intent lifecycle is pinned (docs-only) as a **monotone, deterministic,
idempotent** state machine over the closed state set `{AUDIT_REPLAYED, INTENT_RECORDED, HYPOTHETICAL_CONDITION_MET,
INTENT_EXPIRED, INTENT_RETIRED}`, with **`AUDIT_REPLAYED` as the reconstruction-bootstrap initial state** and
**`INTENT_EXPIRED` / `INTENT_RETIRED` as absorbing terminals**; the **exact legal transition table** (§4) permits
only the forward path `AUDIT_REPLAYED → INTENT_RECORDED → (HYPOTHETICAL_CONDITION_MET)? → (INTENT_EXPIRED |
INTENT_RETIRED)` plus no-op self-loops, and **forbids every unlisted edge** (no regression, no terminal revival, no
cross-terminal). Every transition is triggered **exclusively by sequential S1 audit-replay observations** (no clock/
timer/poll; **freeze on replay stop**), the process is **deterministic and idempotent** with **no side effects**,
`HYPOTHETICAL_OUTCOME` is a firewalled **counterfactual projection** (never realized PnL / balance / advice /
threshold / actionability), the layer is **S1 read-only** (no write-back, no Phase 6.1 mutation, no lifecycle state
on Phase 6.1 DTOs), and everything stays **quarantined downstream** with **capacity deferred at 0 emit sites** and
**no broker/exchange/paper/market-data/execution/routing/order-emission integration**. Tombstoned active vocabulary
stays banned and historical S1 evidence is read verbatim, never censored. **Phase 6.2 remains UNBUILT and NOT
runtime-ready**; the **only** next safe step is a separately-authorized **Phase 6.2 Multi-Event Context-Supply &
Shadow-State Boundary Charter**, **not opened here**. **No executable work is authorized.**
