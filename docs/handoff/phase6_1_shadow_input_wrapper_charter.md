# Phase 6.1 Slice 0A — Passive Shadow-Input Wrapper Charter

> **This is a planning/charter document only.** It authorizes NO runtime
> implementation, NO tests, NO live reads, NO paper/live trading, and NO
> wallet/order/routing/execution behavior. It pins the Slice 0A typed handoff
> *decision*; implementing the wrapper requires separate explicit authorization.

**Base:** `f336d1db41e714200167fa8a8f8b115ee420cd22`
**Subordinate to:** `docs/handoff/phase5_to_live_canary_roadmap.md` and
`docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` (Slice 0A, §4 typed-handoff
requirement). Where any conflict arises, those govern.

---

## 0. Purpose

Slice 0A of the prior charter requires the exact Python type crossing from the
completed Phase 5 evidence/gate chain into Phase 6.1 passive Shadow Scoring to be
**pinned** before any runtime planning (Slices 0B–0E) may proceed. The read-only
Slice 0A extraction concluded `BLOCKED_NEEDS_PASSIVE_SHADOW_INPUT_WRAPPER_CHARTER`:
no existing Phase 5 type satisfies all handoff criteria. This charter records the
ratified decisions that bound that wrapper. It does **not** design the wrapper's
implementation, factory, or field encodings.

---

## 1. Ratified Decision — Option A (profitability-pass source)

**RATIFIED:** Phase 6.1 `PassiveShadowInput` references **`NetEdgeCalculationResult`
by identity** as its **profitability-pass source**.

- `NetEdgeCalculationResult` is the only **actually-emitting** terminal pass carrier
  of the completed Phase 5 chain — it is returned **by identity** from
  `net_edge_profitability_preflight(*, calculation_result, threshold_policy)` on a
  PASS (`phase5/net_edge_profitability_gate_boundary.py`). Blocked →
  `BlockedPacket`; below-threshold → `NoEligibleHaltPacket`.
- `PassiveShadowInput` therefore binds the profitability pass via this object's
  identity, and adds the missing diagnostic/provenance facts (§4–§5) **around** it.

---

## 2. Capacity Deferral

- `CapacityConstraintGate.preflight`
  (`phase5/capacity_constraint_evidence_boundary.py`) is **structurally complete but
  non-live-wirable** for the Slice 0A context. It has **0 emit sites** and emits
  **no capacity PASS token** (UNDEFINED out-of-vocabulary deferral; its pass path is
  explicitly "NOT final pass readiness").
- Therefore `PassiveShadowInput` **must not claim, imply, or require capacity-pass
  readiness.**
- Future wrapper design **must** include a field named **`capacity_pass_reference`**
  whose **Slice 0A meaning is explicitly `None` / deferred**.
- Any future attempt to set `capacity_pass_reference` to a **non-deferred** value
  **requires a separate charter amendment** that may be authored **only after a
  live-wirable capacity PASS token actually exists** (a real emit site).
- This field **must never be interpreted as "capacity validated."** Its deferred
  state is the absence of a capacity pass, not a silent pass.

---

## 3. Handoff Type Name

- The proposed wrapper name is **fixed as `PassiveShadowInput`**.
- **`ShadowValidatedObservation` is rejected** — "validated" can imply
  capacity/actionability readiness, which §2 and §7 forbid. The name must not assert
  validation the chain does not emit.

---

## 4. Missing-Facts Contract (preserved verbatim as wrapper rationale)

The seven missing facts established by the Slice 0A extraction are the required
rationale for the wrapper. They are preserved exactly:

1. **market provenance:** venue, pair, timestamp;
2. **fee maker/taker split;**
3. **estimated slippage reference;**
4. **stale window / latency / opportunity-lifetime;**
5. **diagnostic-EV input decomposition:** `P_success` and `LimitEdge`;
6. **capacity-constraint pass provenance absent/deferred** because 0 emit sites;
7. **no single frozen, closed, anti-coercion typed binding exists today.**

`PassiveShadowInput` exists precisely because no existing Phase 5 type carries facts
1–6, and because fact 7 (the unifying binding) is itself absent.

---

## 5. Source Mapping

Each missing fact is mapped to the Phase 5 / source boundary it must be **carried
from or referenced to**. The wrapper must **carry or strictly reference** these
facts **without recomputation and without live lookup** (replay-first; §7).

| # | Missing fact | Source boundary / module | Carry or reference |
|---|--------------|--------------------------|--------------------|
| 1 | market provenance (venue, pair, timestamp) | Phase 6.1 **read-only ingestion boundary (B1)** raw public/replay snapshot provenance; lineage cross-checked against `venue_readiness_source_*` refs in `phase5/capacity_constraint_evidence_boundary.py` and `phase5/venue_instrument_readiness_boundary.py` | reference (from the immutable ingestion snapshot record) |
| 2 | fee maker/taker split | `phase5/observable_cost_friction_boundary.py` (+ `phase5/observable_cost_source_result_adapter.py`) | reference (no recompute; the pass result holds only aggregate `total_cost`) |
| 3 | estimated slippage reference | `phase5/observable_cost_friction_boundary.py` / `phase5/liquidity_capacity_evidence_boundary.py` | reference |
| 4 | stale window / latency / opportunity-lifetime | provenance timestamp from `phase5/input_provenance_preflight.py` (`PreflightResult`) + timing measured at the Phase 6.1 ingestion boundary (B1) | reference (Phase 5 has no latency fields; timing originates at ingestion, captured deterministically from replay artifacts) |
| 5 | diagnostic-EV decomposition (`P_success`, `LimitEdge`) | `LimitEdge` from gross-edge inputs in `phase5/gross_edge_observation_boundary.py` / `phase5/gross_edge_source_result_adapter.py`; `P_success` has **no Phase 5 source** and is a passive diagnostic input whose origin must be pinned in a later slice (referenced, never recomputed live) | reference |
| 6 | capacity-constraint pass provenance | `phase5/capacity_constraint_evidence_boundary.py` (`CapacityConstraintGate`) — **0 emit sites**; `capacity_pass_reference = None`/deferred per §2 | deferred (no token to reference yet) |
| 7 | unifying frozen/closed/anti-coercion binding | does not exist today | resolved by `PassiveShadowInput` itself (planning only) |

---

## 6. Identity Contract

- `PassiveShadowInput` **references `NetEdgeCalculationResult` by identity.**
- It must **never copy, mutate, recompute, or reinterpret** any
  `NetEdgeCalculationResult` field. The pass result is held by reference; its frozen,
  anti-coercion semantics are inherited, not duplicated.
- The same non-recomputation / non-mutation discipline applies to every referenced
  source in §5: the wrapper references, it does not re-derive.

---

## 7. Non-actionability

`PassiveShadowInput` is **passive, diagnostic, replay-first, and non-actionable.**

- It **authorizes planning only.**
- It implies **none** of: Phase 6 implementation, paper readiness, live readiness,
  routing, sizing, allocation, wallet/balance runtime, execution, order intent,
  signal, or trade candidate.
- It exposes **no actionability verdict** and **no readiness verdict**. Any EV is a
  passive diagnostic only (per the prior charter §6; `diagnostic_`/`passive_`
  prefix), never a recommendation.

---

## 8. Downstream Gate

- **Slices 0B–0E remain BLOCKED** until this wrapper charter is reviewed and
  **separately authorized.** Pinning the handoff *decision* here does not authorize
  building `PassiveShadowInput`.
- **Phase 6.2** calibration, **7.1** paper simulator, **7.2** paper canary, and
  **8.1** live canary remain **separately gated** (roadmap §2/§6). **No downstream
  readiness is implied.**
- **Next named step:** review of this wrapper charter, then — only on explicit
  authorization — the first implementation slice for `PassiveShadowInput`
  (still replay-first, still non-actionable). No unplanned stop.
