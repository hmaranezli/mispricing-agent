# Phase 6.1 — MarketProvenanceContext Runtime DTO TDD Closeout / Ratification Charter

> **This is a docs-only closeout/ratification charter.** It permanently seals the **completed**
> `MarketProvenanceContext` runtime DTO slice (commit `52f21af`). It **builds and designs nothing**. It authorizes
> NO runtime code, NO tests, NO lock-test edits, NO schema/runtime/interface edits, NO edits to the Reader / S2 / B2
> / B3 / Producer / Phase 5 / B4 / S4 / S1 / S5 / lock-tests, NO B2 ingestion runtime, NO S5 runtime, NO storage, NO
> Cell-3 assembly, NO Phase 6.2 work, NO pytest, NO graphify. It is subordinate to
> `docs/handoff/phase6_1_market_provenance_context_field_shape_charter.md`,
> `docs/handoff/phase6_1_d3_non_payload_provenance_supply_contract_charter.md`,
> `docs/handoff/phase6_1_b2_pass_path_ingestion_normalization_contract_charter.md`, and `CLAUDE.md`; where any
> conflict arises, those govern.

**Base:** `52f21af4299f7428f9012d30cf08507b068d58d7`

---

## 1. Base / Dependency Chain

**Base commit:** `52f21af4299f7428f9012d30cf08507b068d58d7`.

References:

- `…_market_provenance_context_field_shape_charter.md` — fixed the frozen, methodless ten-field passive container
  shape this slice implements.
- `…_d3_non_payload_provenance_supply_contract_charter.md` — designed the envelope and the explicit 14-field
  payload+envelope mapping (this DTO is the envelope side).
- `…_b2_pass_path_ingestion_normalization_contract_charter.md` — the still-blocked ingestion edge this DTO is a
  prerequisite for (not resolved here).

**Implemented commit under closeout:** `52f21af` (parent `3328af4`).

**No capacity validation and no capacity pass is claimed by this charter** (see §10).

---

## 2. Current State

- The `MarketProvenanceContext` runtime DTO is **implemented and green** (`52f21af`): a frozen, slotted, immutable,
  methodless passive provenance carrier with exactly ten supplied non-payload fields.
- The Option-B reader/payload, S2, B2, `PublicRawSnapshotRecord`, B3, Producer, Phase 5, B4, S4, S1, and S5 docs
  remain **BUILT/RATIFIED and frozen**. The DTO is **not wired into ingestion** — it is a **test-substrate carrier**.
- The pass path remains **contract-incomplete**; the halt path is complete; Phase 6.1 incomplete; Phase 6.2 not
  ready.

---

## 3. Ratified Implementation Facts (from `52f21af`)

- **Commit:** `52f21af` — `feat(phase6_1): add market provenance context dto` — a **strict 2-file runtime + test
  slice**:
  - `phase6_1/market_provenance_context.py` (new)
  - `tests/test_phase6_1_market_provenance_context.py` (new)
  - Totals: **2 files changed, +305**. No lock-test, docs, Reader, S2, B2, B3, Producer, Phase 5, B4, S4, S1, S5,
    config, data, or storage file touched.
- **Public DTO (RATIFIED):** `MarketProvenanceContext` — `@dataclass(frozen=True, slots=True)` with exactly the ten
  fields `source_artifact`, `source_field`, `base_asset`, `quote_asset`, `instrument_id`, `venue_scope`,
  `venue_buy`, `venue_sell`, `retrieval_epoch_ms`, `raw_snapshot_identity`. Frozen; any field/shape/behavior change
  requires **separate authorization**.
- **Verification (RATIFIED):** DTO suite **18/18**; **both full package-wide lock files passing** (no lock edit, no
  allowlist); recent runtime peers **S4 22/22, B4 21/21, S1 sink 25/25 → 71 passed**; **zero regressions**; **no
  broad pytest**.
- **TDD discipline (RATIFIED):** real RED first (`ModuleNotFoundError` for the missing module). One **avoidable
  prose collision** (the docstring spelled the S2 carrier name) was resolved by **conforming the code** (docstring
  scrub), **never** by weakening the test — honoring the sealed precedent.

---

## 4. Dumb Carrier Seal (RATIFIED)

- `MarketProvenanceContext` is a **strictly passive, frozen/slotted dataclass carrier** with **exactly ten fields**
  and **no extras** (proven: field-surface equality, `__slots__` equals the ten names, no instance `__dict__`).
- It performs **no** semantic validation, parsing, splitting, inference, derivation, normalization, coercion,
  defaulting, casting, business logic, cost logic, routing, scoring, or readiness — and exposes **no** helper/
  static/class method, computed property, or convenience surface (AST-proven: the only function/method in the module
  is `__post_init__`; the only class is `MarketProvenanceContext`; no method decorators).

---

## 5. Structural Guard Ratification (RATIFIED)

- `__post_init__` is ratified as **purely structural**, enforcing **only**:
  - the **nine** string fields are each an **exact `str`** (`type(v) is str`) and **non-empty** (`v == ""` rejected
    with `ValueError`); and
  - `retrieval_epoch_ms` is an **exact `int`** (`type(...) is int`) and **non-negative** (`< 0` rejected with
    `ValueError`).
- It enforces **no** semantic vocabulary, market term, venue name, pair format, base/quote consistency, buy/sell
  meaning, identity pattern, or cost validity (proven: arbitrary non-empty strings — `"!!!"`, `"   "`,
  `"literally anything 123"` — are accepted verbatim). The guard reads fields and raises; it **sets, derives, and
  computes nothing**.

---

## 6. Bool-Rejection Precedent (RATIFIED)

- Because `type(True) is bool` (not `int`) and `type(True) is not str`, the exact-type guards **reject `bool`** for
  both the string fields and `retrieval_epoch_ms` (proven). This is ratified as a **strict-type precedent for future
  boundaries**: a `bool` must **never** be allowed to masquerade as an `int` or `str`. Exact-type discipline
  (`type(x) is T`, never `isinstance`) is the standing rule.

---

## 7. Verbatim Carriage Seal (RATIFIED)

- All ten caller-supplied values are **carried verbatim** (proven: `"  Btc  "` and `"MiXeDcAsE"` are stored
  unchanged). There is **no** split, trim/strip, case normalization (upper/lower), string formatting, casting,
  defaulting, hashing, UUID, counter, or generated/synthesized field. AST-proven: the module imports none of
  `re`/`uuid`/`datetime`/`time`/`hashlib`/`os`/`pathlib`/`io`/`sys`/`json`/`logging`, and calls/attributes none of
  `split`/`strip`/`lower`/`upper`/`replace`/`format`/`str`/`repr`/`hash`/`id`/`open`/`print`/`eval`/`exec`/
  `isinstance`.

---

## 8. Identity-Bypass Affirmation (RATIFIED)

- `raw_snapshot_identity` is **market identity only** — a caller-supplied string carried verbatim, on a plane
  **separate** from S2 Silver/System identity.
- The DTO has **no import, reference, or duplication** of the S2 identity carrier (proven: the source text contains
  neither the carrier class name nor its module name; the import set excludes it). It carries **no** Silver tuple.
  Market Identity and S2 System Identity remain strictly segregated; this DTO never derives one from the other.

---

## 9. Cost / Storage / Runner Exclusion (RATIFIED)

- **No** Cell-3, cost field, fee logic, or `cost_validity_contexts`; **no** COST/GROSS_EDGE binding label in the DTO
  (the ten fields are provenance only).
- **No** persistence/storage/DB/serialization/indexing/retention/cursor/checkpoint/run-state — the DTO is an
  **in-memory, ephemeral, per-event** carrier owning no log.
- **No** S5/runner logic, actionability, route, readiness, verdict, order, trade, execution, or scoring.

---

## 10. Capacity Invariant (Unchanged)

`CapacityConstraintGate` remains **deferred / non-activatable** with **0 emit sites**. No capacity PASS token exists
or is implied. `PassiveShadowInput.capacity_pass_reference` remains `None` / deferred and must never be read as
"capacity validated." Provenance is **not** a capacity decision.

---

## 11. Precise State

- The DTO is **BUILT + RATIFIED** as a **test-substrate provenance carrier**, but is **not wired into ingestion** —
  no component consumes it yet.
- The **pass path remains incomplete**; the **halt path is complete**; **S5 runtime remains ineligible**; **Phase
  6.1 is incomplete**; **Phase 6.2 is not ready**.
- Still-separate prerequisites before the pass path is contract-complete: (a) the **B2 pass-path ingestion contract/
  runtime** combining payload + provenance into `PublicRawSnapshotRecord`; and (b) a **passive cost-context (Cell-3)**
  source for B3/Producer. The **S1 storage-medium** charter remains independently gated; the S1 sink stays a
  **test-only reference sink**.

---

## 12. Still-Forbidden Work

- **No** change to the ratified DTO surface (§3) — no field add/remove/rename, no shape/behavior edit, no method
  beyond `__post_init__`, no semantic validation; **no** mutation/widening/wrap.
- **No** parsing/splitting/derivation/normalization/coercion/defaulting/casting/hashing/UUID/generation (§4, §7);
  **no** `bool`-as-`int`/`str` (§6).
- **No** S2 identity import/reference/duplication; **no** Silver tuple; **no** Market/System identity merge (§8).
- **No** cost/Cell-3/COST field; **no** storage/persistence/cursor/checkpoint/S5-state; **no** actionability/route/
  readiness/verdict/order/trade/execution/scoring (§9).
- **No** lock-test edit; **no** new allowlist; **no** weakening of any guardrail.
- **No** B2 ingestion runtime; **no** S5 runtime; **no** wiring of this DTO into any component.
- **No** Phase 6.1 completion claim; **no** Phase 6.2 readiness claim; **no** 7.x/8.x work.

---

## 13. Next Safe Step

- A **separately-authorized docs-only B2 pass-path ingestion-normalization contract charter** — designing how the
  Option-B payload **plus** this ratified `MarketProvenanceContext` combine into an exact `PublicRawSnapshotRecord`
  via the `f85349c` §6 mapping. Its **primary unresolved complexity** is twofold: (i) the **`field_payload`
  GROSS_EDGE label mapping** (where the binding labels `normalized_field_name` / binding `source_field` /
  `binding_role=GROSS_EDGE` legitimately originate — `MarketProvenanceContext` or a separate passive label
  contract), and (ii) **precision-safe string carriage** of the gross magnitude / `observed_at_epoch_ms`
  (verbatim-string discipline, the only permitted `list→tuple` / non-negative `int→str` conversions, no lossy
  numeric coercion).
- Independently: the **passive cost-context (Cell-3)** source charter and the **S1 storage-medium** charter. Each
  separately gated.
- Only after **both** the pass path (ingestion + cost-context) **and** the halt path are contract-complete does an
  **S5 runtime TDD slice** become eligible.
- **No implementation is authorized by this charter.**

**Conclusion:** the `MarketProvenanceContext` runtime DTO is **BUILT + RATIFIED** at `52f21af` (strict 2-file slice;
DTO **18/18**, both full lock files green with no lock edit, runtime peers **71 passed**, zero regressions, no broad
pytest) — a **strictly passive, frozen/slotted, immutable, methodless** carrier of **exactly ten** supplied
non-payload provenance fields, whose only method `__post_init__` is a **purely structural guard** (nine exact
non-empty `str`; `retrieval_epoch_ms` exact non-negative `int`) with **no** semantic validation, parsing,
derivation, coercion, defaulting, business/cost/routing/scoring logic, or helper method. **Bool rejection** is
sealed as a strict-type precedent; **verbatim carriage** is sealed (no split/trim/case/format/cast/hash/UUID/
generation); **identity bypass** is affirmed (`raw_snapshot_identity` is market identity only; no S2 carrier import/
reference/duplication; no Silver tuple); **cost/storage/runner** are excluded. It is a **test-substrate carrier, not
wired into ingestion**. Existing modules remain **frozen**; this authorizes **no** runtime; the **pass path remains
incomplete**, the **halt path complete**, **S5 runtime ineligible**, **Phase 6.1 incomplete**, and **Phase 6.2 not
ready**. **No executable work is authorized.**
