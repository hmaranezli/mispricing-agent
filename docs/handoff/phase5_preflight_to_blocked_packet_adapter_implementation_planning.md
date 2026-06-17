# Phase 5 Component Implementation-Planning — `phase5_preflight_to_blocked_packet_adapter`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It defines only the planned adapter boundary,
the deterministic status mapping, the explicit field map, and the prohibitions for a future,
separately authorized offline/TDD implementation task.

- `component_name`: `phase5_preflight_to_blocked_packet_adapter`.
- The adapter converts only **blocked** or **contract-violation** `phase5_input_provenance_preflight`
  results into a `BlockedPacket`. It is a **format-boundary adapter only**.
- It must not validate, parse, repair, enrich, infer, downgrade, or interpret source data.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Scope and dependencies

This adapter sits between two already-implemented components and depends on, and must remain
consistent with:

- [`phase5_input_provenance_preflight` planning artifact](phase5_input_provenance_preflight_implementation_planning.md)
- [`phase5_blocked_result_boundary` planning artifact](phase5_blocked_result_boundary_implementation_planning.md)
- [`phase5_fail_closed_blocked_state_contract.md`](../protocols/phase5_fail_closed_blocked_state_contract.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

It is a **format-boundary adapter only**. It must not validate, parse, repair, enrich, infer,
downgrade, or interpret source data.

## 2. Success-path rejection

- A PLANNING_GATE_OBSERVED or success-like preflight result must not be converted into a BlockedPacket.
- The adapter must require fail-closed rejection for any success-path adapter use.
- If the later adapter implementation is invoked with a `PLANNING_GATE_OBSERVED` or any success-like
  preflight result, the later adapter implementation must raise a programmatic misuse error.
- It must never return None, never return an empty/default packet, and never silently pass.

## 3. Deterministic 1:1 status mapping

- The three preflight statuses are `PLANNING_GATE_OBSERVED`, `PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE`,
  and `PLANNING_GATE_CONTRACT_VIOLATION`.
- PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE maps to a BlockedPacket with blocked/evidence-needed semantics.
- PLANNING_GATE_CONTRACT_VIOLATION maps to a BlockedPacket with contract-violation semantics.
- No downgrade from CONTRACT_VIOLATION to BLOCKED.
- No upgrade from BLOCKED to OBSERVED.
- No default/empty/false/zero conversion.

## 4. Origin stamp

- origin_component must be phase5_input_provenance_preflight.
- component_name must identify the adapter/boundary result consistently.
- Source contract/artifact/field values must be carried from declared preflight result fields only.

## 5. Explicit source → destination field map

Mapping must be explicit; no arbitrary dict parsing, no attribute introspection, no heuristic key guessing.

**Source fields required from the preflight result** (`PreflightResult`):

- `status`
- `blocked_status`
- `blocked_reason`
- `missing_or_invalid_field`
- `source_contract`
- `source_artifact`
- `source_field`
- `deterministic_next_action`
- `human_review_required`
- `may_retry_after_evidence`

**Destination `BlockedPacket` fields:**

- `component_name` — set to the adapter/boundary identifier (constant).
- `origin_component` — set to `phase5_input_provenance_preflight` (constant).
- `origin_result_status` — carried from the preflight `status`.
- `status` — carried from the preflight `status`.
- `blocked_status` — carried from the preflight `blocked_status`.
- `reason_code` — carried from the preflight `blocked_reason`.
- `missing_or_invalid_field` — carried from the preflight `missing_or_invalid_field`.
- `source_contract` — carried from the preflight `source_contract`.
- `source_artifact` — carried from the preflight `source_artifact`.
- `source_field` — carried from the preflight `source_field`.
- `deterministic_next_action` — carried from the preflight `deterministic_next_action`.
- `human_review_required` — carried from the preflight `human_review_required`.
- `may_retry_after_evidence` — carried from the preflight `may_retry_after_evidence`.
- `created_from_contract` — set to this adapter planning artifact reference (constant).
- `boundary_version` — set to the adapter boundary version (constant).

## 6. Strict input type

- The later adapter implementation must accept only the explicit typed/frozen PreflightResult emitted by phase5_input_provenance_preflight.
- It must reject raw dicts, generic Mapping, arbitrary objects, or attribute-guessed records.
- No ad-hoc key guessing or object introspection is allowed.

## 7. Adapter boundary

- The adapter may call make_blocked_packet only in a later implementation slice.
- It must not construct parser/loader/verifier/SHA256/artifact-reader behavior.
- It must not consume raw market records or source artifacts.
- It must not inspect values for market truth/data quality/source reliability/economic meaning.

## 8. NO_ELIGIBLE exclusion

- This adapter must not handle NO_ELIGIBLE or economic/business-ineligibility states.
- NO_ELIGIBLE is a separate later boundary and must not be encoded as a BlockedPacket.

## 9. Anti-claim continuity

- The adapter asserts no source truth, data quality, source reliability, profitability, readiness, safety, edge, net-edge, execution, or trading property.
- The adapter authorizes no downstream calculation or next component.

## 10. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 11. Future implementation gate

- Any implementation requires separate explicit authorization, failing tests first, declared provenance, component-scoped work, and offline/TDD scope.
- This planning artifact does not authorize implementation or selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future adapter, must produce **none** of:

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

- exact adapter API surface and misuse-error type rendering.
- exact `boundary_version` and `created_from_contract` value syntax.
- exact reason-code carry rules for each carried status.
- exact test boundary between contract tests and implementation tests.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes no edge, no PnL, no paper readiness, no economics readiness, no execution readiness, no profitability, no alpha, no live readiness, no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It is not a
mathematical proof and does not guarantee correctness. This is a component planning gate only; it
authorizes a separately approved offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 13. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `phase5_preflight_to_blocked_packet_adapter` may follow, with failing tests first and declared
  evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
