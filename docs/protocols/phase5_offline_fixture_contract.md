# Phase 5 Offline Fixture Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract/planning artifact only, not implementation**. It is **offline,
static-fixture discipline contract only**. It follows the
[Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §8
("Offline fixture requirements") of the
[Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract defines the allowed shape, scope, and static-fixture discipline for future offline
fixtures. Fixture cases pin boundary-case invariants; they:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** prove correctness, **must not** verify truth, and **must not** authorize computation;
- **must not** build a calculator, a net-edge aggregation, a friction engine, a parser, a loader, a
  fixture engine, a fixture factory, or a fixture generator;
- **must not** connect to any live order path or execution path (no execution connection);
- **is not** a safety guarantee, **is not** a data-quality guarantee, and **is not** a data-integrity
  guarantee.

This contract defines the offline fixture slice only. Remaining Phase 5 gaps still require separate
authorization. Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Scope — synthetic diagnostic only

- Offline fixtures are **synthetic diagnostic examples only**.
- **Fixture presence must not be treated as market truth, evidence quality, source truth, readiness, economic validity, profitability evidence, paper/live evidence, or net-edge input.**
- Fixture cases **pin boundary-case invariants only**; they **do not prove schema validity, correctness, stationarity, or economic value**.
- Fixtures must be **test/doc-contract scoped only**; they **must not be production inputs**.

## 2. Dependent contracts

This fixture contract depends on, and must remain consistent with:

- [`phase5_interface_contract.md`](phase5_interface_contract.md)
- [`phase5_friction_component_schema_contract.md`](phase5_friction_component_schema_contract.md)
- [`phase5_no_eligible_handling_schema_contract.md`](phase5_no_eligible_handling_schema_contract.md)
- [`phase5_artifact_provenance_contract.md`](phase5_artifact_provenance_contract.md)
- [`phase5_fail_closed_blocked_state_contract.md`](phase5_fail_closed_blocked_state_contract.md)
- [`phase5_observation_discovery_cost_schema_contract.md`](phase5_observation_discovery_cost_schema_contract.md)
- [`phase5_no_claims_reporting_schema_contract.md`](phase5_no_claims_reporting_schema_contract.md)
- [`phase5_input_schema_refinement_contract.md`](phase5_input_schema_refinement_contract.md)

## 3. Fixture source prohibitions

- Fixtures **must not copy generated artifacts**.
- Fixtures **must not be derived from public-data fetches**.
- Fixtures **must not contain private auth, secrets, balances, orders, live clob data, or real trading data**.
- Fixtures **must not create or require runtime data/output artifacts**.
- Fixtures **must not authorize parser, loader, fixture engine, fixture factory, fixture generator, data-fetch, computation, or aggregation**.

## 4. Static constants discipline

- Fixtures **must** be represented as **static, read-only constants** or documented static examples
  only. Specifically:

  - **no dynamic fixture construction**;
  - **no constructor/generator/factory invocation**;
  - **no runtime mutation**;
  - **no randomization**;
  - **no timestamp-now behavior**;
  - **no environment-dependent fixture content**;
  - **no network-dependent fixture content**.

- **If tests need fixture examples, they must use static constants or doc-pinned examples, not generators/factories/loaders/parsers.**
- Any attempt to implement a fixture_engine, fixture_generator, fixture_factory, dynamic fixture
  construction, parser, or loader is **out of scope** and **must be treated as contract violation for this task**.

## 5. Required fixture cases

The following fixture case names are **required** by this contract:

- `eligible_minimal_fixture`
- `no_eligible_fixture`
- `blocked_missing_provenance_fixture`
- `blocked_unresolved_friction_placeholder_fixture`
- `malformed_or_unknown_field_fixture`
- `forbidden_claim_reporting_fixture`

### Per-case invariants

- `eligible_minimal_fixture` **must** represent a **minimal syntactic success shape only**; it **must not imply economic validity, readiness, profitability, execution, or net-edge**.
- `no_eligible_fixture` **must** represent no-eligible as an explicit state; it **must not become error, zero value, zero cost, opportunity cost, idle cost, profitability evidence, readiness signal, or net-edge input**.
- `blocked_missing_provenance_fixture` **must** fail closed to `BLOCKED_NEEDS_EVIDENCE` or contract
  violation as appropriate.
- `blocked_unresolved_friction_placeholder_fixture` **must** keep friction placeholders non-value and
  non-computable; placeholders **must not be 0, null, false, empty string, default, floor, baseline, assumed, guessed, or usable numeric values**.
- Unresolved placeholders in fixtures **must not be treated as cost evidence, zero cost, usable friction value, net-edge input, economic inference, readiness evidence, or implementation authority**.
- `malformed_or_unknown_field_fixture` **must** fail closed; malformed/unknown fields **must not be silently ignored, coerced, cast, defaulted, or treated as valid observed/derived input**.
- `forbidden_claim_reporting_fixture` **must represent forbidden claim wording as contract violation or blocked reporting behavior, not as valid output**.

## 6. Fixture record shape and preserved semantics

- **Fixture expected outputs must not contain alpha, PnL, edge, profitability, readiness, paper/live readiness, execution authority, trading instruction, net-edge, economic inference, safety guarantee, data-quality guarantee, or data-integrity guarantee.**
- Fixture records **must** preserve the input-schema categories: `record_identity`,
  `gross_edge_fields`, `eligibility_state`, `no_eligible_state`, `friction_component_placeholders`,
  `mechanical_observation_metadata`, `provenance_fields`, `reporting_boundary_fields`, and
  `blocked_state_fields`.
- Fixture records **must** preserve the `observed/derived/blocked` vocabulary and
  `BLOCKED_NEEDS_EVIDENCE semantics`.
- Fixture records **must** preserve `source_artifact/source_field provenance` requirements or explicit
  blocked reasons.
- Fixture records **must not downgrade blocked into zero, false, pass, observed, derived, eligible, executable, tradable, ready, profitable, or net-edge input**.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any fixture or fixture expected output, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no PnL, net-edge, or economic-inference figure;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 7. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact fixture record serialization.
- exact fixture_schema_version policy.
- exact static constant location policy.
- exact fixture case vocabulary.
- exact fixture naming convention.
- exact expected-output schema for blocked fixture cases.
- exact rule for separating fixture constants from production inputs.
- exact verifier integration for fixture contract invariants.
- exact policy for adding future fixture cases.
- exact fixture provenance placeholder policy.
- exact synthetic timestamp policy.
- exact no-random/no-network/no-env dependency policy.
- production/live usage blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no safety guarantee,
no data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. A fixture is a
synthetic, static, diagnostic example only; building, generating, or interpreting fixtures requires
separately authorized, evidence-backed, TDD/offline work.
<!-- NO-CLAIMS-END -->

## 8. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 task** may follow, with failing tests
  first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
