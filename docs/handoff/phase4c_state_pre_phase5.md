# Phase 4C — Repo State Memory (pre-Phase-5)

<!-- FRAMING-START -->
## Framing (read first)

This is a **repo-durable state/memory record** of the completed Phase 4C minimum repeatability
observation. It summarizes three public-data **sample-only** observations and points to their
committed audit docs. It carries **no economic inference**, **no stationarity proof**, **no
statistical significance**, and **no readiness claim** of any kind. Nothing here authorizes
Phase 5 implementation, trading, or paper deployment.
<!-- FRAMING-END -->

## Current state

- **Phase 4C minimum repeatability observation: complete and audited** (3 of the protocol-permitted
  3–5 sample-only runs).
- **Latest commit:** `1504bcb` (Add phase 4C repeatability observation 03 audit).
- HEAD == origin/master == `1504bcb` at the time this memory was written.

### Committed reference docs

- Protocol: `docs/protocols/phase4c_repeatability_observation_protocol.md`
- Observation #1 audit: `docs/handoff/phase4c_first_public_batch_audit.md`
- Observation #2 audit: `docs/handoff/phase4c_repeatability_observation_02_audit.md`
- Observation #3 audit: `docs/handoff/phase4c_repeatability_observation_03_audit.md`

## Observation #1

- batch `phase4c_batch_1781631021`
- request_count 12/20 · discovery_requests 4 · book_requests 8
- assets BTC/ETH/SOL/XRP
- stages OK (3 stages, all status ok / exit_code 0)
- audit commit `4a85ff4`

## Observation #2

- batch `phase4c_batch_1781636200`
- request_count 12/20 · discovery_requests 4 · book_requests 8
- assets BTC/ETH/SOL/XRP
- complement_pairs_written 4 · eligible_pairs 4
- audit commit `71f1308`

## Observation #3

- batch `phase4c_batch_1781637248`
- request_count 12/20 · discovery_requests 4 · book_requests 8
- assets BTC/ETH/SOL/XRP
- complement_pairs attempted/written 4/2 · pair_books_ok/failed 8/0
- 4A verdict `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS` · eligible_pairs 0
- ineligible reasons `ONE_SIDED_BOOK: 2` and `SPREAD_TOO_WIDE: 2`
- 4B verdict `PHASE4B_NO_ELIGIBLE_RECORDS` · rejection 1.0
- audit commit `1504bcb`

## Cross-run summary (non-statistical)

| Metric | obs #1 | obs #2 | obs #3 |
|---|---|---|---|
| request_count | 12 | 12 | 12 |
| discovery_requests | 4 | 4 | 4 |
| book_requests | 8 | 8 | 8 |
| artifact count | 5 | 5 | 5 |
| log count | 6 | 6 | 6 |
| stage order | identical | identical | identical |
| complement_pairs_written | 4 | 4 | 2 |
| eligible_pairs | 4 | 4 | 0 |

## Interpretation

- This is a **three-point small-sample observation only**.
- The obs #3 difference (`complement_pairs_written` 2 vs 4, `eligible_pairs` 0 vs 4) is an
  **operator-attention signal**, not proof of instability and not proof of market-dependent behavior.
- **No stationarity proof.**
- **No statistical significance.**
- **No economic inference.**
- **No readiness claim.**
- **Zero deltas do not prove determinism or stability.** Three runs cannot establish stability,
  instability, drift, or its absence.

## Next position

- Before Phase 5, repo memory is **synced** to commit `1504bcb`.
- The next allowed step is a **Phase 5 planning-only protocol/design gate** (docs/design only).
- **Do not implement Phase 5 yet.** Do not trade, do not paper deploy, do not make readiness claims.
- Any Phase 5 work begins behind its own separately-approved gate.

## Safety state update (post-guards)

Two default-safe guards were added after the Phase 4C observations (each TDD/offline, docs in
`docs/protocols/`):

- **`e84ad94` — council decision authority bypassed by default.** `config.COUNCIL_DECISION_AUTHORITY_ENABLED = False`
  disconnects the (deterministic) council from execution authority: a council PASS cannot reach
  `execute()` / `_dry_execute` / `_clob_execute` or create an order intent. The council still runs
  as **diagnostic/read-only** by default. See `docs/protocols/council_decision_authority_bypass.md`
  and `docs/protocols/council_inventory_derisk_gate.md`. (`DRY_RUN` and all guardrails unchanged.)
- **`f7eb12e` — manual order script guarded.** `analysis/test_order.py` posts **nothing by default**;
  it blocks before `create_and_post_order` unless `MANUAL_ORDER_SCRIPT_ENABLED` is explicitly opted
  in. See `docs/protocols/manual_order_script_guard.md`.

Current known state:

- Council is **diagnostic/read-only by default** (no execution authority).
- Manual order script **posts nothing by default**.
- Phase 5 is **planning / interface only** — no implementation.
- The `tools/phase45_evidence_verifier.py` evidence verifier previously returned **PASS** (scoped to
  checked invariants).
- **No readiness / economic / alpha claim** is made by this state.

Next step pointer: Phase 5 may proceed **only as an offline deterministic contract / planning step**
with **no trading authority**; any implementation is separately authorized and TDD/offline first.

Phase 5 contract backlog (planning artifacts only, no implementation):

- `docs/protocols/phase5_friction_component_schema_contract.md` — field-level friction-component
  schema contract (components, per-component fields, Decimal/integer-scaled numeric rule,
  non-negative deduction sign convention, provenance, fail-closed to `BLOCKED_NEEDS_EVIDENCE`,
  contract-only aggregation rule). Contract/planning only; no values, no net-edge calculator, no
  trading authority. Deferred items (exact `uncertainty_buffer` formula, final units/scaling,
  fee/slippage/depth evidence sources, aggregation implementation) remain blocked until separate
  authorization.

## Phase 5 contract state update (friction-component schema)

- **`6b2e577` — Add phase 5 friction component schema contract.** Docs/tests only; a
  planning/contract artifact, **not implementation**.
- The contract (`docs/protocols/phase5_friction_component_schema_contract.md`, pinned by
  `tests/test_phase5_friction_component_schema_contract.py`) defines: the required friction
  components, required per-component fields, provenance (`source_artifact` + `source_field`), numeric
  representation (no binary-float authority; Decimal or integer-scaled), non-negative deduction sign
  convention, **fail-closed to `BLOCKED_NEEDS_EVIDENCE`** (never zero), **no defaults/guesses/floor/
  baseline costs**, **no net-edge calculator**, and **no execution connection**.
- **Phase 5 remains planning / interface only** — no implementation, no trading authority. Any
  implementation is separately authorized and TDD/offline first.
- **No readiness / economic / alpha / PnL / profitability / edge claim** is made by this state.
- **Next likely contract:** the **no-eligible handling schema** (offline/TDD only, docs+tests, no
  public-data fetch, no trading). Not yet authorized — it begins behind its own scoped task.
- `docs/protocols/phase5_no_eligible_handling_schema_contract.md` — no-eligible handling schema
  contract (no-eligible as observed **state, not a calculation**; required fields; valid state
  categories; provenance anchored to obs #3 `phase4c_batch_1781637248` /
  `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS` / `PHASE4B_NO_ELIGIBLE_RECORDS` / `eligible_pairs=0`;
  fail-closed to `BLOCKED_NEEDS_EVIDENCE`; no zero-filling; no calculator; no execution connection;
  `VALID_EVIDENCE`/observed-state, not a stage failure by default). Contract/planning only; no
  trading authority; deferred items remain blocked until separate authorization.
- **Design rationale:** this memory/handoff is the **decision audit trail**. Recording each Phase 5
  contract here keeps its assumptions, deferrals, and boundaries from being orphaned, so a later
  reader can trace why each contract slot is observed, derived, or blocked.

## Phase 5 contract state update (no-eligible handling schema)

- **`f032bf2` — Add phase 5 no eligible handling contract.** Docs/tests only; a planning/contract
  artifact, **not implementation**.
- No-eligible is an **observed state / evidence-contract input**, **not a calculation**, not an
  idle-cost, not an opportunity-cost, and not a profitability/readiness/edge inference.
- The contract (`docs/protocols/phase5_no_eligible_handling_schema_contract.md`, pinned by
  `tests/test_phase5_no_eligible_handling_schema_contract.py`) is **anchored to Phase 4C
  Observation #3**: `phase4c_batch_1781637248`, `GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS`,
  `PHASE4B_NO_ELIGIBLE_RECORDS`, `eligible_pairs=0`, ineligible reasons `ONE_SIDED_BOOK` and
  `SPREAD_TOO_WIDE`.
- It **records observation and discovery accounting and provenance only**. Missing
  provenance/accounting **must** yield `BLOCKED_NEEDS_EVIDENCE`. **No zero-filling**: a no-eligible
  run **must not become cost=0, edge=0, or profitability=0**.
- **Phase 5 remains planning / interface only** — no implementation, no trading authority. Any
  implementation is separately authorized and TDD/offline first.
- **No readiness / economic / alpha / PnL / profitability / edge / idle-cost / opportunity-cost
  claim** is made by this state.
- **Next likely contract:** the **artifact provenance contract** (offline/TDD only, docs+tests, no
  public-data fetch, no trading), because both the friction and no-eligible contracts depend on
  `source_artifact` / `source_field` / `batch_id` / `run_id` evidence. Not yet authorized — it begins
  behind its own scoped task.
- `docs/protocols/phase5_artifact_provenance_contract.md` — artifact provenance contract
  (chain-of-custody / evidence-contract only; required provenance fields; valid `artifact_type` /
  `artifact_phase` vocabularies; provenance required before any observed/derived status; fail-closed
  to `BLOCKED_NEEDS_EVIDENCE` on missing provenance / unknown source / source-field mismatch; no
  hand-entered values without a source chain; classifies only observed | derived | blocked; not-yet-
  implemented fields stay explicit blocked fields; zero-trust stance with no security / data-quality /
  data-integrity guarantee; no calculator; no execution connection). Contract/planning only.

## Phase 5 contract state update (artifact provenance)

- **`37159b5` — Add phase 5 artifact provenance contract.** Docs/tests only; a planning/contract
  artifact, **not implementation**.
- The contract (`docs/protocols/phase5_artifact_provenance_contract.md`, pinned by
  `tests/test_phase5_artifact_provenance_contract.py`) requires every Phase 5 input to link back to
  **evidence, not assumptions** (a concrete `source_artifact` / `source_field` chain).
- Required provenance fields include `source_artifact`, `source_field`, `artifact_type`,
  `artifact_phase`, `batch_id`, `run_id`, `observation_id`, `stage_name`, `verdict_or_status`,
  `utc_timestamp_ms_or_blocked_reason`, `request_count_or_blocked_reason`,
  `source_sha256_or_blocked_reason`, `parser_version_or_blocked_reason`,
  `verifier_result_or_blocked_reason`, and `blocked_reason_if_missing`.
- **Missing provenance, unknown artifact source, or source-field mismatch** **must** yield
  `BLOCKED_NEEDS_EVIDENCE`. **No hand-entered values** without a `source_artifact`/`source_field`
  chain.
- Provenance **does not authorize execution, trading, readiness, profitability, or net-edge
  calculation**; it classifies evidence status only as observed / derived / blocked.
- `source_sha256` / `parser_version` / `verifier_result` are **explicit blocked fields until
  implemented** (recorded as blocked reasons, never omitted).
- The **friction** and **no-eligible** contracts depend on this provenance contract for their source
  chain.
- **Phase 5 remains planning / interface only** — no implementation, no trading authority.
- **No data-quality / data-integrity / safety guarantee claim**, and **no readiness / economic /
  alpha / PnL / profitability / edge claim**, is made by this state.
- **Next likely contract:** the **fail-closed blocked-state contract**, because provenance now
  defines when evidence is missing / unknown / mismatched (offline/TDD only, docs+tests, no
  public-data fetch, no trading). Not yet authorized — it begins behind its own scoped task.
- `docs/protocols/phase5_fail_closed_blocked_state_contract.md` — fail-closed blocked-state contract
  (`BLOCKED_NEEDS_EVIDENCE` canonical for missing/unknown/mismatched evidence; blocked is a
  deterministic, terminal state, not an exception escape hatch; must not be downgraded to
  zero/false/pass/observed/derived/eligible/executable/tradable/ready/profitable/net-edge; required
  blocked-record fields + blocked reason categories; preserves context without inventing fields;
  retry only on new evidence/authorization, TDD/offline first; human review must not substitute for
  source evidence). Contract/planning only; depends on the friction, no-eligible, and provenance
  contracts.

## Phase 5 fail-closed blocked-state closeout

- **`65eaac8` — Add phase 5 fail closed blocked state contract.** Docs/tests only; a contract/planning
  artifact only, **not implementation**.
- It defines **`BLOCKED_NEEDS_EVIDENCE` as the canonical blocked status** for missing / unknown /
  mismatched evidence across the Phase 5 contracts.
- Blocked is **deterministic and terminal for the current path**.
- Blocked **must not be downgraded into zero, false, pass, observed, derived, eligible, executable,
  tradable, ready, profitable, or net-edge input**.
- Blocked-state records require: `blocked_status`, `blocked_reason`, `blocked_source_contract`,
  `missing_or_invalid_field`, `source_artifact_or_blocked_reason`, `source_field_or_blocked_reason`,
  `deterministic_next_action`, `human_review_required`, `may_retry_after_evidence`, and
  `created_utc_timestamp_ms_or_blocked_reason`.
- **Human review must not substitute for `source_artifact`/`source_field` evidence.**
- **Retry requires new evidence or explicit authorization** and remains **TDD/offline first**.
- It depends on: `phase5_friction_component_schema_contract.md`,
  `phase5_no_eligible_handling_schema_contract.md`, and `phase5_artifact_provenance_contract.md`.
- **Phase 5 remains contract/planning only** — no implementation, no calculator, no net-edge
  aggregation, no trading authority, no paper/live readiness, no alpha, no PnL, no profitability, no
  edge claim.
- **Chainlink/F1b is not the active task here.** This closeout does **not** authorize
  PUBLIC_REFERENCE_BASKET / SURROGATE_BASKET integration, data fetch, or net-edge work.

## Phase 5 observation/discovery cost schema closeout

- **`cb71d01` — Add phase 5 observation discovery cost contract.** Docs/tests only; a
  contract/planning artifact only, **not implementation**.
- It represents mechanical observation activity as **evidence-bearing metadata only** and
  **distinguishes mechanical observation metadata from market-content observations**.
- The contract (`docs/protocols/phase5_observation_discovery_cost_schema_contract.md`, pinned by
  `tests/test_phase5_observation_discovery_cost_schema_contract.py`) defines required mechanical
  fields: `request_count`, `discovery_requests`, `book_requests`, `stage_order`, `artifact_count`,
  `log_count`, `candidate_pairs`, `eligible_pairs`, `ineligible_reasons`, `batch_id`, `run_id`,
  `observation_id`, `source_artifact`, `source_field`, `provenance_status`, and
  `blocked_reason_if_missing`.
- It **anchors only to audited Phase 4C obs #1/#2/#3 facts as doc-contract constants**; it does not
  copy generated artifacts, build a parser, build a loader, build a fixture engine, or create runtime
  fixtures.
- It **does not convert** request/discovery/book counts into dollars, bps, edge, net-edge,
  profitability, readiness, idle cost, opportunity cost, or any cost figure.
- **Obs #3 no-eligible is not a cost, not zero cost, not opportunity cost, not idle cost, and not
  profitability evidence.**
- **Missing provenance/accounting must yield `BLOCKED_NEEDS_EVIDENCE`.**
- **Future numeric mapping** from mechanical counts to friction component values **requires a separate
  explicitly authorized TDD/offline task with evidence provenance.**
- It depends on: `phase5_artifact_provenance_contract.md`,
  `phase5_fail_closed_blocked_state_contract.md`, `phase5_no_eligible_handling_schema_contract.md`,
  and `phase5_friction_component_schema_contract.md`.
- **Phase 5 remains contract/planning only** — no implementation, no calculator, no net-edge
  aggregation, no friction engine, no trading authority, no paper/live readiness, no alpha, no PnL,
  no profitability, no edge claim.
- **Chainlink/F1b is not the active task here.** This closeout does **not** authorize
  PUBLIC_REFERENCE_BASKET / SURROGATE_BASKET integration, data fetch, friction implementation, or
  net-edge work.

## Phase 5 no-claims/reporting schema closeout

- **`f9e6260` — Add phase 5 no claims reporting schema contract.** Docs/tests only; a
  contract/planning artifact only, **not implementation**.
- Reporting is **output-vocabulary only**; it authorizes no computation, aggregation, execution,
  trading, readiness, paper/live status, or economic inference.
- Allowed reporting states are `observed`, `derived`, `blocked`; **`BLOCKED_NEEDS_EVIDENCE` is
  canonical** when evidence is missing/unknown/mismatched.
- The contract (`docs/protocols/phase5_no_claims_reporting_schema_contract.md`, pinned by
  `tests/test_phase5_no_claims_reporting_schema_contract.py`) defines all 12 required reporting-record
  fields: `report_schema_version`, `report_scope`, `report_status`, `source_contract`,
  `source_artifact_or_blocked_reason`, `source_field_or_blocked_reason`, `provenance_status`,
  `observed_or_derived_value_or_blocked_reason`, `blocked_reason_if_any`,
  `deterministic_next_action_if_blocked`, `no_claims_block_present`, and
  `created_utc_timestamp_ms_or_blocked_reason`.
- Blocked reports output only the blocked reason, source/provenance context, and deterministic next
  action; they **must not** output derived estimates, fallback values, zero values, or guessed values.
- Reports **must not convert** observed/derived/blocked states into alpha, PnL, edge, profitability,
  readiness, paper readiness, live readiness, execution authority, trading instruction, net-edge,
  economic inference, safety guarantee, data-quality guarantee, or data-integrity guarantee.
- **Every future Phase 5 report must carry the no-claims block** and sample / contract-planning
  framing. **Human/operator review must not convert blocked evidence into observed or derived
  reporting.**
- Missing no-claims block, missing provenance context, unknown source contract, or forbidden claim
  wording **must fail closed** to `BLOCKED_NEEDS_EVIDENCE` or contract violation as appropriate.
- It depends on the interface, friction, no-eligible, provenance, fail-closed, and
  observation/discovery cost contracts.
- **Phase 5 remains contract/planning only** — no implementation, no calculator, no net-edge
  aggregation, no friction engine, no trading authority, no paper/live readiness, no alpha, no PnL,
  no profitability, no edge claim.
- **Chainlink/F1b is not the active task here.** This closeout does **not** authorize
  PUBLIC_REFERENCE_BASKET / SURROGATE_BASKET integration, data fetch, friction implementation,
  input-schema implementation, fixture engine, or net-edge work.

## Phase 5 contract backlog pointer (input-schema refinement)

- `docs/protocols/phase5_input_schema_refinement_contract.md` (pinned by
  `tests/test_phase5_input_schema_refinement_contract.py`) — input-schema refinement contract:
  defines input **shape only** (presence is not evidence quality / source truth / readiness /
  economic validity); separates inputs into record_identity, gross_edge_fields, eligibility_state,
  no_eligible_state, friction_component_placeholders, mechanical_observation_metadata,
  provenance_fields, reporting_boundary_fields, and blocked_state_fields; gross-edge fields read-only
  (no recompute/refresh/fetch/live); friction placeholders are **non-value, non-computable** slots
  that fail closed to `BLOCKED_NEEDS_EVIDENCE` (no impute/coerce/cast/default); mechanical metadata
  stays separate with no count→cost conversion; preserves observed/derived/blocked vocabulary;
  fail-closed on missing/malformed/unknown inputs; human review must not substitute for source
  evidence. Depends on the interface, friction, no-eligible, provenance, fail-closed,
  observation/discovery cost, and no-claims/reporting contracts. Contract/planning only; defined
  before the offline fixture contract so fixtures know which shape they represent. (Committed-hash
  state-update recorded by the follow-up memory task.)

## Next position (after no-claims/reporting closeout)

- Current position: **Master F → Phase 5 contract/planning layer.**
- The **no-claims/reporting schema slice is recorded**, but remaining Phase 5 gaps still require
  separate authorization.
- **The net-edge engine is still not authorized.**
- Remaining likely Phase 5 contract gaps include **offline fixture and input-schema refinement**.
- Any later implementation **must** proceed **component-by-component with failing tests first and
  declared provenance**.

<!-- NO-CLAIMS-START -->
## No-claims statement

This memory record makes **no edge, no PnL, no paper readiness, no economics readiness, no
execution readiness, no profitability, no alpha, no live readiness, no system-ready, no
ready-to-fly, and no ready claim** of any kind. It does not prove stationarity and asserts no
statistical significance. All verdict labels referenced above are sample-only diagnostic labels,
not assertions of any tradeable property.
<!-- NO-CLAIMS-END -->

## Safety note

This file is docs/memory only. The `data/output/phase4c_batch_*` directories remain **untracked**
and **not staged**; generated artifacts are never committed.
