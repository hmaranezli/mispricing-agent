# Phase 5 Component Implementation-Planning — `phase5_net_edge_profitability_gate_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It jointly designs two future components and
defines only their contracts, the threshold-comparison rule, the unit policy, the failure taxonomy,
the blocked/no-eligible reason vocabulary, and the deferred decisions for a future, separately
authorized offline/TDD implementation task.

- `component_name`: `phase5_net_edge_profitability_gate_boundary`.
- This artifact will **jointly design two future components**: (1) `ProfitabilityThresholdPolicyContext`
  and (2) `NetEdgeProfitabilityGate` / `net_edge_profitability_preflight`.
- The two future components are ProfitabilityThresholdPolicyContext and NetEdgeProfitabilityGate / net_edge_profitability_preflight.
- The future policy carrier is pinned as `ProfitabilityThresholdPolicyContext` with factory
  `make_profitability_threshold_policy_context`.
- The future gate is pinned as `NetEdgeProfitabilityGate` / `net_edge_profitability_preflight`.
- The future function shape is pinned as `net_edge_profitability_preflight(*, calculation_result, threshold_policy)`.
- This planning task must not implement any of these symbols.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_net_edge_calculator_boundary` planning artifact](phase5_net_edge_calculator_boundary_implementation_planning.md)
- [`phase5_pre_net_edge_calculation_input_gate` planning artifact](phase5_pre_net_edge_calculation_input_gate_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

## 2. Gate V1 role

- It is a pure/offline/deterministic profitability threshold gate.
- It consumes exact NetEdgeCalculationResult plus exact ProfitabilityThresholdPolicyContext.
- It is not a calculator.
- It is not a parser.
- It is not an adapter.
- It is not a unit converter.
- It is not an FX/oracle.
- It is not a cost-applicability policy.
- It is not a readiness gate.
- It is not an actionability gate.
- It is not a liquidity/depth/slippage/balance/margin/order-sizing/execution/trading/reporting/paper-live component.
- It must not decide whether to trade.
- It must not produce order size, allocation, readiness, actionability, paper/live authority, or execution instruction.

## 3. ProfitabilityThresholdPolicyContext planned carrier contract

- Future carrier wraps only explicit threshold policy data needed by the gate.
- It must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only.
- It must not read env/config/files/db/network/time.
- It must not compute or infer a threshold.
- No hardcoded/default threshold.
- No source_artifact parsing.
- Planned fields should include only explicit threshold and provenance/contract fields, all exact str.

### 3.1 Required planned fields

- `component_name`
- `threshold_value`
- `threshold_unit`
- `source_contract`
- `source_artifact`
- `source_field`
- `policy_id`
- `boundary_version`

### 3.2 Threshold value/unit discipline

- threshold_value must be a canonical signed decimal string in the future implementation.
- threshold_unit must be exact non-empty str and case-sensitive.
- Negative, zero, and positive threshold values are all policy data; the gate must not impose sign morality.
- If a non-negative threshold rule is ever desired, it is deferred to a future policy factory/governance layer, not this V1 gate.

## 4. Gate input contract

- net_edge_profitability_preflight accepts exact type(calculation_result) is NetEdgeCalculationResult.
- subclasses rejected.
- raw dict/Mapping/JSON/duck-typed objects rejected.
- exact BlockedPacket or exact NoEligibleHaltPacket received as calculation_result is a misroute and must be rejected as a programmatic routing bug.
- threshold_policy must be exact ProfitabilityThresholdPolicyContext.
- wrong type/misroute must be TypeError / MisroutedHaltCarrierError, never a market packet.
- Missing/malformed exact policy evidence is BlockedPacket, not NoEligible.

## 5. Allowed local math

- Decimal comparison only after canonical decimal string validation.
- Use Decimal locally only from already-canonical strings.
- No float, no Decimal from float, no rounding, no quantize.
- No net-edge recalculation.
- No cost summing.
- No mutation, copy, wrapping, transformation, sorting, filtering, or enrichment of calculation_result.
- Success returns the exact same calculation_result object identity.

## 6. Comparison rule

- Gate compares net_edge_value >= threshold_value.
- Equality passes.
- No special sign logic.
- No profitability score.
- No ranking.
- No statistical inference.

## 7. Unit policy

- calculation_result.net_edge_unit must exactly equal threshold_policy.threshold_unit.
- Case-sensitive exact match only.
- No .upper(), .lower(), .casefold(), alias mapping, spelling repair, normalization, conversion, FX/oracle, or proportional/absolute conversion.
- Unit mismatch is evidence failure -> BlockedPacket.
- Do not inspect gross_edge_unit, total_cost_unit, or any upstream cost units for additional policy.
- Do not infer units from source fields.

## 8. Failure taxonomy

1. Programmatic wrong-path / wrong-type:
   - wrong calculation_result type, wrong threshold_policy type, subclasses, raw objects, exact halt carrier misroute.
   - TypeError / MisroutedHaltCarrierError.
   - never BlockedPacket or NoEligibleHaltPacket.
2. Exact result + missing/malformed/unsupported threshold evidence:
   - BlockedPacket.
   - Examples: malformed threshold_value, missing threshold policy field, empty threshold_unit, unit mismatch.
   - This means system blindness / missing policy evidence, not market unprofitability.
3. Exact result + exact policy + unit match + net_edge_value < threshold_value:
   - NoEligibleHaltPacket.
   - This means mathematically valid but below profitability threshold.
4. Exact result + exact policy + unit match + net_edge_value >= threshold_value:
   - pass-through identity: return the exact same NetEdgeCalculationResult object.
   - This is not actionable and not trade-ready.

### 8.1 Reason vocabulary to pin for future implementation

- NET_EDGE_PROFITABILITY_GATE_BLOCKED_MISSING_THRESHOLD_POLICY
- NET_EDGE_PROFITABILITY_GATE_BLOCKED_MALFORMED_THRESHOLD_POLICY
- NET_EDGE_PROFITABILITY_GATE_BLOCKED_UNIT_MISMATCH
- NET_EDGE_PROFITABILITY_GATE_NO_ELIGIBLE_BELOW_THRESHOLD

## 9. Output contract

- Success must return input identity, not a new carrier.
- Do NOT create ProfitabilityPassedResult, ActionableCandidate, TradeCandidate, Signal, Opportunity, ReadyCandidate, ExecutableCandidate, or Payload.
- No wrapper, no union carrier, no shared base hierarchy, no cross-conversion, no downgrade, no masking.
- Passing this gate means only "net edge met explicit profitability threshold".
- Passing this gate does not mean actionable, ready, executable, safe, paper-ready, live-ready, or trade-authorized.

## 10. Explicitly prohibited V1 checks

- No venue/base/quote/instrument validation.
- No source_artifact/source_field parsing.
- No regex extraction from provenance.
- No policy provenance comparison against venue/asset/instrument because NetEdgeCalculationResult does not carry those fields.
- No threshold defaults from env/config/file/db.
- No clock/staleness/evaluation time checks.
- No order sizing.
- No balance/margin/capital checks.
- No liquidity/depth/slippage checks.
- No paper/live/trading/reporting/execution.
- No profitability inference beyond the single Decimal comparison.

## 11. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- Venue/asset/instrument applicability policy
- Threshold governance/factory rules
- Non-negative threshold policy, if ever needed
- Strategy-specific threshold selection
- Dynamic threshold model
- Readiness/actionability gate
- Liquidity/depth/slippage gate
- Balance/capital gate
- Paper/live execution
- Performance benchmark/microbenchmark

## 12. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 13. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the gate function/class, the policy carrier, or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future gate, must produce **none** of:

- no profitability score; no alpha/edge claim; no PnL or economic-inference verdict;
- no order size, allocation, sizing, or execution instruction;
- no trade recommendation; no deployment or order instruction;
- no actionability, eligibility, or readiness verdict;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement.

A net edge at or above an explicit threshold is a threshold-filtered mathematical result only; it
authorizes no trading, no paper/live work, and no readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no PnL, no alpha, no actionability, no readiness.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no source-truth guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. A passed profitability gate is still only a threshold-filtered mathematical result.
This is a component planning gate only; it authorizes a separately approved offline/TDD implementation
task, not implementation.
<!-- NO-CLAIMS-END -->

## 14. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `ProfitabilityThresholdPolicyContext` and `NetEdgeProfitabilityGate` / `net_edge_profitability_preflight`
  may follow, with failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
