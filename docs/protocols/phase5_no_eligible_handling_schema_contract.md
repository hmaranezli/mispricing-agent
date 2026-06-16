# Phase 5 No-Eligible Handling Schema Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract only** — it is **offline, observation and evidence-contract only**.
It follows the [Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §3
("No-eligible handling schema") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

A no-eligible result is an **observed state, not a calculation**. This contract:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a calculator, a cost model, an idle-cost model, or an opportunity-cost model;
- **must not** connect to any live order path or execution path;
- **defines** the observed-state shape and provenance a future component must record;
- **is not a mathematical proof** and assigns no economic meaning to a no-eligible state.

**Implementation still requires separate TDD and explicit authorization.** This contract authorizes
no Phase 5 implementation; any future implementation must be separately authorized and TDD/offline
first.
<!-- FRAMING-END -->

## 1. Scope — no-eligible is a state

- A no-eligible result is an **observed state, not a calculation**. It records *that* a run produced
  zero eligible records, with provenance — it computes nothing.
- A no-eligible state **must not update edge, net-edge, profitability, readiness, or trading authority**.
  It **may record observation and discovery accounting and provenance only**.
- A no-eligible state is **not** an idle-cost, **not** an opportunity-cost, and **not** a
  profitability/readiness inference.

## 2. Provenance anchor — Phase 4C Observation #3

This contract is anchored to the observed no-eligible evidence from Phase 4C Observation #3
(read-only, already audited):

- batch_id `phase4c_batch_1781637248`.
- Phase 4A verdict `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS`; `eligible_pairs=0`.
- Phase 4B verdict `PHASE4B_NO_ELIGIBLE_RECORDS`.
- ineligible reasons observed: `ONE_SIDED_BOOK` and `SPREAD_TOO_WIDE`.

These are observed labels from that run; they assert no tradeable property and no economic value.

## 3. Required no-eligible state fields

A future no-eligible state record **must** declare all of the following fields:

- `state_name` — the no-eligible state category (see §4).
- `status` — one of `observed | blocked`.
- `source_artifact` — the read-only artifact the state is observed from.
- `source_field` — the exact field within `source_artifact`.
- `observation_id` — the repeatability observation identifier (e.g. observation #3).
- `batch_id` — the batch identifier (e.g. `phase4c_batch_1781637248`).
- `run_id` — the run identifier within the batch.
- `candidate_pairs` — observed candidate/complement pair count.
- `eligible_pairs` — observed eligible pair count (e.g. `0`).
- `ineligible_reasons` — observed ineligible reason histogram (e.g. `ONE_SIDED_BOOK`, `SPREAD_TOO_WIDE`).
- `request_count` — observed mechanical request count.
- `discovery_requests` — observed discovery request count.
- `book_requests` — observed book request count.
- `deterministic_interpretation` — the deterministic, evidence-backed reading of the observed state.
- `blocked_reason_if_missing` — explicit blocked reason when required evidence is absent.

## 4. Valid no-eligible state categories

A no-eligible `state_name` **must** be one of:

- `spread_too_wide`
- `one_sided_book`
- `no_complement_token`
- `data_void`
- `request_cap_blocked`
- `unknown_requires_evidence`

`unknown_requires_evidence` is the fail-closed default: an unclassifiable no-eligible observation
**must** use it and **must** be treated as `blocked` until evidence supports a specific category.

## 5. Provenance and fail-closed behavior

- Every no-eligible state record **must** declare `source_artifact` and `source_field`.
- **Missing provenance** or missing accounting fields **must** yield `BLOCKED_NEEDS_EVIDENCE`.
  Provenance and accounting **must not** be inferred, defaulted, or fabricated.
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

## 6. No zero-filling

- **No zero-filling.** A run with zero eligible records **must not become cost=0, edge=0, or profitability=0**.
- Absence of eligible records is an observed state with `eligible_pairs=0`; it **must not** be
  silently converted into any numeric cost, edge, or profitability value.

## 7. No live execution connection

- This contract defines **no live order** path and **no execution connection**. It connects to no
  CLOB client, no order intent, no council execution authority, and no trading path.

## 8. Verifier language

- A no-eligible observation with complete provenance is **`VALID_EVIDENCE`** / **observed-state**
  material; it is **not a stage failure by default**.
- A no-eligible observation becomes `BLOCKED_NEEDS_EVIDENCE` only when provenance or accounting is
  missing — never as a penalty for the absence of eligible records itself.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any artifact that claims to satisfy it, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no idle-cost or opportunity-cost figure;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 9. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact representation of no-eligible state records in future implementation.
- exact verifier integration status labels.
- exact mapping from Phase 4C ineligible reasons to Phase 5 state categories.
- whether request/accounting cost joins friction schema later.
- no-eligible aggregation rules deferred.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no idle-cost, no opportunity-cost, no
system-ready, no ready-to-fly, and no ready claim** of any kind. It asserts no statistical
significance, no stationarity proof, and no economic inference. It is not a mathematical proof and
does not guarantee correctness. A no-eligible state is structural/observed only; recording or
interpreting it requires separately authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 10. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 implementation task** may follow, with
  failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
