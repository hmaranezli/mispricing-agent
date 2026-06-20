# Phase 5 External-Market Replay Provenance Amendment Charter

> **This is a planning/charter document only.** It defines the *requirements* for a future Phase 5
> provenance amendment that would admit external public-market replay evidence without spoofing internal
> planning-artifact provenance. It authorizes NO runtime, NO tests, NO Phase 5 runtime modification, NO
> B2 schema extension, NO B3 wiring, NO Shadow Intent Envelope runtime/schema, NO network calls. It
> unblocks **future planning only**. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_shadow_scoring_tdd_planning.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_resolution_charter.md`, and
> `docs/handoff/phase6_1_structural_boundary_ratification_charter.md`. Where any conflict arises, those
> govern.

**Base:** `ef72c6a766bbede85f92977a2e3a740d2fab2929`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B3 wiring charter | Phase 5 wiring planning charter (grounded mapping matrix) | `d646981` |
| Structural boundary resolution charter | two structural hard gaps recorded, blocked pending ratification | `738490a` |
| Structural boundary ratification charter | Option B (envelope) ratified; provenance amendment requirement ratified; all impl/schema blocked | `ef72c6a` |

- See `docs/handoff/phase6_1_structural_boundary_resolution_charter.md` (`738490a`) for the original
  finding: the Phase 5 provenance preflight admits only a planning-artifact provenance vocabulary, and
  external public-market replay evidence is not admitted.
- See `docs/handoff/phase6_1_structural_boundary_ratification_charter.md` (`ef72c6a`) for the human
  ratification that a **formal external-market replay provenance contract amendment** is required before
  any B2 schema extension or B3 implementation.

**Phase 5 external-market replay provenance amendment planning is required before B2 schema extension or
B3 implementation.** This charter is that planning step — and only the planning step.

**No capacity validation and no capacity pass is claimed by this charter** (see §9).

---

## 2. Problem Statement

- `phase5/input_provenance_preflight.py::evaluate_input_provenance_preflight(record)` currently admits a
  **planning-artifact provenance vocabulary only**: `ALLOWED_SOURCE_CONTRACTS` is a fixed set of Phase 5
  contract markdown documents, and the required identity/provenance fields (`REQUIRED_RECORD_IDENTITY_FIELDS`,
  `REQUIRED_PROVENANCE_FIELDS`) are shaped for planning artifacts.
- **External public-market replay evidence is not currently admitted** by that vocabulary.
- **B2/B3 must not fabricate** `source_contract`, `source_sha256` / `parser_version` / `verifier_result`
  fields, or any internal planning-artifact record identity, to pass the gate.
- This charter **defines the future amendment requirements only**; it does not implement them. No
  `phase5/*.py` change is authorized here.

---

## 3. Anti-Spoofing Rule

- The future amendment must define an **explicit external-market replay `source_contract` vocabulary**,
  **separate** from the internal planning-artifact contracts.
- It is **forbidden** to use any existing internal planning-artifact `source_contract` value (e.g.
  `phase5_interface_contract.md`, `phase5_offline_fixture_contract.md`) to label public-market replay
  evidence.
- It is **forbidden** to fabricate `source_sha256`, `parser_version`, `verifier_result`, `batch_id` /
  `run_id` / `observation_id` identities, or any other provenance field, to satisfy the gate.
- Future tests must prove that **spoofed internal provenance is rejected** when the underlying evidence is
  external public-market replay material.

---

## 4. Immutable Provenance Anchor

- The future amendment must require an **immutable anchor** for replay evidence — a value that binds the
  admitted record to the exact evidence it came from and cannot be silently mutated.
- Candidate anchors (documented here, **not implemented**):
  - the **replay artifact content hash**, when a local replay artifact is used;
  - the **`PublicRawSnapshotRecord` identity** (the B2 raw-snapshot carrier referenced by identity);
  - the **raw `source_artifact` reference**;
  - a **parser / verifier identity for the replay artifact**, if such a parser/verifier is later
    introduced.
- **Removing the hash requirement without supplying a replacement anchor is forbidden.** An anchor must
  always exist.
- The future runtime **must fail fast** if the anchor is **missing, malformed, mutable, or inconsistent**
  with the evidence it claims to bind.

---

## 5. Time Isolation / Lookahead-Bias Lock

- `retrieval_epoch_ms` and `observed_at_epoch_ms` must be **strictly separated**:
  - `retrieval_epoch_ms` = when the system **obtained / froze** the evidence;
  - `observed_at_epoch_ms` = when the market event was **observed at the source**.
- They **must not be silently substituted** for each other in either direction.
- The future runtime **must fail fast** if either timestamp is **missing, malformed, or semantically
  ambiguous**.
- Future tests must prove that **no lookahead bias** can be introduced by replacing `observed_at_epoch_ms`
  with `retrieval_epoch_ms` or vice versa.
- The timestamp rules **must preserve replay determinism** (the same replay artifact always yields the
  same admitted timestamps).

---

## 6. Market Provenance vs Intent Provenance Isolation

- This amendment charter is **only** for **external market evidence provenance**.
- It **must not** define Shadow Intent Envelope provenance.
- The **Shadow Intent Envelope** is **separate test-intent provenance**, not market-evidence provenance.
- **Market provenance fields must never be reused to carry `edge_direction` intent** (or any intent).
- Future Shadow Intent Envelope planning remains **separately gated** under the ratification charter
  (`ef72c6a`, §1).

---

## 7. Allowed Future Amendment Shape

The future Phase 5 amendment **may** (when separately authorized):

- add an **explicit external-market replay `source_contract` class / vocabulary**, disjoint from the
  internal planning-artifact set;
- add **required identity / provenance fields specific to replay evidence** (e.g. an anchor field per §4
  and the two distinct timestamps per §5);
- It **must preserve strict provenance-preflight behavior and fail closed** — unknown, malformed, or
  ambiguous records are rejected, never admitted by default;
- It **must not weaken** existing internal planning-artifact provenance rules (the current
  `ALLOWED_SOURCE_CONTRACTS`, required identity, and required provenance fields remain exactly as strict
  for internal records).

---

## 8. Still-Blocked Work

- **B2 schema extension** remains blocked.
- **B3 mapping amendment** remains blocked.
- **B3 implementation** remains blocked.
- **Shadow Intent Envelope contract planning** remains separate and separately gated.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.
- **No** scoring, ranking, threshold, execution, routing, sizing, allocation, signal, candidate, trade,
  paper, live, or actionability semantics are authorized.

---

## 9. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS
token exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and
must never be read as "capacity validated."

---

## 10. Future TDD Proof Targets (planning notes only — NOT written now)

1. **Reject internal provenance spoofing** — external replay evidence labeled with an internal
   planning-artifact `source_contract` is rejected.
2. **Require external-market replay `source_contract`** — replay evidence must carry the explicit
   external-market vocabulary; absence fails closed.
3. **Require immutable replay provenance anchor** — missing/malformed/mutable/inconsistent anchor fails
   fast.
4. **Preserve retrieval-vs-observed timestamp isolation** — the two timestamps are distinct and never
   substituted.
5. **Reject ambiguous / missing timestamps** — either timestamp missing, malformed, or ambiguous fails
   fast; no lookahead bias.
6. **Isolate market provenance from Shadow Intent provenance** — market provenance fields never carry
   `edge_direction` or any intent.
7. **Keep B2/B3 from fabricating Phase 5 provenance** — no B2/B3-originated `source_contract`/sha/parser/
   verifier/identity.
8. **Keep existing internal planning-artifact provenance strict** — internal records remain exactly as
   strict; the amendment does not weaken them.
9. **No network / env / secret / file IO** in any of this work.
10. **No carrier construction or Phase 5 bypass** — the only admissible path remains B1 → B2 → B3 →
    Phase 5 chain; no carrier built in this scope.

---

## 11. Planning-Only Authority

- This charter authorizes **no implementation** — no runtime, no tests, no Phase 5 runtime change, no B2
  schema change, no B3 wiring, no Shadow Intent Envelope runtime/schema, no network.
- The next named step is **human review** of these amendment requirements, then — only on explicit
  authorization — either the separately-gated **Shadow Intent Envelope contract planning charter** or a
  further **Phase 5 provenance amendment design** step. No runtime, schema, or test implementation is
  authorized.
- B1 adapter implementation, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
