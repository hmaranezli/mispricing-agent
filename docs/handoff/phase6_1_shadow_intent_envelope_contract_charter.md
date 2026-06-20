# Phase 6.1 Shadow Intent Envelope Contract Planning Charter

> **This is a planning/charter document only.** It defines the strict, non-actionable boundary for a
> future Shadow Intent Envelope — the externally-supplied, replay/shadow-only carrier for `edge_direction`.
> It authorizes NO runtime, NO tests, NO B2 schema extension, NO B3 wiring, NO Phase 5 runtime change, NO
> Shadow Intent Envelope runtime/schema, NO network calls. It is subordinate to
> `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_b3_phase5_wiring_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_resolution_charter.md`,
> `docs/handoff/phase6_1_structural_boundary_ratification_charter.md`, and
> `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`. Where any conflict arises,
> those govern.

**Base:** `759bf93e47fba6649fce38f519f6c1e26e111feb`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| Structural boundary resolution charter | two structural hard gaps recorded, blocked pending ratification | `738490a` |
| Structural boundary ratification charter | Option B (envelope) ratified; provenance amendment requirement ratified | `ef72c6a` |
| Phase 5 external-market replay provenance amendment charter | first prerequisite planned (market-evidence provenance) | `759bf93` |

- See `docs/handoff/phase6_1_structural_boundary_resolution_charter.md` (`738490a`) — the `edge_direction`
  actionability hard gap.
- See `docs/handoff/phase6_1_structural_boundary_ratification_charter.md` (`ef72c6a`) — human ratification
  of **Option B** (direction supplied only via an explicit typed per-fixture Shadow Intent Envelope).
- See `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` (`759bf93`) — the first
  prerequisite (Phase 5 external-market replay provenance amendment planning).

**This charter is the second prerequisite** before any future B2 schema extension charter can be
considered. Both prerequisites (market-evidence provenance amendment, and this Shadow Intent Envelope
contract) must be planned before B2 schema extension is even reviewable.

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Purpose and Boundary

The Shadow Intent Envelope is **only** a **replay / shadow test-intent carrier** for an externally
supplied `edge_direction`. It is:

- **not** market evidence;
- **not** B1 raw input (`PublicRawSnapshotRecord`);
- **not** B2 normalized evidence (`NormalizedEvidenceMaterial`);
- **not** B3 wiring;
- **not** Phase 5 runtime;
- **not** a trade / order / execution / paper / live / actionability object.

It exists solely to carry, by explicit external authorship, a direction that B1/B2/B3 are
constitutionally forbidden to originate.

---

## 3. Exact Payload Restriction

- The **only** allowed semantic payload is `edge_direction`.
- Allowed values are **exactly** `LONG`, `SHORT`, `CROSS_VENUE` — matching the Phase 5 `edge_direction`
  vocabulary (`_ALLOWED_DIRECTIONS` in `phase5/gross_edge_observation_boundary.py`).
- **No other semantic payload is permitted.**
- The following (non-exhaustive) fields are **explicitly forbidden** as envelope payload: `target_price`,
  `price`, `score`, `threshold`, `quantity`, `size`, `allocation`, `route`, venue preference, `candidate`,
  `signal`, `ranking`, `verdict`, expected PnL, realized PnL, `capacity`, `wallet`, `balance`, `account`,
  `order`, `execution`, `trade`, `paper`, `live`, or any equivalent actionability field.
- Future runtime/tests **must fail** if any extra semantic field is introduced beyond `edge_direction`
  (and the envelope's own identity/provenance fields per §7).

---

## 4. Zero Inference and No Defaults

- **B1/B2/B3 must never infer, compute, default, derive, or fabricate `edge_direction`.**
- **No global static dummy** direction is allowed.
- **No silent default** is allowed.
- If a future replay/shadow path requires `edge_direction` and the Shadow Intent Envelope is **absent,
  malformed, or ambiguous**, the system **must fail fast**.
- If `edge_direction` is **not exactly one** of `LONG`, `SHORT`, `CROSS_VENUE`, the system **must fail
  fast**.

---

## 5. Isolation from B1/B2 and Market Provenance

- The envelope **must remain separate** from `PublicRawSnapshotRecord` and `NormalizedEvidenceMaterial`.
- It **must not be embedded** inside any B1 or B2 carrier.
- It **must not inherit** from any B1/B2 carrier.
- It **must not reuse** market-evidence provenance fields as intent provenance.
- **Market provenance and intent provenance must remain disjoint.**
- The envelope **must not alter or backfill** market-evidence provenance.

---

## 6. Fixture / Replay / Shadow Scope Only

- The envelope is valid **only** in replay/shadow fixture scope.
- It has **no** live, paper, execution, routing, sizing, allocation, signal, candidate, scoring,
  threshold, ranking, verdict, trade, wallet, balance, or account semantics.
- It **must not** be accepted as a live/paper decision source.
- It **must not** be used to create a downstream action.

---

## 7. Self-Contained Identity and Provenance

- The envelope **must have its own future typed identity/provenance contract** — distinct from market
  evidence and from internal planning artifacts.
- Future planning **must define** fields such as: fixture identity, intent source contract, intent
  author/source, intent record id, intent schema version, and an immutable intent artifact/reference.
- These fields are **planning targets only** — **do not implement them here**.
- Future runtime **must fail fast** if intent identity/provenance is **missing, malformed, mutable, or
  inconsistent**.
- Intent provenance **must not spoof** external-market provenance or internal planning-artifact
  provenance (see `phase5_external_market_replay_provenance_amendment_charter.md`, §3).

---

## 8. Relationship to Phase 5 and B3

- This charter **does not** authorize Phase 5 runtime changes.
- This charter **does not** authorize B3 mapping or wiring.
- Future B3 planning may **only** consume the envelope as a **separate exact-type input alongside B2
  material**, after separate authorization.
- B3 **must never synthesize** an envelope.
- B3 **must never modify** the envelope.
- B3 **must never treat** the envelope as market evidence.

---

## 9. Still-Blocked Work

- **B2 schema extension** remains blocked after this charter unless separately authorized.
- **B3 mapping amendment** remains blocked.
- **B3 implementation** remains blocked.
- **Phase 5 runtime modification** remains blocked.
- **Shadow Intent Envelope runtime/schema** remains blocked.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

---

## 10. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS
token exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and
must never be read as "capacity validated."

---

## 11. Future TDD Proof Targets (planning notes only — NOT written now)

1. **Exact `edge_direction` vocabulary only** — `LONG`/`SHORT`/`CROSS_VENUE`; anything else fails fast.
2. **Reject missing/malformed/ambiguous envelope** — required-but-absent or malformed fails closed.
3. **Reject silent defaults and global dummies** — no implicit or static direction.
4. **Reject any extra semantic/actionability payload** — only `edge_direction` plus identity/provenance.
5. **Prove B1/B2/B3 never infer or compute `edge_direction`** — direction only ever carried by identity.
6. **Prove envelope is separate from B1/B2 carriers** — no embedding, no inheritance, no reuse.
7. **Prove market provenance and intent provenance stay disjoint** — no field reuse either direction.
8. **Prove B3 cannot synthesize or mutate the envelope** — B3 consumes by identity only.
9. **No network / env / secret / file IO** in any of this work.
10. **No carrier construction or Phase 5 bypass** — only the admissible B1 → B2 → B3 → Phase 5 chain.

---

## 12. Next Safe Step

- After this docs-only charter, **both prerequisites** for a future B2 schema extension charter have been
  **planned**: (a) the Phase 5 external-market replay provenance amendment (`759bf93`), and (b) this
  Shadow Intent Envelope contract planning charter.
- **B2 schema extension is still not authorized automatically.** Planning the prerequisites does not
  unblock implementation.
- The next step must be a **separate review** deciding whether to author the **B2 schema extension
  charter**.
- **No runtime, schema, or test implementation is authorized.** B1 adapter implementation, Phase 6.2
  calibration, and 7.x/8.x remain separately gated.
