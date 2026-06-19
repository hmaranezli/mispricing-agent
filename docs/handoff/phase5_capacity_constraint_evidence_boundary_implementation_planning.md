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
- The factory signature is **keyword-only** and accepts **exactly twelve (12)** caller-supplied
  parameters — the four per-source provenance triplets only (items 3–14 of the closed field set):
  `post_profitability_source_contract`, `post_profitability_source_artifact`,
  `post_profitability_source_field`, `venue_readiness_source_contract`,
  `venue_readiness_source_artifact`, `venue_readiness_source_field`,
  `liquidity_capacity_source_contract`, `liquidity_capacity_source_artifact`,
  `liquidity_capacity_source_field`, `capital_margin_source_contract`,
  `capital_margin_source_artifact`, `capital_margin_source_field`. No positional parameters, no extra
  keywords, and no defaults.
- The factory **must not accept** `component_name` or `boundary_version` as parameters; these two
  stored fields are set **internally** from constants (see Internal constants). Passing
  `component_name` or `boundary_version` must raise `TypeError` as unexpected keyword input.
- **Direct construction is blocked**: the carrier may not be built by calling its type directly; only
  the factory may build it.
- Every supplied field value must be **exact str** (`type(value) is str`), **non-empty**, and
  **non-whitespace**, and is stored **verbatim**. There is **no implicit coercion** of any value.

### Internal constants (exact)

The future module pins these constants **verbatim** (each on a single line):

```
CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME = "phase5_capacity_constraint_evidence_boundary"
BOUNDARY_VERSION = "phase5.capacity_constraint_evidence_boundary.v0"
```

The factory sets component_name internally to
`CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME`, and sets boundary_version internally to
`BOUNDARY_VERSION`. Neither identity field is a caller-supplied parameter, and neither may be
spoofed, overridden, or injected by the caller.

### Slotted / no-instance-dict hardening

- The carrier must be **slotted** (or use an equivalent **no-instance-dict** mechanism); instances
  have **no `__dict__`**.
- **Dynamic attribute injection** is **physically blocked**: no attribute may be added or rebound
  after construction.
- The carrier remains **frozen**, **repr-safe**, **anti-truthiness**, **anti-coercion**, and
  **factory-only**.

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

## 7.2 Slice 0 structural-auditor interface (charter amendment — gate / preflight)

<!-- GATE-CONTRACT-START -->
This section pins the future Slice 0 structural multi-source join auditor's contract. It is a
separate, separately authorized implementation slice; this amendment pins the contract but implements
nothing. **NO ORDER EXISTS** at this boundary.

### Names and interface shape

The future Slice 0 runtime pins these names: `CapacityConstraintGate`,
`capacity_constraint_preflight`, `CapacityConstraintGateTypeError`,
`CapacityConstraintMisroutedHaltCarrierError`.

`CapacityConstraintGate` is a **stateless**, non-carrier namespace (matching the CapitalMargin /
Liquidity precedent): it carries no state and requires no construction state.

```
__slots__ = ()
preflight = staticmethod(capacity_constraint_preflight)
```

The exact preflight signature is **keyword-only**, with **no positional parameters**, **no defaults**,
and **no extra keyword parameters**:

```
capacity_constraint_preflight(
    *,
    evidence_envelope,
    venue_readiness,
    liquidity_evidence,
    capital_evidence,
)
```

`CapacityConstraintEvidenceContext is NOT an input` to the preflight; it is only the pass output.

Exact required input types (exact-type only):

```
type(evidence_envelope) is PostProfitabilityEvidenceEnvelope
type(venue_readiness) is VenueInstrumentReadinessStateContext
type(liquidity_evidence) is LiquidityCapacityEvidenceContext
type(capital_evidence) is CapitalMarginEvidenceContext
```

An exact `BlockedPacket` or exact `NoEligibleHaltPacket` supplied to any input slot must raise
`CapacityConstraintMisroutedHaltCarrierError` and must **never produce a packet**. Any other wrong
input type must raise `CapacityConstraintGateTypeError` and must **never produce a packet**.

### Pass return contract

On pass, `capacity_constraint_preflight` **pass returns** a `CapacityConstraintEvidenceContext`,
produced only by the factory `make_capacity_constraint_evidence_context`, which receives exactly the
**12 caller-supplied provenance parameters**; `component_name` and `boundary_version` are never passed
because the factory sets them internally.
`CapacityConstraintEvidenceContext` is the **output certificate**, **never an input carrier**.

Exact source mapping on pass:

```
post_profitability_source_contract = evidence_envelope.source_contract
post_profitability_source_artifact = evidence_envelope.source_artifact
post_profitability_source_field = evidence_envelope.source_field
venue_readiness_source_contract = venue_readiness.source_contract
venue_readiness_source_artifact = venue_readiness.source_artifact
venue_readiness_source_field = venue_readiness.source_field
liquidity_capacity_source_contract = liquidity_evidence.source_contract
liquidity_capacity_source_artifact = liquidity_evidence.source_artifact
liquidity_capacity_source_field = liquidity_evidence.source_field
capital_margin_source_contract = capital_evidence.source_contract
capital_margin_source_artifact = capital_evidence.source_artifact
capital_margin_source_field = capital_evidence.source_field
```

### Canonical identity and blocked provenance

`PostProfitabilityEvidenceEnvelope` is the **canonical** identity / provenance source once all four
upstream carriers structurally agree. Every blocked packet uses provenance from `evidence_envelope`
only:

```
evidence_envelope.source_contract
evidence_envelope.source_artifact
evidence_envelope.source_field
```

**No blocked packet may use** `venue_readiness` / `liquidity_evidence` / `capital_evidence`
provenance.

### BlockedPacket contract

Every blocked branch returns an existing `BlockedPacket` built with `make_blocked_packet` using
exactly this field mapping:

```
component_name = CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME
origin_component = CAPACITY_CONSTRAINT_EVIDENCE_BOUNDARY_COMPONENT_NAME
origin_result_status = PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
status = PLANNING_GATE_BLOCKED_NEEDS_EVIDENCE
blocked_status = BLOCKED_NEEDS_EVIDENCE
reason_code = the exact branch token from the branch-to-token table
missing_or_invalid_field = the exact offending field name when branch-specific and known, otherwise None
source_contract = evidence_envelope.source_contract
source_artifact = evidence_envelope.source_artifact
source_field = evidence_envelope.source_field
deterministic_next_action = NEXT_ACTION_OBTAIN_EVIDENCE
human_review_required = True
may_retry_after_evidence = True
created_from_contract = GATE_SOURCE_CONTRACT
boundary_version = BOUNDARY_VERSION
```

with:

```
GATE_SOURCE_CONTRACT = "phase5_capacity_constraint_evidence_boundary_implementation_planning.md"
```

### Branch-to-token constants and mapping

The future Slice 0 runtime pins these exact constant names and exact string values:

```
CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE"
CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH"
CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH = "CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH"
CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE = "CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE"
```

Exact branch-to-token mapping:

- missing carrier or missing required field/attribute -> `CAPACITY_CONSTRAINT_BLOCKED_MISSING_EVIDENCE`
- malformed scalar grammar or invalid scalar value -> `CAPACITY_CONSTRAINT_BLOCKED_MALFORMED_EVIDENCE`
- 4-way identity mismatch, side mismatch, or size-magnitude mismatch -> `CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH`
- unit mismatch -> `CAPACITY_CONSTRAINT_BLOCKED_UNIT_MISMATCH`
- stale epoch comparison -> `CAPACITY_CONSTRAINT_BLOCKED_STALE_EVIDENCE`
- value/reference present and well-formed but not resolvable within the checked scope -> `CAPACITY_CONSTRAINT_BLOCKED_UNDEFINED_EVIDENCE`

Wrong-type / misrouted halt carriers are programmatic errors, **not** blocked tokens.

### Missing vs malformed vs undefined classification

**MISSING:** one of the four required upstream carrier arguments is absent; or a required
field/attribute is absent from an otherwise correct carrier.

**MALFORMED:** required scalar value is present but is None; required scalar value is **not exact str**
where exact str is required; empty string; whitespace-only; leading/trailing whitespace; Decimal scalar
with invalid grammar; Decimal scalar parsing to NaN or Infinity; epoch/tolerance scalar that is not a
base-10 integer string; bool/int/float/complex/Decimal objects supplied instead of exact str are
malformed, not coerced.

**UNDEFINED:** the required value/reference is present and grammatically well-formed but cannot be
resolved within the four supplied carriers' checked scope. Do not use undefined for missing fields. Do
not use undefined for None / empty / whitespace / malformed scalar grammar.

### Decimal size parsing and comparison

Size fields must be exact str and are parsed with `Decimal` only: **no float coercion**, no int
coercion, no bool coercion, no implicit conversion from non-str types, no rounding, no quantization,
and no normalization for equality other than Decimal value comparison. Reject NaN and Infinity.
Reject scientific notation such as `"1E+3"`. Reject signs, commas, underscores, leading/trailing
whitespace,
and locale formats. Allowed grammar is non-negative base-10 decimal notation with digits before the
decimal point and optional fractional digits after one decimal point, e.g. `"0"`, `"1"`, `"1.0"`,
`"123.45"`.

Exact size comparison (structural convergence only — not sizing, not min(), not final capacity, not
tradable size, not allocation/exposure/balance/order preparation):

```
Decimal(size_a).compare(Decimal(size_b)) == Decimal("0")
```

### Epoch and tolerance parsing and comparison

Epoch and tolerance fields must be exact str and are parsed as base-10 non-negative integers only: no
float coercion, no int coercion from non-str, no bool coercion, no Decimal coercion, and
**no default tolerance**.
Missing tolerance is missing evidence; malformed tolerance is malformed evidence.
**No clock reads**: no time.now / datetime.now / system time.

Exact staleness formula:

```
abs(int(epoch_a) - int(epoch_b)) <= int(tolerance)
```

The only arithmetic allowed in Slice 0 is this integer subtraction inside `abs(...)` for epoch
tolerance comparison; size comparison uses Decimal compare/equality only.

### Forbidden logic guard (Slice 0)

Slice 0 performs and produces none of: no min(), no max(), no final capacity, no computed capacity
value, no tradable size, no order size, no allocation, no exposure value, no exposure runtime, no
balance runtime, no wallet reservation, no routing, no execution preparation, no paper/live readiness,
no PnL, no net edge, no alpha/edge claim, and no economic actionability. **NO ORDER EXISTS.** Slice 0
uses no float in parsing or comparison.
<!-- GATE-CONTRACT-END -->

## 7.3 Slice 0 final micro-hardening (charter amendment)

<!-- GATE-HARDENING-START -->
This section finalises four Slice 0 soft spots and preserves every §7.2 GATE-CONTRACT rule. It
implements nothing. **NO ORDER EXISTS** at this boundary.

### Deterministic missing_or_invalid_field mapping

`missing_or_invalid_field` must be **deterministic**, **branch-specific**, and **never chosen dynamically**.
When multiple fields fail in the same branch, the pinned branch-local order determines the first
reported `missing_or_invalid_field`.

- **Missing carrier:** the exact missing input parameter name, one of `evidence_envelope`,
  `venue_readiness`, `liquidity_evidence`, `capital_evidence`.
- **Missing required field/attribute:** the exact missing attribute name as written in the
  charter/schema.
- **Malformed scalar:** the exact malformed scalar field name.
- **Identity mismatch:** follows the pinned identity sub-check order below; the first failing sub-check
  determines it.
- **Unit mismatch:** follows this pinned order (first failing sub-check determines it): `size_unit`,
  `observed_size_unit`, `capacity_unit`, `required_capital_unit`, `available_free_capital_unit`.
- **Stale evidence:** follows this pinned order (first failing epoch comparison determines it):
  `liquidity_snapshot_epoch_ms`, `required_capital_epoch_ms`,
  `available_free_capital_snapshot_epoch_ms`.
- **Undefined evidence:** the exact field whose present, well-formed value is not resolvable within the
  checked scope.

### Identity sub-check order

The exact **identity sub-check order** is, with the **first failing sub-check** determining
`missing_or_invalid_field` and all six failures mapping to
`CAPACITY_CONSTRAINT_BLOCKED_IDENTITY_MISMATCH`:

1. `venue` 4-way convergence
2. `instrument_id` 4-way convergence
3. `base_asset` 4-way convergence
4. `quote_asset` 4-way convergence
5. side convergence: `evidence_envelope.side == capital_evidence.side`
6. size magnitude convergence of `observed_size`:

```
evidence_envelope.observed_size == liquidity_evidence.observed_size == capital_evidence.observed_size as Decimal magnitudes
```

### UNDEFINED branch trigger

`UNDEFINED` is a **defensive but reachable** branch, **not dead code**. UNDEFINED means a required
value/reference is present, exact-str, non-empty, non-whitespace, scalar-grammar-valid, and not
missing/malformed, but it cannot be resolved inside the closed four-carrier checked scope.

Concrete reachable examples:

- a unit label is grammatically valid but outside the **finite allowed unit vocabulary** pinned by the contributing carrier schemas;
- a venue/instrument/base/quote identifier is grammatically valid but outside the **finite identity vocabulary** available within the four supplied carriers' checked scope;
- a `source_contract`/`source_artifact`/`source_field` reference is present and well-formed but is **not resolvable** among the four supplied carriers' provenance triplets.

Exclusions (these never use UNDEFINED):

- None is MALFORMED, not UNDEFINED;
- empty string is MALFORMED, not UNDEFINED;
- whitespace-only string is MALFORMED, not UNDEFINED;
- missing attribute is MISSING, not UNDEFINED;
- invalid Decimal grammar is MALFORMED, not UNDEFINED;
- invalid epoch/tolerance grammar is MALFORMED, not UNDEFINED;
- a mismatch among resolvable values remains IDENTITY_MISMATCH / UNIT_MISMATCH / STALE as applicable, not UNDEFINED.

### AST / operator lock (future runtime test requirement)

The Slice 0 runtime tests must include an AST / **operator lock** scoped to
`phase5/capacity_constraint_evidence_boundary.py` after implementation. This is a
**future runtime test requirement**; the planning doc carries no runtime class/def implementation.

The only arithmetic/comparison the lock allows is Decimal size equality via
`Decimal(...).compare(...) == Decimal("0")` and integer epoch tolerance via
`abs(int(epoch_a) - int(epoch_b)) <= int(tolerance)`.

Forbidden AST constructs for Slice 0 runtime: `ast.Add`, `ast.Mult`, `ast.Div`, `ast.FloorDiv`,
`ast.Mod`, `ast.Pow`, `ast.MatMult`, and `ast.USub` for negative numeric construction.

Forbidden calls: calls to float, calls to min, calls to max, calls to sum, calls to round, and calls to sorted for branch ordering.

Forbidden imports: any import of math, statistics, numpy, pandas, datetime, time, os, socket, requests, urllib, subprocess, json.

`ast.Sub is allowed only` inside the epoch tolerance expression equivalent to
`abs(int(epoch_a) - int(epoch_b)) <= int(tolerance)`; `ast.Sub` must not appear in
size/capacity/economic/order/allocation/exposure logic.
`ast.LtE is allowed only` for the epoch tolerance comparison; no economic/capacity sufficiency
comparison is allowed.
<!-- GATE-HARDENING-END -->

## 8. Deferred decisions

The following are **deferred** and require separate, explicitly authorized work:

- the boundary's gate/preflight function shape and canonical-identity selection are now pinned in
  §7.2 (Slice 0 structural-auditor interface) and are **no longer deferred**; the carrier's exact
  closed field set remains pinned in §6A;
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
