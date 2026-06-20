# Phase 6.1 B2 Schema Extension Charter

> **This is a planning/charter document only.** It defines the *intended categories and dependencies* of
> a future B2 schema extension needed before B3 Phase 5 wiring can be planned. It authorizes NO runtime,
> NO tests, NO B1 fetch/source change, NO B2 schema implementation, NO B3 wiring, NO Phase 5 runtime
> change, NO Shadow Intent Envelope runtime/schema, NO network calls. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_resolution_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_ratification_charter.md`,
> `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`, and
> `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md`. Where any conflict arises, those
> govern.

**Base:** `17d7960bd5208a37a2c5c4700bf14aab2c54ed3a`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B3 wiring charter | Phase 5 wiring planning charter (grounded mapping matrix) | `d646981` |
| Structural boundary resolution charter | two structural hard gaps recorded | `738490a` |
| Structural boundary ratification charter | Option B ratified; provenance amendment requirement ratified | `ef72c6a` |
| Phase 5 external-market replay provenance amendment charter | prerequisite #1 (market-evidence provenance) | `759bf93` |
| Shadow Intent Envelope contract charter | prerequisite #2 (externally-supplied direction) | `17d7960` |

- See `docs/handoff/phase6_1_b3_phase5_wiring_charter.md` (`d646981`) — the grounded mapping matrix that
  found Phase 5 required fields not carried by the current B2 binding schema.
- See `docs/handoff/phase6_1_structural_boundary_resolution_charter.md` (`738490a`) and
  `docs/handoff/phase6_1_structural_boundary_ratification_charter.md` (`ef72c6a`) — the two structural
  hard gaps and their ratification.
- See `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` (`759bf93`) and
  `docs/handoff/phase6_1_shadow_intent_envelope_contract_charter.md` (`17d7960`) — the two prerequisite
  planning charters.

**Both prerequisite planning charters are complete, but no implementation is authorized.** Completing the
prerequisites does not unblock B2 schema implementation; this charter only plans the extension shape.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Purpose and Boundary

The B2 schema extension is **only** a planning contract for future
`NormalizedEvidenceMaterial` / `PublicRawSnapshotRecord`-compatible fields required by eventual B3
mapping. It is:

- **not** B3 wiring;
- **not** Phase 5 runtime;
- **not** a Shadow Intent Envelope;
- **not** market fetching (B1);
- **not** scoring / actionability.

It exists solely to scope which evidence-carrying fields a future, separately-authorized B2 slice might
add so that B3 mapping has grounded targets — without inventing actionability or direction.

---

## 3. Core Market Identity Fields — `CORE_MARKET_IDENTITY_OR_BINDING_FIELDS`

The following future B2 / B2-output fields are **sourceable from existing replay / public snapshot
material** (pending later TDD), and are grouped as **`CORE_MARKET_IDENTITY_OR_BINDING_FIELDS`**:

- `base_asset`
- `quote_asset`
- `venue_scope`
- `venue_buy`
- `venue_sell`
- `observed_at_epoch_ms` — as a **canonical unsigned integer string**
- `instrument_id`
- binding **role/kind** discriminator (gross-edge vs cost)
- `zero_cost_evidence` carriage

These are **planning-only** and may be implementable later **only after explicit authorization**. No
field here is authorized for implementation by this charter.

---

## 4. Depth-Source Dependency Lock — `B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`

The following future depth-related fields are grouped as **`B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`**:

- `observed_size`
- `size_unit`
- `depth_source_field`
- `depth_source_artifact`
- `depth_source_contract`

- The current B1 / `PublicRawSnapshotRecord` **does not fetch or carry order-book depth material**.
- **No B2 runtime/test may implement or require these depth fields** until a **separate B1 fetch/source
  amendment is chartered and authorized**.
- These fields **must remain blocked** in any future B2 implementation **until B1 provides immutable,
  provenance-tagged depth evidence**.

---

## 5. Time Isolation / Lookahead-Bias Inheritance

This charter **inherits the time-isolation rule** from
`docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` (§5):

- `retrieval_epoch_ms` and `observed_at_epoch_ms` must remain **semantically distinct**.
- `retrieval_epoch_ms` (when the system obtained/froze evidence) **must not be silently copied,
  substituted, or renamed** into `observed_at_epoch_ms`.
- `observed_at_epoch_ms` must be **source-observed market time**, a **canonical unsigned integer string**,
  and must **fail fast if missing, malformed, or ambiguous**.
- Future tests must prove **no lookahead bias** is introduced by timestamp substitution.

---

## 6. Role/Kind and Semantic Mapping Lock

- A future B2 binding **role/kind** must distinguish **gross-edge evidence from cost evidence** without
  relying on **tuple position**.
- Role/kind **must not encode** actionability, verdict, score, threshold, direction, route, quantity,
  size, allocation, paper/live, or execution semantics.
- `edge_direction` remains **exclusively outside B2**, in the separately-planned **Shadow Intent
  Envelope** path (`17d7960`).
- **No `normalized_field_name` positional semantics** are allowed.

---

## 7. Zero-Cost Evidence Rule

- `zero_cost_evidence` may be carried **only** as provenance/evidence required by Phase 5 for numerically
  zero costs.
- B2 **must not compute** whether a cost is economically meaningful.
- B2 **must not score, rank, suppress, or reinterpret** zero costs.
- Future runtime **must fail fast** if zero-cost evidence is required but absent or malformed.

---

## 8. Provenance Requirements

- Future B2 fields must **preserve provenance continuity** back to `PublicRawSnapshotRecord` and the
  external-market replay provenance.
- B2 **must not fabricate** `source_contract`, parser/verifier fields, replay anchors, observed
  timestamps, source artifacts, or intent provenance.
- **Market provenance and Shadow Intent provenance remain disjoint.**
- A future B2 extension **must not weaken** existing exact-type / provenance locks.

---

## 9. Still-Blocked Work

- **No B2 schema runtime implementation** is authorized.
- **No tests** are authorized.
- **No B1 fetch/source amendment** is authorized.
- **No B3 mapping amendment or implementation** is authorized.
- **No Phase 5 runtime modification** is authorized.
- **No Shadow Intent Envelope runtime/schema** is authorized.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

---

## 10. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS
token exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and
must never be read as "capacity validated."

---

## 11. Future TDD Proof Targets (planning notes only — NOT written now)

1. **Exact-type / slotted / frozen schema-extension carriers** if later authorized.
2. **Reject missing/malformed core market identity fields** (`CORE_MARKET_IDENTITY_OR_BINDING_FIELDS`).
3. **Reject timestamp substitution and lookahead bias** (`retrieval` ≠ `observed`).
4. **Reject role/kind positional semantics** — role carried explicitly, never by tuple position.
5. **Reject `edge_direction` inside B2** — direction lives only in the Shadow Intent Envelope path.
6. **Reject actionability payloads** — no score/verdict/threshold/route/size/allocation/paper/live/exec.
7. **Reject depth fields unless B1 source amendment is present** (`B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`).
8. **Preserve market-provenance / intent-provenance separation** — disjoint, never reused.
9. **Prove B2 cannot fabricate Phase 5 provenance** — no B2-originated contract/parser/verifier/anchor.
10. **No network / env / secret / file IO** in any of this work.
11. **No carrier construction or Phase 5 bypass** — only the admissible B1 → B2 → B3 → Phase 5 chain.

---

## 12. Next Safe Step

- After this docs-only charter, the next step is a **separate review** deciding whether to authorize the
  **first B2 schema extension TDD slice**.
- That future slice, if authorized, **must be narrow** and **should start with core market identity
  fields only** (`CORE_MARKET_IDENTITY_OR_BINDING_FIELDS`), **not** depth-source fields
  (`B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`, which remain blocked behind a separate B1 amendment).
- **No runtime, schema, or test implementation is authorized by this charter.** B1 adapter
  implementation, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
