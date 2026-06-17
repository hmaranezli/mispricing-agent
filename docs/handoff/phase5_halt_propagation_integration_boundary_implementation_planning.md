# Phase 5 Component Implementation-Planning — `phase5_halt_propagation_integration_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It defines only the planned routing semantics,
exact-type carrier separation, halt/bypass discipline, unknown-input handling, pass-through identity,
success-path continuity, and prohibitions for a future, separately authorized offline/TDD
implementation task.

- `component_name`: `phase5_halt_propagation_integration_boundary`.
- Purpose: define how a future integration boundary routes already-typed halt carriers around
  calculator / net-edge / friction / trading paths, keeping the two halt carriers semantically
  separate and keeping calculator code free of halt-semantics interpretation.
- It is an **integration boundary only, not a calculator** and not an eligibility judge.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_blocked_result_boundary` planning artifact](phase5_blocked_result_boundary_implementation_planning.md)
- [`phase5_no_eligible_halt_propagation_boundary` planning artifact](phase5_no_eligible_halt_propagation_boundary_implementation_planning.md)
- [`phase5_fail_closed_blocked_state_contract.md`](../protocols/phase5_fail_closed_blocked_state_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](../protocols/phase5_no_eligible_handling_schema_contract.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Exact-type halt carrier separation

- BlockedPacket is the evidence/provenance/contract failure halt carrier.
- NoEligibleHaltPacket is the non-error no-candidate halt carrier.
- They are separate exact-type halt carriers.
- There must be no shared BaseHaltPacket, GenericHaltPacket, HaltPacket, union packet, or polymorphic halt hierarchy, and no isinstance-based generic halt acceptance.
- Future implementation must use exact type checks only — `type(x) is BlockedPacket` and `type(x) is NoEligibleHaltPacket` — never a shared base, union, or isinstance branch.

## 3. No cross-conversion

- BlockedPacket must not be converted, downgraded, translated, wrapped, or re-emitted as NoEligibleHaltPacket.
- NoEligibleHaltPacket must not be converted, upgraded, translated, wrapped, or re-emitted as BlockedPacket.
- CONTRACT_VIOLATION must not become NO_ELIGIBLE.
- NO_ELIGIBLE must not become BLOCKED, CONTRACT_VIOLATION, OBSERVED, ELIGIBLE, or success.

## 4. Bypass / halt behavior

- BlockedPacket bypasses calculator/net-edge/friction/trading/reporting-economic paths as a fail-closed error halt.
- NoEligibleHaltPacket bypasses calculator/net-edge/friction/trading/reporting-economic paths as a non-error no-candidate halt.
- Both may only be routed toward a future non-economic reporting/output boundary.
- Neither may call or imply net-edge calculation.
- Neither may trigger parser/loader/artifact reader/endpoint/paper/live runner behavior.

## 5. Unknown input behavior

- An unknown object, raw dict, generic Mapping, arbitrary object, subclass, or attribute-guessed record is not NO_ELIGIBLE.
- Unknown input is a contract/integration misuse path.
- Future implementation must reject it with a strict TypeError/contract-violation-style error or fail-closed boundary violation, and must not mask it as NoEligibleHaltPacket.
- There must be no str/repr/introspection of the unknown object; any rejection message may use only `type(obj).__name__` or a fixed phrase.

## 6. No coercion

- Halt carriers must never be coerced into bool, int, float, str, bytes, None, empty, zero, false, default, eligible=false, edge=0, cost=0, net_edge=0, gross_edge=0, no-op success, or calculator input.
- Future implementation must not call bool(), len(), int(), float(), str(), bytes(), repr(), or equality on halt carrier payloads.
- It must preserve the anti-truthiness/anti-coercion guarantees already defined for each carrier.

## 7. Pass-through identity

- An exact BlockedPacket input must be returned/carried identically if routed to the blocked halt output.
- An exact NoEligibleHaltPacket input must be returned/carried identically if routed to the no-eligible halt output.
- There must be no mutation, downgrade, upgrade, wrapping, copying, enrichment, repair, inference, or field rewriting of a carried halt signal.

## 8. Success-path continuity

- If the future integration boundary receives a valid non-halt actionable payload type, it must pass it through identically to the later calculator-eligible path.
- It must not mutate, coerce, parse, enrich, repair, infer, or attach economic meaning to that payload.
- The exact actionable payload type and calculator input schema are deferred to a later calculator/input-boundary task.
- This planning task must not define the eligible payload schema, and defines no calculator input schema here.

## 9. No claims / no authorization

- The boundary asserts no source truth, data quality, data integrity, source reliability, safety, readiness, profitability, alpha, edge, net-edge, execution, trading, or paper/live property.
- The boundary authorizes no net-edge calculator, no friction engine, no trading, no reporting runtime, no paper/live readiness, and no next-component implementation.

## 10. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 11. Future implementation gate

- Any implementation requires separate explicit authorization, failing tests first, declared provenance, component-scoped work, and offline/TDD scope.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future boundary, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no PnL, net-edge, or economic-inference figure;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 12. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact integration-boundary function signature and routing-output names.
- exact non-halt actionable payload type and the calculator input schema.
- exact non-economic reporting/output boundary that consumes routed halt carriers.
- exact test boundary between contract tests and implementation tests.
- production/live usage deferred until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes no edge, no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no alpha, no live readiness, no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. This is a component planning gate only; it authorizes a separately approved
offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 13. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `phase5_halt_propagation_integration_boundary` may follow, with failing tests first and declared
  evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
