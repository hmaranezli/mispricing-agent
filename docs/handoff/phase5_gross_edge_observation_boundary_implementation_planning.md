# Phase 5 Component Implementation-Planning — `phase5_gross_edge_observation_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document.
No net-edge calculator work is authorized, and no next component implementation is authorized. It
defines only the planned atomic carrier name, the observation-not-decision role, gross-edge
semantics, carrier separation, decimal/direction/asset/venue/time/value/depth field discipline,
halt-misroute protection, input discipline, and prohibitions for a future, separately authorized
offline/TDD implementation task.

- `component_name`: `phase5_gross_edge_observation_boundary`.
- The future atomic carrier is pinned as `GrossEdgeObservation`.
- It is a gross-edge observation planning boundary only, not a calculator and not a decision carrier, and is the pre-net-edge counterpart to the observable-cost/friction boundary.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_observable_cost_friction_boundary` planning artifact](phase5_observable_cost_friction_boundary_implementation_planning.md)
- [`phase5_observable_cost_source_result_adapter` planning artifact](phase5_observable_cost_source_result_adapter_implementation_planning.md)
- [`phase5_halt_propagation_integration_boundary` planning artifact](phase5_halt_propagation_integration_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Boundary role

- GrossEdgeObservation is an observation carrier, not a decision carrier.
- It is not an actionable payload.
- It is not a calculator input implementation.
- It is not a raw parser, exchange/API parser, loader, endpoint reader, order-book model, venue model, sizing model, risk model, execution model, trading component, or reporting component.
- It may only define future contracts for carrying explicitly observed gross-edge facts with provenance.
- It must not infer, enrich, repair, normalize, aggregate, net, sum, subtract, annualize, rank, score, decide, size, allocate, route orders, or trade.
- It must not be named ActionableCandidate, TradeCandidate, ExecutableCandidate, ReadyCandidate, Opportunity, or Signal, because nothing is actionable before net-edge, risk, output, and paper/live gates.

## 3. Gross edge semantics

- Gross edge is pre-friction and pre-net-edge.
- Gross edge is not net edge.
- Gross edge is not profitability.
- Gross edge is not readiness.
- Gross edge is not a trade recommendation.
- A positive gross edge must not imply positive net edge.
- A gross-edge observation must not authorize order placement or paper/live action.

## 4. Name and semantic separation from cost observations

- GrossEdgeObservation is separate from ObservableCostObservation.
- It must not reuse ObservableCostObservation.
- It must not subclass or share a generic base observation carrier.
- No shared BaseObservation, GenericObservation, EdgePacket, CandidatePacket, or polymorphic hierarchy.
- Future routing must use exact type checks only.
- No isinstance acceptance for boundary carriers.

## 5. Canonical decimal discipline

- Gross-edge numeric values must be represented as canonical exact decimal strings in future implementation.
- Binary float arithmetic is prohibited.
- No float parsing, no float-to-string conversion, no binary-float rounding, no epsilon comparison, no approximate equality, no exponent normalization.
- Accepted future format intent: an optional leading `-`, one or more digits, and an optional `.` followed by one or more digits. Do not implement the carrier in this task.

## 6. Direction discipline

- Direction must be an explicit exact string field in future implementation.
- Planning names a future field `edge_direction`.
- Direction values may be planned as exact labels such as LONG, SHORT, or CROSS_VENUE.
- Direction is descriptive only.
- Direction must not authorize trading, order side, execution, readiness, or paper/live action.
- Unknown, empty, inferred, or default direction is prohibited.

## 7. Asset / instrument identity

- Future gross-edge observation must carry explicit base/quote/instrument identity as exact string fields.
- Planning includes fields such as `base_asset`, `quote_asset`, and `instrument_id`.
- Unitless or instrumentless gross-edge is invalid.
- The boundary must not infer base/quote from symbols, filenames, venue names, or raw strings.
- No parser or symbol-normalizer is authorized.

## 8. Venue / cross-venue identity

- Future gross-edge observation must carry exact string venue fields.
- Planning includes `venue_scope`, `venue_buy`, and `venue_sell`.
- venue_scope may distinguish SINGLE_VENUE from CROSS_VENUE.
- No tuple/list/container venue representation.
- No venue inference.
- For non-applicable venue fields, future implementation may use explicit sentinel strings, but no None/empty/default values.
- Cross-venue identity must remain explicit and provenance-backed.

## 9. Time / freshness discipline

- Future gross-edge observation must carry explicit observed time and staleness threshold fields.
- Planning includes `observed_at_epoch_ms` and `staleness_threshold_ms`.
- These should be exact integer strings in future implementation.
- The boundary must not compute valid_until.
- The boundary must not calculate freshness/staleness in this planning component.
- Freshness calculation belongs to a separately authorized future calculator/input gate.
- Missing, inferred, default, current-time, wall-clock, or system-time substitution is prohibited.

## 10. Gross-edge value + unit + provenance

- Future gross-edge observation must carry `gross_edge_value`, `gross_edge_unit`, `gross_edge_source_contract`, `gross_edge_source_artifact`, and `gross_edge_source_field`.
- Bare numeric gross-edge values are prohibited.
- Unitless values are prohibited.
- Source-less values are prohibited.
- Unit/source must be explicit, not inferred.
- No market-truth, source-truth, or data-quality claim is made by carrying these fields.

## 11. Liquidity / depth observation

- Future gross-edge observation must carry observed liquidity/depth capacity as observation, not sizing decision.
- Planning includes `observed_size`, `size_unit`, `depth_source_contract`, `depth_source_artifact`, and `depth_source_field`.
- observed_size should be a canonical exact decimal string in future implementation.
- This is not trade_size.
- This is not allocation.
- This is not order sizing.
- This is not a max tradable size decision.
- This is only an observed depth/liquidity fact with provenance.
- No sizing decision is authorized.

## 12. Atomic observation only

- The future boundary must carry one atomic gross-edge observation only.
- No list, collection, set, batch, basket, portfolio, aggregation, ranking, or selection behavior.
- No aggregation across venues, instruments, timestamps, or observations.
- No arithmetic output.

## 13. Halt-carrier misroute protection

- BlockedPacket and NoEligibleHaltPacket must not be processed by the gross-edge observation boundary.
- If a halt carrier reaches this boundary, that is a routing/integration bug, not a gross-edge observation.
- Planning must require strict misroute rejection, not pass-through and not conversion.
- It must not duplicate route_halt_carrier.
- It must not convert BLOCKED / CONTRACT_VIOLATION / NO_ELIGIBLE into gross-edge observations.
- It must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects.

## 14. Input discipline

- The future input/source for gross-edge observation must be explicitly typed/frozen or otherwise strictly defined.
- Raw dicts, generic Mapping, JSON-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, and heuristic key guessing are prohibited.
- No exchange/API/raw-market parsing is authorized.
- Parser/adapter work, if needed, must be a separate future slice.

## 15. No calculator / no economic output

- The boundary must not compute or authorize net_edge, total_cost, net_cost, effective_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, or execution.
- Gross edge and observed size do not imply net edge or tradability.
- Net-edge calculator work remains unauthorized.

## 16. No market-truth / readiness claims

- The boundary proves no market truth, no price correctness, no liquidity correctness, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee.
- It only plans a future atomic observation contract.

## 17. Relationship to observable cost

- The observable-cost/friction boundary remains separate and already implemented.
- Gross-edge observation must not include cost/friction observations.
- Gross-edge observation must not compute with costs.
- Cost collection/set behavior remains deferred.
- Calculator-input behavior remains deferred.

## 18. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 19. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future boundary, must produce **none** of:

- no net edge, total cost, net cost, or effective cost figure;
- no profitability score; no alpha/edge claim; no PnL or economic-inference figure;
- no order size, allocation, sizing, or execution instruction;
- no trade recommendation; no deployment or order instruction;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.

It authorizes no parser, loader, endpoint reader, order-book model, sizing model, calculator, reporting, trading, or paper/live work.
<!-- PROHIBITED-OUTPUTS-END -->

## 20. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact `GrossEdgeObservation` field list, value syntax, and direction/venue vocabulary.
- exact typed/frozen source-result type and its strict construction discipline.
- exact misroute-rejection and wrong-input error types and message discipline.
- exact test boundary between contract tests and implementation tests.
- production/live usage deferred until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes no edge, no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no alpha, no live readiness, no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. This is a component planning gate only; it authorizes a separately approved
offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 21. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `phase5_gross_edge_observation_boundary` may follow, with failing tests first and declared
  evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
