# Phase 6.1 B3 Mapping-Extraction Ratification Charter

> **This is a docs-only ratification/planning charter.** It ratifies or explicitly keeps blocked the
> `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cells that gate Master-B3 Phase-5 gate/mapping wiring. It authorizes NO
> runtime, NO tests, NO lock-test edits, NO Master B3 wiring, NO Phase 5 integration, NO B4 scoring, NO durable
> logs, NO output carrier, NO Shadow Intent runtime/schema, NO live adapter runtime, NO capacity activation, NO
> Phase 6.2 work, NO pytest, NO graphify. It **parses, casts, normalizes, bridges, and wires nothing.** It is
> subordinate to `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`, `docs/handoff/phase5_to_live_canary_roadmap.md`, and
> `CLAUDE.md`; where any conflict arises, those govern.

**Base:** `dde8f65a93f52e8ca11ea5d9b7a13a0941779cca`

---

## 1. Base / Dependency Chain

**Base commit:** `dde8f65a93f52e8ca11ea5d9b7a13a0941779cca`.

References:

- `docs/handoff/phase6_1_completion_sequencing_charter.md` — names this as the FIRST critical-path docs step.
- `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` — records the `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cells
  (mapping matrix grounded at its base `9cfd1c7`).
- `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md` — the boundary model (Master B3 = Phase-5 evidence/gate
  validation).
- `docs/handoff/phase5_to_live_canary_roadmap.md` — stage order and Phase 6.1 hard barrier.

**No capacity validation and no capacity pass is claimed by this charter** (see §7).

---

## 2. Why This Charter Exists

The wiring charter's mapping matrix was grounded at `9cfd1c7`, **before** the B2 schema-extension slices
(`6398291` core identity fields, `5fbdec2` binding role, `0d993c9` zero-cost evidence) and the depth chain.
Several cells were marked `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` **because the field was not yet carried by B2
and a derivation would be required** (and "B3 must not invent a derivation"). This charter re-checks each cell
against the **current** B2 carrier and the **current** Phase 5 factories, and ratifies only what repo evidence
proves — keeping the rest BLOCKED.

---

## 3. Evidence Inventory Inspected (read-only)

- `phase6_1/b2_normalization_contract.py` — `PublicRawSnapshotRecord` declared fields (lines 80–95):
  `component_name, boundary_version, source_artifact, source_field, venue, pair, base_asset, quote_asset,
  instrument_id, venue_scope, venue_buy, venue_sell, retrieval_epoch_ms, observed_at_epoch_ms,
  raw_snapshot_identity, field_payload`; `NormalizedEvidenceFieldBinding` (`normalized_field_name, source_field,
  binding_role, unit_bound_magnitude, zero_cost_evidence`); `UnitBoundMagnitude.magnitude` (exact string).
- `phase5/gross_edge_observation_boundary.py` — `make_gross_edge_observation` required fields; `observed_size`/
  `gross_edge_value` are canonical decimal strings (`_CANONICAL_DECIMAL`, "no float parsing"); `observed_at_epoch_ms`
  is an exact integer string (`_EXACT_INTEGER = \d+`, `_INTEGER_FIELDS`).
- `phase5/observable_cost_friction_boundary.py` — `make_observable_cost_observation`: `cost_component_type`
  validated only as an exact non-empty `str`; **no allowed-vocabulary set exists**; `signed_decimal_value` is a
  canonical decimal string.
- `phase5/net_edge_calculator_boundary.py` — the **sole** `Decimal` parser in the path (lines ~363–367:
  `Decimal("0")`, `Decimal(value)`, `gross_dec - total_cost_dec`), internal to Phase 5 and downstream of the
  observation carriers.

---

## 4. The Five Mapping-Extraction Cells — Status

| # | Cell | Status |
|---|------|--------|
| 1 | `pair` → `base_asset` / `quote_asset` split | **RATIFIED** (no split; explicit B2 pass-through) |
| 2 | venue scope / buy / sell semantics | **RATIFIED** (no derivation; explicit B2 pass-through) |
| 3 | cost-component vocabulary (`normalized_field_name` → `cost_component_type`) | **BLOCKED** |
| 4 | numeric-coercion boundary | **RATIFIED** (B3 is not a coercer) |
| 5 | timestamp / canonical event-time boundary | **RATIFIED** (event time = B2 `observed_at_epoch_ms`) |

---

## 5. Per-Cell Detail

### Cell 1 — `pair` → `base_asset` / `quote_asset` — **RATIFIED**
- **Repo evidence:** `PublicRawSnapshotRecord` carries `base_asset` and `quote_asset` as **explicit fields**
  (b2 lines 86–87), supplied by the replay artifact. Phase 5 `make_gross_edge_observation` requires
  `base_asset` / `quote_asset`.
- **Ratified decision:** Master B3 maps `base_asset ← raw_snapshot.base_asset` and
  `quote_asset ← raw_snapshot.quote_asset` by **explicit pass-through**. **No pair-split is performed**; `pair`
  remains provenance only and is never decomposed by B3.
- **Risk if guessed:** a B3-invented split rule (e.g. on `"-"`) is a derivation the wiring charter forbids and
  would silently fabricate identity from a string.
- **Future proof (at wiring time):** prove B3 reads `base_asset`/`quote_asset` verbatim and never parses `pair`.

### Cell 2 — venue scope / buy / sell — **RATIFIED**
- **Repo evidence:** `PublicRawSnapshotRecord` carries `venue_scope`, `venue_buy`, `venue_sell` as **explicit
  fields** (b2 lines 89–91). Phase 5 requires the same three.
- **Ratified decision:** Master B3 maps `venue_scope`/`venue_buy`/`venue_sell` by **explicit pass-through**.
  **No single-venue-vs-scope inference** is performed; `venue` remains provenance only.
- **Risk if guessed:** inferring scope/buy/sell from a bare `venue` invents venue-identity semantics.
- **Future proof:** prove B3 passes the three explicit fields verbatim and never infers them from `venue`.

### Cell 3 — cost-component vocabulary — **BLOCKED**
- **Repo evidence:** Phase 5 `cost_component_type` is validated **only** as an exact non-empty `str`; there is
  **no allowed-vocabulary set** anywhere in Phase 5. B2 carries `binding_role ∈ {GROSS_EDGE, COST}` and
  `zero_cost_evidence`, but **no explicit `cost_component_type` field**. The wiring charter's
  `normalized_field_name → cost_component_type` cell therefore has neither a ratified target vocabulary nor an
  explicit B2 source.
- **Why still blocked:** mapping a free-form `normalized_field_name` to a `cost_component_type` would be a
  **B3-invented derivation** over an **undefined** vocabulary — exactly the forbidden case.
- **Risk if guessed:** silently coining a cost taxonomy (`fee_maker`/`fee_taker`/`slippage`/`total_cost`) not
  ratified anywhere; downstream cost identity becomes fabricated.
- **Required future proof to unblock:** a separate charter must ratify **both** (a) the closed allowed
  `cost_component_type` vocabulary, **and** (b) an explicit, non-derived B2 carrier for it (likely a B2
  binding-schema extension), before this cell can move to RATIFIED.

### Cell 4 — numeric-coercion boundary — **RATIFIED**
- **Repo evidence:** B2 `UnitBoundMagnitude.magnitude` is an exact string; Phase 5 observation factories
  (`gross_edge`, `observable_cost`) carry `gross_edge_value`/`signed_decimal_value` as **canonical decimal
  strings** with **no float parsing**; the **only** `Decimal` parser in the path is the internal Phase 5
  `net_edge_calculator_boundary` (downstream of the observations).
- **Ratified decision:** **B3 must not parse, cast, `Decimal`-ize, round, normalize, or reformat any value.**
  It passes magnitude/unit **strings verbatim**. The **sole authorized numeric parser** is Phase 5's internal
  net-edge calculator; the observation factories enforce **canonical-decimal FORMAT** via their own fail-fast
  string regex. B3 is a router, never a coercer.
- **Open sub-point (validation, not coercion):** B2 `magnitude` is format-**unconstrained** (accepts
  `"not-a-number"`), whereas Phase 5 requires canonical-decimal format. This mismatch is resolved **by the
  Phase 5 factory's fail-fast**, not by B3 reformatting. The future wiring slice must prove B3 forwards verbatim
  and lets Phase 5 reject non-canonical strings — it must not "fix" them.
- **Risk if guessed:** B3 silently becoming a type coercer (parsing strings to numbers) destroys exact-evidence
  discipline and can mask malformed input.

### Cell 5 — timestamp / canonical event-time — **RATIFIED**
- **Repo evidence:** B2 now carries **both** `observed_at_epoch_ms` (source-observed market time, canonical
  unsigned-int string) **and** `retrieval_epoch_ms`; the B1/B2 carriers enforce the time-isolation lock
  (`observed != str(retrieval)`). Phase 5 `make_gross_edge_observation.observed_at_epoch_ms` requires an exact
  unsigned integer string — **format-compatible** with B2 `observed_at_epoch_ms`.
- **Ratified decision:** the Phase 5 event time maps from **B2 `observed_at_epoch_ms`** (the source-observed
  time). **`retrieval_epoch_ms` must NEVER be substituted** for the event time; it stays provenance only. This
  directly resolves the wiring charter's `retrieval_epoch_ms → observed_at_epoch_ms` BLOCKED cell, which was
  blocked only because B2 did not yet carry a distinct observed time.
- **Risk if guessed:** substituting `retrieval_epoch_ms` (a later, post-hoc freeze time) for the event time
  injects **lookahead bias** and defeats the time-isolation lock.
- **Future proof:** prove B3 reads `observed_at_epoch_ms` for the event time and never reads/substitutes
  `retrieval_epoch_ms` there.

---

## 6. Is Master B3 Wiring Unblocked?

**No — Master B3 wiring remains BLOCKED.** Cells 1, 2, 4, 5 are ratified, but:

- **Cell 3 (cost-component vocabulary) remains BLOCKED** — no ratified vocabulary and no explicit B2 carrier.
- **Outside these five cells, the wiring charter's row-72 gaps persist:** `edge_direction` (the actionability
  field; tied to the **deferred** Shadow Intent Envelope) and `staleness_threshold_ms` are **not carried by B2**
  and are not ratified here. (`instrument_id`, `observed_size`/`size_unit`/`depth_source_*`, `zero_cost_evidence`
  are now carried by B2 / the depth chain, but `edge_direction` and `staleness_threshold_ms` are not.)

Master B3 may be chartered only once **Cell 3 is separately ratified** (vocabulary + explicit B2 carrier) **and**
the `edge_direction` / `staleness_threshold_ms` gaps are separately resolved. This charter unblocks four of the
five named cells; it does not unblock Master B3.

---

## 7. Still-Forbidden Work

- **No** Master B3 runtime, design, or wiring.
- **No** Phase 5 integration; **no** parsing/casting/normalizing/bridging.
- **No** B4 `ShadowScore` design; **no** durable shadow-log schema/persistence.
- **No** output carrier; **no** Shadow Intent runtime/schema; **no** live adapter runtime.
- **No** capacity activation (`CapacityConstraintGate` non-activatable, 0 emit sites, no capacity PASS token;
  `PassiveShadowInput.capacity_pass_reference` stays `None` / deferred).
- **No** Phase 6.2 readiness claim; **no** 7.x/8.x work.
- **No** resolution of any cell by assumption — Cell 3 and the row-72 gaps stay BLOCKED until separately
  ratified with evidence.

---

## 8. Next Safe Step

- A **separate review** to decide whether to authorize a **docs-only cost-component vocabulary + B2 carrier
  charter** (to unblock Cell 3) and a separate handling of `edge_direction` (via the deferred Shadow Intent
  Envelope) and `staleness_threshold_ms`.
- Master B3 wiring may be chartered **only after** Cell 3 and those gaps are resolved.
- **No implementation is authorized by this charter.** Master B3 wiring, B4 scoring, durable logs, the live
  adapter, Shadow Intent Envelope, capacity activation, Phase 6.2, and 7.x/8.x remain separately gated.
