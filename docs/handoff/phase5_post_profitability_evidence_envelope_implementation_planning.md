# Phase 5 Component Implementation-Planning — `phase5_post_profitability_evidence_envelope_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It designs one future component and defines
only its carrier contract, factory shape, field rules, single-provenance V1 rule, failure taxonomy,
banned output names, and deferred decisions for a future, separately authorized offline/TDD
implementation task.

- `component_name`: `phase5_post_profitability_evidence_envelope_boundary`.
- The future carrier is pinned as `PostProfitabilityEvidenceEnvelope` with factory
  `make_post_profitability_evidence_envelope`.
- This planning task must not implement any of these symbols.

This envelope is an explicit evidence aggregation carrier only. It is NOT a profitability pass certificate, NOT proof that NetEdgeProfitabilityGate evaluated the result, NOT actionable, NOT trade-ready, NOT executable, NOT paper-ready, NOT live-ready, and NOT an order/signal/candidate.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_net_edge_profitability_gate_boundary` planning artifact](phase5_net_edge_profitability_gate_implementation_planning.md)
- [`phase5_net_edge_calculator_boundary` planning artifact](phase5_net_edge_calculator_boundary_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

## 2. Envelope V1 role

- It is an explicit evidence aggregation carrier only.
- It is a frozen carrier that holds one already-computed net-edge result alongside explicitly
  supplied market-topology / size / time evidence.
- It is not a profitability pass certificate.
- It is not proof that NetEdgeProfitabilityGate evaluated the result.
- It is not a calculator.
- It is not a parser.
- It is not an adapter.
- It is not a gate.
- It is not a unit converter.
- It is not an FX/oracle.
- It is not a venue/liquidity/balance/sizing/trading/reporting/paper-live component.
- It must not decide whether to trade.
- It must not produce order size, allocation, readiness, actionability, paper/live authority, or
  execution instruction.

## 3. Future carrier contract

### 3.1 Carrier and factory names

- Future carrier: `PostProfitabilityEvidenceEnvelope`.
- Future factory: `make_post_profitability_evidence_envelope`.
- `component_name` value: `phase5_post_profitability_evidence_envelope_boundary`.

### 3.2 Exact field set (closed, exactly 15 fields)

- `component_name`
- `calculation_result`
- `venue`
- `instrument_id`
- `base_asset`
- `quote_asset`
- `side`
- `observed_size`
- `size_unit`
- `observed_at_epoch_ms`
- `staleness_threshold_ms`
- `source_contract`
- `source_artifact`
- `source_field`
- `boundary_version`

### 3.3 Exact factory shape (pinned, keyword-only)

```text
make_post_profitability_evidence_envelope(
    *,
    calculation_result,
    venue,
    instrument_id,
    base_asset,
    quote_asset,
    side,
    observed_size,
    size_unit,
    observed_at_epoch_ms,
    staleness_threshold_ms,
    source_contract,
    source_artifact,
    source_field,
    boundary_version,
)
```

- The factory is keyword-only (the leading `*,` is mandatory); positional construction is rejected.
- `component_name` is set by the factory to the fixed component value above and is not a factory
  parameter.

## 4. Future carrier rules

- The carrier must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only.
- calculation_result must be exact NetEdgeCalculationResult by type(); subclasses and duck-typed objects are rejected.
- calculation_result must be stored by identity, not copied, unpacked, or serialized.
- All other fields must be exact str, non-empty, non-whitespace; str subclasses are rejected.
- observed_size must be an unsigned canonical decimal string matching `0|[1-9]\d*(\.\d+)?` (no
  leading zeros, no sign, no exponent).
- observed_at_epoch_ms must be a canonical unsigned integer string matching `0|[1-9]\d*` (no leading
  zeros, no sign).
- staleness_threshold_ms must be a canonical unsigned integer string matching `0|[1-9]\d*` (no
  leading zeros, no sign).
- side is exact str only; no enum validation, no BUY/buy normalization, and no semantic interpretation.
- size_unit is exact str only; no unit conversion or normalization.
- The repr must expose only limited non-sensitive identifier fields and must not coerce, evaluate, or
  expose provenance values.

## 5. Single-provenance V1 rule

- V1 is single-provenance aggregation only.
- All envelope market topology/size/time fields are asserted to come from the single explicit source_contract/source_artifact/source_field supplied to the factory.
- Mixed-source aggregation is explicitly deferred and forbidden in V1.

## 6. No-derivation / no-reach-back rule

- No field may be derived from calculation_result, source_artifact, source_field, or any upstream object.
- No reach-back to GrossEdgeObservation.
- This planning artifact bans re-attach, recover, reconstruct, hydrate, enrich, and resolve language;
  the only sanctioned framing is explicitly supplied evidence aggregation only.

## 7. Explicitly prohibited V1 behavior

- Do not parse source_artifact or source_field.
- Do not infer venue/base/quote/instrument/side/size/time from any other field.
- No defaults.
- No clock/time/datetime/now.
- No network/api probes.
- No case or unit normalization.
- No order sizing, balance, margin, liquidity, depth, slippage, venue readiness, trading, reporting,
  paper-live, or execution behavior.

## 8. Failure taxonomy

- Exact BlockedPacket or exact NoEligibleHaltPacket passed as calculation_result -> MisroutedHaltCarrierError.
- Wrong type / None / dict / float / duck / subclass calculation_result -> PostProfitabilityEvidenceEnvelopeTypeError.
- Wrong type / None / dict / float / str subclass / hostile object for string fields -> PostProfitabilityEvidenceEnvelopeTypeError.
- Empty or whitespace string fields -> ValueError (consistent with existing carrier patterns).
- Malformed observed_size / observed_at_epoch_ms / staleness_threshold_ms -> ValueError (consistent
  with existing carrier patterns).
- This component must never return BlockedPacket.
- This component must never return NoEligibleHaltPacket.
- This component must never perform market/economic evaluation.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden output names and claims

The future carrier must NOT be named, aliased, or emitted as any of:

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

The envelope produces no profitability score, no order, no signal, no candidate, no allocation, no
sizing, no actionability, no readiness verdict, and no execution instruction. Aggregating evidence
authorizes no trading, no paper/live work, and no readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 9. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- Mixed-source / multi-provenance aggregation
- Venue readiness gate
- Liquidity/depth/slippage gate
- Balance/capital/margin gate
- Order sizing / allocation
- Readiness/actionability gate
- Side enum / semantic side policy
- Unit normalization / conversion policy
- Paper/live execution

## 10. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 11. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the carrier, the factory, or selecting
  the next component.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no PnL, no alpha, no actionability, no readiness.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no source-truth guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. This envelope is an explicit evidence aggregation only and asserts no tradeable property. A passed profitability gate upstream remains only a threshold-filtered mathematical result.
This is a component planning gate only; it authorizes a separately approved offline/TDD implementation
task, not implementation.
<!-- NO-CLAIMS-END -->

## 12. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `PostProfitabilityEvidenceEnvelope` / `make_post_profitability_evidence_envelope` may follow, with
  failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
