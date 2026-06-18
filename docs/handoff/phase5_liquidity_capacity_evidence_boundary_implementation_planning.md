# Phase 5 Component Implementation-Planning — `phase5_liquidity_capacity_evidence_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It jointly designs two future components and
defines only their contracts, the identity-equality comparison rule, the deterministic supplied-scalar
staleness rule, the inclusive capacity-sufficiency rule, the failure taxonomy, the blocked/no-eligible
reason vocabulary, and the deferred decisions for a future, separately authorized offline/TDD
implementation task.

- `component_name`: `phase5_liquidity_capacity_evidence_boundary`.
- This artifact will **jointly design two future components**: (1) `LiquidityCapacityEvidenceContext`
  and (2) `LiquidityCapacityGate` / `liquidity_capacity_preflight`.
- The future evidence carrier is pinned as `LiquidityCapacityEvidenceContext` with factory
  `make_liquidity_capacity_evidence_context`.
- The future gate is pinned as `LiquidityCapacityGate` / `liquidity_capacity_preflight`.
- The two future components are LiquidityCapacityEvidenceContext and LiquidityCapacityGate / liquidity_capacity_preflight.
- The future function shape is pinned as `liquidity_capacity_preflight(*, evidence_envelope, liquidity_evidence)`.
- This planning task must not implement any of these symbols.

This boundary evaluates supplied liquidity/depth capacity evidence against an upstream evidence
envelope. It is a capacity sufficiency boundary only. Sufficiency here means only: explicit supplied
capacity evidence covers the explicit observed size for this boundary. This is not actionability and
not execution safety. Passing this future boundary must not imply safe-to-trade, executable,
actionable, order-ready, paper-ready, live-ready, or candidate status. Do not broaden sufficient
capacity into execution readiness.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_post_profitability_evidence_envelope_boundary` planning artifact](phase5_post_profitability_evidence_envelope_implementation_planning.md)
- [`phase5_venue_instrument_readiness_boundary` planning artifact](phase5_venue_instrument_readiness_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

The upstream explicit evidence envelope is `PostProfitabilityEvidenceEnvelope`; this boundary
consumes it as an opaque, exact-typed input and reads only its already-explicit identity, size, and
epoch fields. It must not put "slippage" in the component name; any slippage evidence is passive
metadata only and must not drive gate decisions.

## 2. Gate V1 role

- It is a pure/offline/deterministic liquidity/depth capacity sufficiency gate.
- It is a capacity sufficiency boundary only.
- It consumes exact PostProfitabilityEvidenceEnvelope plus exact LiquidityCapacityEvidenceContext.
- It is not a slippage calculator.
- It is not a net-edge calculator.
- It is not a sizing engine.
- It is not an order router.
- It is not an execution component.
- It is not a balance/capital/margin component.
- It is not a reporting component.
- It is not paper/live readiness.
- It must not decide whether to trade.
- It must not produce order size, allocation, max tradable size, fill probability, actionability,
  paper/live authority, or execution instruction.

## 3. Hard semantic boundary

- Sufficiency here means only: explicit supplied capacity evidence covers the explicit observed size.
- Passing this future boundary must not imply safe-to-trade, executable, actionable, order-ready, paper-ready, live-ready, or candidate status.
- Do not broaden sufficient capacity into execution readiness.
- This is not trade readiness, not actionability, not execution safety, and not proof an order can be placed.

## 4. LiquidityCapacityEvidenceContext planned carrier contract

- Future carrier wraps only explicit supplied liquidity/depth capacity evidence needed by the gate.
- It must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only.
- It must not read env/config/files/db/network/time.
- It must not compute or infer liquidity, depth, or capacity.
- No api calls, no network probes, no retries, no ping checks, no time fetching.
- No parsing or inferring identity/size/capacity from strings.
- No parsing of source_artifact.

### 4.1 Required planned fields

- `component_name`
- `venue`
- `instrument_id`
- `base_asset`
- `quote_asset`
- `observed_size`
- `observed_size_unit`
- `available_capacity`
- `capacity_unit`
- `liquidity_snapshot_epoch_ms`
- `evidence_epoch_tolerance_ms`
- `source_contract`
- `source_artifact`
- `source_field`
- `liquidity_evidence_id`
- `boundary_version`
- `estimated_slippage_bps` (optional passive metadata)

### 4.2 Field discipline

- All identity/provenance/string fields must be exact, non-empty, non-whitespace str (`type(value) is str`; str subclasses rejected), preserved verbatim.
- Numeric magnitude fields must be exact, non-empty decimal strings, preserved verbatim (`observed_size`, `available_capacity`, and the passive `estimated_slippage_bps`).
- Decimal strings reject float objects, int objects, Decimal objects, bool, None, bytes, dicts, exponent notation, NaN, Infinity, signed Infinity, empty, whitespace, and malformed decimal text. Negative magnitudes are rejected as a carrier-format error where a magnitude must be unsigned.
- liquidity_snapshot_epoch_ms and evidence_epoch_tolerance_ms are canonical unsigned integer strings, preserved verbatim.
- `component_name` is fixed by the factory to `phase5_liquidity_capacity_evidence_boundary` and is not a factory parameter.

### 4.3 Slippage passivity

- estimated_slippage_bps is passive evidence/audit metadata only.
- The gate must not read estimated_slippage_bps for decisioning.
- The gate must not compute net-edge minus slippage.
- The gate must not compute a slippage model.
- The gate must not compare slippage against profitability or any threshold.

## 5. Gate input contract

- liquidity_capacity_preflight accepts exact type(evidence_envelope) is PostProfitabilityEvidenceEnvelope.
- subclasses rejected.
- raw dict/Mapping/JSON/duck-typed objects rejected.
- exact BlockedPacket or exact NoEligibleHaltPacket received on either argument is a misroute and must be rejected as a programmatic routing bug.
- liquidity_evidence must be exact LiquidityCapacityEvidenceContext.
- wrong type/misroute must be TypeError / MisroutedHaltCarrierError, never a market packet.
- Missing/malformed/wrong-type/ambiguous liquidity evidence is BlockedPacket, not NoEligible.

## 6. Identity-equality comparison rule

- The gate compares the envelope's explicit venue, instrument_id, base_asset, and quote_asset to the liquidity evidence's by exact, case-sensitive equality.
- Identity mismatch is a BlockedPacket, not NoEligible.
- No case normalization, no alias mapping, no semantic broadening.
- No reach-back beyond the explicit envelope and the explicit liquidity evidence.
- Do not parse or infer identity from any string field.

## 7. Deterministic staleness rule

- No internal clock.
- No time.time(), datetime.now(), utcnow(), monotonic(), or runtime clock import.
- Staleness is a deterministic comparison of supplied scalar fields only.
- Planned equation: abs(evidence_envelope.observed_at_epoch_ms - liquidity_snapshot_epoch_ms) <= evidence_epoch_tolerance_ms.
- The upstream epoch field is the envelope's already-explicit `observed_at_epoch_ms`; if the relevant
  upstream epoch field name differs at implementation time, the implementation task must read repo
  patterns and use the existing field — it must not invent a clock.
- Missing or malformed epoch or tolerance fields fail closed.
- Negative epoch tolerance fails closed.
- Stale liquidity evidence returns a BlockedPacket, not a NoEligibleHaltPacket.

## 8. Capacity-sufficiency rule

- The gate compares only supplied magnitudes: observed_size <= available_capacity.
- The inequality is inclusive: equal capacity is sufficient.
- available_capacity of "0" or negative is malformed liquidity evidence and returns a BlockedPacket, not a NoEligibleHaltPacket.
- observed_size that is zero, negative, or malformed fails closed per the upstream envelope contract and is never silently reinterpreted.
- Unit mismatch between observed_size_unit and capacity_unit returns a BlockedPacket.
- Insufficient positive capacity with valid identity/unit/staleness returns a NoEligibleHaltPacket.
- Sufficient capacity with valid identity/unit/staleness returns the exact same upstream evidence envelope object by identity.
- No partial fill, no reduced size, no max tradable size, no allocation, no order quantity, no order intent, and no routing.

## 9. Decimal conversion rule

- The gate may convert decimal strings to Decimal only in local ephemeral comparison variables.
- Decimal conversion must never mutate evidence_envelope or LiquidityCapacityEvidenceContext attributes.
- No float arithmetic, no Decimal-from-float, no rounding/quantize, and no economic recalculation.

## 10. Failure taxonomy

1. Programmatic wrong-path / wrong-type:
   - wrong evidence_envelope type, wrong liquidity_evidence type, subclasses, raw objects, exact halt carrier misroute on either argument.
   - TypeError / MisroutedHaltCarrierError.
   - never BlockedPacket or NoEligibleHaltPacket.
2. Exact inputs + missing/malformed/ambiguous/mismatched liquidity evidence:
   - BlockedPacket.
   - Examples: missing field, malformed decimal/epoch, unrecognized unit, identity mismatch, stale evidence, non-positive available_capacity.
   - This means system blindness / missing or non-corresponding capacity evidence, not market insufficiency.
3. Exact inputs + valid identity/unit/staleness + insufficient positive capacity:
   - NoEligibleHaltPacket.
   - This means a valid explicit insufficiency, not missing evidence.
4. Exact inputs + valid identity/unit/staleness + sufficient capacity:
   - pass-through identity: return the exact same PostProfitabilityEvidenceEnvelope object.
   - This is not actionable and not trade-ready.

### 10.1 Reason vocabulary to pin for future implementation

- LIQUIDITY_CAPACITY_GATE_BLOCKED_MISSING_LIQUIDITY_EVIDENCE
- LIQUIDITY_CAPACITY_GATE_BLOCKED_MALFORMED_LIQUIDITY_EVIDENCE
- LIQUIDITY_CAPACITY_GATE_BLOCKED_IDENTITY_MISMATCH
- LIQUIDITY_CAPACITY_GATE_BLOCKED_UNIT_MISMATCH
- LIQUIDITY_CAPACITY_GATE_BLOCKED_STALE_EVIDENCE
- LIQUIDITY_CAPACITY_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPACITY

The reason vocabulary uses only the `LIQUIDITY_CAPACITY_GATE_` prefix; it does not copy any prior
profitability or threshold reason tokens, and it introduces no net-edge or profitability-threshold
semantics.

## 11. Provenance rule

- Any future BlockedPacket or NoEligibleHaltPacket must preserve the rejected upstream
  opportunity/evidence lineage.
- Packet source_contract/source_artifact/source_field must come from the upstream PostProfitabilityEvidenceEnvelope, not from LiquidityCapacityEvidenceContext.
- Liquidity evidence provenance may be recorded as decision context only if the existing packet schema
  supports it; liquidity evidence provenance must not overwrite the upstream envelope provenance.
- Do not invent new packet fields, schemas, factories, or reason builders.

## 12. Explicitly prohibited V1 checks

- No position sizing.
- No balance/capital/margin.
- No wallet/custody.
- No order routing.
- No order quantity.
- No fill probability.
- No orderbook simulation.
- No slippage model.
- No net-edge recalculation.
- No profitability recalculation.
- No threshold copying.
- No clock/time/datetime/now.
- No network/api/db/file/env/config.
- No source_artifact parsing.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden output names and claims

The future carrier/gate must NOT be named, aliased, or emitted as any of:

- `ActionableCandidate`
- `TradeCandidate`
- `ReadyEnvelope`
- `ExecutableSignal`
- `Opportunity`
- `ExecutionPayload`
- `Signal`
- `OrderIntent`
- `Fillable`
- `Tradable`
- `Candidate`

This boundary produces no order, no signal, no candidate, no allocation, no sizing, no order quantity,
no max tradable size, no fill probability, no actionability verdict, no trade-readiness verdict, and no
execution instruction. Sufficient capacity is a capacity-evidence fact only; it authorizes no trading,
no paper/live work, and no readiness-to-trade claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 13. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- Slippage modelling
- Order sizing / allocation
- Balance/capital/margin gate
- Order routing / execution
- Fill-probability / orderbook simulation
- Multi-venue / multi-source capacity aggregation
- Paper/live execution

## 14. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 15. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the gate function/class, the evidence carrier, or selecting the next component.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no PnL, no alpha, no actionability, no readiness.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no fill certainty, no liquidity-correctness guarantee, no source-truth guarantee, no price-correctness guarantee, no market-truth guarantee.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. A passed capacity sufficiency gate is still only an explicit-evidence-filtered result. This is a component planning gate only; it authorizes a separately approved offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 16. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `LiquidityCapacityEvidenceContext` and `LiquidityCapacityGate` / `liquidity_capacity_preflight`
  may follow, with failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged blindly.
