# Phase 5 Offline Interface Contract

<!-- FRAMING-START -->
## Status and framing

This document defines **contracts only** — it is **offline, interface-contract only**. It follows
the [Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and **does not authorize
implementation** (no implementation is authorized by this document).

This interface contract:

- **is not a mathematical proof**;
- **does not guarantee correctness**;
- **does not authorize implementation**;
- **does not authorize economic inference**;
- **defines testable interface expectations**;
- **reduces ambiguity before implementation**;
- **makes schema drift easier to detect later**;
- **separates schema/taxonomy design from implementation** and provides boundaries for future
  TDD/offline implementation.

No-eligible handling and observation/discovery cost handling must each be **represented explicitly**,
but their **economic treatment remains unclaimed**.
**Future implementation must be separately authorized and TDD/offline first.**
<!-- FRAMING-END -->

## 1. Gross-edge input schema

Defines the read-only shape a future Phase 5 component would consume from Phase 4A/4B sample-only
records (descriptive inputs, not signals):

- record identity: `batch_id`, `run_index`, source artifact path (read-only provenance reference).
- per-pair gross-edge fields as already emitted by Phase 4A (e.g. `buy_both_gross_edge`,
  `sell_both_gross_edge`, spread/timestamp-delta fields) — consumed **as-is**, never recomputed
  from live data here.
- eligibility status per record (eligible / ineligible) and ineligible reason codes.
- The contract fixes field **names/types/units expectations** so schema drift is detectable; it
  assigns no economic meaning to any field.

## 2. Friction component schema

Defines the **shape** of a friction/cost taxonomy to be designed and tested later — names and units
only, with no values authorized here:

- a friction taxonomy is a set of named, typed components (e.g. fee-like, spread-like,
  observation/discovery-like) — **enumerated structurally**, not quantified.
- each component declares: name, unit, source-of-truth reference, and whether it is
  observation-derived or assumption-derived.
- **No fixed cost, floor cost, baseline overhead, or economic treatment is authorized here.** The
  schema only reserves slots; populating them requires a separate authorized step.
- This taxonomy is refined at field level by the
  [Friction-Component Schema Contract](phase5_friction_component_schema_contract.md)
  (contract-only; no values authorized; fail-closed to `BLOCKED_NEEDS_EVIDENCE`).

## 3. No-eligible handling schema

- A run with **zero eligible records** (as observed in obs #3) must be representable **explicitly**
  as a first-class state, not as an error or an empty silence.
- The schema records: eligible count `0`, ineligible reason histogram, and a `no_eligible: true`
  marker.
- **Its economic treatment remains unclaimed**: no-eligible handling does **not** imply
  cost imputation, baseline overhead, or any fixed economic treatment. The representation is
  structural only.
- This handling is refined at field/state level by the
  [No-Eligible Handling Schema Contract](phase5_no_eligible_handling_schema_contract.md)
  (observed-state only; no calculation; fail-closed to `BLOCKED_NEEDS_EVIDENCE`).

## 4. Observation/discovery cost schema

- Observation/discovery activity (e.g. discovery_requests, book_requests, request_count) must be
  **representable explicitly** as observed mechanical counts, separated from market-content fields.
- The schema reserves named slots for observation/discovery cost **representation**, but **no fixed
  cost, floor cost, baseline overhead, or economic treatment is authorized here**.
- Mechanical observation metadata (counts, stage order, artifact/log counts) must be schema-separated
  from market-content observations (eligibility, gross-edge fields).

## 5. Artifact provenance schema

- Every consumed input must carry a **provenance reference**: originating `batch_id`, run index,
  artifact filename, and the audited commit that recorded it.
- Generated `data/output` artifacts are **read-only evidence**, never committed source. They remain
  **untracked** and are never staged.
- A future component must refuse inputs lacking provenance (see fail-closed contract).
- This provenance is refined at field level by the
  [Artifact Provenance Contract](phase5_artifact_provenance_contract.md)
  (chain-of-custody only; no quality/integrity guarantee; fail-closed to `BLOCKED_NEEDS_EVIDENCE`).

## 6. Reporting / no-claims schema

- Any future report must carry the standard no-claims block and sample-only framing.
- Reports may state observed deltas and operator-attention signals; they must not state economic
  conclusions.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

A future Phase 5 component, and this contract, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no trade recommendation; no deployment instruction; no execution instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 7. Fail-closed behavior contract

A future implementation must fail closed (stop, mark failed, produce no downstream output) on:

- missing or malformed input schema;
- missing provenance;
- a request/observation count exceeding the configured cap;
- any ambiguity the schema does not explicitly cover.

Fail-closed behavior is the required default; silent continuation is forbidden.

## 8. Offline fixture requirements

- All contract tests and any future implementation tests must run **offline** against **synthetic
  fixtures** — no endpoints, no market-data fetch, no subprocess batch.
- Fixtures must be clearly labeled (e.g. `diagnostic_fixture: true`) and must cover at least: an
  eligible-records case and a **no-eligible** case.

<!-- NO-CLAIMS-START -->
## No-claims statement

This interface contract makes **no edge, no PnL, no paper readiness, no economics readiness, no
execution readiness, no profitability, no alpha, no live readiness, no system-ready, no
ready-to-fly, and no ready claim** of any kind. It asserts no statistical significance, no
stationarity proof, and no economic inference. It is not a mathematical proof and does not guarantee
correctness. No-eligible handling and observation/discovery cost handling are represented
structurally only; their economic treatment remains unclaimed.
<!-- NO-CLAIMS-END -->

## 9. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 implementation task** may follow,
  one contract at a time, each with failing tests first.
- **No implementation is authorized by this document.**
  Future implementation must be separately authorized and TDD/offline first.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
