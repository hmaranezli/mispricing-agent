# Phase 5 Fail-Closed Blocked-State Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract only** — it is **offline, fail-closed behavior contract only**. It
follows the [Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §7
("Fail-closed behavior contract") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract specifies how missing, unknown, or mismatched evidence **must** be represented. It:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a calculator, a cost model, or a net-edge calculation;
- **must not** connect to any live order path or execution path;
- **is not** a readiness verdict, **is not** a safety guarantee, **is not** a data-quality guarantee,
  and **is not** a data-integrity guarantee;
- **is not a mathematical proof** and reaches no economic inference.

**Implementation still requires separate TDD and explicit authorization.** This contract authorizes
no Phase 5 implementation; any future implementation must be separately authorized and TDD/offline
first.
<!-- FRAMING-END -->

## 1. Canonical blocked status

- **BLOCKED_NEEDS_EVIDENCE is the canonical blocked status** for missing, unknown, or mismatched evidence across all Phase 5 contracts.
- Blocked status **must** be a **deterministic state** produced by an explicit decision rule. It is
  **not an exception-handling escape hatch**, not a caught error, and not a silent fallback.

## 2. Dependent contracts

This contract is the shared fail-closed behavior for the existing Phase 5 contracts. Each routes its
missing/unknown/mismatched evidence into a blocked-state record defined here:

- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md)
- [`phase5_artifact_provenance_contract.md`](phase5_artifact_provenance_contract.md)

## 3. Blocked status must not be downgraded

- A blocked status **must not be converted into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input**.
- Blocked is not a quiet default: absence of evidence **must** surface as `BLOCKED_NEEDS_EVIDENCE`,
  never as a permissive value.

## 4. Required blocked-state record fields

Every blocked-state record **must** declare all of the following fields:

- `blocked_status` — the canonical status (`BLOCKED_NEEDS_EVIDENCE`).
- `blocked_reason` — one of the blocked reason categories (see §5).
- `blocked_source_contract` — the contract that raised the block (friction / no-eligible / provenance).
- `missing_or_invalid_field` — the specific field that is missing or invalid.
- `source_artifact_or_blocked_reason` — the source artifact path, **or** an explicit blocked reason.
- `source_field_or_blocked_reason` — the source field, **or** an explicit blocked reason.
- `deterministic_next_action` — the deterministic next action the decision path must take.
- `human_review_required: true | false` — whether human review is required.
- `may_retry_after_evidence: true | false` — whether retry is permitted once evidence arrives.
- `created_utc_timestamp_ms_or_blocked_reason` — creation UTC timestamp in ms, **or** an explicit blocked reason.

## 5. Required blocked reason categories

`blocked_reason` **must** be one of:

- `missing_provenance`
- `unknown_artifact_source`
- `source_field_mismatch`
- `missing_component`
- `missing_formula`
- `missing_numeric_representation`
- `missing_no_eligible_accounting`
- `missing_timestamp`
- `missing_verifier_result`
- `unsupported_artifact_type`
- `implementation_not_authorized`

## 6. Context preservation without fabrication

- A blocked output **must preserve** the provenance and accounting context that is available (e.g. a
  partial `source_artifact`, observed counts) so the block is auditable.
- A blocked output **must not invent missing fields**. Absent evidence stays absent and is recorded
  as a blocked reason, never filled with a placeholder value.

## 7. Blocked is terminal for the current path

- A blocked output is **terminal for the current deterministic decision path** until evidence or
  authorization changes. The path **must** stop and **must not** continue downstream on a block.
- A blocked output **must not authorize execution, trading, readiness, profitability, edge, net-edge, or paper/live progression**.

## 8. Retry only on new evidence or authorization

- Retry is permitted **only** when **new evidence or explicit authorization** is present. A retry
  without new evidence/authorization **must not** occur.
- Any retry path **must** remain **TDD/offline first**; it builds no live or trading path.

## 9. Human review does not substitute for evidence

- A blocked-state record may set `human_review_required: true`, but **human review alone must not convert blocked evidence into observed/derived without source evidence**.
- **Human/operator judgment must not substitute for source_artifact/source_field evidence.** Review
  may authorize a separate evidence-gathering step; it **must not** itself supply the missing value.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

A blocked-state record, and this contract, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 10. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact blocked-state record serialization.
- exact deterministic_next_action vocabulary.
- exact human_review_required policy.
- exact retry policy and retry evidence requirements.
- exact verifier integration for BLOCKED_NEEDS_EVIDENCE.
- exact mapping from provenance/no-eligible/friction failures into blocked reasons.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no economic inference. It is
not a mathematical proof and does not guarantee correctness. A blocked state is a deterministic
contract state only; implementing or interpreting it requires separately authorized, evidence-backed,
TDD/offline work.
<!-- NO-CLAIMS-END -->

## 11. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 implementation task** may follow, with
  failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
