# Phase 5 Component Implementation-Planning — `phase5_net_edge_calculator_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It defines only the planned deterministic
algebra/calculation boundary contract, its input/output discipline, the net-edge formula, the
Decimal discipline, the dimensional-compatibility policy, the failure taxonomy, the blocked reason
vocabulary, and the deferred decisions for a future, separately authorized offline/TDD implementation
task.

- `component_name`: `phase5_net_edge_calculator_boundary`.
- The future result carrier is pinned as `NetEdgeCalculationResult`.
- The future calculator function is pinned as `calculate_net_edge`.
- The optional stateless class wrapper is pinned as `NetEdgeCalculator`.
- The future function shape is pinned as `calculate_net_edge(*, calculation_input)`.
- This planning task must not implement any of these symbols.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_pre_net_edge_calculation_input_gate` planning artifact](phase5_pre_net_edge_calculation_input_gate_implementation_planning.md)
- [`phase5_pre_net_edge_calculation_input_boundary` planning artifact](phase5_pre_net_edge_calculation_input_boundary_implementation_planning.md)
- [`phase5_gross_edge_observation_boundary` planning artifact](phase5_gross_edge_observation_boundary_implementation_planning.md)
- [`phase5_observable_cost_friction_boundary` planning artifact](phase5_observable_cost_friction_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

## 2. Calculator V1 role

- It is a deterministic algebra/calculation boundary.
- It consumes only exact PreNetEdgeCalculationInput that has already passed the future net_edge_input_preflight gate.
- It is not a gate/preflight.
- It is not a parser.
- It is not an adapter.
- It is not a unit converter.
- It is not a cost-applicability policy.
- It is not an FX/oracle.
- It is not a profitability gate.
- It is not a readiness gate.
- It is not an actionability gate.
- It is not a paper/live/trading/reporting/execution component.
- It must not decide whether to trade.
- It must not return NoEligibleHaltPacket.
- It must not produce order size, allocation, execution instruction, readiness, profitability verdict, or paper/live authority.

## 3. Input contract

- future calculate_net_edge accepts exact type(calculation_input) is PreNetEdgeCalculationInput.
- subclasses rejected.
- raw dict/Mapping/JSON-like object/duck-typed object rejected.
- exact BlockedPacket / exact NoEligibleHaltPacket received at this boundary is a misroute and must be rejected as a programmatic routing bug.
- wrong type/misroute is TypeError / MisroutedHaltCarrierError, never BlockedPacket or NoEligibleHaltPacket.

## 4. Output contract

- Future success output is NetEdgeCalculationResult.
- NetEdgeCalculationResult is a calculated result, not an observation.
- It must not be named NetEdgeObservation, ActionableCandidate, TradeCandidate, Signal, Opportunity, ReadyCandidate, ExecutableCandidate, or Payload.
- It is not actionable.
- It proves no profitability, no readiness, no safety, no source truth, no paper/live readiness.
- Negative, zero, and positive net values are all successful calculated results if dimensionally valid.
- Negative net edge is not a failure.
- Zero net edge is not a failure.
- Positive net edge is not actionable.

### 4.1 Planned NetEdgeCalculationResult fields

- `component_name`
- `origin_component`
- `origin_result_status`
- `status`
- `gross_edge_value`
- `gross_edge_unit`
- `total_cost_value`
- `total_cost_unit`
- `net_edge_value`
- `net_edge_unit`
- `cost_component_count`
- `source_contract`
- `source_artifact`
- `source_field`
- `calculation_method`
- `boundary_version`

### 4.2 Result field discipline

- All result fields must be exact str in future implementation.
- Decimal outputs must be canonical decimal strings with no exponent notation.
- No float.
- No NaN.
- No Infinity.
- No None.
- cost_component_count must be exact unsigned integer string.
- Result must be frozen, repr-safe, anti-truthiness, anti-coercion, and constructed only by the calculator/factory in future implementation.

## 5. Core algebra

- NetEdgeCalculator V1 formula: net_edge = gross_edge - sum(cost_i)
- Costs are algebraic signed values:
  - positive cost reduces net edge.
  - negative cost/rebate increases net edge via subtraction of a negative value.
  - zero cost is valid if carried by ObservableCostObservation zero-cost evidence.
- Calculator must not discard zero costs.
- Calculator must preserve cost_component_count including zero-cost components.
- Calculator must not mutate the input or any carrier.
- Calculator must not sort, deduplicate, filter, or reinterpret cost contexts.
- Cost tuple order must be traversed only to accumulate algebraic total cost in future implementation.

## 6. Decimal discipline

- Calculator V1 may use Decimal locally for arithmetic.
- Decimal must be constructed only from already-canonical decimal strings.
- No float construction.
- No Decimal from float.
- No float arithmetic.
- No binary floating point.
- No rounding unless a future explicitly planned precision policy exists.
- No quantize policy in V1 unless separately authorized.
- Decimal results must be serialized back to canonical decimal strings:
  - no exponent notation
  - no leading plus
  - minus preserved for negative results
  - zero canonicalization must be planned explicitly
- Do not normalize values in a way that changes economic meaning.

## 7. Dimensional compatibility policy V1

- Calculator V1 only computes when gross and all costs are dimensionally compatible without inference.
- Exact unit match is compatible: cost.unit == gross.gross_edge_unit
- If gross_edge_unit and all cost units are the same exact proportional unit, calculator may compute in that proportional unit.
- Proportional vocabulary is exact and case-sensitive: BPS, BASIS_POINTS, RATE, PERCENT, PERCENTAGE.
- No case normalization.
- No .upper(), .lower(), .casefold(), alias mapping, or spelling repair.
- Mixed proportional units are not compatible unless an explicit future policy exists.
- Example: BPS and PERCENT together must be blocked in V1; do not convert 100 BPS to 1 PERCENT.
- Absolute gross unit with proportional cost unit requires explicit notional/reference-price evidence, which current PreNetEdgeCalculationInput does not carry.
- Proportional gross unit with absolute cost unit requires explicit conversion basis, which current input does not carry.
- Different absolute units are incompatible.
- Unsupported/mixed units must block, not infer.

## 8. Blocked conditions V1

Future calculator must return BlockedPacket, not exception, for exact valid calculation_input with:

- proportional cost against absolute gross unit without explicit notional/reference-price evidence
- absolute cost against proportional gross unit without explicit conversion basis
- mixed proportional units
- different absolute units
- unsupported unit vocabulary
- malformed exact carrier state discovered during calculation
- any dimensional incompatibility that prevents algebra

### 8.1 Reason vocabulary to pin for future BlockedPacket results

- NET_EDGE_CALCULATOR_BLOCKED_MISSING_NOTIONAL_FOR_PROPORTIONAL_COST
- NET_EDGE_CALCULATOR_BLOCKED_MISSING_CONVERSION_BASIS_FOR_ABSOLUTE_COST
- NET_EDGE_CALCULATOR_BLOCKED_MIXED_PROPORTIONAL_UNITS
- NET_EDGE_CALCULATOR_BLOCKED_INCOMPATIBLE_ABSOLUTE_UNITS
- NET_EDGE_CALCULATOR_BLOCKED_UNSUPPORTED_UNIT_VOCABULARY
- NET_EDGE_CALCULATOR_CONTRACT_VIOLATION_MALFORMED_INPUT_STATE

## 9. No NoEligible

- Calculator V1 must never return NoEligibleHaltPacket.
- Unprofitable, negative, zero, or positive results are all mathematical outputs, not no-eligible states.
- Market staleness and eligibility are upstream/downstream gates, not calculator behavior.
- Profitability filtering is deferred to a future ProfitabilityGate / ReadinessGate, not this calculator.

## 10. No actionability

- NetEdgeCalculationResult must not contain actionable, eligible, ready, executable, trade, order, allocation, paper_live, live, or readiness fields.
- Positive net_edge_value must not imply readiness.
- No order-size calculation.
- No balance/capital check.
- No slippage/model update.
- No source-truth claim.
- No paper/live readiness claim.

## 11. Source/provenance policy

- Result must carry calculation provenance fields.
- It may reference the calculator source contract/artifact/field.
- It must not claim source truth or data quality.
- It must not parse source_artifact/source_field to infer missing values.
- It must not fabricate missing notional/reference price.
- It must not invent applicability fields.

## 12. Failure taxonomy

1. Programmatic wrong-path / wrong-type:
   - wrong calculation_input type, subclass, raw object, exact halt carrier misroute.
   - TypeError / MisroutedHaltCarrierError.
   - never BlockedPacket or NoEligibleHaltPacket.
2. Exact input but dimensional/evidence failure:
   - BlockedPacket.
   - missing/incompatible evidence semantics.
3. Exact input and dimensionally compatible:
   - NetEdgeCalculationResult.
   - regardless of negative/zero/positive net edge.
4. NoEligible:
   - never returned by calculator V1.

## 13. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 14. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the calculator function/class, the result carrier, or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future calculator, must produce **none** of:

- no profitability score; no alpha/edge claim; no PnL or economic-inference verdict;
- no order size, allocation, sizing, or execution instruction;
- no trade recommendation; no deployment or order instruction;
- no actionability, eligibility, or readiness verdict;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement.

A computed `net_edge_value` (negative, zero, or positive) is a mathematical output only; it authorizes
no trading, no paper/live work, and no readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 15. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- notional/reference-price carrier or policy
- CostApplicabilityContext
- unit conversion policy
- precision/rounding/quantization policy
- proportional-to-absolute conversion
- mixed proportional unit conversion
- profit threshold policy
- readiness/actionability gate
- paper/live connection
- performance benchmark/microbenchmark

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

## 16. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `NetEdgeCalculator` / `calculate_net_edge` / `NetEdgeCalculationResult` may follow, with failing
  tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
