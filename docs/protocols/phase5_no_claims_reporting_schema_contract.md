# Phase 5 No-Claims / Reporting Schema Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract/planning artifact only, not implementation**. It is **offline,
reporting output-vocabulary contract only**. It follows the
[Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §6
("Reporting / no-claims schema") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract defines reporting/output vocabulary and reporting boundaries. It:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a calculator, a cost model, a net-edge aggregation, or a friction engine;
- **must not** connect to any live order path or execution path (no execution connection);
- **is not** a safety guarantee, **is not** a data-quality guarantee, and **is not** a data-integrity
  guarantee;
- **is not a mathematical proof** and reaches no economic inference.

This contract defines the reporting/output-vocabulary slice only. Remaining Phase 5 gaps still
require separate authorization. Implementation still requires separate TDD and explicit
authorization.
<!-- FRAMING-END -->

## 1. Scope — output vocabulary only

- The reporting schema is **output-vocabulary only**: it bounds *how* Phase 5 states may be reported.
  It **does not authorize computation, aggregation, execution, trading, or readiness**.
- Reporting describes evidence states; it produces no new value and reaches no economic conclusion.

## 2. Dependent contracts

This reporting contract bounds the output of, and depends on, the existing Phase 5 contracts:

- [`phase5_interface_contract.md`](phase5_interface_contract.md)
- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md)
- [`phase5_artifact_provenance_contract.md`](phase5_artifact_provenance_contract.md)
- [`phase5_fail_closed_blocked_state_contract.md`](phase5_fail_closed_blocked_state_contract.md)
- [`phase5_observation_discovery_cost_schema_contract.md`](phase5_observation_discovery_cost_schema_contract.md)

## 3. Allowed reporting states

A `report_status` **must** be one of:

- `observed` — an evidence-backed observed value with a source chain.
- `derived` — a derived value with an explicit source chain.
- `blocked` — a blocked state with a blocked reason.
- **BLOCKED_NEEDS_EVIDENCE as the canonical blocked status** when evidence is missing, unknown, or mismatched.

## 4. Required reporting-record fields

Every reporting record **must** declare all of the following fields:

- `report_schema_version` — the reporting schema version.
- `report_scope` — the scope of the report (which contract slice / observation).
- `report_status` — one of the allowed reporting states (see §3).
- `source_contract` — the originating Phase 5 contract.
- `source_artifact_or_blocked_reason` — the source artifact path, **or** an explicit blocked reason.
- `source_field_or_blocked_reason` — the source field, **or** an explicit blocked reason.
- `provenance_status` — provenance classification (observed / derived / blocked).
- `observed_or_derived_value_or_blocked_reason` — the observed/derived value, **or** a blocked reason.
- `blocked_reason_if_any` — the blocked reason when status is blocked.
- `deterministic_next_action_if_blocked` — the deterministic next action when blocked.
- `no_claims_block_present` — whether the report carries the no-claims block (must be true).
- `created_utc_timestamp_ms_or_blocked_reason` — creation UTC timestamp in ms, **or** a blocked reason.

## 5. Blocked reports emit no synthetic values

- When status is `blocked` or `BLOCKED_NEEDS_EVIDENCE`, the report **must** output only the blocked
  reason, source/provenance context, and deterministic next action.
- A blocked report **must not output derived estimates, fallback values, zero values, or guessed values**.

## 6. No conversion into unauthorized claims

- Reports **must not convert observed/derived/blocked states into alpha, PnL, edge, profitability, readiness, paper readiness, live readiness, execution authority, trading instruction, net-edge, economic inference, safety guarantee, data-quality guarantee, or data-integrity guarantee**.
- Reports **may state only evidence-backed observations, derived values with explicit source chain, or blocked status with blocked reason**.

## 7. No-claims block and framing required

- **Every future Phase 5 report must carry the no-claims block** and sample-only / **contract-planning framing**.
- A report that omits the no-claims block is not a valid Phase 5 report.

## 8. Human review does not convert blocked

- **Human review must not convert blocked evidence into observed or derived reporting.** Operator
  judgment may authorize a separate evidence step; it **must not** itself supply the missing value.

## 9. Fail-closed reporting

- **Missing no-claims block, missing provenance context, unknown source contract, or forbidden claim wording must fail closed** to `BLOCKED_NEEDS_EVIDENCE` or a contract violation, as appropriate.
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

A Phase 5 report, and this contract, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no PnL, net-edge, or economic-inference figure;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 10. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact report record serialization.
- exact report_schema_version policy.
- exact source_contract vocabulary.
- exact allowed human-readable summary template.
- exact verifier integration for forbidden reporting claims.
- exact blocked-report rendering policy.
- exact aggregation/report composition policy if multiple records include mixed observed/derived/blocked states.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. A reporting
record is an output-vocabulary contract state only; implementing or rendering it requires separately
authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 11. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 task** may follow, with failing tests
  first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
