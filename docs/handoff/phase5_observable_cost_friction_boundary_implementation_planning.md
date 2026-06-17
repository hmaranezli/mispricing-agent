# Phase 5 Component Implementation-Planning — `phase5_observable_cost_friction_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document.
Net-edge calculator work remains unauthorized. It defines only the planned role, epistemology, sign convention, unit/provenance
requirements, decimal discipline, atomic-observation scope, halt-misroute protection, input
discipline, and prohibitions for a future, separately authorized offline/TDD implementation task.

- `component_name`: `phase5_observable_cost_friction_boundary`.
- Purpose: define how explicitly observed cost/friction facts may later be carried toward a future
  calculator, with provenance — without computing total cost, net cost, gross edge, net edge,
  profitability, readiness, or any trade decision.
- It is an **observable-cost / friction planning boundary only, not a calculator**, and is a
  pre-net-edge planning component.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_halt_propagation_integration_boundary` planning artifact](phase5_halt_propagation_integration_boundary_implementation_planning.md)
- [`phase5_blocked_result_boundary` planning artifact](phase5_blocked_result_boundary_implementation_planning.md)
- [`phase5_no_eligible_halt_propagation_boundary` planning artifact](phase5_no_eligible_halt_propagation_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Boundary role

- The observable-cost / friction boundary is not a calculator.
- It is not an exchange parser, fee schedule parser, slippage model, loader, endpoint reader, artifact reader, or trading component.
- It may only define future contracts for carrying explicitly observed atomic cost/friction components.
- It must not infer, enrich, repair, normalize, aggregate, net, sum, subtract, annualize, rank, score, or decide.

## 3. Epistemology of zero

- Missing cost data and zero cost are not equivalent.
- A value of 0, 0.0, the string "0", empty, None, False, omitted, default, fallback, parse failure, unavailable field, or unknown field must never be treated as zero cost.
- A true zero cost is valid only when actively and explicitly observed from a declared source field as "cost is exactly zero".
- Future implementation must fail closed on unproven zero.
- No default-zero behavior is allowed anywhere.

## 4. Sign convention

The planning doc defines the sign convention for a future calculator to consume:

- positive value = cost / penalty / friction debit
- negative value = rebate / credit, such as maker rebate
- zero value = explicitly observed zero only

- Negative observed values must not be clipped, absolutized, rejected by default, or silently converted to positive cost.
- The boundary itself does not compute gross-edge-minus-friction; it only preserves sign semantics for a future calculator.
- No downgrade from rebate to cost and no upgrade from unknown to rebate/zero.

## 5. Unit / scale / source requirement

- Bare numeric values are prohibited.
- Every future observable-cost component must carry an explicit unit/scale and explicit source provenance.
- Example unit/scale labels may include bps, decimal_rate, quote_amount, base_amount, fee_rate, spread_bps, or slippage_bps, but the planning doc must not implement a parser or conversion table.
- Every observation must be traceable to declared source_contract, source_artifact, and source_field, or equivalent explicit provenance.
- Unitless numbers are invalid and must be fail-closed in future implementation.

## 6. Binary-float / rounding prohibition

- Binary float arithmetic is prohibited for cost/friction semantics.
- Planning must require exact decimal representation in future implementation, such as Decimal or exact decimal strings.
- No float-derived rounding, epsilon comparison, approximate equality, binary-float normalization, or float defaulting.
- This planning task must not choose final implementation mechanics beyond requiring exact decimal semantics later.

## 7. Atomic observations only

- The future boundary must carry atomic observed components only.
- It must not include or authorize fields like total_cost, net_cost, effective_cost, gross_edge, net_edge, profit, expected_profit, readiness, trade_score, or eligibility.
- Aggregation and arithmetic belong to a separately authorized future calculator, not this boundary.

## 8. Halt carrier misroute protection

- BlockedPacket and NoEligibleHaltPacket must not be processed by the observable-cost / friction boundary.
- If a halt carrier reaches this boundary, that is a routing/integration bug, not a cost observation.
- Planning must require strict misroute rejection, e.g. a future MisroutedHaltCarrierError / TypeError-class or ContractViolation-class behavior.
- Do not pass through, convert, unwrap, serialize, or reinterpret halt carriers here.
- Do not call bool/len/int/float/str/bytes/repr/equality/introspection on offending halt or hostile objects.

## 9. Input discipline

- The future input must be explicitly typed/frozen or otherwise strictly defined.
- Raw dicts, generic Mapping, arbitrary objects, attribute-guessed records, JSON-like blobs, and heuristic key guessing are prohibited.
- The boundary must not parse exchange/API/raw-market payloads.
- Adapter/parser work, if needed, must be a separate future slice.

## 10. No market-truth / economic claims

- The boundary does not prove a market exists.
- The boundary does not prove cost correctness, source truth, source reliability, liquidity, profitability, readiness, or trade eligibility.
- It only defines the contract for carrying explicitly observed cost/friction facts with provenance.

## 11. Relationship to halt propagation

- Halt propagation remains separate and already implemented.
- This boundary must not duplicate route_halt_carrier.
- This boundary must not convert BLOCKED / CONTRACT_VIOLATION / NO_ELIGIBLE into cost observations.
- It must state that halted payloads bypass cost/friction planning and calculation paths.

## 12. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 13. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- No net-edge calculator work is authorized by this planning artifact.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future boundary, must produce **none** of:

- no total cost, net cost, effective cost, gross edge, or net edge figure;
- no profitability score; no alpha/edge claim; no PnL or economic-inference figure;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.

It authorizes no parser, loader, endpoint reader, exchange fee model, slippage model, calculator, reporting, trading, or paper/live work.
<!-- PROHIBITED-OUTPUTS-END -->

## 14. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact observable-cost component type, field list, and value syntax.
- exact unit/scale vocabulary and the exact decimal representation mechanics.
- exact typed/frozen input type and its strict construction discipline.
- exact misroute-rejection error type and message discipline.
- exact test boundary between contract tests and implementation tests.
- production/live usage deferred until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes no edge, no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no alpha, no live readiness, no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. This is a component planning gate only; it authorizes a separately approved
offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 15. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `phase5_observable_cost_friction_boundary` may follow, with failing tests first and declared
  evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
