# Phase 6.1 Depth Evidence Replay Chain — Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It formally ratifies the completed Phase 6.1
> replay-only depth evidence chain and records the invariant proofs that hold at the base SHA. It
> authorizes NO runtime, NO tests, NO lock-test edits, NO B1/B2/B3/Phase 5/Shadow Intent runtime change,
> NO pytest, NO graphify update, NO network/API/env/secret access. It is subordinate to the charters it
> closes out; where any conflict arises, the constitution (`CLAUDE.md`) and the prior charters govern.

**Base:** `50ce30bb05de6f9c2d8acf7a272a5877911493a3`

---

## 1. What Is Ratified — The Completed Replay-Only Depth Evidence Chain

The following end-to-end, replay-only, read-only depth evidence chain is **complete and ratified** at this
base:

```
replay depth artifact (local, public, immutable)
  -> phase6_1/b1_replay_depth_artifact_reader.py   (read_replay_depth_artifact)
  -> PublicDepthSourceRecord                        (via make_public_depth_source_record)
  -> phase6_1/b2_replay_normalization.py            (normalize_replay_snapshot_to_evidence_material)
  -> NormalizedEvidenceMaterial.depth_source_reference  (optional, by exact identity)
```

The chain carries depth **evidence** only. It produces a trade nothing, decides nothing, and ranks nothing.
Each hop is exact-type, fail-fast, and provenance-preserving; the depth record is validated once (at the B1
factory) and thereafter carried blindly by identity.

**No capacity validation and no capacity pass is claimed by this charter** (see §3, last bullet, and §4).

---

## 2. Completed Commit Chain and Purposes

| SHA | Purpose |
|-----|---------|
| `908e263` | B2 schema extension charter — field inventory (core identity / binding / depth-source groups). |
| `6398291` | B2 core market identity fields (base/quote asset, venue scope/buy/sell, instrument id, observed time). |
| `5fbdec2` | B2 `binding_role` discriminator (`GROSS_EDGE` / `COST`), no default, addressed by label. |
| `0d993c9` | B2 `zero_cost_evidence` carrier (COST-only, optional; never derived from magnitude). |
| `96eccb4` | B1 depth source amendment charter — future replay depth-evidence source requirements. |
| `235de27` | `PublicDepthSourceRecord` contract — frozen/slotted/init-blocked depth carrier + factory. |
| `bab9b3d` | B2 `NormalizedEvidenceMaterial.depth_source_reference` slot (optional, by identity). |
| `c9125e5` | Replay depth-artifact reader planning charter — strict IO/parsing boundaries. |
| `ecfed7d` | IO-lock exception amendment charter — single basename-scoped no-IO carve-out. |
| `3b2d1e1` | IO-lock test amendment + replay depth reader (combined TDD slice). |
| `50ce30b` | B2 replay-depth threading — reader record → `depth_source_reference` by identity (this base). |

---

## 3. Ratified Invariant Proofs

The following invariants are proven by the locked test suite at this base and are ratified:

- **`PublicDepthSourceRecord` is strict** — frozen, slotted, `__init__`-blocked, anti-coercion (no
  truthiness/len/int/float/str/bytes), constructed only via `make_public_depth_source_record`.
- **Reader constructs only `PublicDepthSourceRecord`** — `read_replay_depth_artifact` builds exactly one
  record via the B1 factory and references no other carrier (no B2/B3/Phase 5 object).
- **`observed_size` remains exact string evidence** — carried verbatim (`"100.00"` stays `"100.00"`,
  `"not-a-number"` preserved); a JSON-number `observed_size` is rejected; no `Decimal`/`float`/`int`/
  `complex` parsing anywhere in the reader.
- **B2 carries `depth_source_reference` by exact identity** — proven with `is` **and** `id()`; the exact
  reader object is threaded through, never copied, deepcopied, serialized, dict/tuple-converted, or
  reconstructed.
- **Absent depth propagates as `None`** — default and explicit-`None` both carry `None`; no dummy,
  fabricated, `UNKNOWN`, or empty stand-in is ever created.
- **B2 does not inspect/parse depth subfields** — a word-boundary source scan proves none of
  `observed_size`, `size_unit`, `depth_source_field`, `depth_source_artifact`, `depth_source_contract`,
  `depth_snapshot_identity`, `depth_observed_at_epoch_ms`, `depth_retrieval_epoch_ms` is named/read in B2.
- **B2 adds no IO surface** — no `open`, no `json`/`csv`/`pathlib`/`io`/`os` import in B2 replay
  normalization; it accepts a reader-produced object or `None` from an explicit caller only.
- **The IO exception is basename-scoped** — the package-wide no-IO locks relax only for exactly
  `b1_replay_depth_artifact_reader.py` (read-only `open` + closed import allowlist `{pathlib, json, csv}`);
  every other `phase6_1/*.py` module stays under the full no-IO posture.
- **Network / env / secrets / write / append remain banned** — globally and inside the reader: no network
  roots, no `environ`/`getenv`/`popen`/`system`, no write/append/non-literal-mode `open`, no subprocess, no
  dynamic exec.
- **Time isolation remains enforced through the B1 depth contract** — `depth_observed_at_epoch_ms` (canonical
  unsigned int string, source-observed) must not equal `str(depth_retrieval_epoch_ms)`; the lookahead-bias
  lock fails fast.
- **Capacity invariant unchanged** — `CapacityConstraintGate` remains deferred / non-activatable with 0 emit
  sites; no capacity PASS token exists or is implied; `PassiveShadowInput.capacity_pass_reference` remains
  `None` / deferred and must never be read as "capacity validated."

---

## 4. Explicitly Blocked Boundaries

The following remain **unauthorized** and are **not** opened by this closeout:

- **No B3 mapping/wiring** is authorized.
- **No Phase 5 runtime integration** is authorized.
- **No Shadow Intent Envelope runtime/schema** is authorized.
- **No live/network public read** is authorized.
- **No actionability, sizing, allocation, route, execution, score, threshold, verdict, trade, or candidate
  semantics** are authorized.
- **No construction** of `PassiveShadowInput`, `ShadowObservation`, or `NetEdgeCalculationResult` is
  authorized.

The depth evidence chain ends at `NormalizedEvidenceMaterial.depth_source_reference`. Nothing downstream
consumes it yet, and nothing in this charter permits such consumption.

---

## 5. Future Work Requires Separate Review and Authorization

Any future B3 depth-evidence mapping/wiring, any Phase 5 integration, any Shadow Intent Envelope work, and
any live public read each require a **separate review** and a **separate charter / explicit authorization**.
This closeout grants none of them. The replay-only, evidence-only posture is the ratified ceiling for Phase
6.1 depth work at this base.

---

## 6. Next Safe Step

- The next step is a **separate review** to decide whether to author a **B3 depth-evidence mapping/wiring
  charter** (planning only).
- **No implementation is authorized by this closeout.** B3 mapping/wiring, Phase 5 integration, Shadow Intent
  Envelope, live reads, Phase 6.2 calibration, and 7.x/8.x remain separately gated.
