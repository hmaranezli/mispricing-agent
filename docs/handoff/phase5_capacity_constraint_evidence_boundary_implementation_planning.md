# Phase 5 Component Implementation-Planning — `phase5_capacity_constraint_evidence_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It designs the contract of a future, separately
authorized offline/TDD component and authorizes no runtime code, no tests beyond its paired planning
test, and no component selection beyond itself.

This boundary, if ever authorized, is framed as a **constitutional safety barrier / airgap**, not a
normal downstream component and **no Phase 6 bridge**. It is **not an actionable decision engine**. It
exists to refuse to let unmatched, malformed, stale, or undefined supplied evidence converge silently;
it produces no order and no instruction. **NO ORDER EXISTS** at this boundary: it does not create,
modify, constrain, resize, route, submit, reserve for, or evaluate any active or pending order.

- `component_name`: `phase5_capacity_constraint_evidence_boundary` (flat `phase5_` naming only).
- The future passive carrier is pinned as `CapacityConstraintEvidenceContext`.
- The future boundary is pinned as `CapacityConstraintEvidenceBoundary`.
- This planning task must not implement any of these symbols.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies (source contracts)

This component-planning artifact depends on, and must remain consistent with, the four upstream
component planning artifacts whose carriers it consumes:

- [`phase5_post_profitability_evidence_envelope_implementation_planning.md`](phase5_post_profitability_evidence_envelope_implementation_planning.md)
- [`phase5_venue_instrument_readiness_implementation_planning.md`](phase5_venue_instrument_readiness_implementation_planning.md)
- [`phase5_liquidity_capacity_evidence_boundary_implementation_planning.md`](phase5_liquidity_capacity_evidence_boundary_implementation_planning.md)
- [`phase5_capital_margin_evidence_boundary_implementation_planning.md`](phase5_capital_margin_evidence_boundary_implementation_planning.md)

It also remains consistent with the
[`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)
and [`phase5_interface_contract.md`](../protocols/phase5_interface_contract.md).

## 2. Core principle — passive constitutional safety barrier, not a calculator

- The capacity-constraint boundary is a **passive admissibility constraint** and a structural
  cross-evidence auditor. It is explicitly **not exposure runtime** and **not balance runtime**.
- It is not sizing, not allocation, not order intent, and not execution preparation.
- It computes nothing economic: it derives no price, no notional, no fee, no margin requirement, no
  capital reservation, no PnL, and no net edge.
- It is a constitutional safety barrier / airgap: its only purpose is to fail closed when the supplied
  multi-source evidence does not converge, so that nothing downstream can proceed on unmatched or
  unverified evidence. It reaches no admissibility verdict beyond "the supplied evidence structurally
  converges within the checked scope" or "blocked".

## 3. Consumed source carriers (exactly four)

Slice 0 consumes exactly these four already-implemented Phase 5 carriers, each supplied explicitly and
treated as opaque, exact-typed input (no reach-back, no construction, no mutation):

1. `PostProfitabilityEvidenceEnvelope`
2. `VenueInstrumentReadinessStateContext`
3. `LiquidityCapacityEvidenceContext`
4. `CapitalMarginEvidenceContext`

No other carrier is consumed. Per-carrier provenance is exactly `source_contract` / `source_artifact`
/ `source_field`. **No external input-schema record-identity or provenance tokens** (such as those
defined only in `phase5/const.py` for the input-provenance preflight) are treated as carrier source
fields on these four carriers.

## 4. Slice 0 scope — structural multi-source join auditor only

Slice 0 is strictly a **structural multi-source join auditor**. It:

- verifies exact carrier/class identity for each of the four supplied inputs;
- verifies required-field presence on each carrier;
- verifies each carrier's provenance triplet (`source_contract` / `source_artifact` / `source_field`);
- verifies identity convergence and the size / unit / time bindings **only over fields proven present
  in the repo** (Section 5);
- fails closed on missing, malformed, stale, mismatched, or undefined evidence.

Slice 0 computes **no min()**, **no final capacity**, no order size, no allocation, and no exposure
value. It produces no executable instruction and reaches no order decision, because **NO ORDER
EXISTS**.

## 5. Binding rules (only over fields proven present)

The join auditor evaluates these bindings using exact, case-sensitive equality (and inclusive
deterministic epoch comparison) over fields that actually exist on the named carriers:

- **4-way identity convergence:** `venue`, `instrument_id`, `base_asset`, `quote_asset` must agree
  across all four carriers.
- **side binding (where present only):** `PostProfitabilityEvidenceEnvelope.side` must equal
  `CapitalMarginEvidenceContext.side`. (`VenueInstrumentReadinessStateContext` and
  `LiquidityCapacityEvidenceContext` carry no `side` and are excluded from side binding.)
- **size binding (where present only):** `PostProfitabilityEvidenceEnvelope.observed_size` must agree
  with `LiquidityCapacityEvidenceContext.observed_size` and `CapitalMarginEvidenceContext.observed_size`
  (compared as magnitudes). (`VenueInstrumentReadinessStateContext` carries no size and is excluded.)
- **unit binding:** `PostProfitabilityEvidenceEnvelope.size_unit` must equal
  `LiquidityCapacityEvidenceContext.observed_size_unit` and
  `CapitalMarginEvidenceContext.observed_size_unit`; `LiquidityCapacityEvidenceContext.capacity_unit`
  must equal its `observed_size_unit`; `CapitalMarginEvidenceContext.required_capital_unit` must equal
  `CapitalMarginEvidenceContext.available_free_capital_unit`.
- **time / freshness (staleness) binding (where epoch+tolerance fields exist only):**
  `PostProfitabilityEvidenceEnvelope.observed_at_epoch_ms` is compared against
  `LiquidityCapacityEvidenceContext.liquidity_snapshot_epoch_ms` using
  `LiquidityCapacityEvidenceContext.evidence_epoch_tolerance_ms`, and against
  `CapitalMarginEvidenceContext.required_capital_epoch_ms` and
  `CapitalMarginEvidenceContext.available_free_capital_snapshot_epoch_ms` using
  `CapitalMarginEvidenceContext.evidence_epoch_tolerance_ms`. `VenueInstrumentReadinessStateContext`
  carries no epoch/tolerance fields and is excluded from time/freshness binding.

No silent defaults: a missing, malformed, unknown, or mismatched field must never become zero, false,
pass, default, baseline, assumed, eligible, or admissible.

## 6. `CapacityConstraintEvidenceContext` — passive structural validation context

- The future carrier is a passive structural validation context only, with **no computed capacity value**.
  It records only that the four supplied carriers structurally converged within the checked scope.
- It must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only, and must read no
  env/config/files/db/network/time.
- It derives, computes, and infers nothing; it stores only explicit, supplied, verbatim evidence
  references plus provenance from the upstream envelope.

## 6A. Carrier-only implementation slice and closed contract (charter amendment)

<!-- CARRIER-CONTRACT-START -->
This section pins a discrete **carrier-only implementation slice** for
`CapacityConstraintEvidenceContext`. This slice is purely a **TDD sequencing unit**: it scopes a
future, separately authorized passive-carrier implementation and nothing else.
It is **not a downstream component**, it is **no Phase 6 bridge**, and it is
**not authorization for the Slice 0** structural multi-source join auditor, its gate, or its
preflight. Implementing this carrier authorizes
no audit, no gate, no preflight, and no join logic. **NO ORDER EXISTS** at this carrier.

### Factory (exact)

- The only construction entry point is the factory `make_capacity_constraint_evidence_context`.
- The factory signature is **keyword-only** and accepts **exactly** the closed field set below — no
  positional parameters, no extra keywords, and no defaults.
- **Direct construction is blocked**: the carrier may not be built by calling its type directly; only
  the factory may build it.
- Every supplied field value must be **exact str** (`type(value) is str`), **non-empty**, and
  **non-whitespace**, and is stored **verbatim**. There is **no implicit coercion** of any value.

### Closed field set (exactly fourteen, and no others)

`CapacityConstraintEvidenceContext` stores **exactly** these **fourteen** fields and **no others**:

1. `component_name`
2. `boundary_version`
3. `post_profitability_source_contract`
4. `post_profitability_source_artifact`
5. `post_profitability_source_field`
6. `venue_readiness_source_contract`
7. `venue_readiness_source_artifact`
8. `venue_readiness_source_field`
9. `liquidity_capacity_source_contract`
10. `liquidity_capacity_source_artifact`
11. `liquidity_capacity_source_field`
12. `capital_margin_source_contract`
13. `capital_margin_source_artifact`
14. `capital_margin_source_field`

The **exactly-four source-carrier rule** stays a **doc/test invariant**, **not stored data**: the
carrier stores only the four per-source provenance triplets above; it stores no count of audited
carriers. `audited_evidence_count` is **never** a carrier field.

### Excluded — the carrier must NOT store any of

The carrier stores **none** of the following, and declares no field for any of them:

- any status verdict: `join_status`, `binding_status`, `identity_status`, `freshness_status`,
  `unit_status`, or **any `*_status` field**;
- `audited_evidence_count`;
- any computed / economic value: `observed_size`, `available_capacity`, `required_capital`,
  `final_capacity`, `computed_min`, `order_size`, `allocation`, `exposure`, `balance`;
- any execution / runtime token: `route`, `reservation`, `wallet`, and no paper/live readiness;
- any external record-identity / provenance token: `batch_id`, `run_id`, `observation_id`,
  `provenance_status`.

### Repr and safety (exact)

- Safe `repr` exposes **only** `component_name` and `boundary_version`; it leaks no provenance value
  and no raw evidence.
- The carrier is **frozen** (immutable), **repr-safe**, **anti-truthiness**, **anti-coercion**, and
  **factory-only**.
- It reads **no env**, no `config`, no `files`, no `db`, no `network`, and no `time` (no clock).
- It **derives, computes, compares, audits, validates, infers, and decides nothing**; it stores only
  the explicit, supplied, verbatim provenance references above.
<!-- CARRIER-CONTRACT-END -->

## 7. Fail-closed branch priority and blocked taxonomy

The future boundary evaluates in a fixed, fail-closed branch priority; the first matching outcome
wins, and **presence/missing and malformed checks precede identity / unit / time comparisons**:

1. wrong-type / misroute (exact halt carrier supplied) → programmatic error, never a market packet;
2. **missing** allow-listed carrier or field → blocked;
3. **malformed** grammar / scalar validity → blocked;
4. **identity-mismatch** (4-way identity, side, size magnitude) → blocked;
5. **unit-mismatch** → blocked;
6. **stale** (either applicable epoch axis) → blocked;
7. **undefined** evidence (an evidence field whose value is not resolvable within the checked scope)
   → blocked;
8. otherwise → passive structural-convergence pass (no computed capacity, no order decision).

Required blocked taxonomy: **missing**, **malformed**, **stale**, **identity-mismatch**,
**unit-mismatch**, **undefined** evidence. All are deterministic and fail closed.

### 7.1 Blocked reason vocabulary to pin (doc-only; no runtime constants)

These token **names** are defined in this planning document only; this planning batch adds **no runtime
constants** and creates no runtime module:

- `CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE`
- `CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE`
- `CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE`
- `CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH`
- `CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH`
- `CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE`

Blocked outputs reuse the existing `BlockedPacket` semantics and the canonical `BLOCKED_NEEDS_EVIDENCE`
blocked status conceptually; this boundary introduces **no new packet** schema, factory, or reason
builder. Packet provenance must come only from the upstream `PostProfitabilityEvidenceEnvelope`
`source_*` fields.

## 8. Deferred decisions

The following are **deferred** and require separate, explicitly authorized work:

- the boundary's exact gate/preflight function shape (the carrier's exact closed field set is now
  pinned in §6A and is no longer deferred);
- exact canonical-identity selection when all four carriers agree;
- any later slice beyond the Slice 0 structural join (none authorized here).

## 9. Task boundary

- This task makes **no phase5 runtime code edits** and creates no `phase5/` module.
- This task does not edit the central handoff/memory file and performs no memory closeout.
- This task creates exactly two files: this planning doc and its paired planning test.

## 10. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and
  declared-provenance.
- This planning artifact does not authorize implementation, the boundary class, the carrier, or
  selecting the next component.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This boundary and its planning artifact must produce **none** of:

- no profitability score; no alpha/edge claim; no PnL, net-edge, or economic-inference figure;
- no data-quality or data-integrity guarantee; no safety guarantee;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict; no system-ready or ready-to-fly statement.

Explicit no-go scope for this boundary (each phrase pinned verbatim):

- no order size, no allocation, no routing, no execution preparation
- no sizing
- no exposure runtime
- no balance runtime
- no wallet reservation
- no paper/live readiness

It is **not an actionable decision engine** and is **no Phase 6 bridge**. **NO ORDER EXISTS**: it
interacts with no active or pending order.
<!-- PROHIBITED-OUTPUTS-END -->

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes **no edge, no PnL, no paper readiness, no economics readiness, no
execution readiness, no profitability, no alpha, no live readiness, no safety guarantee, no
data-quality guarantee, no data-integrity guarantee, no system-ready, no ready-to-fly, and no ready
claim** of any kind. It asserts no statistical significance, no stationarity proof, and no economic
inference. A passed structural-convergence audit is still only an explicit-evidence-filtered
observation; it authorizes no trading, no paper/live work, and no readiness-to-trade claim. This is a
component planning artifact only; it authorizes a separately approved offline/TDD implementation task,
not implementation.
<!-- NO-CLAIMS-END -->

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
