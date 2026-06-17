# Phase 5 Input-Schema Refinement Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract/planning artifact only, not implementation**. It is **offline,
input-shape contract only**. It follows the
[Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §1
("Gross-edge input schema") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract defines the allowed shape and required provenance of future Phase 5 inputs. It:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** prove correctness, **must not** verify truth, and **must not** authorize computation;
- **must not** build a calculator, a cost model, a net-edge aggregation, a friction engine, or a
  parser/loader/fixture engine;
- **must not** connect to any live order path or execution path (no execution connection);
- **is not** a safety guarantee, **is not** a data-quality guarantee, and **is not** a data-integrity
  guarantee.

This contract defines the input-schema refinement slice only. Remaining Phase 5 gaps still require
separate authorization. Implementation still requires separate TDD and explicit authorization. Input
schema is defined before the offline fixture contract so fixtures know which shape they represent.
<!-- FRAMING-END -->

## 1. Scope — shape only

- The input schema **describes shape only**. It bounds the categories and fields a future Phase 5
  input may carry; it computes nothing and proves nothing.
- **Input presence must not be treated as evidence quality, source truth, readiness, or economic validity.**
  A field being present says nothing about whether its value is correct, sourced, or usable.

## 2. Dependent contracts

This input contract depends on, and must remain consistent with:

- [`phase5_interface_contract.md`](phase5_interface_contract.md)
- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md)
- [`phase5_artifact_provenance_contract.md`](phase5_artifact_provenance_contract.md)
- [`phase5_fail_closed_blocked_state_contract.md`](phase5_fail_closed_blocked_state_contract.md)
- [`phase5_observation_discovery_cost_schema_contract.md`](phase5_observation_discovery_cost_schema_contract.md)
- [`phase5_no_claims_reporting_schema_contract.md`](phase5_no_claims_reporting_schema_contract.md)

## 3. Required input categories

A future Phase 5 input record **must** separate fields into these categories:

- `record_identity`
- `gross_edge_fields`
- `eligibility_state`
- `no_eligible_state`
- `friction_component_placeholders`
- `mechanical_observation_metadata`
- `provenance_fields`
- `reporting_boundary_fields`
- `blocked_state_fields`

## 4. Required record_identity fields

`record_identity` **must** declare: `input_schema_version`, `input_record_type`, `batch_id`,
`run_id`, `observation_id`, and `source_contract`.

## 5. Required provenance fields

`provenance_fields` **must** declare: `source_artifact`, `source_field`,
`artifact_type_or_blocked_reason`, `artifact_phase_or_blocked_reason`, `provenance_status`,
`source_sha256_or_blocked_reason`, `parser_version_or_blocked_reason`, and
`verifier_result_or_blocked_reason`.

## 6. Gross-edge fields are read-only

- `gross_edge_fields` **must** be consumed as read-only descriptive inputs from prior audited /
  sample-only artifacts.
- They **must not be recomputed, refreshed, fetched, or treated as live data** by this contract.

## 7. Eligibility and no-eligible states

- `eligibility_state` and `no_eligible_state` **must** represent eligible, ineligible, and
  no-eligible states **explicitly**.
- **no-eligible must not be converted into error, zero value, opportunity cost, idle cost, profitability evidence, or readiness signal.**

## 8. Friction component placeholders are non-value

- `friction_component_placeholders` are **non-value placeholders only**.
- A friction component placeholder **must not be represented as 0, null, false, empty string, default value, floor value, baseline value, assumed value, guessed value, or usable numeric input**.
- Each placeholder **must** carry either an explicit blocked reason / `BLOCKED_NEEDS_EVIDENCE` state,
  or a future separately authorized `source_artifact`/`source_field` chain.
- Placeholder presence **must not be treated as cost evidence, zero cost, usable friction value, net-edge input, economic inference, readiness evidence, or implementation authority**.
- If a placeholder lacks required blocked/provenance context, the input schema **must fail closed** to
  `BLOCKED_NEEDS_EVIDENCE` or contract violation as appropriate.

### 8a. Placeholder semantics

- Friction component placeholders **must define explicit non-value placeholder semantics**. Example
  labels may include `PENDING_SOURCE_FIELD` or `BLOCKED_PLACEHOLDER`, but the exact vocabulary remains
  a deferred contract decision unless pinned by a separate authorized task.
- A placeholder **must be non-computable**. Future implementation **must not consume a placeholder as a numeric, boolean, empty, default, floor, baseline, assumed, guessed, or usable friction value**.
- If a future computation path encounters an unresolved placeholder, the permitted contract outcome is
  `BLOCKED_NEEDS_EVIDENCE` or contract violation; it **must not silently impute, coerce, cast, or default the value**.
- **Placeholder resolution requires a separate explicitly authorized TDD/offline task with evidence provenance.**

## 9. Mechanical observation metadata stays separate

- `mechanical_observation_metadata` **must** remain separate from market-content observations.
- It **must not be converted into dollars, bps, edge, net-edge, profitability, readiness, idle cost, opportunity cost, or any cost figure**.

## 10. Reporting boundary fields

- `reporting_boundary_fields` **must** preserve the `observed/derived/blocked` vocabulary and **must
  not** authorize unauthorized claims (per the no-claims/reporting contract).

## 11. Fail-closed input behavior

- **Missing/malformed/unknown input fields, missing provenance, unknown source contract, source-field mismatch, or forbidden claim wording must fail closed** to `BLOCKED_NEEDS_EVIDENCE` or contract violation as appropriate.
- A blocked input **must not be downgraded into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input**.
- **Human/operator review must not substitute for source_artifact/source_field evidence.**
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any input that claims to satisfy it, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no PnL, net-edge, or economic-inference figure;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 12. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact input record serialization.
- exact input_schema_version policy.
- exact input_record_type vocabulary.
- exact source_contract vocabulary.
- exact source_field path syntax.
- exact gross-edge field allowlist from audited artifacts.
- exact blocked-input rendering policy.
- exact non-value placeholder serialization for friction component placeholders.
- exact rule for distinguishing placeholder, blocked, observed, and derived input fields.
- exact fixture shape to be handled by the later offline fixture contract.
- verifier integration for malformed/missing/unknown input fields.
- exact placeholder vocabulary, including whether labels like PENDING_SOURCE_FIELD or BLOCKED_PLACEHOLDER are canonical.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. An input
record is a shape contract only; populating, parsing, or interpreting it requires separately
authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 13. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 task** may follow, with failing tests
  first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
