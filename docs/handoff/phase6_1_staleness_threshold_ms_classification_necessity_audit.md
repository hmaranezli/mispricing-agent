# Phase 6.1 `staleness_threshold_ms` Classification & Necessity Audit

> **This is a docs-only classification/necessity audit.** It classifies the architectural domain and necessity
> of `staleness_threshold_ms` for the Phase 6.1 passive shadow path — **without designing policy, runtime,
> thresholds, filtering, scoring, or wiring, and without proposing, inferring, or defaulting any numeric
> value**. It authorizes NO runtime, NO tests, NO lock-test edits, NO Python code, NO interface/schema/runtime
> edits, NO B2/B3 runtime/schema/carrier changes, NO Master B3 wiring, NO Phase 5 runtime amendment, NO passive
> producer design, NO B4 scoring design/math, NO durable shadow logs, NO Shadow Intent Envelope
> design/runtime/schema, NO `edge_direction` mechanism/design/values/defaults, NO capacity activation, NO Phase
> 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_passive_entrypoint_slice0a_handoff_pinning_classification_sequencing_charter.md`,
> `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md`,
> `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md`,
> `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase5_to_live_canary_roadmap.md`, and `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `01c3e922c1eac0d6bb360f55a34c421d2ad3a46e`

---

## 1. Base / Dependency Chain

**Base commit:** `01c3e922c1eac0d6bb360f55a34c421d2ad3a46e`.

References:

- `docs/handoff/phase6_1_passive_entrypoint_slice0a_handoff_pinning_classification_sequencing_charter.md` —
  pinned the passive handoff boundary (magnitude-only `NetEdgeCalculationResult` by identity; no actionability).
- `docs/handoff/phase6_1_phase5_gross_edge_gate_invocation_necessity_decision_charter.md` — gross-edge
  actionability gate **NOT_NECESSARY** for the passive path.
- `docs/handoff/phase6_1_edge_direction_classification_necessity_audit.md` — `edge_direction` external intent;
  NOT NECESSARY for the passive path.
- `docs/handoff/phase6_1_master_b3_remaining_blockers_reclassification_readiness_audit.md` — `staleness_threshold_ms`
  recorded as a separate, unresolved **policy** blocker.
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — passive B4 scoring (deferred); replay-first/no-clock.
- `docs/handoff/phase5_to_live_canary_roadmap.md` — governs gating/sequencing/calibration.

**No capacity validation and no capacity pass is claimed by this charter** (see §11).

---

## 2. Why This Audit Exists

The Master-B3 readiness audit isolated `staleness_threshold_ms` as one of the remaining blockers, provisionally
classified as temporal policy. Before any Master-B3 step, that classification must be **established from
evidence** and the **necessity** of `staleness_threshold_ms` for the Phase 6.1 passive path examined directly —
without inventing a threshold value or embedding freshness logic anywhere. This audit finds the **owner/domain**,
not the number. It designs nothing.

---

## 3. Evidence Inventory Inspected (read-only)

- **Carrier location** — `phase5/gross_edge_observation_boundary.py` and
  `phase5/gross_edge_source_result_adapter.py`: `staleness_threshold_ms` is a field on the **gross-edge
  observation** (the actionability gate carrier), declared an **exact integer string**, carried **verbatim**
  ("no freshness/valid_until computation here"; "no … timestamp-substituted, or freshness-computed"). The
  observation boundary **carries** the field; it does **not** evaluate freshness.
- **Policy consumers** — `phase5/capacity_constraint_evidence_boundary.py` (a `STALE_EVIDENCE` branch anchored on
  `evidence_envelope.observed_at_epoch_ms`) and `phase5/capital_margin_evidence_boundary.py` ("two independent
  deterministic staleness axes (**no clock**)"). Staleness is **evaluated** in the **capacity / capital-margin
  evidence** boundaries — the **capacity track**, which Phase 6.1 keeps **non-activatable / deferred**.
- **Temporal discipline** — staleness evaluation there is **deterministic and clockless**, anchored on
  `observed_at_epoch_ms` (integer), never on a wall clock and never substituting `retrieval_epoch_ms`.
- **Passive handoff** — the pinned passive handoff references `NetEdgeCalculationResult` (magnitude/unit/status
  only); it carries **no** `staleness_threshold_ms`.
- **B2 carriers** — carry `observed_at_epoch_ms` and `retrieval_epoch_ms` distinctly, with the time-isolation
  lock (`observed != str(retrieval)`); B2 carries **no** `staleness_threshold_ms` and computes no freshness.

---

## 4. Current Timestamp Fields & Prior Ratifications

- **`observed_at_epoch_ms`** — source-observed market/event time (canonical unsigned-int string in B2). This is
  the **only** legitimate anchor for any temporal/freshness reasoning.
- **`retrieval_epoch_ms`** — the later system freeze/retrieval time. **Provenance only**; must **never** be
  substituted for event time (B2 time-isolation lock; Phase 5 adapters perform "no … timestamp-substituted").
- **`staleness_threshold_ms`** — an exact integer string **policy parameter** carried on the gross-edge gate;
  consumed (when the capacity/margin track is active) as a deterministic, clockless staleness axis anchored on
  `observed_at_epoch_ms`. Phase 6.1 keeps the capacity track **deferred**.

---

## 5. Architectural Classification — **temporal validity POLICY parameter (external/calibration-owned)**

`staleness_threshold_ms` is classified as a **temporal-validity policy parameter** — a *chosen freshness bound*,
not a fact and not a diagnostic computed from the data.

| Candidate domain | Verdict | Why |
|---|---|---|
| **Observation fact** | **Rejected** | It is not something the market *is*; `observed_at_epoch_ms` is the observed fact, the *threshold* is a chosen bound applied to it. B2/B3 must not originate it. |
| **Temporal validity policy** | **ACCEPTED (primary)** | It parameterizes a freshness/validity decision; in Phase 5 it is consumed by evidence-validity (capacity/margin) boundaries as a staleness axis. |
| **Downstream scoring diagnostic** | **Possible (deferred)** | A future passive B4 *could* expose a freshness diagnostic, but B4 scoring is undesigned/deferred; not decided here. |
| **External calibration parameter** | **ACCEPTED (value-origin)** | The *value* of the bound is a calibration/policy choice (roadmap calibration territory), not derivable from a single replay record. The number is **out of scope** of this audit. |
| **B2/B3-derived** | **Forbidden** | Deriving a threshold (or a stale/fresh verdict) inside B2/B3 would invent temporal policy in the observation/router layers. |

**Net:** it is a **policy/calibration parameter** whose *evaluation* (if ever) belongs to a downstream
validity/scoring consumer and whose *value* is an external calibration choice — **never** an observation, and
**never** B2/B3-owned. The **number is not proposed here**.

---

## 6. Necessity Decision for Phase 6.1 / Master B3

- **For B3 / Master-B3 routing — NOT_NECESSARY (B3 stays a dumb pipe).** B3 must **not** own staleness policy,
  stale-filtering, drop logic, pass/fail, or freshness verdicts. Staleness is **downstream policy**, not router
  logic. Master B3, as a passive router, does **not** need `staleness_threshold_ms` to carry/route evidence.
- **For the Phase 6.1 passive path as currently scoped — NOT_NECESSARY.** The passive path does not invoke the
  gross-edge gate that carries the field; its policy consumers (capacity/margin) are **deferred/non-activatable**;
  and the pinned passive handoff (`NetEdgeCalculationResult`) does not carry it.
- **For the broader passive objective (future B4 diagnostics / calibration) — BLOCKED / DEFERRED.** Whether an
  eventual passive freshness *diagnostic* (or a calibrated validity bound) is wanted is a **deferred** B4 /
  external-calibration decision. Per the "prefer evidence-grounded BLOCKED/DEFERRED over invented thresholds"
  posture, this remains **DEFERRED**; **no threshold value, formula, or example is proposed**, and no freshness
  logic is placed in B2/B3.

**Combined verdict:** `staleness_threshold_ms` is **NOT_NECESSARY for the passive routing/observation path and
for B3**, and **BLOCKED/DEFERRED as a downstream policy/calibration concern** — owner classified, value and
design untouched.

---

## 7. Owner / Domain Analysis

- **B2 — not owner.** Carries distinct timestamps only; must never originate, derive, or evaluate a threshold.
- **B3 — not owner.** Passive router; must never embed temporal policy/filtering/verdicts (§8).
- **Passive producer (future) — not owner.** Produces a non-actionable net-edge result; not a policy authority.
- **B4 scoring (deferred) — possible *diagnostic* consumer.** A future passive freshness *diagnostic* could read
  `observed_at_epoch_ms`-anchored facts, but that is undesigned and deferred; it would be diagnostic-only,
  non-actionable, and would still not *invent* a threshold.
- **Phase 5 evidence-validity (capacity/margin) — existing policy *consumer*.** Where staleness is actually
  evaluated today (deferred/non-activatable in Phase 6.1). Untouched.
- **Durable logging / external calibration — value owner (deferred).** The *threshold value* is a
  calibration/policy choice owned externally (roadmap calibration), never fabricated here.

**Conclusion:** the **policy/value** is **deferred external calibration**; the **evaluation** (if ever in the
passive path) is a **downstream consumer** (Phase 5 validity today; a deferred B4 diagnostic at most) — **never**
B2 or B3.

---

## 8. B3 May / May-Not-Do Rules

- **May:** (only when separately chartered) route/carry timestamp provenance (`observed_at_epoch_ms`,
  `retrieval_epoch_ms`) verbatim by identity.
- **May not:** own, derive, default, or evaluate `staleness_threshold_ms`; implement stale-filtering, drop logic,
  pass/fail, freshness verdicts, or any temporal policy; compute/compare freshness; introduce a threshold value.
  B3 remains a **passive dumb pipe** unless a future, separately-authorized charter proves otherwise.

---

## 9. Timestamp Integrity & Lookahead-Bias Locks

- **Distinction preserved.** `observed_at_epoch_ms` (event time) and `retrieval_epoch_ms` (freeze time) remain
  **disjoint**; this audit modifies, substitutes, canonicalizes, or recomputes **no** timestamp.
- **Anchor rule.** Any future temporal/freshness reasoning must anchor on **`observed_at_epoch_ms`** with
  deterministic integer comparison and **no wall clock** (consistent with the existing clockless Phase 5
  staleness axes).
- **Lookahead-bias risk.** Using `retrieval_epoch_ms` (a later, post-hoc freeze time) — or any downstream/“now”
  knowledge — to judge freshness would inject **lookahead bias** (treating information unavailable at the event
  as if it were). This is **forbidden**; `retrieval_epoch_ms` stays provenance only and must never drive a
  staleness verdict. The B2 time-isolation lock (`observed != str(retrieval)`) is **not weakened**.

---

## 10. Effect on Master B3 Readiness

- **Master B3 remains BLOCKED.** This audit firms the classification (downstream policy/calibration; not B3) and
  decides necessity (NOT_NECESSARY for B3/passive routing; DEFERRED as downstream policy); it resolves **no**
  wiring blocker.
- The `staleness_threshold_ms` blocker is **downgraded** from "unresolved policy blocking B3" to "downstream,
  deferred policy/calibration — explicitly **not** required for B3 to remain a passive router." B3 stays passive;
  policy is pushed downstream.
- Other remaining blockers stand: the **future passive producer slice**, the **`PassiveShadowInput`
  implementation**, and the **router-only Cell-3** cost-type pass-through. `edge_direction` is not a passive-path
  blocker. None is unblocked here.

---

## 11. Still-Forbidden Work

- **No** numeric threshold proposed/inferred/defaulted; **no** formula; **no** example value (no ms figures of
  any kind); the audit finds owner/domain, not the number.
- **No** temporal policy / stale-filtering / drop / pass-fail / freshness verdict embedded in B2 or B3.
- **No** timestamp modification/substitution/canonicalization/recomputation; **no** `retrieval_epoch_ms`
  substitution for event time.
- **No** passive producer design; **no** B4 scoring/diagnostic-EV math; **no** durable-log schema; **no** Phase
  5 entrypoint/runtime amendment; **no** runtime interface.
- **No** connection of staleness to `edge_direction`, Shadow Intent, capacity, sizing, execution, routing, or any
  trade/action decision.
- **No** B2/B3 runtime/schema/carrier change; **no** Master B3 wiring; **no** B3 route designed.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** reopening of cost vocabulary values; **no** weakening of the B2 passive cost-type carrier invariants.
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 12. Next Safe Step

- With `edge_direction` and `staleness_threshold_ms` now both classified out of the passive-path blocker set, the
  remaining Master-B3 gating reduces to: (a) the **future passive producer slice** (separately authorized), (b)
  the **`PassiveShadowInput` wrapper implementation** (decision ratified; impl deferred), and (c) the
  **router-only Cell-3** cost-type pass-through charter. A **separately-authorized review** may pick the next of
  these to charter (docs-first), designing nothing until authorized.
- Any eventual freshness *diagnostic* or calibrated validity bound is a **deferred B4 / external-calibration**
  matter, to be chartered separately and **never** with an invented value.
- **No implementation is authorized by this charter.** The passive producer, `PassiveShadowInput` implementation,
  Master B3 wiring, any B3 route, B4 scoring, durable logs, Phase 5 modification, the Shadow Intent Envelope,
  capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
