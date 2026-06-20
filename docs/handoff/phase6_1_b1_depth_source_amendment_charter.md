# Phase 6.1 B1 Fetch/Source Amendment Charter — Depth Evidence

> **This is a planning/charter document only.** It defines how a future B1 public-read/replay source may
> carry immutable, provenance-tagged **depth evidence** required by the still-blocked
> `B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`. It authorizes NO runtime, NO tests, NO network fetching, NO B1/B2/B3
> runtime change, NO B2 schema code change, NO Phase 5 runtime change, NO live public read. It is
> subordinate to `docs/handoff/phase5_to_live_canary_roadmap.md`,
> `docs/handoff/phase6_1_live_public_read_adapter_charter.md`,
> `docs/handoff/phase6_1_b2_normalization_boundary_charter.md`,
> `docs/handoff/phase6_1_b2_schema_extension_charter.md`, and
> `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`. Where any conflict arises,
> those govern.

**Base:** `0d993c937df36d6a1b1d71438011a587e558275a`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B1 live-public-read adapter charter | replay-first public read planning | `a12a5f5` |
| Phase 5 external-market replay provenance amendment charter | market-evidence provenance requirements | `759bf93` |
| B2 schema extension charter | core identity / binding / depth-field inventory | `908e263` |
| B2 core identity fields (Slice 1) | `base_asset`/`quote_asset`/`venue_scope`/`venue_buy`/`venue_sell`/`observed_at_epoch_ms`/`instrument_id` | `6398291` |
| B2 binding role discriminator (Slice 2A) | `binding_role` ∈ {GROSS_EDGE, COST} | `5fbdec2` |
| B2 zero-cost evidence carrier (Slice 2B) | `zero_cost_evidence` (COST-only, optional) | `0d993c9` |

- See `docs/handoff/phase6_1_live_public_read_adapter_charter.md` (`a12a5f5`) — the replay-first public-read
  boundary.
- See `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` (`759bf93`) — the
  external-market replay provenance requirements (anchor, time isolation, anti-spoofing).
- See `docs/handoff/phase6_1_b2_schema_extension_charter.md` (`908e263`) — the field inventory that grouped
  `CORE_MARKET_IDENTITY_OR_BINDING_FIELDS` (now implemented) and `B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS` (still
  blocked).

**B2 core schema extension is complete** for the core identity and binding fields (Slices 1, 2A, 2B).
**Depth-source fields remain blocked** until this B1 source planning is complete and a later slice is
separately authorized.

**No capacity validation and no capacity pass is claimed by this charter** (see §12).

---

## 2. Problem Statement

- The current B1 / `PublicRawSnapshotRecord` path carries price/replay snapshot material but **not**
  order-book / depth material.
- The B2 depth-source fields remain blocked because B1 does not yet carry `observed_size`, `size_unit`,
  `depth_source_field`, `depth_source_artifact`, or `depth_source_contract`.
- This charter defines **future source/fetch requirements only**; it does not implement them. No `phase6_1/*`
  runtime, no B2 schema code, no fetcher is written here.

---

## 3. Depth Evidence Boundary

- Future depth evidence is **public, unauthenticated** market-depth/source material associated with the same
  replay/public market snapshot family.
- It must be **immutable, provenance-tagged, and replay-artifact-first**.
- It must be **read/frozen as evidence**, never interpreted as sizing, liquidity, routing, allocation, or
  decision intent.
- It must **not** produce a trade, candidate, signal, score, threshold, route, size decision, or
  actionability verdict.

---

## 4. Future Fields to Support — `B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS`

Planning-only inventory of future B1/B2 source-dependent fields:

- `observed_size`
- `size_unit`
- `depth_source_field`
- `depth_source_artifact`
- `depth_source_contract`

These are **planning-only** and **remain blocked in runtime** until a separately authorized TDD slice.

---

## 5. Public-Only / No-Secret / No-Private Boundary

- A future B1 depth source must remain **public-only and unauthenticated**.
- **No** API keys, signatures, sessions, account/wallet/private endpoints, order endpoints, balance
  endpoints, or trading endpoints.
- **No** environment access or secrets.
- **No** private-endpoint fallback.
- Future tests must enforce **allowlist/denylist** behavior **before** any live public read is authorized.

---

## 6. Replay-Artifact-First Rule

- The first implementation slice, when later authorized, **must use replay artifacts only**.
- **No** live API/network call in the first implementation slice.
- The replay artifact must include **immutable depth evidence** and an **external-market provenance anchor**.
- A live public depth read, if ever considered, **must be a later, separately reviewed slice**.

---

## 7. Provenance Continuity

- Depth evidence must **inherit** the external-market replay provenance requirements from
  `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`.
- `depth_source_contract` **must not spoof** internal planning-artifact provenance.
- `depth_source_artifact` must be **immutable and traceable** to the replay artifact or public source
  reference.
- `depth_source_field` must identify the **exact** source field/key/path used for `observed_size`.
- **Missing/malformed/mutable/inconsistent** depth provenance must **fail fast** in future runtime.

---

## 8. Time Isolation

- A depth observed time must **not** be silently substituted with `retrieval_epoch_ms`.
- If a future depth observed time is needed, it must be **explicitly source-observed** and kept **distinct**
  from retrieval time (consistent with the Slice-1 `observed_at_epoch_ms` ≠ `retrieval_epoch_ms` lock).
- **No lookahead-bias** path may be introduced.
- **Replay determinism** must be preserved.

---

## 9. No Actionability / No Sizing Semantics

- `observed_size` is **evidence about available depth only**.
- It must **not** be used by B1 or B2 as a sizing decision.
- It must **not** imply allocation, routing, execution, candidate selection, ranking, threshold, score, or
  verdict.
- B1 and B2 must remain **evidence carriers only**.

---

## 10. Relationship to B2 / B3 / Phase 5

- This charter **does not** authorize B2 depth-field runtime.
- This charter **does not** authorize B3 mapping or wiring.
- This charter **does not** authorize Phase 5 runtime modification.
- Future B2 depth-field implementation may proceed **only after** this source amendment is reviewed and
  separately authorized.
- Future B3 may consume depth fields **only after** B1 and B2 have **both** supplied exact,
  provenance-tagged depth evidence.

---

## 11. Still-Blocked Work

- **No B1 adapter/runtime implementation** is authorized.
- **No B2 schema runtime implementation for depth fields** is authorized.
- **No tests** are authorized.
- **No B3 implementation** is authorized.
- **No Phase 5 runtime change** is authorized.
- **No live public read** is authorized.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

---

## 12. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS
token exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must
never be read as "capacity validated."

---

## 13. Future TDD Proof Targets (planning notes only — NOT written now)

1. **Public-only / unauthenticated endpoint allowlist** — only public depth sources admitted.
2. **No secrets / env / private endpoints** — no keys, sessions, account/wallet/order/balance endpoints.
3. **Replay-artifact-first depth evidence** — first slice consumes replay artifacts only.
4. **Immutable depth artifact / source references** — depth artifact/source cannot be mutated.
5. **Exact source-field provenance** — `depth_source_field` identifies the precise source key/path.
6. **No retrieval/observed timestamp substitution** — depth observed time distinct from retrieval time.
7. **Fail-fast on missing/malformed/mutable depth evidence**.
8. **No sizing/allocation/routing/actionability semantics** — `observed_size` stays evidence-only.
9. **No network in the first implementation slice**.
10. **No carrier construction or Phase 5 bypass** — only the admissible B1 → B2 → B3 → Phase 5 chain.

---

## 14. Next Safe Step

- After this docs-only charter, the next step is a **separate review** deciding whether to authorize a
  narrow **replay-artifact-only B1 depth source contract/TDD slice**, or a **B2 depth-field contract slice**.
- **Implementation is not authorized by this charter.** B1 adapter implementation, Phase 6.2 calibration,
  and 7.x/8.x remain separately gated.
