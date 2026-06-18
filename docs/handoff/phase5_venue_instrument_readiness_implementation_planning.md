# Phase 5 Component Implementation-Planning — `phase5_venue_instrument_readiness_boundary`

<!-- FRAMING-START -->
## Status and framing

This document is **implementation-planning only, not implementation**. It is a component-scoped
implementation-planning artifact produced under the
[Phase 5 Implementation-Planning Gate — Entrance Criteria](../protocols/phase5_implementation_planning_gate_entrance_criteria.md).

**No implementation is authorized** by this document. It jointly designs two future components and
defines only their contracts, the identity-equality comparison rule, the explicit status vocabulary,
the failure taxonomy, the blocked/no-eligible reason vocabulary, and the deferred decisions for a
future, separately authorized offline/TDD implementation task.

- `component_name`: `phase5_venue_instrument_readiness_boundary`.
- This artifact will **jointly design two future components**: (1) `VenueInstrumentReadinessStateContext`
  and (2) `VenueInstrumentReadinessGate` / `venue_instrument_readiness_preflight`.
- The future state carrier is pinned as `VenueInstrumentReadinessStateContext` with factory
  `make_venue_instrument_readiness_state_context`.
- The future gate is pinned as `VenueInstrumentReadinessGate` / `venue_instrument_readiness_preflight`.
- The two future components are VenueInstrumentReadinessStateContext and VenueInstrumentReadinessGate / venue_instrument_readiness_preflight.
- The future function shape is pinned as `venue_instrument_readiness_preflight(*, evidence_envelope, readiness_state)`.
- This planning task must not implement any of these symbols.

This boundary evaluates explicit supplied venue/instrument state only. Readiness here means only:
explicit venue/instrument state evidence permits or halts this boundary. This is not trade readiness.
This is not actionability. This is not execution safety. This is not liquidity readiness. This is not
balance/margin readiness. This is not proof an order can be placed.

Implementation still requires separate TDD and explicit authorization.
<!-- FRAMING-END -->

## 1. Dependencies

This component-planning artifact depends on, and must remain consistent with:

- [`phase5_post_profitability_evidence_envelope_boundary` planning artifact](phase5_post_profitability_evidence_envelope_implementation_planning.md)
- [`phase5_net_edge_profitability_gate_boundary` planning artifact](phase5_net_edge_profitability_gate_implementation_planning.md)
- [`phase5_implementation_planning_gate_entrance_criteria.md`](../protocols/phase5_implementation_planning_gate_entrance_criteria.md)

The upstream explicit evidence envelope is `PostProfitabilityEvidenceEnvelope`; this boundary
consumes it as an opaque, exact-typed input and reads only its already-explicit venue/instrument
identity fields.

## 2. Gate V1 role

- It is a pure/offline/deterministic venue/instrument readiness-state gate.
- It consumes exact PostProfitabilityEvidenceEnvelope plus exact VenueInstrumentReadinessStateContext.
- It is not a calculator.
- It is not a parser.
- It is not an adapter.
- It is not a unit converter.
- It is not an FX/oracle.
- It is not a liquidity/orderbook/depth/slippage gate.
- It is not a balance/capital/margin gate.
- It is not an order-sizing/execution/trading/reporting/paper-live component.
- It must not decide whether to trade.
- It must not produce order size, allocation, readiness-to-trade, actionability, paper/live authority, or execution instruction.

## 3. Hard semantic boundary

- Readiness here means only: explicit venue/instrument state evidence permits or halts this boundary.
- Passing this future boundary must not imply safe-to-trade, executable, actionable, paper-ready, live-ready, order-ready, or candidate status.
- This is not trade readiness.
- This is not actionability.
- This is not execution safety.
- This is not liquidity readiness.
- This is not balance/margin readiness.
- This is not proof an order can be placed.

## 4. VenueInstrumentReadinessStateContext planned carrier contract

- Future carrier wraps only explicit supplied venue/instrument readiness-state data needed by the gate.
- It must be frozen, repr-safe, anti-truthiness, anti-coercion, factory-only.
- It must not read env/config/files/db/network/time.
- It must not compute or infer venue/instrument readiness.
- No api calls, no network probes, no retries, no ping checks, no time fetching.
- No parsing or inferring venue/instrument/status from strings.
- No source_artifact parsing.

### 4.1 Required planned fields

- `component_name`
- `venue`
- `instrument_id`
- `base_asset`
- `quote_asset`
- `readiness_status`
- `source_contract`
- `source_artifact`
- `source_field`
- `state_id`
- `boundary_version`

### 4.2 Field discipline

- All carrier fields must be exact, non-empty, non-whitespace str (`type(value) is str`; str subclasses rejected), preserved verbatim.
- readiness_status must be an exact, case-sensitive token from the planned status vocabulary; it is not normalized, broadened, or inferred.
- `component_name` is fixed by the factory to `phase5_venue_instrument_readiness_boundary` and is not a factory parameter.

### 4.3 Planned status vocabulary (explicit, case-sensitive)

- `VENUE_INSTRUMENT_STATE_ACTIVE` — explicit active state (the only permitting state).
- `VENUE_INSTRUMENT_STATE_SUSPENDED` — explicit non-active state.
- `VENUE_INSTRUMENT_STATE_MAINTENANCE` — explicit non-active state.
- `VENUE_INSTRUMENT_STATE_CLOSED` — explicit non-active state.
- `VENUE_INSTRUMENT_STATE_UNSUPPORTED` — explicit non-active state.

## 5. Gate input contract

- venue_instrument_readiness_preflight accepts exact type(evidence_envelope) is PostProfitabilityEvidenceEnvelope.
- subclasses rejected.
- raw dict/Mapping/JSON/duck-typed objects rejected.
- exact BlockedPacket or exact NoEligibleHaltPacket received on either argument is a misroute and must be rejected as a programmatic routing bug.
- readiness_state must be exact VenueInstrumentReadinessStateContext.
- wrong type/misroute must be TypeError / MisroutedHaltCarrierError, never a market packet.
- Missing/malformed/wrong-type/mixed-provenance/ambiguous readiness evidence is BlockedPacket, not NoEligible.

## 6. Identity-equality comparison rule

- The gate compares the envelope's explicit venue, instrument_id, base_asset, and quote_asset to the readiness_state's by exact, case-sensitive equality.
- Identity mismatch is a BlockedPacket, not NoEligible.
- No case normalization, no alias mapping, no spelling repair, no semantic broadening of status.
- No reach-back beyond the explicit envelope and the explicit readiness state.
- Do not parse or infer venue/instrument/status from any string field.

## 7. Status-evaluation rule

- An explicit active state with matching identity passes.
- An explicit suspended/maintenance/closed/unsupported state halts as no-eligible.
- An unrecognized status token is BlockedPacket, not NoEligible.
- Success returns the exact same PostProfitabilityEvidenceEnvelope object identity.
- No new wrapper, no union carrier, no shared base hierarchy, no cross-conversion, no downgrade, no masking.

## 8. Failure taxonomy

1. Programmatic wrong-path / wrong-type:
   - wrong evidence_envelope type, wrong readiness_state type, subclasses, raw objects, exact halt carrier misroute on either argument.
   - TypeError / MisroutedHaltCarrierError.
   - never BlockedPacket or NoEligibleHaltPacket.
2. Exact inputs + missing/malformed/ambiguous/mismatched readiness evidence:
   - BlockedPacket.
   - Examples: missing readiness_state field, malformed field, unrecognized status vocabulary, identity mismatch.
   - This means system blindness / missing or non-corresponding state evidence, not market unreadiness.
3. Exact inputs + identity match + explicit non-active state:
   - NoEligibleHaltPacket.
   - This means a valid explicit state that is not active, not missing evidence.
4. Exact inputs + identity match + explicit active state:
   - pass-through identity: return the exact same PostProfitabilityEvidenceEnvelope object.
   - This is not actionable and not trade-ready.

### 8.1 Reason vocabulary to pin for future implementation

- VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MISSING_READINESS_STATE
- VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_MALFORMED_READINESS_STATE
- VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_IDENTITY_MISMATCH
- VENUE_INSTRUMENT_READINESS_GATE_BLOCKED_UNRECOGNIZED_STATE_VOCABULARY
- VENUE_INSTRUMENT_READINESS_GATE_NO_ELIGIBLE_STATE_NOT_ACTIVE

## 9. Explicitly prohibited V1 checks

- No liquidity/orderbook/depth/slippage checks.
- No balance/capital/margin checks.
- No order sizing.
- No network/api probe, ping, or reachability check.
- No clock/time/datetime/now.
- No defaults.
- No case or unit normalization.
- No source_artifact/source_field parsing.
- No regex extraction from provenance.
- No semantic broadening of status.
- No paper/live/trading/reporting/execution.

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

This boundary produces no order, no signal, no candidate, no allocation, no sizing, no
actionability verdict, no trade-readiness verdict, and no execution instruction. An explicit active
venue/instrument state is a state-evidence fact only; it authorizes no trading, no paper/live work,
and no readiness-to-trade claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 10. Deferred decisions

The following decisions are **deferred** and require separate, explicitly authorized work:

- Liquidity/orderbook/depth/slippage gate
- Balance/capital/margin gate
- Order sizing / allocation
- Trade-readiness / actionability gate
- Dynamic venue/instrument status source
- Multi-venue / multi-provenance readiness aggregation
- Paper/live execution

## 11. Task boundary

- This task makes no phase5 runtime code edits.
- This task does not edit the central handoff/memory file and performs no memory closeout.

## 12. Future implementation gate

- Future implementation must be separately authorized, component-scoped, offline, TDD-first, and declared-provenance.
- This planning artifact does not authorize implementation, the gate function/class, the state carrier, or selecting the next component.

<!-- NO-CLAIMS-START -->
## No-claims statement

This planning artifact makes: no edge, no PnL, no alpha, no actionability, no readiness.
It makes: no paper readiness, no live readiness, no execution readiness, no economics readiness.
It makes: no safety guarantee, no data-quality guarantee, no data-integrity guarantee, no source-truth guarantee.
It makes: no system-ready, no ready-to-fly, and no ready claim of any kind.
It asserts no statistical significance, no stationarity proof, and no economic inference. It does not
prove correctness. A passed venue/instrument readiness-state gate is still only an explicit-state-filtered result. This is a component planning gate only; it authorizes a separately approved offline/TDD implementation task, not implementation.
<!-- NO-CLAIMS-END -->

## 13. Next allowed step

- Only a **separate, explicitly authorized offline/TDD implementation task** for
  `VenueInstrumentReadinessStateContext` and `VenueInstrumentReadinessGate` /
  `venue_instrument_readiness_preflight` may follow, with failing tests first and declared evidence
  provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
