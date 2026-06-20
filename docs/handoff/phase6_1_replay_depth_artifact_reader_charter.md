# Phase 6.1 Replay Depth-Artifact Reader Planning Charter

> **This is a planning/charter document only.** It defines the strict IO/parsing boundaries for a *future*
> replay-only depth-artifact reader that may later construct `PublicDepthSourceRecord` from a local replay
> artifact. It authorizes NO runtime, NO tests, NO artifact reading, NO B2 threading, NO B3 wiring, NO
> Phase 5 runtime change, NO live/public/private network read. It is subordinate to
> `docs/handoff/phase6_1_b1_depth_source_amendment_charter.md`,
> `docs/handoff/phase6_1_b2_schema_extension_charter.md`, and
> `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md`. Where any conflict arises,
> those govern.

**Base:** `bab9b3d1416d1f278c259495a73ddd0575431b0d`

---

## 1. Base and Dependency Chain

| Step | Artifact | SHA |
|------|----------|-----|
| B1 depth source amendment charter | future depth-evidence source requirements | `96eccb4` |
| B1 depth source contract (runtime carrier) | `PublicDepthSourceRecord` + `make_public_depth_source_record` | `235de27` |
| B2 depth source identity reference | `NormalizedEvidenceMaterial.depth_source_reference` (optional, by identity) | `bab9b3d` |

- See `docs/handoff/phase6_1_b1_depth_source_amendment_charter.md` — the future B1 depth-evidence source
  requirements (public-only, replay-artifact-first, immutable anchor, time isolation, no sizing/actionability).
- See `docs/handoff/phase6_1_b2_schema_extension_charter.md` — the field inventory that grouped
  `CORE_MARKET_IDENTITY_OR_BINDING_FIELDS` (implemented) and `B1_PLUS_B2_SOURCE_DEPENDENT_FIELDS` (carried by
  the B1 depth contract; threading into B2 normalization still blocked).
- See `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` — the external-market
  replay provenance requirements (immutable anchor, retrieval-vs-observed time isolation, anti-spoofing).

**`PublicDepthSourceRecord` exists** at `phase6_1/b1_depth_source_contract.py` (created `235de27`) and is
constructed only through `make_public_depth_source_record(...)`. **B2 can already hold it by exact identity**
via the optional `NormalizedEvidenceMaterial.depth_source_reference` field (at `bab9b3d`); B2 does not copy,
extract, inspect, or parse any depth subfield.

**The replay depth-artifact reader is not implemented yet.** No reader, parser, or fetcher exists.

**No capacity validation and no capacity pass is claimed by this charter** (see §13).

---

## 2. Purpose and Boundary

- The future reader is **replay-artifact-only**.
- It may, in a **later separately authorized** implementation slice, read a **local replay artifact** only.
- It must produce a `PublicDepthSourceRecord` **and nothing else**.
- It must **not** produce B2 material (`NormalizedEvidenceMaterial`, `NormalizedEvidenceFieldBinding`,
  `PublicRawSnapshotRecord`) directly.
- It must **not** wire B2 or B3.
- It must **not** call Phase 5.
- It must **not** make live, public, or private network calls.

The reader is an evidence-loading boundary, not a decision boundary.

---

## 3. Strict Field Contract

A future replay depth artifact must provide **all 8** `PublicDepthSourceRecord` fields **explicitly**:

- `observed_size`
- `size_unit`
- `depth_source_field`
- `depth_source_artifact`
- `depth_source_contract`
- `depth_snapshot_identity`
- `depth_observed_at_epoch_ms`
- `depth_retrieval_epoch_ms`

Rules:

- **Missing** required fields must **fail fast**.
- **Unknown extra semantic fields** must **fail fast** unless separately chartered.
- **No default values** may be invented — not `None`, not `"UNKNOWN"`, not `0`, not the empty string, and not
  any fallback contract value. The artifact supplies every field, or construction fails.

---

## 4. No Numeric Parsing / No Type Coercion

- The reader must **not** parse `observed_size` into `int`, `float`, `Decimal`, `complex`, or any numeric type.
- The reader must **preserve `observed_size` as the exact artifact string**.
- The reader must **not** stringify a numeric value after parsing (no parse-then-`str()` round trip).
- The reader must **reject** artifacts where `observed_size` is not **already** represented as an exact string.
- The reader must **not** compare, aggregate, threshold, rank, score, or normalize `observed_size`.
- Future tests must prove **precision-preserving verbatim carriage** — e.g. `"100.00"` remains `"100.00"`
  (no collapse to `"100.0"` or `100`), and `"not-a-number"` is carried verbatim as a string. `observed_size`
  is evidence only; the reader never judges it.

---

## 5. Timestamp and Lookahead-Bias Rules

- `depth_observed_at_epoch_ms` must be an **explicit artifact string**, a **canonical unsigned integer
  string** (digits only, no sign, no separators, no leading zeros; `"0"` is the sole zero form).
- `depth_retrieval_epoch_ms` must be an **explicit artifact integer**.
- The reader must **not** copy, substitute, or derive the observed time from the retrieval time.
- The reader must **fail fast** if `depth_observed_at_epoch_ms == str(depth_retrieval_epoch_ms)` (the
  anti-copy / time-isolation lock already enforced by the B1 carrier; the reader must not route around it).
- The reader must **fail fast** on missing, malformed, or ambiguous timestamps.

These rules preserve replay determinism and forbid any lookahead-bias path.

---

## 6. Immutable Artifact Anchor

- A future reader must require an **immutable replay artifact anchor** before construction.
- Candidate anchor fields **may** include the artifact path/reference, a content hash, a parser identity, a
  schema version, and a verifier result — **but this charter does not implement them** and does not fix their
  exact shape.
- The reader must **not** fabricate artifact hashes or provenance anchors.
- The reader must **fail fast** if the artifact anchor is missing, mutable, malformed, or inconsistent.
- Anchor requirements must align with
  `docs/handoff/phase5_external_market_replay_provenance_amendment_charter.md` (immutable provenance anchor,
  retrieval-vs-observed time isolation, market-vs-intent provenance isolation, anti-spoofing).

---

## 7. No Live / Network / Env / Secrets

- **No** `requests`, `urllib`, HTTP clients, sockets, `aiohttp`, `websocket`/`websockets`, or network fallback.
- **No** environment access, secrets, or API keys.
- **No** account, wallet, private, order, balance, or trading endpoints.
- **No** fallback from a missing artifact to a live API.
- Future tests must **AST-scan** the reader runtime for network, env, secret, and private-endpoint usage and
  reject any occurrence.

---

## 8. Local IO Scope

- Any future implementation may **only** read the **explicitly supplied** local replay artifact
  path/reference.
- **No** directory scanning, globbing, config discovery, or implicit path lookup unless separately chartered.
- **No** writes.
- **No** mutation of the replay artifact.
- **No** subprocess and **no** dynamic exec (`eval`, `exec`, `compile`, `__import__`).

---

## 9. Provenance and Anti-Spoofing

- The reader must construct `PublicDepthSourceRecord` **through `make_public_depth_source_record` only**.
- The reader must **not** bypass the B1 depth contract (no `object.__new__`/`object.__setattr__` construction,
  no direct field injection).
- `depth_source_contract` must be **explicit from the artifact** and must **not spoof** internal
  planning-artifact provenance.
- `depth_source_artifact` and `depth_snapshot_identity` must remain **traceable** to the replay artifact.
- The reader must **not** fabricate or backfill provenance fields.

---

## 10. No Actionability / No Sizing Semantics

- The reader must treat `observed_size` as **evidence only**.
- The reader must **not** decide whether depth is enough or insufficient.
- The reader must **not** create sizing, allocation, routing, execution, candidate, signal, score, threshold,
  ranking, verdict, trade, paper, live, wallet, balance, or account semantics.
- The reader stays an evidence-loading boundary; it carries depth evidence and decides nothing.

---

## 11. Relationship to B2 / B3 / Phase 5

- This charter **does not** authorize threading depth into B2 replay normalization.
- This charter **does not** authorize B3 mapping or wiring.
- This charter **does not** authorize Phase 5 runtime modification.
- Future B2 threading of `depth_source_reference` (beyond the already-implemented optional identity hold) must
  be **separately authorized**.
- The future reader may **only** produce `PublicDepthSourceRecord`, never `NormalizedEvidenceMaterial`.

---

## 12. Still-Blocked Work

- **No runtime reader implementation** is authorized.
- **No tests** are authorized.
- **No B2 threading** is authorized.
- **No B3 implementation** is authorized.
- **No Phase 5 runtime change** is authorized.
- **No live/network read** is authorized.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

---

## 13. Capacity Invariant

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token
exists or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be
read as "capacity validated."

---

## 14. Future TDD Proof Targets (planning notes only — NOT written now)

1. **Missing required fields fail fast** — any of the 8 fields absent → reject.
2. **Unknown semantic fields fail fast** — extra semantic keys → reject unless separately chartered.
3. **No numeric parsing / coercion of `observed_size`** — AST-scan rejects `int`/`float`/`Decimal`/`complex`
   and the `decimal` import.
4. **Exact string preservation** — `"100.00"` stays `"100.00"`; `"not-a-number"` carried verbatim.
5. **Timestamp isolation** — observed time distinct from retrieval; reject when
   `depth_observed_at_epoch_ms == str(depth_retrieval_epoch_ms)`.
6. **Immutable artifact anchor required** — construction blocked without a valid immutable anchor.
7. **No network / env / secrets / private endpoints** — AST-scan rejects them.
8. **Local explicit artifact only** — no globbing/discovery/implicit lookup.
9. **No writes / subprocess / dynamic exec**.
10. **Construct via `make_public_depth_source_record` only** — no carrier bypass.
11. **No B2 / B3 / Phase 5 bypass** — only the admissible B1 → B2 → B3 → Phase 5 chain.
12. **No sizing / actionability semantics** — `observed_size` stays evidence-only.

---

## 15. Next Safe Step

- After this docs-only charter, the next step is a **separate review** deciding whether to authorize the
  **first replay depth-artifact reader TDD slice**.
- That future slice, **if authorized**, must be **replay-only**, **local-artifact-only**, **no network**,
  **no B2 threading**, and **no Phase 5 / B3**.
- **No implementation is authorized by this charter.** B1 reader implementation, B2 depth threading, B3
  mapping/wiring, Phase 5 runtime changes, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
