# Phase 5 Component Implementation-Planning — `phase5_pre_net_edge_calculation_input_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document.
No net-edge calculator work is authorized, and no next component implementation is authorized. It
defines only the planned carrier contracts, the carrier-vs-gate-vs-calculator separation, strict
typing/tuple discipline, deferred cross-object checks, and prohibitions for a future, separately
authorized offline/TDD implementation task.

- `component_name`: `phase5_pre_net_edge_calculation_input_boundary`.
- The future carriers are pinned as `ObservableCostValidityContext` and `PreNetEdgeCalculationInput`.
- The future cross-object validation gate is named only as deferred: `PreNetEdgeCalculationInputGate`
  (or `net_edge_input_preflight`). This task must not implement any of these names.
- It is a **carrier-contract planning only, not a validation gate and not a calculator**.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_gross_edge_observation_boundary` planning artifact](phase5_gross_edge_observation_boundary_implementation_planning.md)
- [`phase5_observable_cost_friction_boundary` planning artifact](phase5_observable_cost_friction_boundary_implementation_planning.md)
- [`phase5_gross_edge_source_result_adapter` planning artifact](phase5_gross_edge_source_result_adapter_implementation_planning.md)
- [`phase5_observable_cost_source_result_adapter` planning artifact](phase5_observable_cost_source_result_adapter_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Boundary role

- This boundary plans carrier contracts only.
- It is not a validation gate.
- It is not a calculator.
- It is not a raw parser, exchange/API parser, loader, endpoint reader, order-book model, venue model, cost aggregator, unit converter, freshness calculator, risk model, sizing model, execution model, trading component, or reporting component.
- It must not infer, enrich, repair, normalize, round, parse, aggregate, net, sum, subtract, compare, score, decide, size, allocate, route orders, or trade.

## 3. Carrier vs gate separation

- ObservableCostValidityContext and PreNetEdgeCalculationInput are future carriers only.
- They must enforce only intra-object shape/type/format rules.
- They must not validate cross-object compatibility.
- Cross-object checks are deferred to a future separately authorized PreNetEdgeCalculationInputGate / net_edge_input_preflight.
- Future gate checks may include: cost validity interval covers gross observed time; cost units are compatible or convertible with gross-edge units; instrument/base/quote context compatibility; venue context compatibility; depth/size context compatibility.
- Those checks are not implemented here.

## 4. No cross-validation in carrier factories

Future make_pre_net_edge_calculation_input must not:

- compare gross observed time to cost validity intervals;
- compare valid_from_epoch_ms to valid_until_epoch_ms;
- compare gross units to cost units;
- compare instruments across gross and cost;
- compare venues across gross and cost;
- compare sizes/depth across gross and cost;
- compute freshness;
- compute valid_until;
- compute aggregate cost;
- compute net_edge.

- Future make_observable_cost_validity_context must not compare valid_from_epoch_ms <= valid_until_epoch_ms.
- Reason: comparison/coercion is gate behavior, not carrier behavior.

## 5. ObservableCostValidityContext contract

- Future ObservableCostValidityContext wraps exactly one ObservableCostObservation.
- It must carry explicit validity interval metadata: `valid_from_epoch_ms`, `valid_until_epoch_ms`, `validity_source_contract`, `validity_source_artifact`, `validity_source_field`, `validity_assertion_type`, and `boundary_version`.
- cost_observation must be exact type(cost_observation) is ObservableCostObservation.
- Subclasses must not be accepted.
- No None.
- No raw dict/Mapping/JSON-like object.
- No inference from ObservableCostObservation.source_* fields.
- No default TTL.
- No current-time / wall-clock / system-time / monotonic-time substitution.
- No duration field.
- No computed valid_until.
- No fee-schedules-are-usually-daily assumption.
- Validity metadata must be provided by a separately authorized upstream/orchestrator/validity-source adapter as exact strings with provenance.
- This context does not prove validity; it only carries the declared validity interval and provenance.

## 6. Cost validity timestamp discipline

- valid_from_epoch_ms and valid_until_epoch_ms must be exact integer strings in future implementation (one or more digits, no sign, no decimal point, no exponent).
- No int coercion in carrier.
- No string comparison in carrier.
- No valid_from <= valid_until comparison in carrier.
- No current-time fallback.
- No derived timestamp.

## 7. PreNetEdgeCalculationInput contract

- Future PreNetEdgeCalculationInput wraps exactly one GrossEdgeObservation and a non-empty tuple of ObservableCostValidityContext.
- gross_observation must be exact type(gross_observation) is GrossEdgeObservation.
- cost_validity_contexts must be exact tuple.
- The tuple must be non-empty.
- Every tuple item must be exact type(item) is ObservableCostValidityContext.
- Subclasses must not be accepted.
- List, set, dict, frozenset, Mapping, raw JSON-like containers, generator, iterator, or arbitrary collection must be rejected.
- No mutation, no append, no sorting, no deduplication, no aggregation.

## 8. Strict tuple discipline

- The tuple is used only as an immutable carrier structure.
- Tuple membership order must be preserved.
- The carrier must not sort, rank, group, deduplicate, merge, filter, or aggregate cost contexts.
- Duplicate cost contexts are not interpreted here; any duplicate-detection or semantic validation is deferred to a future gate.
- An empty tuple is invalid.

## 9. Unit compatibility is deferred

- Gross-edge units and cost units may differ.
- The carrier must not convert bps/rate/quote/base units.
- The carrier must not decide convertibility.
- Unit compatibility declaration/checking belongs to a future gate.
- No unit inference.
- No unit normalization.
- No conversion table.
- No arithmetic.

## 10. Asymmetric freshness is deferred

- The gross-edge observation is a fast market snapshot.
- Cost validity may be slower-moving metadata.
- The carrier must not require equal timestamps.
- The carrier must not require symmetric freshness windows.
- The future gate, not this carrier, must decide whether a cost validity interval covers the gross observation time.
- No freshness calculation in this planning task.

## 11. Halt-carrier and wrong-path handling

- Exact BlockedPacket and exact NoEligibleHaltPacket must not be accepted as gross observations, cost observations, validity contexts, or calculation inputs.
- If a halt carrier reaches this boundary, that is a routing/integration bug.
- Future implementation must reject exact halt carriers with strict error behavior, not pass-through and not conversion.
- It must not duplicate route_halt_carrier.
- It must not convert BLOCKED / CONTRACT_VIOLATION / NO_ELIGIBLE into gross, cost, validity, or calculation-input carriers.
- It must not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects.

## 12. Input discipline

- Future inputs must be explicitly typed/frozen or otherwise strictly defined.
- Raw dicts, generic Mapping, JSON-like blobs, arbitrary objects, attribute-guessed records, duck-typed records, heuristic key guessing, and generic containers are prohibited.
- No parser behavior is authorized.
- No adapter behavior is authorized in this planning task.

## 13. No arithmetic / no calculator behavior

- The future carriers must not compute net_edge, gross_edge_minus_cost, total_cost, net_cost, effective_cost, sum_cost, profitability, expected_profit, readiness, trade_score, eligibility, order_size, allocation, execution, valid_until, or freshness.
- The future carriers must not iterate over the cost tuple to sum or convert values.
- They must not call int, float, Decimal, or arithmetic operators to compare or compute semantic relationships.
- Tuple traversal is allowed only for exact item type checking in future implementation.

## 14. No market-truth / readiness claims

- This boundary proves no market truth, no cost truth, no gross-edge truth, no validity truth, no source truth, no source reliability, no data-quality guarantee, no profitability, no readiness, no paper/live readiness, and no safety guarantee.
- It only plans carrier contracts for a future gate/calculator path.

## 15. Relationship to existing components

- GrossEdgeObservation remains separate and already implemented.
- ObservableCostObservation remains separate and already implemented.
- Gross-edge and cost source-result adapters remain separate and already implemented.
- This boundary must not reuse or subclass those carriers.
- This boundary must not alter those carriers.
- This boundary must not retroactively add TTL to ObservableCostObservation.
- This boundary must not retroactively add calculator fields to GrossEdgeObservation.

## 16. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 17. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- Implementation should likely be split into separate slices: `ObservableCostValidityContext`, `PreNetEdgeCalculationInput`, and the future gate/preflight.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future carriers, must produce **none** of:

- no net edge, gross-minus-cost, total cost, net cost, effective cost, or summed-cost figure;
- no profitability score; no alpha/edge claim; no PnL or economic-inference figure;
- no order size, allocation, sizing, or execution instruction;
- no valid_until, freshness, or validity verdict;
- no trade recommendation; no deployment or order instruction;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.

It authorizes no parser, adapter, validation gate, loader, endpoint reader, cost aggregator, calculator, reporting, trading, or paper/live work.
<!-- PROHIBITED-OUTPUTS-END -->

## 18. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact `ObservableCostValidityContext` and `PreNetEdgeCalculationInput` field lists and construction discipline.
- exact `validity_assertion_type` vocabulary.
- exact `PreNetEdgeCalculationInputGate` / `net_edge_input_preflight` cross-object compatibility checks.
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

## 19. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** (likely split into the
  `ObservableCostValidityContext` slice, the `PreNetEdgeCalculationInput` slice, and the future
  gate/preflight) may follow, with failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
