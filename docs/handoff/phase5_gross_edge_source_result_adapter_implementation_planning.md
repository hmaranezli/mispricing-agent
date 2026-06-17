# Phase 5 Component Implementation-Planning — `phase5_gross_edge_source_result_adapter`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document.
No net-edge calculator work is authorized, and no next component implementation is authorized. It
defines only the planned adapter role, the future input/output names, strict typing, the explicit
1:1 mapping contract, validation delegation, float/decimal discipline, time/direction/venue/depth/
unit/source discipline, halt-misroute protection, and prohibitions for a future, separately
authorized offline/TDD implementation task.

- `component_name`: `phase5_gross_edge_source_result_adapter`.
- Purpose: plan a future adapter from a typed/frozen `GrossEdgeSourceResult` into exactly one
  `GrossEdgeObservation`, with no parsing, no inference, and no economic computation.
- It is a **typed-to-typed adapter planning only, not a parser and not a calculator**.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_gross_edge_observation_boundary` planning artifact](phase5_gross_edge_observation_boundary_implementation_planning.md)
- [`phase5_observable_cost_source_result_adapter` planning artifact](phase5_observable_cost_source_result_adapter_implementation_planning.md)
- [`phase5_halt_propagation_integration_boundary` planning artifact](phase5_halt_propagation_integration_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Future names

- The future input type is pinned as `GrossEdgeSourceResult`.
- This task must not implement GrossEdgeSourceResult.
- This task must not define its full runtime class or parser; it may only declare the future name and contract expectations.
- The future adapter function is pinned as `adapt_gross_edge_source_result_to_observation(result)`.
- This task must not implement that function.

## 3. Adapter role

- The future adapter is a typed-to-typed adapter only.
- It converts exactly one GrossEdgeSourceResult into exactly one GrossEdgeObservation.
- It is not a raw parser, not a JSON parser, not an exchange/API parser, not a loader, not an endpoint reader, not an order-book model, not a venue model, not a sizing model, not an aggregator, and not a calculator.
- It must not infer, enrich, repair, normalize, round, parse, aggregate, net, sum, subtract, score, decide, size, allocate, route orders, or trade.

## 4. Strict input type

- The future adapter must accept only the finalized typed/frozen GrossEdgeSourceResult.
- Raw dicts, generic Mapping, JSON-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, and heuristic key guessing are prohibited.
- Planning must require strict type rejection for wrong input.
- Wrong input must be a programmatic error, not None, not empty, not pass-through, and not a default observation.
- Subclasses must not be accepted.

## 5. Forward-declared source-result contract

- GrossEdgeSourceResult must be documented as a future typed/frozen source-result object.
- It must carry already-canonical string fields required by make_gross_edge_observation.
- It must not rely on the adapter for conversion from float, exponent notation, nullable values, direction inference, venue inference, base/quote inference, source inference, timestamp substitution, staleness calculation, or depth/size inference.
- Exact field implementation is deferred, but the planning doc must require enough future source fields to map 1:1 into every GrossEdgeObservation destination field.

## 6. Explicit 1:1 keyword mapping

Every destination `GrossEdgeObservation` field must be supplied by an explicit source field:

- `component_name`
- `origin_component`
- `origin_result_status`
- `status`
- `edge_direction`
- `base_asset`
- `quote_asset`
- `instrument_id`
- `venue_scope`
- `venue_buy`
- `venue_sell`
- `observed_at_epoch_ms`
- `staleness_threshold_ms`
- `gross_edge_value`
- `gross_edge_unit`
- `gross_edge_source_contract`
- `gross_edge_source_artifact`
- `gross_edge_source_field`
- `observed_size`
- `size_unit`
- `depth_source_contract`
- `depth_source_artifact`
- `depth_source_field`
- `boundary_version`

- The future adapter must call make_gross_edge_observation(*, ...) using explicit keyword arguments only.
- No positional construction.
- No dict unpacking from raw or generic mappings.
- No automatic defaults.
- No fallback values.
- No field guessing.
- No renaming by heuristic.
- No lossy transformation.
- No hardcoded component_name, direction, venue, timestamp, staleness, unit, source, size, or boundary_version.

## 7. Validation delegation without weakening

- The adapter must not reimplement or weaken make_gross_edge_observation validation.
- Exact-str enforcement, canonical decimal discipline, integer-string time/staleness discipline, direction allowed-set, venue_scope rules, venue buy/sell rules, sentinel rejection, non-negative observed_size, and provenance rules remain enforced by the observation factory.
- The adapter may only pass already-declared source fields through explicitly.
- It must not catch factory exceptions and downgrade them to None, empty observations, default observations, or no-op.

## 8. Float / decimal discipline

- The future adapter must not convert float to string.
- It must not accept binary floats.
- It must not normalize 1e-3 into 0.001.
- It must not use Decimal to repair input.
- It must not round, epsilon-compare, approximate, or canonicalize values.
- If upstream source-result fields are not already canonical strings, future implementation must fail closed.

## 9. Time / freshness discipline

- The future adapter must not create observed_at_epoch_ms.
- It must not substitute current time, wall-clock time, system time, or monotonic time.
- It must not create or compute staleness_threshold_ms.
- It must not compute valid_until.
- It must not calculate freshness/staleness.
- Time and staleness fields must be carried only from explicit typed source-result fields.

## 10. Direction / asset / venue discipline

- The future adapter must not infer edge_direction.
- It must not infer base_asset, quote_asset, or instrument_id.
- It must not infer venue_scope, venue_buy, or venue_sell.
- It must not normalize symbols, venue names, or instruments.
- It must not convert SINGLE/CROSS venue states.
- It must not insert sentinel values.
- All direction, asset, instrument, and venue fields must be carried from explicit typed source-result fields.

## 11. Depth / liquidity discipline

- The future adapter must not infer observed_size.
- It must not compute trade size, order size, max tradable size, allocation, or liquidity decision.
- It must not convert missing depth into zero.
- It must not aggregate depth across venues/order books.
- Depth fields must be carried from explicit typed source-result fields only.

## 12. Unit / source discipline

- The future adapter must not infer units.
- It must not infer source_contract, source_artifact, or source_field values.
- Bare values without unit/provenance are invalid.
- Gross-edge and depth provenance must be carried from explicit typed source-result fields.
- No exchange/API/raw-market parsing is authorized.

## 13. Halt-carrier and wrong-path handling

- If the adapter is invoked with exact BlockedPacket or exact NoEligibleHaltPacket, planning must require strict misroute rejection, not pass-through and not conversion.
- It must not duplicate route_halt_carrier.
- It must not convert BLOCKED / CONTRACT_VIOLATION / NO_ELIGIBLE into gross-edge observations.
- It must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects.
- Subclasses are not valid halt carriers and not valid source results; they must not be accepted as either.

## 14. Status / state handling

- The adapter should convert only source-result states that represent an explicitly observed gross-edge fact.
- Success-like or observed-like state must be explicitly named in planning, but implementation is deferred.
- Unknown, missing, failure, blocked, no-eligible, stale, malformed, or non-observed states must fail closed.
- It must never silently return None.

## 15. No arithmetic / economic output

- The adapter must not compute net_edge, total_cost, net_cost, effective_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, execution, valid_until, or freshness.
- It must not aggregate multiple observations.
- It must not produce list/collection/batch observations.
- It must not authorize net-edge or calculator behavior.

## 16. No market-truth / readiness claims

- The adapter proves no market truth, no price correctness, no liquidity correctness, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee.
- It only plans a typed-to-typed mapping contract.

## 17. Relationship to observable-cost side

- The gross-edge adapter mirrors the already established observable-cost typed-to-typed adapter discipline.
- It must not reuse the observable-cost adapter.
- It must not convert cost observations into gross-edge observations.
- It must not convert gross-edge observations into cost observations.
- Calculator-input behavior remains deferred.

## 18. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 19. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future adapter, must produce **none** of:

- no net edge, total cost, net cost, or effective cost figure;
- no profitability score; no alpha/edge claim; no PnL or economic-inference figure;
- no order size, allocation, sizing, or execution instruction;
- no valid_until or freshness verdict;
- no trade recommendation; no deployment or order instruction;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.

It authorizes no parser, loader, endpoint reader, order-book model, sizing model, calculator, reporting, trading, or paper/live work.
<!-- PROHIBITED-OUTPUTS-END -->

## 20. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact `GrossEdgeSourceResult` type, field list, and construction discipline.
- exact source-result observed/success-like state vocabulary.
- exact misroute-rejection and wrong-input/wrong-state error types and message discipline.
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
  `phase5_gross_edge_source_result_adapter` may follow, with failing tests first and declared
  evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
