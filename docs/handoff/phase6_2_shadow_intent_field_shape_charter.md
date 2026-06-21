# Phase 6.2 — Shadow Intent Field-Shape Charter

> **This is a docs-only field-shape charter.** It pins the **passive, inert, non-actionable** schema and lifecycle
> vocabulary for a **future** Phase 6.2 shadow-intent capability, derived from the ratified S1 audit-replay
> boundary. It **implements nothing and authorizes nothing executable**: no runtime code, no tests, no lock-test
> edits, no frozen-component edits, no schema module, no state machine, no Phase 6.2 runtime, no pytest, no
> graphify. It makes **no** Phase 6.2 runtime/paper/live/production readiness claim. It is subordinate to
> `docs/handoff/phase6_2_readiness_risk_audit_charter.md`,
> `docs/handoff/phase6_1_full_completion_closeout_ratification.md`, the S1 durable-storage charters, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `a9ed9f472e6a5319a8c90e1b8d57bb320b7f4fda`

---

## 1. Base / Purpose

**Base commit:** `a9ed9f472e6a5319a8c90e1b8d57bb320b7f4fda`.

The Phase 6.2 readiness risk audit (`a9ed9f4`) fixed the boundaries; this charter pins the **inert field shape and
vocabulary** of a shadow intent — the passive bookkeeping artifact derived from the S1 audit trail — so a future,
separately-authorized runtime/state-machine slice has an unambiguous, non-actionable target. It resolves the schema
and lifecycle-vocabulary prerequisites (risk-inventory §9.1–§9.3 of `a9ed9f4`) **only**; everything else stays open.

**No capacity validation and no capacity pass is claimed by this charter** (see §8).

---

## 2. Inert Bookkeeping Seal (binding)

A **shadow intent** is defined **strictly** as a **passive bookkeeping / state-tracking DTO** — a frozen,
methodless record of "what a hypothetical exposure *would* have been, given observed evidence." It is:

- **NOT** an executable order, **NOT** a trading instruction, **NOT** a routing/sizing/allocation directive;
- **architecturally incapable** of direct broker / exchange / venue / paper-API submission — it carries no
  endpoint, credential, connection, callback, or emission surface, and the future DTO must be a pure data carrier
  (frozen dataclass, structural guards only) like every Phase 6.1 carrier;
- a **diagnostic shadow** computed from already-recorded passive observations; inert by construction.

It records; it never acts.

---

## 3. Anti-Actionability Vocabulary (binding)

For **newly defined** Phase 6.2 schema names, class names, field names, lifecycle states, and enum values, the
following **action/execution vocabulary is FORBIDDEN** (case-insensitive): `ORDER`, `TRADE`, `EXECUTE`/`EXECUTION`,
`SUBMIT`, `BUY`, `SELL`, `ROUTE`/`ROUTING`, `FILL`, `CANCEL`, plus `SIZING`/`ALLOCATION`/`SIGNAL`/`PAPER`/`LIVE`
(consistent with the existing package-wide token locks). Newly defined names MUST use **passive quantitative
vocabulary**, e.g.:

- `SHADOW_INTENT` (the artifact);
- `POSITIVE_EXPOSURE` / `NEGATIVE_EXPOSURE` (the hypothetical directional bookkeeping — never `BUY`/`SELL`);
- `INERT_STATE` (the passive nature marker);
- `HYPOTHETICAL_OUTCOME` (the counterfactual result, never a realized fill/PnL).

**Historical-evidence exception:** this ban governs **only newly minted Phase 6.2 names**. It does **NOT** authorize
rewriting, censoring, normalizing, or mutating historical **S1 audit evidence** that may carry legacy field names —
the S1 audit trail is append-only and immutable, and its already-recorded payload strings are read **verbatim and
opaque**, never edited to satisfy this vocabulary.

---

## 4. Tombstoned Lifecycle States (binding)

Shadow-intent lifecycle states MUST use **strictly historical / hypothetical / passive** vocabulary. **Banned new
lifecycle states:** `PENDING`, `FILLED`, `CANCELLED`, `SUBMITTED`, `ROUTED`, `EXECUTED` (and any action-implying
synonym). **Mandated style** (the closed lifecycle vocabulary a future charter would ratify), e.g.:

- `INTENT_RECORDED` — the shadow intent was observed/derived and written;
- `HYPOTHETICAL_CONDITION_MET` — a counterfactual condition was observed to hold (no action taken);
- `INTENT_EXPIRED` — the hypothetical window lapsed by observed time, passively;
- `INTENT_RETIRED` — the bookkeeping entry was passively closed out (no cancel/fill semantics);
- `AUDIT_REPLAYED` — the state was (re)derived from an S1 audit replay.

Every state names a **past/hypothetical observation**, never a present/future action. Transitions (to be pinned by a
later charter) are **observed-event-driven only** — no clock-driven action, no implicit transition.

---

## 5. S1 Replay Dependency (binding)

The shadow-intent shape and its future state transitions are **derived through the ratified S1 SQLite/WAL audit
replay boundary** — the append-only durable trail is the **single source of truth**. The DTO therefore carries
**by-reference / by-identity links to S1 audit evidence** (e.g. the opaque Silver identity pair and the
`append_sequence`-ordered audit position as already recorded), **never** fabricated or live-recomputed state. Future
tests may use **temporary S1 audit fixtures** (temp SQLite DBs populated via the ratified adapter), but **ad-hoc
synthetic bypasses of S1** — hand-rolled intents that never flowed through the S1 boundary — are **forbidden**. The
S1 read surface stays **minimal append-order replay** (no analytics/query DSL).

---

## 6. Inert Field-Shape (conceptual, key-level only — no runtime)

At **conceptual key level only** (no concrete types, encodings, or ordering fixed here), a shadow intent carries
**passive evidentiary references + hypothetical bookkeeping state** and nothing else:

- **`shadow_intent_identity_reference`** — a by-reference link to the S1-audited observation(s) the intent derives
  from (the opaque Silver identity pair + audited append position), borrowed, never minted.
- **`exposure_orientation`** — one of `POSITIVE_EXPOSURE` / `NEGATIVE_EXPOSURE` / `INERT_STATE` — passive
  directional bookkeeping, **never** a buy/sell/order directive.
- **`lifecycle_state`** — one value from the §4 closed historical/hypothetical vocabulary.
- **`hypothetical_outcome_reference`** — an opaque, by-reference projection of the counterfactual outcome evidence
  (read from S1), never a realized fill or real PnL.
- **`evidence_provenance_reference`** — opaque audit provenance (which S1 replay produced this), carried verbatim.

These are **observation/bookkeeping facts**. **No** field is an order, route, size, threshold, decision, trigger,
real price/PnL, or actionability. **No** concrete schema/types/serialization is fixed here.

---

## 7. Phase 6.1 Quarantine & Multi-Event Context Boundary (binding)

- **Quarantine:** Phase 6.2 shapes, the multi-event context, registries, resolvers, and any state machine MUST live
  in an **isolated downstream Phase 6.2 boundary/package** (e.g. a future `phase6_2_shadow_intent/` package,
  analogous to the quarantined `phase6_1_s1_storage/`). They MUST NOT pollute S5, any Phase 6.1 carrier/DTO, the
  frozen records, or the S1 durable adapter — no Phase 6.1 module gains an intent/state field, and no Phase 6.1
  module imports Phase 6.2.
- **Multi-event context:** cross-time shadow state requires a multi-event context/state boundary — acknowledged,
  but kept **downstream and strictly one-way from the S1 replay** (Phase 6.2 reads S1; S1/Phase 6.1 never know
  about Phase 6.2). **No** broker/API integration, routing hook, order-emission surface, or callback may be designed
  — here or there — under this acknowledgement.

---

## 8. Capacity & Integration Ban (binding)

- **Capacity:** remains **DEFERRED with exactly 0 emit sites**; no shadow-intent shape may reference, consume, or
  assert capacity, and none may add an emit site.
- **Integration ban:** **NO** exchange, broker, paper-trading, market-data, or venue API; **NO** execution,
  routing, order-emission, or actionability integration is designed here or implied for Phase 6.2. A shadow intent
  is inert evidentiary bookkeeping.

---

## 9. No Semantic Smuggling (binding)

The shadow-intent DTO carries **passive evidentiary references and hypothetical bookkeeping state only**. It MUST
NOT calculate or carry: executable advice, thresholds, trade/route/size decisions, real (realized) PnL, business
actionability, or any value that converts observation into instruction. `HYPOTHETICAL_OUTCOME` is a **counterfactual
projection read from audited evidence**, never a realized result or a recommendation. The future DTO is a dumb
carrier with structural guards only — it derives, computes, thresholds, ranks, and decides **nothing**.

---

## 10. Precise Post-Charter State (ratified)

- **Phase 6.2: UNBUILT and NOT runtime-ready.** This charter pins **only** the inert field shapes and the
  vocabulary (schema concept §6; anti-actionability vocabulary §3; tombstoned lifecycle states §4).
- The **state-transition rules, lifecycle transition semantics, replay-determinism/idempotency mechanics, the
  multi-event context/state runtime, and all §9 risk-inventory items 4–10 of `a9ed9f4`** remain **open** and
  unauthorized.
- **Phase 6.1:** COMPLETE + RATIFIED (unchanged). **Capacity:** deferred (0 emit sites). **Production / live /
  paper / canary / execution / routing / actionability:** forbidden.
- **Any runtime / state-machine TDD requires separate authorization.**

---

## 11. Next Safe Step

The field-shape evidence (concrete types, the closed lifecycle-state set, the by-reference S1 link shape, and the
transition rules) shows the next gate is **further design, not implementation**:

- A **separately-authorized Phase 6.2 Shadow Intent Lifecycle / State-Transition Charter** — a docs-only design
  fixing the **closed** lifecycle-state set, the exact-typed, **observed-event-driven** transition rules, and the
  replay-determinism / idempotency invariants, all **derived from the S1 audit replay**, in the isolated downstream
  Phase 6.2 boundary, with the §2–§9 seals intact.
- Only after that (and the multi-event context-supply boundary) is resolved may a **separately-authorized Phase 6.2
  shadow-intent runtime/state-machine TDD slice** be considered. **This charter does NOT open, draft, or perform
  either step.**

**Conclusion:** a Phase 6.2 **shadow intent** is pinned (docs-only, key-level) as a **passive, inert, frozen
bookkeeping DTO** derived **only** through the ratified **S1 audit-replay** boundary — carrying by-reference
evidentiary links (the opaque Silver identity + audited position), a passive `exposure_orientation`
(`POSITIVE_EXPOSURE`/`NEGATIVE_EXPOSURE`/`INERT_STATE`), a `lifecycle_state` from a **historical/hypothetical**
vocabulary (`INTENT_RECORDED` / `HYPOTHETICAL_CONDITION_MET` / `INTENT_EXPIRED` / `INTENT_RETIRED` /
`AUDIT_REPLAYED`; `PENDING`/`FILLED`/`CANCELLED`/`SUBMITTED`/`ROUTED`/`EXECUTED` **banned**), an opaque
`HYPOTHETICAL_OUTCOME` projection, and opaque audit provenance — and **nothing actionable**. New Phase 6.2 names
forbid `ORDER`/`TRADE`/`EXECUTE`/`SUBMIT`/`BUY`/`SELL`/`ROUTE`/`FILL`/`CANCEL` (historical S1 evidence is read
verbatim, never censored). All Phase 6.2 shapes/context/registries/state machines stay **quarantined downstream and
one-way from S1**; **capacity stays deferred at 0 emit sites**; **no exchange/broker/paper/market-data/venue/
execution/routing/order-emission integration** is designed; and the DTO carries **no** executable advice, threshold,
decision, real PnL, or actionability. **Phase 6.2 remains UNBUILT and NOT runtime-ready**; the **only** next safe
step is a separately-authorized **Phase 6.2 Shadow Intent Lifecycle / State-Transition Charter**, **not opened
here**. **No executable work is authorized.**
