# Phase 5 Component Implementation-Planning — `phase5_pre_net_edge_calculation_input_gate`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. **No net-edge calculator work is authorized**,
and no next component implementation is authorized. It defines only the planned cross-object
validation gate / preflight contract, its input discipline, the exact time equations, the failure
taxonomy and precedence, the unit policy, the deferred checks, and the planned reason vocabulary for
a future, separately authorized offline/TDD implementation task.

- `component_name`: `phase5_pre_net_edge_calculation_input_gate`.
- The future gate is pinned as `PreNetEdgeCalculationInputGate`.
- The future function is pinned as `net_edge_input_preflight`.
- The future function shape is pinned as `net_edge_input_preflight(*, calculation_input, evaluation_epoch_ms)`.
- This planning task must not implement any of these symbols.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_pre_net_edge_calculation_input_boundary` planning artifact](phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md)
- [`phase5_gross_edge_observation_boundary` planning artifact](phase5_gross_edge_observation_boundary_implementation_planning.md)
- [`phase5_observable_cost_friction_boundary` planning artifact](phase5_observable_cost_friction_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Gate V1 role

- It is a cross-object validation gate / preflight.
- It is not a carrier.
- It is not a calculator.
- It is not a parser.
- It is not an adapter.
- It is not a cost aggregator.
- It is not a unit converter.
- It is not a price/FX oracle.
- It is not a trading, reporting, paper-live, or execution component.
- It decides only whether an exact PreNetEdgeCalculationInput can proceed toward the future calculator.
- It produces no net-edge, no total-cost, no profitability, no readiness, no order size, no execution instruction.

## 3. Input contract

- future net_edge_input_preflight accepts exact type(calculation_input) is PreNetEdgeCalculationInput.
- subclasses rejected.
- raw dict/Mapping/JSON-like object/duck-typed object rejected.
- exact BlockedPacket / exact NoEligibleHaltPacket received at this boundary is a misroute and must be rejected as a programmatic routing bug.
- evaluation_epoch_ms must be provided explicitly by the caller/orchestrator.
- evaluation_epoch_ms must be exact str, non-empty, non-whitespace, and match ^\d+$.
- str subclasses, None, bool/int/float/Decimal/containers/objects rejected.
- No current-time, wall-clock, system-time, monotonic-time, datetime, or fallback time source is allowed.
- No default evaluation time.

## 4. Allowed local math

- Gate may locally parse exact integer strings with int() only after exact ^\d+$ validation.
- Gate may perform integer timestamp comparisons and the single timestamp addition gross_observed_at_epoch_ms + gross_staleness_threshold_ms.
- Parsed ints are local temporaries only.
- The original carrier fields remain exact strings and must never be mutated, rewritten, normalized, or re-emitted as ints.
- No Decimal, float, economic arithmetic, cost arithmetic, gross-minus-cost, total-cost, or net-edge arithmetic.

## 5. Time checks to pin

Let:

- gross_observed = int(calculation_input.gross_observation.observed_at_epoch_ms)
- gross_staleness = int(calculation_input.gross_observation.staleness_threshold_ms)
- evaluation_time = int(evaluation_epoch_ms)

For each cost validity context:

- cost_from = int(context.valid_from_epoch_ms)
- cost_until = int(context.valid_until_epoch_ms)

Future Gate V1 must check:

- evaluation_time >= gross_observed
- cost_from <= cost_until
- cost_from <= gross_observed <= cost_until
- cost_from <= evaluation_time <= cost_until
- evaluation_time <= gross_observed + gross_staleness

## 6. Failure taxonomy

### 6.1 Programmatic wrong path / wrong type

- wrong calculation_input type, subclasses, raw containers, hostile objects, exact halt carriers misrouted.
- future behavior: TypeError / MisroutedHaltCarrierError.
- never BlockedPacket or NoEligibleHaltPacket.

### 6.2 Contract/data contradiction

- evaluation_time < gross_observed.
- cost_from > cost_until.
- corrupted exact carrier state that violates required exact string/time fields.
- future behavior: BlockedPacket with PLANNING_GATE_CONTRACT_VIOLATION semantics.

### 6.3 Evidence/applicability failure

- cost validity interval does not cover gross_observed.
- cost validity interval does not cover evaluation_time.
- unsupported unit compatibility evidence.
- future behavior: BlockedPacket with PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE / BLOCKED_NEEDS_EVIDENCE semantics.

### 6.4 Market no-eligible

- evaluation_time > gross_observed + gross_staleness.
- future behavior: NoEligibleHaltPacket.
- this is the only V1 no-eligible market-fact failure.

### 6.5 Pass

- return the identical PreNetEdgeCalculationInput object by identity.
- no copy, no wrapping, no enrichment, no mutation.

## 7. Precedence

- Programmatic wrong-path errors happen before semantic gate results.
- Contract/data contradictions and evidence/applicability failures must not be masked as NoEligible.
- Blocked outcomes take precedence over NoEligible if both could be observed.
- NoEligible is reserved for gross market snapshot staleness only in V1.
- Success returns input identity.

## 8. Unit policy V1

- Gate V1 must not convert units.
- Gate V1 must not normalize case.
- Gate V1 must not call .upper(), .lower(), strip-for-normalization, or map aliases.
- Unit checks are case-sensitive exact string checks.
- Exact match passes: cost_observation.unit == gross_observation.gross_edge_unit.
- Static proportional cost units are admissible without conversion only if cost_observation.unit is exactly one of: BPS, BASIS_POINTS, RATE, PERCENT, PERCENTAGE.
- Any other non-matching absolute unit is blocked as missing/unsupported unit compatibility evidence.
- No FX rate, no oracle, no conversion table, no quote/base conversion, no Decimal math.

## 9. Deferred checks — explicitly out of Gate V1

The following are deferred and must not be attempted in Gate V1:

- instrument/base/quote compatibility.
- venue compatibility.
- size/depth compatibility.
- volume tier / applicable size range.
- cost duplicate detection.
- cost ordering interpretation.
- cost aggregation.
- gross observed_size > 0 eligibility.
- gross_edge_value positive/negative/profitability interpretation.
- source_artifact/source_field parsing.
- regex extraction from provenance strings.
- source_contract semantics inference.
- any inference from file names, artifact names, or source fields.

### 9.1 Reason for deferral

- Current ObservableCostObservation / ObservableCostValidityContext does not carry explicit base_asset, quote_asset, instrument_id, venue, applicable_size_range, or volume-tier fields.
- Gate V1 must not invent missing applicability data.
- Missing applicability policy may require a future CostApplicabilityContext or separately authorized policy object.

## 10. Output planning

- Future pass output is exact same PreNetEdgeCalculationInput identity.
- Future blocked output uses existing BlockedPacket / make_blocked_packet.
- Future no-eligible output uses existing NoEligibleHaltPacket / make_no_eligible_halt_packet.
- No new generic union wrapper.
- No shared base class.
- No polymorphic halt hierarchy.
- No conversion between BlockedPacket and NoEligibleHaltPacket.
- No downgrading CONTRACT_VIOLATION to NO_ELIGIBLE.
- No masking missing evidence as NO_ELIGIBLE.

## 11. Planned blocked/no-eligible reason vocabulary (planned, not implemented)

- PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_TIME_CAUSALITY
- PRE_NET_EDGE_GATE_CONTRACT_VIOLATION_INVALID_COST_INTERVAL
- PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_GROSS_TIME
- PRE_NET_EDGE_GATE_BLOCKED_COST_VALIDITY_DOES_NOT_COVER_EVALUATION_TIME
- PRE_NET_EDGE_GATE_BLOCKED_UNSUPPORTED_UNIT_COMPATIBILITY
- PRE_NET_EDGE_GATE_NO_ELIGIBLE_GROSS_SNAPSHOT_STALE

## 12. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 13. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the gate function/class, the calculator, or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future gate, must produce **none** of:

- no net edge, gross-minus-cost, total cost, net cost, effective cost, or summed-cost figure;
- no profitability score; no alpha/edge claim; no PnL or economic-inference figure;
- no order size, allocation, sizing, or execution instruction;
- no trade recommendation; no deployment or order instruction;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.

It authorizes no parser, adapter, loader, endpoint reader, cost aggregator, unit converter, FX/oracle,
calculator, reporting, trading, or paper/live work.
<!-- PROHIBITED-OUTPUTS-END -->

## 14. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact `PreNetEdgeCalculationInputGate` / `net_edge_input_preflight` implementation and its test boundary.
- exact mapping of each reason-vocabulary token into `make_blocked_packet` / `make_no_eligible_halt_packet` field values.
- exact `CostApplicabilityContext` (or equivalent policy object) shape for the deferred applicability checks.
- exact unit-compatibility policy beyond the V1 proportional vocabulary.
- production/live usage deferred until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no net-edge, no PnL, no profitability, no alpha.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no source-truth guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. This is a component planning gate only; it authorizes a separately approved
offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 15. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `PreNetEdgeCalculationInputGate` / `net_edge_input_preflight` may follow, with failing tests first
  and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
