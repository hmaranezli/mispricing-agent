# Phase 5 Component Implementation-Planning — `phase5_input_provenance_preflight`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is the first
component-scoped implementation-planning artifact, produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It defines only the acceptance criteria, blocked
behavior, source contracts, source artifacts, source fields, and required failing-test plan for a
future, separately authorized offline/TDD implementation task.

- `component_name`: `phase5_input_provenance_preflight`.
- This component **does not validate market truth, data quality, economic validity, profitability, readiness, or source reliability**.
- This component **only checks declared input shape and provenance requirements before any downstream Phase 5 component may be planned**.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Source contracts

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
- [`phase5_input_schema_refinement_contract.md`](../protocols/phase5_input_schema_refinement_contract.md)
- [`phase5_artifact_provenance_contract.md`](../protocols/phase5_artifact_provenance_contract.md)
- [`phase5_fail_closed_blocked_state_contract.md`](../protocols/phase5_fail_closed_blocked_state_contract.md)
- [`phase5_no_claims_reporting_schema_contract.md`](../protocols/phase5_no_claims_reporting_schema_contract.md)
- [`phase5_offline_fixture_contract.md`](../protocols/phase5_offline_fixture_contract.md)
- [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md)

## 2. Entry packet

The future implementation-planning entry packet for this component declares all of:

- `component_name` — `phase5_input_provenance_preflight`.
- `source_contracts` — the §1 list.
- `source_artifacts` — declared read-only provenance references (no artifact is parsed here).
- `source_fields` — declared fields mapped to their source contracts.
- `required_input_schema_fields` — the input-schema categories/fields the preflight expects as shape.
- expected observed/derived/blocked outputs — the deterministic status outputs (see §4).
- `blocked_reason` mapping — blocked reasons for each fail condition.
- `deterministic_next_action` — the deterministic next action on block.
- required failing tests — the failing-test plan a future task must write first.
- no-claims/reporting boundary — the reporting boundary this component must preserve.
- proof that no execution/trading authority is introduced — an explicit non-authority statement.

## 3. Planned input checks

A future implementation of this component is planned to check (declaration-level only; no parsing):

- record identity fields are declared.
- provenance fields are declared.
- source_contract is known and allowed.
- source_artifact is declared as a read-only provenance reference.
- source_field is declared and mapped to the source contract.
- required input-schema categories are present as shape declarations.
- blocked semantics are declared for missing/unknown/mismatched evidence.
- source_sha256_or_blocked_reason is declared for the source artifact.
- parser_version_or_blocked_reason is declared.
- verifier_result_or_blocked_reason is declared.

If `source_sha256`, `parser_version`, or `verifier_result` are not implemented, they **must be explicit blocked fields with blocked reasons, not omitted**.

### Chain-break fail conditions

The plan defines **chain-break fail conditions** for: missing source_artifact, unknown source_artifact, missing source_field, source_field mismatch, missing source_sha256_or_blocked_reason, missing parser_version_or_blocked_reason, and missing verifier_result_or_blocked_reason.

## 4. Deterministic status mapping

- evidence present within checked scope → `PLANNING_GATE_OBSERVED`.
- missing or unknown source_artifact/source_field/source_contract evidence → `PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE`.
- missing source_sha256_or_blocked_reason, parser_version_or_blocked_reason, or verifier_result_or_blocked_reason → `PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE`.
- malformed field declaration, forbidden field mapping, unsupported source contract assertion, or claim that planning authorizes implementation → `PLANNING_GATE_CONTRACT_VIOLATION`.
- claiming source truth, data validity, source reliability, or data-quality/data-integrity guarantee → `PLANNING_GATE_CONTRACT_VIOLATION`.

`BLOCKED_NEEDS_EVIDENCE` remains canonical for missing/unknown/mismatched evidence.

## 5. No silent defaults

- Missing/malformed/unknown/mismatched fields **must not become zero, false, pass, default, floor, baseline, assumed, guessed, eligible, executable, tradable, ready, profitable, or net-edge input**.

## 6. No-claims continuity

- This component planning artifact **must not output or imply alpha, PnL, edge, net-edge, profitability, readiness, trading instruction, execution authority, safety guarantee, data-quality guarantee, data-integrity guarantee, or source-truth guarantee**.

## 7. Fixture boundary

- **Future tests must use static offline diagnostic fixtures only.**
- **No fixture generator/factory/loader/parser.**

## 8. Later implementation requirements

- **Any later implementation of this component requires separate explicit authorization, failing tests first, declared provenance, and offline/TDD scope.**

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This planning artifact, and the future component, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no PnL, net-edge, or economic-inference figure;
- no source-truth, data-quality, or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 9. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- exact preflight serialization and status rendering.
- exact source_field declaration syntax.
- exact required failing-test list for the future implementation task.
- exact blocked_reason vocabulary mapping for chain-break conditions.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes **no edge, no PnL, no paper readiness, no economics readiness, no
execution readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. This is a
component planning gate only; it authorizes a separately approved offline/TDD implementation task, not
implementation.
<!-- NO-CLAIMS-END -->

## 10. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `phase5_input_provenance_preflight` may follow, with failing tests first and declared evidence
  provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
