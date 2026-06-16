# Phase 5 Artifact Provenance Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract only** — it is **offline, chain-of-custody / evidence-contract
only**. It follows the [Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and
refines §5 ("Artifact provenance schema") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

Provenance is **chain-of-custody** recording, not a quality verdict. This contract:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a calculator, a cost model, or a net-edge calculation;
- **must not** connect to any live order path or execution path;
- **is not** a data-quality guarantee, **is not** a data-integrity guarantee, and **is not** a
  safety guarantee;
- **defines** the provenance fields and fail-closed rules a future component must record;
- **is not a mathematical proof** and assigns no economic meaning to any provenance record.

**Implementation still requires separate TDD and explicit authorization.** This contract authorizes
no Phase 5 implementation; any future implementation must be separately authorized and TDD/offline
first.
<!-- FRAMING-END -->

## 1. Purpose — provenance gates evidence status

- **Provenance is required before any** Phase 5 observed or derived status may be accepted. No input
  becomes `observed` or `derived` without a complete provenance record.
- Provenance must link every Phase 5 input back to **evidence, not assumptions**: a concrete
  `source_artifact` and `source_field`, never a remembered or hand-entered number.
- This contract is a chain-of-custody / evidence-contract artifact only. It records *where evidence
  came from*; it computes nothing and asserts no quality of that evidence.

## 2. Dependent contracts

Both existing Phase 5 contracts depend on this provenance contract for their `source_artifact` /
`source_field` chain:

- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md)

Each component or state in those contracts **must** carry a provenance record satisfying §3 before it
may leave `blocked`.

## 3. Required provenance fields

Every Phase 5 provenance record **must** declare all of the following fields:

- `source_artifact` — the read-only artifact path the value comes from.
- `source_field` — the exact field within `source_artifact`.
- `artifact_type` — one of the valid artifact types (see §4).
- `artifact_phase` — one of the valid artifact phases (see §5).
- `batch_id` — the batch identifier.
- `run_id` — the run identifier within the batch.
- `observation_id` — the repeatability observation identifier.
- `stage_name` — the producing stage (e.g. `phase4a_analyzer`).
- `verdict_or_status` — the observed verdict/status label recorded by the source stage.
- `utc_timestamp_ms_or_blocked_reason` — source UTC timestamp in ms, **or** an explicit blocked reason.
- `request_count_or_blocked_reason` — observed mechanical request count, **or** an explicit blocked reason.
- `source_sha256_or_blocked_reason` — content hash of the source artifact, **or** an explicit blocked reason.
- `parser_version_or_blocked_reason` — version of the parser that read the artifact, **or** an explicit blocked reason.
- `verifier_result_or_blocked_reason` — evidence-verifier result for the source, **or** an explicit blocked reason.
- `blocked_reason_if_missing` — explicit blocked reason when any required evidence is absent.

## 4. Valid artifact_type values

`artifact_type` **must** be one of:

- `json`
- `jsonl`
- `manifest`
- `summary`
- `audit_doc`
- `protocol_doc`
- `test_report`

## 5. Valid artifact_phase values

`artifact_phase` **must** be one of:

- `phase3d5`
- `phase4a`
- `phase4b`
- `phase4c`
- `phase5_contract`

## 6. Fail-closed behavior (zero-trust stance)

This contract takes a **zero-trust** stance toward inputs: no input is accepted on assumption; every
input **must** carry provenance. This is contract language only — it claims **no security guarantee,
no correctness guarantee, no data-integrity guarantee, and no data-quality guarantee**.

The following **must** each yield `BLOCKED_NEEDS_EVIDENCE`:

- **Missing required provenance** — any required §3 field absent.
- **Unknown artifact source** — `source_artifact` does not resolve to a known read-only artifact.
- **Source field mismatch** — `source_field` is absent from, or inconsistent with, `source_artifact`.

Phase 5 **must not** use **hand-entered values** without a **source_artifact/source_field chain**.

## 7. Status classification only

- Provenance **may only classify evidence status as observed | derived | blocked**. It assigns no
  numeric value and reaches no economic conclusion.
- Provenance **must not authorize execution, trading, readiness, profitability, or net-edge calculation**.

## 8. Not-yet-implemented fields stay explicit

- If `source_sha256`, `parser_version`, or `verifier_result` are not yet implemented, they **must**
  be recorded as **explicit blocked fields, not omitted** (i.e. `source_sha256_or_blocked_reason`
  carries a blocked reason, never silence).
- An omitted required field is **not** equivalent to a blocked field; omission **must** be treated as
  `BLOCKED_NEEDS_EVIDENCE`.

## 9. No live execution connection

- This contract defines **no live order** path and **no execution connection**. It connects to no
  CLOB client, no order intent, no council execution authority, and no trading path.
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any artifact that claims to satisfy it, must produce **none** of:

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

- exact source_sha256 generation method.
- exact parser_version naming/versioning scheme.
- exact verifier_result vocabulary.
- manifest-to-artifact join rules.
- source_field path syntax.
- handling for missing timestamps.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee, no data-quality
guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready claim** of any
kind. It asserts no statistical significance, no stationarity proof, and no economic inference. It is
not a mathematical proof and does not guarantee correctness. Provenance is chain-of-custody recording
only; recording or interpreting it requires separately authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 11. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 implementation task** may follow, with
  failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
