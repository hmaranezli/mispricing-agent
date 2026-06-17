# Phase 5 Observation/Discovery Cost Schema Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract only** — it is **offline, observation/discovery representation
schema only**, and it is **contract/planning only, not implementation**. It follows the
[Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §4
("Observation/discovery cost schema") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract represents mechanical observation activity as **evidence-bearing metadata only**. It:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a calculator, a cost model, a net-edge aggregation, or a friction engine;
- **must not** connect to any live order path or execution path;
- **is not** a safety guarantee, **is not** a data-quality guarantee, and **is not** a data-integrity
  guarantee;
- **is not a mathematical proof** and reaches no economic inference.

This contract **closes only the observation/discovery cost schema slice**.
**Remaining Phase 5 gaps still require separate authorization.** Implementation still requires
separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Scope — representation only

- Observation/discovery cost is a **representation schema only**. It records *that* mechanical
  observation activity occurred (counts, stages, artifact/log counts) with provenance; it computes
  no value.
- The schema **must distinguish mechanical observation metadata from market-content observations**:
  request/discovery/book counts, stage order, and artifact/log counts are mechanical; eligibility and
  gross-edge fields are market-content and are not redefined here.

## 2. Dependent contracts

This schema depends on, and must remain consistent with:

- [`phase5_artifact_provenance_contract.md`](phase5_artifact_provenance_contract.md) — source chain.
- [`phase5_fail_closed_blocked_state_contract.md`](phase5_fail_closed_blocked_state_contract.md) — blocked behavior.
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md) — no-eligible state.
- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md) — friction taxonomy.

## 3. Required mechanical fields

Every observation/discovery record **must** declare all of the following fields:

- `request_count` — observed total request count.
- `discovery_requests` — observed discovery request count.
- `book_requests` — observed book request count.
- `stage_order` — observed stage order (mechanical sequence).
- `artifact_count` — observed artifact count.
- `log_count` — observed log count.
- `candidate_pairs` — observed candidate/complement pair count.
- `eligible_pairs` — observed eligible pair count.
- `ineligible_reasons` — observed ineligible reason histogram.
- `batch_id` — the batch identifier.
- `run_id` — the run identifier within the batch.
- `observation_id` — the repeatability observation identifier.
- `source_artifact` — the read-only artifact the counts are observed from.
- `source_field` — the exact field within `source_artifact`.
- `provenance_status` — provenance classification (observed / blocked).
- `blocked_reason_if_missing` — explicit blocked reason when required evidence is absent.

## 4. Audited Phase 4C observation anchors

These audited mechanical facts (sample-only diagnostic counts) are used **only as doc-contract
constants**, never as generated artifacts or runtime fixtures:

- obs #1: request_count 12, discovery_requests 4, book_requests 8, eligible_pairs 4.
- obs #2: request_count 12, discovery_requests 4, book_requests 8, eligible_pairs 4.
- obs #3: request_count 12, discovery_requests 4, book_requests 8, eligible_pairs 0.

The obs #3 no-eligible result **may inform planning** but is
**not a cost, not zero cost, not opportunity cost, not idle cost, and not profitability evidence**.
It is an observed state recorded per the no-eligible handling contract.

## 5. Fail-closed behavior

- Missing provenance or missing accounting fields **must** yield `BLOCKED_NEEDS_EVIDENCE`, consistent
  with the fail-closed blocked-state contract. A **missing provenance** record is never silently
  zero-filled.
- This contract **preserves `BLOCKED_NEEDS_EVIDENCE` behavior**: blocked is deterministic, terminal
  for the current path, and not downgraded into a permissive value.

## 6. No cost, no conversion

- The contract **must not authorize fixed cost, default cost, floor cost, baseline overhead, assumed request cost, or guessed mapping**.
- The contract **must not convert request counts into dollars, bps, edge, net-edge, profitability, or readiness**.
- Mechanical counts are descriptive evidence only; they carry no monetary or edge authority here.

## 7. Future numeric mapping is deferred

- Any future numeric mapping from mechanical counts to friction component values **requires a separate explicitly authorized TDD/offline task with evidence provenance**.
- Until such a task is authorized, mechanical counts remain representation-only and any friction
  component that would consume them stays `blocked`.

## 8. No live execution connection

- This contract defines **no live order** path and **no execution connection**. It connects to no
  CLOB client, no order intent, no council execution authority, and no trading path.
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any artifact that claims to satisfy it, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no cost figure, no idle-cost or opportunity-cost figure derived from mechanical counts;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 9. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact serialization of observation/discovery cost records.
- exact source_field path syntax for mechanical fields.
- exact request-count cap integration.
- exact mapping, if ever authorized, from mechanical counts to friction component values.
- exact verifier vocabulary for observed vs blocked mechanical accounting.
- exact interaction with no-eligible state records.
- exact fixture shape for eligible and no-eligible examples.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. Mechanical
observation/discovery counts are descriptive evidence only; mapping or interpreting them requires
separately authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 10. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 task** may follow, with failing tests
  first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
