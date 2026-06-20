# Phase 6.1 B3 Phase 5 Wiring Planning Charter

> **This is a planning/charter document only.** It authorizes NO runtime implementation, NO tests, NO
> network calls. It scopes the deferred B3 wiring boundary so a later, separately authorized TDD slice
> can begin. It is subordinate to `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`,
> `docs/handoff/phase6_1_live_public_read_adapter_charter.md`, and
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`. Where any conflict arises, those govern.

**Base:** `9cfd1c7906a6322865cb2fde2178df714442c860`

---

## 1. Current Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B1 charter | live-public-read adapter planning charter | `a12a5f5` |
| B2 charter | normalization boundary planning charter | `4f68c10` |
| B2 typed contract | `PublicRawSnapshotRecord` / `UnitBoundMagnitude` / `NormalizedEvidenceFieldBinding` / `NormalizedEvidenceMaterial` | `099ddd4` |
| B2 field-binding patch | positional semantics removed; explicit field bindings | `fa39a1c` |
| B2 replay-only normalization | `normalize_replay_snapshot_to_evidence_material` | `9cfd1c7` |

B2 now produces `NormalizedEvidenceMaterial` **from replay artifacts only**.

---

## 2. B3 Boundary

- **Consumes:** only an exact `NormalizedEvidenceMaterial`.
- **Action:** maps each explicit `NormalizedEvidenceFieldBinding` into Phase-5-compatible evidence/gate
  inputs.
- **Is not:** B1, B2, a carrier factory, an output writer, a scorer, or anything actionable.

---

## 3. Grounded Semantic Mapping Protocol

The mapping must be grounded in **actual existing Phase 5 code** (signatures inspected at this base) and
handoff docs. Targets must not be invented. Where an exact target field cannot be pinned from the
current B2 binding schema, the cell is marked **`BLOCKED_NEEDS_B3_MAPPING_EXTRACTION`**.

### Phase 5 input surface (grounded at `9cfd1c7`)
- `phase5/gross_edge_observation_boundary.py::make_gross_edge_observation(...)` — requires, among
  others: `gross_edge_value`, `gross_edge_unit`, `gross_edge_source_contract/artifact/field`,
  `edge_direction`, `base_asset`, `quote_asset`, `instrument_id`, `venue_scope`, `venue_buy`,
  `venue_sell`, `observed_at_epoch_ms`, `staleness_threshold_ms`, `observed_size`, `size_unit`,
  `depth_source_contract/artifact/field`, `boundary_version`.
- `phase5/observable_cost_friction_boundary.py::make_observable_cost_observation(...)` — requires:
  `cost_component_type`, `signed_decimal_value`, `unit`, `source_contract/artifact/field`,
  `zero_cost_evidence`, `boundary_version`.
- `phase5/pre_net_edge_calculation_input_boundary.py::make_pre_net_edge_calculation_input(gross_observation, cost_validity_contexts, boundary_version)`
  then `net_edge_input_preflight(*, calculation_input, evaluation_epoch_ms)`.
- `phase5/input_provenance_preflight.py::evaluate_input_provenance_preflight(record)`.

### Mapping matrix (B2 binding → Phase 5 target)

| B2 source | Phase 5 target module / factory / field | Status |
|-----------|-----------------------------------------|--------|
| `binding(normalized_field_name="gross_edge").unit_bound_magnitude.magnitude` | `make_gross_edge_observation.gross_edge_value` | grounded |
| `binding(normalized_field_name="gross_edge").unit_bound_magnitude.unit` | `make_gross_edge_observation.gross_edge_unit` | grounded |
| `binding.source_field` | `make_gross_edge_observation.gross_edge_source_field` | grounded |
| `raw_snapshot.source_artifact` | `make_gross_edge_observation.gross_edge_source_artifact` | grounded |
| cost-type binding `.magnitude` (e.g. `fee_maker`/`fee_taker`/`slippage`/`total_cost`) | `make_observable_cost_observation.signed_decimal_value` | grounded |
| cost-type binding `.unit` | `make_observable_cost_observation.unit` | grounded |
| cost-type binding `.source_field` | `make_observable_cost_observation.source_field` | grounded |
| `normalized_field_name` → cost-component identity | `make_observable_cost_observation.cost_component_type` | **BLOCKED_NEEDS_B3_MAPPING_EXTRACTION** (mapping rule + allowed vocabulary must be ratified) |
| `raw_snapshot.pair` (e.g. `"BTC-USD"`) → `base_asset` / `quote_asset` | `make_gross_edge_observation.base_asset` / `.quote_asset` | **BLOCKED_NEEDS_B3_MAPPING_EXTRACTION** (a pair-split rule is a derivation; B3 must not invent it) |
| `raw_snapshot.venue` → venue scope/buy/sell | `make_gross_edge_observation.venue_scope` / `.venue_buy` / `.venue_sell` | **BLOCKED_NEEDS_B3_MAPPING_EXTRACTION** (single venue vs scope/buy/sell semantics unresolved) |
| `raw_snapshot.retrieval_epoch_ms` → observation time | `make_gross_edge_observation.observed_at_epoch_ms` | **BLOCKED_NEEDS_B3_MAPPING_EXTRACTION** ("retrieval" vs "observed" semantics differ) |
| `edge_direction`, `instrument_id`, `staleness_threshold_ms`, `observed_size`, `size_unit`, `depth_source_*`, `zero_cost_evidence`, all `*_contract`/`boundary_version` | required Phase 5 fields not carried by the B2 binding schema | **BLOCKED_NEEDS_B3_MAPPING_EXTRACTION** (B2 schema gap) |

**Conclusion of the grounded pass:** a meaningful subset is pin-able (magnitude/unit/source_field for
gross-edge and cost observations), but a large set of Phase 5 required fields is **not** carried by the
current B2 binding schema. B3 implementation is therefore **gated** on a dedicated **B3 mapping
extraction** (and likely a B2 binding-schema extension) to resolve every `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION`
cell before any wiring is written. No target field may be invented to fill a gap.

---

## 4. No Positional Semantics

- B3 reads only `normalized_field_name` and `source_field` from each binding (plus the bound
  magnitude/unit through `unit_bound_magnitude`).
- Tuple position **never** defines meaning.
- **Unknown** `normalized_field_name` fails fast.
- **Missing** required `normalized_field_name` fails fast.
- **Duplicate target mapping** fails fast.
- **No default fallback values.**

---

## 5. Carrier Integrity / Preflight Validator Requirement

B3 implementation **must** include a structural preflight before any Phase 5 wiring:

- exact type `NormalizedEvidenceMaterial`;
- exact `raw_snapshot` type (`PublicRawSnapshotRecord`);
- exact tuple of `NormalizedEvidenceFieldBinding`;
- exact `UnitBoundMagnitude` per binding;
- provenance fields present and exact non-empty `str`;
- raw snapshot identity preserved;
- **no structurally-corrupted carrier built via `object.__new__` may pass silently.**

This charter defines the preflight as a **future TDD proof target only**; it is not implemented here.

---

## 6. Provenance Continuity

B3 must preserve, through the Phase 5 input-construction path: `source_artifact`, `source_field`,
`venue`, `pair`, `retrieval_epoch_ms`, `raw_snapshot_identity`, `normalized_field_name`, and the
`UnitBoundMagnitude` identity. **No recomputation from live data. No secondary lookup. No mutation of
B2 carriers.**

---

## 7. Numeric / Value Discipline

- B3 must **not** compute, compare, score, rank, threshold, or decide.
- B3 must **not** perform unit conversion.
- B3 must **not** perform magnitude comparison.
- If Phase 5 requires canonical numeric strings, B3 may only **pass through already-carried strings**
  or **route to existing Phase 5 validation**; it must never create a trading/action verdict.

---

## 8. Only Admissible Future Path

```
B1 raw snapshot
  -> B2 replay/public normalization
  -> B3 Phase 5 wiring
  -> Phase 5 provenance / evidence / gate chain
  -> PASS NetEdgeCalculationResult
  -> PassiveShadowInput
  -> ShadowObservation
  -> Slice 0 locks
```

---

## 9. Capacity Statement

This charter claims **no capacity validation and no capacity pass**. `CapacityConstraintGate` remains
**deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists or is implied.
`PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 10. Future TDD Proof Targets (to be written later — NOT written now)

1. exact `NormalizedEvidenceMaterial` input guard;
2. structural preflight rejects corrupted exact-type carriers (incl. `object.__new__` fakes);
3. explicit mapping matrix enforced (only ratified `normalized_field_name` values accepted);
4. unknown / missing / duplicate mapping fails fast;
5. provenance continuity preserved through Phase 5 input construction;
6. no mutation of B2 carriers;
7. no positional semantics (reversal-invariant);
8. no B1 adapter / network / env / secret / file IO;
9. no `PassiveShadowInput` / `ShadowObservation` construction in B3;
10. no output writing;
11. no actionability / verdict / scoring / ranking / threshold;
12. capacity remains deferred;
13. deterministic replay reproducibility.

---

## 11. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no network.
- **B3 TDD implementation** (and its prerequisite **B3 mapping extraction** for every
  `BLOCKED_NEEDS_B3_MAPPING_EXTRACTION` cell), **B1 adapter implementation**, **Phase 6.2
  calibration**, **7.x paper / paper canary**, and **8.x live canary** remain **separately gated** and
  require explicit future authorization.
- The next named step is review of this charter, then — only on explicit authorization — a read-only
  **B3 mapping extraction** to resolve the blocked cells before any B3 wiring slice. No unplanned stop.
