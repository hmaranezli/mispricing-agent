# Phase 6.1 / Phase 5 Structural Boundary Resolution Charter

> **This is a planning/charter document only.** It authorizes NO runtime implementation, NO tests, NO
> B2 schema extension, NO B3 wiring, NO network calls. It records two structural hard gaps surfaced by
> the read-only B3 mapping extraction and **blocks** all downstream B2 schema extension and B3
> implementation until explicit human ratification. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_shadow_input_wrapper_charter.md`,
> `docs/handoff/phase6_1_live_public_read_adapter_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`, and
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`. Where any conflict arises, those govern.

**Base:** `d64698118a710d0b6eba83d948c1f1a4b6365e43`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B1 charter | live-public-read adapter planning charter | `a12a5f5` |
| B2 charter | normalization boundary planning charter | `4f68c10` |
| B2 typed contract | `PublicRawSnapshotRecord` / `UnitBoundMagnitude` / `NormalizedEvidenceFieldBinding` / `NormalizedEvidenceMaterial` | `099ddd4` |
| B2 field-binding patch | positional semantics removed; explicit field bindings | `fa39a1c` |
| B2 replay-only normalization | `normalize_replay_snapshot_to_evidence_material` | `9cfd1c7` |
| B3 wiring charter | Phase 5 wiring planning charter (grounded mapping matrix) | `d646981` |

- B2 replay normalization **exists** and produces `NormalizedEvidenceMaterial` from replay artifacts only.
- The B3 Phase 5 wiring planning charter **exists** and grounded a mapping matrix against real Phase 5
  factory signatures.
- A **read-only B3 mapping extraction** was then performed at base `d646981`. It resolved a meaningful
  subset of fields (gross-edge and cost magnitude/unit/source_field/source_artifact ground cleanly) and
  surfaced **two structural hard gaps** that no normalization or wiring can close without an explicit
  human architectural decision. Those two gaps are the subject of this charter.

**No capacity validation and no capacity pass is claimed by this charter** (see §6).

---

## 2. `edge_direction` Actionability Hard Gap

### Finding
`phase5/gross_edge_observation_boundary.py::make_gross_edge_observation(...)` **requires** an exact
non-empty string `edge_direction` constrained to the fixed set `{"LONG", "SHORT", "CROSS_VENUE"}`
(`_ALLOWED_DIRECTIONS`). Construction fails closed if `edge_direction` is absent or outside that set.

### Why this is a hard gap, not a schema gap
A passive public-market read (B1) and its replay normalization (B2) carry **observed facts only** — a
magnitude, a unit, a venue, a pair, a timestamp, a provenance label. **A direction is not an observed
fact; it is a verdict** about which way the edge points. Producing `LONG`/`SHORT`/`CROSS_VENUE` from
passive evidence necessarily means **inferring, computing, deciding, or defaulting** a direction.

B1, B2, and B3 are constitutionally **non-actionable**: they must not score, rank, threshold, compare,
decide, or otherwise emit a verdict. Therefore **B1/B2/B3 cannot infer, compute, default, or derive
`edge_direction`** from passive public-market evidence without violating non-actionability. No schema
extension can source this field from raw evidence, because the field is not evidence.

### Explicit rejections
The following are **forbidden** and must never appear in any future B2/B3 work:
- a **silent default** direction (e.g. implicitly treating absence as `LONG`);
- a **global static dummy** direction constant injected to satisfy the constructor;
- any **direction value fabricated, inferred, or computed by B2 or B3** from magnitudes, deltas, signs,
  price movement, or any other passive datum.

### Architectural options (presented only — Claude must NOT choose)
- **Option A — Re-target the passive-shadow path.** Change the passive-shadow target away from
  `make_gross_edge_observation` toward a **direction-agnostic** Phase 5 contract that does not require a
  directional verdict as a precondition of construction.
- **Option B — Explicit typed Shadow Intent Envelope.** Supply direction through a **separate, explicit,
  typed, per-fixture Shadow Intent Envelope** that carries its own provenance. The direction would be an
  externally-provided input with its own source record — **no default, no inference, and no B2/B3
  computation**. B2/B3 would only carry it by identity, never originate it.

**Status: `HUMAN_RATIFICATION_REQUIRED`.** Claude must not choose between Option A and Option B. The
direction-sourcing architecture is a human decision.

---

## 3. Phase 5 Provenance Vocabulary Hard Gap

### Finding
`phase5/input_provenance_preflight.py::evaluate_input_provenance_preflight(record)` admits records only
against a **planning-artifact provenance vocabulary** defined in `phase5/const.py`:
- `ALLOWED_SOURCE_CONTRACTS` is a fixed set of **Phase 5 planning/contract markdown documents** (e.g.
  `phase5_artifact_provenance_contract.md`, `phase5_interface_contract.md`, `phase5_offline_fixture_contract.md`).
- `REQUIRED_RECORD_IDENTITY_FIELDS` requires `input_schema_version`, `input_record_type`, `batch_id`,
  `run_id`, `observation_id`, `source_contract`.
- `REQUIRED_PROVENANCE_FIELDS` requires `source_artifact`, `source_field`, `artifact_type_or_blocked_reason`,
  `artifact_phase_or_blocked_reason`, `provenance_status`, `source_sha256_or_blocked_reason`,
  `parser_version_or_blocked_reason`, `verifier_result_or_blocked_reason`.

A **live or replay public-market snapshot** is not admitted by this vocabulary: its `source_contract`
is not in `ALLOWED_SOURCE_CONTRACTS`, and it does not naturally carry the planning-artifact identity and
provenance fields.

### Explicit rejection
B2/B3 must **not fabricate** a `source_contract`, **not fabricate** `source_sha256` / `parser_version` /
`verifier_result` provenance fields, and **not fabricate** any planning-artifact record identity in order
to pass the Phase 5 provenance gate. Spoofing planning-artifact provenance to admit market data is a
fail-closed violation of the anti-hallucination constitution.

### Requirement
A **formal Phase 5 external-market replay provenance contract amendment** — defining how live/replay
public-market provenance is legitimately represented and admitted — **must be ratified before** any B2
schema extension or B3 implementation can proceed. This is a Phase 5-side decision, upstream of B2/B3.

**Status: `HUMAN_RATIFICATION_REQUIRED`.**

---

## 4. B2 Schema Extension — Blocked

The read-only mapping extraction identified fields that may eventually require a B2 (and in some cases
B1) extension to be sourceable. These are recorded here **only as a blocked inventory**, not as an
authorization:

- `base_asset`, `quote_asset` — split of `raw.pair` (a derivation that, if done at all, belongs in B2).
- `venue_scope`, `venue_buy`, `venue_sell` — projection of the single `raw.venue`.
- `observed_at_epoch_ms` — as a **canonical unsigned integer string**, semantically distinct from B2's
  current integer `retrieval_epoch_ms`.
- `instrument_id` — not carried; venue+pair composition is a derivation.
- binding **role/kind** discriminator — to distinguish a gross-edge binding from a cost binding (Phase 5
  `cost_component_type` is free-form, but the routing role is not carried by the current schema).
- `zero_cost_evidence` — required by `make_observable_cost_observation` whenever a cost is numerically
  zero; not carried.
- depth-source carriage — `observed_size`, `size_unit`, `depth_source_contract/artifact/field` (also
  requires a B1 fetch extension, since order-book depth is not in the current public-read snapshot).

**All of these schema extensions are BLOCKED** until the §2 `edge_direction` gap and the §3 Phase 5
provenance gap are ratified. No B2 or B1 schema field may be added before then.

---

## 5. Forbidden Work (under this charter and until ratification)

- **No B2 schema extension** (no new fields on any B2 carrier; no B1 fetch extension).
- **No B3 TDD implementation** (no wiring runtime, no wiring tests).
- **No Phase 5 runtime modification** (no edits to any `phase5/*.py`).
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult`.
- **No** scoring, ranking, threshold, execution, routing, sizing, allocation, signal, candidate, trade,
  paper, or live semantics — in any form, anywhere.

---

## 6. Capacity Invariant

This charter claims **no capacity validation and no capacity pass**. `CapacityConstraintGate` remains
**deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists or is implied.
`PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated."

---

## 7. Future TDD Proof Targets (planning notes only — NOT written now)

1. **No `edge_direction` inference/defaults** — a future test must prove B2/B3 never originate, infer,
   compute, or default a direction; absence fails closed.
2. **No provenance spoofing** — a future test must prove B2/B3 never fabricate `source_contract`,
   sha/parser/verifier fields, or planning-artifact identity to pass the Phase 5 provenance gate.
3. **Schema extension blocked until ratification** — a future guard must reflect that no B2/B1 field was
   added before §2 and §3 are ratified.
4. **Exact-type and provenance continuity** — exact-type discipline preserved; provenance carried by
   identity, never recomputed.
5. **No Phase 5 bypass** — the only admissible path remains B1 → B2 → B3 → Phase 5 chain.
6. **No carrier construction** — no `PassiveShadowInput` / `ShadowObservation` / `NetEdgeCalculationResult`
   built in this scope.
7. **No network / env / secret / file IO** in any of this work.

---

## 8. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no schema change, no network.
- The two hard gaps (§2 `edge_direction`, §3 Phase 5 provenance vocabulary) are both
  **`HUMAN_RATIFICATION_REQUIRED`**. Claude must not choose a path for either.
- The next named step is **human review and ratification** of §2 and §3. Only after explicit
  authorization may any B2 schema-extension charter, B3 mapping amendment, or B3 implementation be
  considered. B1 adapter implementation, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
