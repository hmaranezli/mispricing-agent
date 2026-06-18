# Phase 5 Component Implementation-Planning — `phase5_capital_margin_evidence_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It jointly designs two future components and
defines only their contracts, the identity-equality comparison rule, the capital-unit binding rule,
the two deterministic supplied-scalar staleness checks, the inclusive capital-sufficiency rule, the
failure taxonomy, the blocked/no-eligible reason vocabulary, and the deferred decisions for a future,
separately authorized offline/TDD implementation task.

- `component_name`: `phase5_capital_margin_evidence_boundary`.
- This artifact will **jointly design two future components**: (1) `CapitalMarginEvidenceContext`
  and (2) `CapitalMarginGate` / `capital_margin_preflight`.
- The future evidence carrier is pinned as `CapitalMarginEvidenceContext` with factory
  `make_capital_margin_evidence_context`.
- The future gate is pinned as `CapitalMarginGate` / `capital_margin_preflight`.
- The two future components are CapitalMarginEvidenceContext and CapitalMarginGate / capital_margin_preflight.
- The future function shape is pinned as `capital_margin_preflight(*, evidence_envelope, capital_evidence, expected_capital_scope_id)`.
- This planning task must not implement any of these symbols.

This boundary audits supplied capital/margin evidence against an upstream evidence envelope. It is a
capital sufficiency boundary only. Sufficiency here means only: explicit supplied free-capital evidence
covers the explicit supplied required-capital evidence for this boundary's capital scope. This is not
actionability and not execution safety. Passing this future boundary must not imply safe-to-trade,
executable, actionable, order-ready, paper-ready, live-ready, or candidate status. Do not broaden
sufficient capital into execution readiness.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_post_profitability_evidence_envelope_boundary` planning artifact](phase5_post_profitability_evidence_envelope_implementation_planning.md)
- [`phase5_liquidity_capacity_evidence_boundary` planning artifact](phase5_liquidity_capacity_evidence_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

The upstream explicit evidence envelope is `PostProfitabilityEvidenceEnvelope`; this boundary consumes
it as an opaque, exact-typed input and reads only its already-explicit identity, size, and epoch
fields.

## 2. Core principle — ledger auditor, not calculator

- The capital/margin boundary is a ledger auditor, not a calculator.
- required_capital and available_free_capital are supplied evidence scalars; the gate audits them, it
  does not derive them.
- It must not compute price.
- It must not compute notional.
- It must not compute leverage.
- It must not compute fee.
- It must not compute a margin requirement.
- It must not compute capital reservation.
- It must not compute sizing.
- It must not compute allocation.
- It must not compute routing or execution.
- It must not compute PnL, profitability, or net edge.
- It is a pure/offline/deterministic capital sufficiency ledger auditor.
- It consumes exact PostProfitabilityEvidenceEnvelope plus exact CapitalMarginEvidenceContext plus the
  exact control scalar expected_capital_scope_id.
- It is not a sizing engine.
- It is not an order router.
- It is not an execution component.
- It is not a reporting component.
- It must not decide whether to trade.

## 3. Hard semantic boundary

- Sufficiency here means only: explicit supplied free-capital evidence covers the explicit supplied
  required-capital evidence for the audited capital scope.
- Passing this future boundary must not imply safe-to-trade, executable, actionable, order-ready, paper-ready, live-ready, or candidate status.
- Do not broaden sufficient capital into execution readiness.
- This is not trade readiness, not actionability, not execution safety, and not proof an order can be placed.

## 4. CapitalMarginEvidenceContext planned carrier contract

- Future carrier wraps only explicit supplied capital/margin evidence needed by the gate.
- It must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only.
- It must not read env/config/files/db/network/time.
- It must not compute or infer capital, margin, or balance.
- No api calls, no network probes, no retries, no ping checks, no time fetching.
- No parsing or inferring identity/size/capital from strings.
- No parsing of source_artifact.

### 4.1 Required planned fields

The field set is exact and closed:

- `component_name`
- `venue`
- `instrument_id`
- `base_asset`
- `quote_asset`
- `side`
- `observed_size`
- `observed_size_unit`
- `required_capital`
- `required_capital_unit`
- `available_free_capital`
- `available_free_capital_unit`
- `required_capital_epoch_ms`
- `available_free_capital_snapshot_epoch_ms`
- `evidence_epoch_tolerance_ms`
- `capital_scope_id`
- `source_contract`
- `source_artifact`
- `source_field`
- `capital_evidence_id`
- `boundary_version`

### 4.2 Field discipline

- All carrier fields must be exact, non-empty, non-whitespace str (`type(value) is str`; str subclasses rejected), preserved verbatim.
- No decimal/int parsing in the carrier.
- No numeric validation in the carrier — magnitude-like and epoch-like fields are kept as exact strings only; their grammar and validity are audited later by the gate, never by the carrier.
- No bool/truthiness/coercion — the carrier raises on `bool`/`len`/`int`/`float`/`complex`/`index`/`str`/`bytes`.
- Safe repr exposes only component_name and boundary_version.
- component_name is fixed by the factory to phase5_capital_margin_evidence_boundary and is not a factory parameter.

## 5. Gate input and control-scalar contract

- capital_margin_preflight accepts exact type(evidence_envelope) is PostProfitabilityEvidenceEnvelope.
- subclasses rejected.
- raw dict/Mapping/JSON/duck-typed objects rejected.
- exact BlockedPacket or exact NoEligibleHaltPacket received on any argument is a misroute and must be rejected as a programmatic routing bug.
- capital_evidence must be exact CapitalMarginEvidenceContext.
- expected_capital_scope_id must be an exact, non-empty, non-whitespace str.
- wrong type/misroute must be TypeError / MisroutedHaltCarrierError, never a market packet.
- A wrong-type control scalar is a CapitalMarginGateTypeError (a programmatic wrong-path, never a market packet).
- Missing/malformed/wrong-type/ambiguous capital evidence is BlockedPacket, not NoEligible.

## 6. Identity-equality comparison rule

- The gate compares the envelope's explicit venue, instrument_id, base_asset, quote_asset, and side to the capital evidence's by exact, case-sensitive equality.
- side binding is an identity comparison; a side mismatch is an identity mismatch.
- The size-magnitude binding is an identity comparison: Decimal(evidence_envelope.observed_size) != Decimal(capital_evidence.observed_size) is an identity mismatch (compared as Decimal magnitudes, not raw strings).
- The capital-scope binding is an identity comparison: expected_capital_scope_id != capital_evidence.capital_scope_id is an identity mismatch.
- Identity mismatch is a BlockedPacket, not NoEligible.
- No case normalization, no alias mapping, no semantic broadening.
- No reach-back beyond the explicit envelope, the explicit capital evidence, and the explicit control scalar.
- Do not parse or infer identity from any string field.

## 7. Unit-binding rule

- evidence_envelope.size_unit must equal capital_evidence.observed_size_unit.
- capital_evidence.required_capital_unit must equal capital_evidence.available_free_capital_unit.
- Comparison is exact, case-sensitive equality; no unit normalization and no FX/oracle conversion.
- Unit mismatch returns a BlockedPacket.

## 8. Deterministic staleness rule

- No internal clock.
- No time.time(), datetime.now(), utcnow(), monotonic(), or runtime clock import.
- Staleness is a deterministic comparison of supplied scalar fields only.
- There are two separate staleness checks; both must pass.
- Required-capital staleness: abs(int(evidence_envelope.observed_at_epoch_ms) - int(required_capital_epoch_ms)) <= int(evidence_epoch_tolerance_ms).
- Free-capital staleness: abs(int(evidence_envelope.observed_at_epoch_ms) - int(available_free_capital_snapshot_epoch_ms)) <= int(evidence_epoch_tolerance_ms).
- If either staleness check fails the gate returns a BlockedPacket.
- The upstream epoch field is the envelope's already-explicit `observed_at_epoch_ms`; if the relevant
  upstream epoch field name differs at implementation time, the implementation task must read repo
  patterns and use the existing field — it must not invent a clock.
- Missing or malformed epoch or tolerance fields fail closed.
- Negative epoch tolerance fails closed.
- Stale capital evidence returns a BlockedPacket, not a NoEligibleHaltPacket.

## 9. Capital-sufficiency rule

- The gate compares only supplied scalars: required_capital <= available_free_capital.
- The inequality is inclusive: equal capital is sufficient.
- required_capital that is zero, negative, or malformed is malformed capital evidence and returns a BlockedPacket, not a NoEligibleHaltPacket.
- observed_size that is zero, negative, or malformed is malformed capital evidence and returns a BlockedPacket.
- Negative available_free_capital is malformed capital evidence and returns a BlockedPacket.
- available_free_capital of "0" is a valid explicit insufficiency and returns a NoEligibleHaltPacket, not a BlockedPacket (free capital is zero while required capital is positive, so it is an explicit shortfall, not missing evidence).
- Insufficient positive capital with valid identity/unit/staleness returns a NoEligibleHaltPacket.
- Sufficient capital with valid identity/unit/staleness returns the exact same upstream evidence envelope object by identity.
- No partial sizing, no allocation, no order quantity, no order intent, no routing, and no execution.

## 10. Decimal conversion rule

- The gate may convert decimal strings to Decimal only in local ephemeral comparison variables.
- Epoch and tolerance strings may be converted to int only in local ephemeral comparison variables.
- Decimal conversion must never mutate evidence_envelope or CapitalMarginEvidenceContext attributes.
- No float arithmetic, no Decimal-from-float, no rounding/quantize, and no economic recalculation.

## 11. Branch priority

The gate evaluates in this fixed order; the first matching outcome wins:

1. exact BlockedPacket or NoEligibleHaltPacket in any argument -> MisroutedHaltCarrierError
2. exact type checks — evidence_envelope must be exact PostProfitabilityEvidenceEnvelope, capital_evidence must be exact CapitalMarginEvidenceContext, expected_capital_scope_id must be an exact non-empty str; a wrong type or wrong control scalar is a CapitalMarginGateTypeError
3. missing allow-listed capital evidence field -> CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE
4. malformed grammar / scalar validity -> CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE (observed_size malformed or <= 0; required_capital malformed or <= 0; available_free_capital malformed or < 0; required_capital_epoch_ms / available_free_capital_snapshot_epoch_ms / evidence_epoch_tolerance_ms malformed)
5. identity mismatch -> CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH (venue/instrument_id/base_asset/quote_asset/side, size magnitude, expected_capital_scope_id)
6. unit mismatch -> CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH
7. stale evidence -> CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE (either of the two staleness checks)
8. insufficient capital -> CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL (available_free_capital == 0, or required_capital > available_free_capital)
9. sufficient -> same evidence_envelope by identity

## 12. Failure taxonomy

1. Programmatic wrong-path / wrong-type:
   - wrong evidence_envelope type, wrong capital_evidence type, wrong-type expected_capital_scope_id, subclasses, raw objects, exact halt carrier misroute on any argument.
   - TypeError / MisroutedHaltCarrierError.
   - never BlockedPacket or NoEligibleHaltPacket.
2. Exact inputs + missing/malformed/ambiguous/mismatched capital evidence:
   - BlockedPacket.
   - Examples: missing field, malformed decimal/epoch, non-positive required_capital, negative available_free_capital, unit mismatch, identity mismatch, stale evidence.
   - This means system blindness / missing or non-corresponding capital evidence, not market insufficiency.
3. Exact inputs + valid identity/unit/staleness + insufficient positive capital (or zero free capital):
   - NoEligibleHaltPacket.
   - This means a valid explicit insufficiency, not missing evidence.
4. Exact inputs + valid identity/unit/staleness + sufficient capital:
   - pass-through identity: return the exact same PostProfitabilityEvidenceEnvelope object.
   - This is not actionable and not trade-ready.

### 12.1 Reason vocabulary to pin for future implementation

- CAPITAL_MARGIN_GATE_BLOCKED_MISSING_CAPITAL_EVIDENCE
- CAPITAL_MARGIN_GATE_BLOCKED_MALFORMED_CAPITAL_EVIDENCE
- CAPITAL_MARGIN_GATE_BLOCKED_IDENTITY_MISMATCH
- CAPITAL_MARGIN_GATE_BLOCKED_UNIT_MISMATCH
- CAPITAL_MARGIN_GATE_BLOCKED_STALE_EVIDENCE
- CAPITAL_MARGIN_GATE_NO_ELIGIBLE_INSUFFICIENT_CAPITAL

The reason vocabulary uses only the `CAPITAL_MARGIN_GATE_` prefix; it does not copy any prior
liquidity, profitability, or threshold reason tokens, and it introduces no net-edge or
profitability-threshold semantics.

## 13. Provenance rule

- Any future BlockedPacket or NoEligibleHaltPacket must preserve the rejected upstream
  opportunity/evidence lineage.
- Packet source_contract/source_artifact/source_field must come from the upstream PostProfitabilityEvidenceEnvelope, not from CapitalMarginEvidenceContext.
- capital_evidence.source_contract, capital_evidence.source_artifact, capital_evidence.source_field, capital_evidence_id, and boundary_version must not be used as packet provenance.
- Packet reasons and details must not leak raw observed_size, required_capital, available_free_capital, epoch, tolerance, or scope values; only static reason tokens and field names are permitted.
- Do not invent new packet fields, schemas, factories, or reason builders.

## 14. Explicitly prohibited V1 checks

- No position sizing.
- No allocation.
- No order quantity.
- No order routing.
- No execution.
- No wallet fetch.
- No wallet/custody balance fetch, no exchange balance call.
- No network.
- No clock.
- No PnL.
- No profitability.
- No threshold.
- No net-edge.
- No price.
- No notional.
- No fee.
- No leverage.
- No margin formula.
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
no capital reservation, no fill probability, no actionability verdict, no trade-readiness verdict, and
no execution instruction. Sufficient capital is a capital-evidence fact only; it authorizes no trading,
no paper/live work, and no readiness-to-trade claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 15. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- Order sizing / allocation
- Order routing / execution
- Margin requirement modelling
- Leverage / notional / fee computation
- Capital reservation / locking
- Multi-account / cross-margin netting
- Paper/live execution

## 16. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 17. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the gate function/class, the evidence carrier, or selecting the next component.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no PnL, no alpha, no actionability, no readiness.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no solvency guarantee, no capital-correctness guarantee, no balance-truth guarantee, no margin-correctness guarantee, no funds-availability guarantee.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. A passed capital sufficiency gate is still only an explicit-evidence-filtered result. This is a component planning gate only; it authorizes a separately approved offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 18. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `CapitalMarginEvidenceContext` and `CapitalMarginGate` / `capital_margin_preflight`
  may follow, with failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged blindly.
