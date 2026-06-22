# Post-Phase 6.2 — Read-Only Real-World Evidence Acquisition Boundary Charter

> **This is a docs-only ingress-boundary charter.** It reconciles the as-built Option-B → S5 → S1 → Phase 6.2
> topology with the stale planning text, **pins one exact future read-only acquisition topology**, and makes
> **exactly one** future read-only one-shot acquisition runtime/TDD slice **ELIGIBLE — only after independent
> external ratification of this committed charter.** It **builds nothing and authorizes nothing executable**: no
> runtime code, no collector, no tests, no fixtures, no adapter, no config, no locks, no package exports, no tracking
> files, no pytest, no graphify, and **no network call**. Committing it performs **no data acquisition**. It is
> subordinate to the Phase 6.2 Slice-G closeout charter
> (`docs/handoff/phase6_2_slice_g_runtime_closeout_ratification.md`), the Phase 6.1 / Phase 5 charter chain, and
> `CLAUDE.md`; where any conflict arises, those govern, **except** that this charter is expressly authorized to
> supersede the single stale "in-memory-only persistence" planning statement (§5) and to record the stale
> roadmap/B1 topology statements (§2).

**Base:** `570d60725c5dd3c9e45dd7054d83c7ed82f053f8`

---

## 1. As-Built Evidence Reconciliation (source-verified, not planning text)

Inspected and reconciled against the live tree at base `570d607` (not against stale planning prose):

| Reality | As-built finding (verified) |
|---|---|
| `phase6_1_s1_storage/s1_durable_sqlite_sink.py` | `S1DurableSqliteSink(*, database_path)` durably appends genuine frozen `ObservationScoreRecord` / `ObservationHaltRecord` via one ACID INSERT; `replay()` returns append-order rows; `append_sequence` (rowid) is ordering only, omitted from INSERT, never surfaced. **S1 durable storage/replay is COMPLETE.** |
| `phase6_1/s5_runner.py` | `run_in_memory_shadow_pipeline(*, text_stream, artifact_locator, market_provenance_context, gross_edge_binding_label_context, evidence_epoch_tolerance_ms, observation_sink)` drives one passive run to natural EOF and calls `observation_sink.record_observation(...)`. **S5 imports no `sqlite3` and no durable package**; it consumes a **caller-injected** Option-B text stream + one caller-supplied provenance context + one binding-label context. **S5 is not a network collector.** |
| `phase6_1/option_b_event_stream_reader.py` | `read_option_b_event_stream(*, text_stream, artifact_locator)` is a **dumb** per-physical-line `json.loads` parser emitting `OptionBEventEnvelope(parsed_payload_or_local_halt, artifact_locator, physical_record_position)` or an `OptionBLocalParseHalt(raw_line)`; medium metadata is carried verbatim, never sourced from the payload. |
| `phase6_1/cell3_passive_cost_context_source.py` | A **factory-only, hermetic, zero-cost test substrate** built exclusively through the frozen Phase 5 factories; cost magnitude is a carried constant `"0"` with an explicit honest declared zero-cost evidence string — **not** a real fee model. |
| `phase6_1/s1_in_memory_observation_sink.py` | A `record_observation` sink used in tests; the durable sink satisfies the same `record_observation` shape (duck-typed sink contract). |
| Phase 6.2 Slice-G closeout charter | Phase 6.2 is the deterministic, replay-only, quarantined **reconstruction** runtime (six behavior-bearing modules + inert initializer), COMPLETE + RATIFIED **only upon** independent external ratification of that Slice-G charter, in its **offline audit-reconstruction** scope. |
| `data/*.py` (e.g. `hyperliquid.py`, `hl_candles.py`, `polymarket.py`, `shortterm.py`, `orderbook_snapshot.py`, `chainlink_streams.py`, `ws_prices.py`, `fair_value.py`, `fee_rate.py`, `depth_enricher.py`, `clob_*`, `model_telemetry.py`, `shadow_quote.py`) | **Untrusted legacy candidates only.** Not automatically authorized dependencies; not inspected here for trust; see §6 reuse-gating. |

Mandatory explicit records:

1. **S1 durable storage/replay is COMPLETE, but real-world acquisition is NOT built.** There is no authorized
   network-reading collector and no proven public-source → S1 path.
2. **The old B1 charter (`docs/handoff/phase6_1_live_public_read_adapter_charter.md`) is planning-only** ("authorizes
   NO runtime, NO tests, NO network"; "Live public reads are deferred"). It **predates** the current Option-B → S5 →
   S1 → Phase 6.2 topology, **cannot itself authorize network reads**, and **cannot prove a valid source-to-S1 path.**
3. **S5 currently consumes a caller-injected Option-B text stream** plus one caller-supplied provenance context and
   one binding-label context. **It is not a network collector** and manufactures nothing.
4. **`S1DurableSqliteSink` accepts genuine SCORE/HALT records but has no authorized real-world acquisition
   coordinator.**
5. **Cell-3 is a factory-only zero-cost test substrate.** Records produced with it **must not** be called
   fee/slippage-complete or calibration-grade.

---

## 2. Stale Statements Recorded (and what supersedes them)

| Stale statement | Source | Status |
|---|---|---|
| "Phase 6.2 = Quantitative Calibration from shadow logs" | `phase5_to_live_canary_roadmap.md` (route table) | **STALE.** As-built Phase 6.2 is the deterministic offline **reconstruction** runtime (Slice-G closeout), **not** calibration. Calibration is a **later, separate** charter (§8 sequencing). *(Recorded only; the roadmap file is not edited here.)* |
| "Live public reads are deferred … not authorized"; planning-only B1 boundary | `phase6_1_live_public_read_adapter_charter.md` | **STALE/SUPERSEDED as an authority.** B1 is planning-only and predates Option-B→S5→S1→6.2; it neither authorizes network reads nor proves a source→S1 path. This charter (post-ratification) is the authority that makes one read-only slice eligible. *(B1 file not edited here.)* |
| Persistence is "in-memory sink only" | planning text / the `run_in_memory_shadow_pipeline` *name* | **SUPERSEDED (§5).** The live S5 callable already accepts a **caller-supplied `record_observation` sink** (dependency injection); durable persistence is achieved by injecting `S1DurableSqliteSink`. The "in-memory-only" notion is the **one** stale statement this charter is authorized to supersede. **S5 is NOT modified in this docs task.** |

No other stale statement is superseded; no planning text is treated as current implementation.

---

## 3. Selected & Pinned Future Ingress Topology (exactly one)

This charter selects **one** exact direction — no competing alternatives:

```
public, unauthenticated read-only source
  -> immutable raw-response capture WITH retrieval/source provenance   (RAW_CAPTURED)
  -> source-specific projection into the already-ratified Option-B physical event shape
  -> one homogeneous bounded batch per exact (market / provenance / binding) context
  -> existing Option-B reader  (read_option_b_event_stream)
  -> existing S2 / B2 / Cell-3 / B3 / B4 / S4 / S5 chain  (run_in_memory_shadow_pipeline; UNMODIFIED)
  -> exact frozen SCORE / HALT records
  -> caller-injected S1DurableSqliteSink  (dependency injection; database_path-owned)
  -> append-order S1 replay  (replay())
  -> existing Phase 6.2 reconstruction  (verify_artifact -> reconstruct_shadow_intent_state)
```

The acquisition boundary terminates at producing the **Option-B physical event stream** (and preserving the raw
response); everything downstream is the already-built, unmodified chain.

---

## 4. Ownership Rules (pinned)

- The acquisition boundary owns **only**: one-shot public fetch; exact raw-byte capture; retrieval provenance; and
  source-specific projection into the Option-B physical event shape.
- It owns **no** scoring, lifecycle classification, reconstruction, calibration, thresholds, strategy, execution, or
  actionability.
- **S5 remains storage-ignorant:** it must not import SQLite or the durable package. **Durable persistence is
  caller-owned dependency injection** (the caller constructs `S1DurableSqliteSink(database_path=…)` and passes it as
  `observation_sink`).
- **No** direct SQL insert, fabricated DTO, synthetic SCORE/HALT, or bypass around Option-B / S2 / B2 / S5 is
  permitted. The only path to S1 is genuine records emitted by the unmodified S5 chain.
- **Raw evidence MUST be preserved before projection.** The irreversible S1 textual projection is **not** a
  replacement for the original public response; the raw response (bytes + provenance) is retained independently.
- `rowid` / `append_sequence` remains **ordering only**, never domain identity.
- **Historical evidence and HALTs are never censored or removed** — malformed lines become genuine local-parse
  halts / `ObservationHaltRecord`s and are appended verbatim, not dropped.

---

## 5. The One Authorized Supersession (docs-only)

The stale "in-memory sink only" persistence statement is **superseded** because the live callable already supports
caller-supplied `record_observation` sinks: `run_in_memory_shadow_pipeline` calls `observation_sink.record_observation(...)`
on a caller-injected sink and imports no storage. Therefore **durable persistence is the caller injecting
`S1DurableSqliteSink`**, not a code change to S5.

- This supersession is **documentary only**. **`phase6_1/s5_runner.py` is NOT modified in this docs task** (and no
  rename of `run_in_memory_shadow_pipeline` is implied or authorized here).
- No other persistence/topology statement is superseded.

---

## 6. Public-Source Quarantine & Reuse-Gating

- **Only public, unauthenticated market-data reads** may become eligible.
- **Forbidden:** private/account/wallet/balance/order/trade endpoints; API signing; credentials; secrets; execution
  modules; Telegram; broker clients; any authenticated or stateful-session surface.
- **Existing `data/` modules are legacy candidates only.** Reuse of any one of them may be authorized **only after**
  separately proving, per module:
  1. **public and unauthenticated** (no auth/signing/credential/secret path);
  2. **no private/execution imports** (no `clob_live_adapter` / order / wallet / broker / Telegram transitive deps);
  3. **no fallback/default manufacturing** (no synthesized value when the source is missing/unavailable);
  4. **no cache-derived stale substitution** (no returning a prior/cached value as if freshly fetched);
  5. **exact source-field authority** (each Option-B field traces to an exact named source field, verbatim);
  6. **exact raw-response preservation** (the unprojected response is retained).
- **No endpoint response or field mapping is invented here.** The acquisition slice must inventory the exact public
  endpoint families and exact response fields it needs and prove the six gates above before any reuse.

### 6.1 Required Option-B payload fields (target shape) and exact source-authority blockers

The ratified Option-B passive physical line (consumed by the dumb `json.loads` reader and validated downstream by
S2/B2) carries these fields: **`gross_magnitude`, `unit`, `venue`, `pair`, `observed_at_epoch_ms`** (all as exact
strings). Projecting a raw public response into this shape currently has **unresolved source-authority blockers**
that the acquisition slice MUST resolve (named, not invented):

- **BLOCKER B-1 — `gross_magnitude` (+ `unit`) authority.** `gross_magnitude` is a **gross-edge** quantity, **not a
  verbatim field** of any public unauthenticated market-data endpoint (those expose prices / orderbook / funding,
  not a pre-computed gross edge). Its exact source-field provenance / admissible derivation authority is
  **unresolved** and may not be fabricated or defaulted.
- **BLOCKER B-2 — `observed_at_epoch_ms` authority.** Event-time vs retrieval-time must be disambiguated: which exact
  source timestamp is authoritative, and whether it satisfies the S5 `evidence_epoch_tolerance_ms` contract, is
  **unresolved**. Retrieval time is **not** silently substitutable for event time.
- **BLOCKER B-3 — `venue` / `pair` canonical-token authority.** The exact mapping from a source's instrument
  identifiers to the Option-B `venue` / `pair` tokens must be an exact-source-field mapping with **no fabricated
  normalization**; it is **unresolved** here.
- **BLOCKER B-4 — real cost/fee/slippage authority (calibration firewall).** No real fee/slippage source exists; only
  the Cell-3 zero-cost substrate. This **blocks CALIBRATION_ELIGIBLE** (§7), not RAW/S1 structural observation.

These blockers are exact and must be closed (or each unavailable field formally named as a standing blocker) by the
future acquisition + quality charters — never papered over.

---

## 7. Calibration-Eligibility Firewall (three distinct evidence classes)

- **RAW_CAPTURED** — a genuine public response preserved verbatim with retrieval/source provenance, before any
  projection.
- **S1_AUDITED** — genuine `ObservationScoreRecord` / `ObservationHaltRecord`s produced through the **ratified,
  unmodified** Option-B→S5 chain and durably appended via `S1DurableSqliteSink`.
- **CALIBRATION_ELIGIBLE** — **forbidden** until **all** of: real cost/fee/slippage context (not Cell-3 zero-cost);
  resolved source authority (§6.1 blockers closed); data-quality thresholds; and an **independent sufficiency
  ratification** exist.

**Current zero-cost Cell-3 output may reach RAW_CAPTURED / S1_AUDITED for structural observation only, and MUST NEVER
be labeled CALIBRATION_ELIGIBLE.** Reaching S1_AUDITED proves structural plumbing, never economic sufficiency.

---

## 8. Sequencing (pinned actual next steps)

1. **This docs charter.**
2. **Independent Gemini + Codex ratification** of the committed charter.
3. **One** separately-authorized read-only **one-shot** acquisition runtime/TDD slice (§3/§4/§9).
4. **Start accumulating** genuine RAW_CAPTURED and S1_AUDITED evidence.
5. While evidence accumulates, **build the separate quality/baseline measurement charter.**
6. **Threshold ratification and sufficiency verdict.**
7. **Separate calibration/analytics charter.**
8. **Offline calibration and out-of-sample replay.**
9. **Phase 7.1 eligibility review.**

Each step is its own separately-authorized gate; no step is opened by completing the prior one.

---

## 9. Execution Lifecycle of the First Acquisition Slice (bounded, one-shot)

The first future acquisition runtime must be **one-shot and bounded**:

- exactly **one caller-triggered acquisition**;
- **no** daemon, cron, scheduler, reconnect loop, polling loop, background worker, thread, or async supervisor;
- **explicit timeout and fail-fast** network behavior;
- **no retry and no fallback** in the first slice;
- **raw response captured before parsing** (RAW_CAPTURED precedes any projection);
- **natural completion closes all network and database resources**;
- **no partial synthetic success** after any failure — a failed fetch yields a clean failure, never a fabricated or
  partial record.

---

## 10. Capacity & Authority

- **Capacity remains exactly 0.** No capacity pass or validation exists.
- **No** paper, canary, live trading, execution, routing, order, sizing, allocation, wallet, balance, or
  actionability surface exists or is authorized.
- **"Live" in this charter means public read-only observation only — never live trading.**
- **Phase 6.2 remains COMPLETE + RATIFIED in its narrow offline reconstruction scope** (conditional on the Slice-G
  charter's own independent ratification); this charter does not alter that scope.
- **Phase 7.1, Phase 7.2, and Phase 8.1 remain BLOCKED.**
- **Committing this charter builds no collector and performs no data acquisition.**

---

## 11. Frozen / Unchanged Surfaces

This charter changes **none** of: `phase6_1/` (Option-B reader, S5 runner, Cell-3, in-memory sink); `phase6_1_s1_storage/`;
`phase6_2_shadow_intent/` (runtime + `__init__.py`); S1 / S5; the frozen DTOs; `config.py`; any `data/` module; existing
charters (roadmap and B1 included); lock tests; capacity boundaries; analytics/export boundaries. It adds **only** the
single new docs file
`docs/handoff/post_phase6_2_read_only_real_world_evidence_acquisition_boundary_charter.md`.

---

## 12. Post-State (after commit)

- **This charter:** BUILT / RATIFIABLE / **UNRATIFIED**, pending independent Gemini + Codex review.
- **Read-only one-shot acquisition runtime:** **UNBUILT**, pending independent ratification (eligible to be opened
  only at sequencing step 3).
- **Data collection:** **NOT STARTED.**
- **Data sufficiency / calibration:** **NOT ESTABLISHED.**
- **Capacity:** **0.**

**Conclusion:** S1 durable storage/replay is complete, but real-world acquisition is unbuilt; the old B1 charter is
planning-only and cannot authorize network reads or prove a source→S1 path; S5 is a storage-ignorant, caller-injected
pipeline (not a collector); `S1DurableSqliteSink` has no acquisition coordinator; and Cell-3 is an honest zero-cost
substrate that is never calibration-grade. The **one pinned ingress topology** is *public unauthenticated read →
immutable raw capture with provenance → source-specific projection into the ratified Option-B physical shape → one
bounded homogeneous batch → existing Option-B reader → unmodified S2/B2/Cell-3/B3/B4/S4/S5 chain → exact SCORE/HALT →
caller-injected `S1DurableSqliteSink` → append-order replay → existing Phase 6.2 reconstruction*, with the acquisition
boundary owning only fetch / raw capture / provenance / projection and nothing downstream, durable persistence as
caller-owned DI, raw evidence preserved before irreversible projection, `append_sequence` as ordering only, and HALTs
never censored. The single authorized supersession is the stale "in-memory-only persistence" statement (now caller-injected
DI; S5 unmodified). Public-source quarantine forbids all private/account/execution/credential surfaces; `data/` modules are
legacy candidates gated behind six reuse proofs; and the exact source-authority blockers **B-1 `gross_magnitude`/`unit`**,
**B-2 `observed_at_epoch_ms`**, **B-3 `venue`/`pair`**, and **B-4 real cost/fee authority** are named, not invented. The
calibration firewall keeps Cell-3 output at most S1_AUDITED, never CALIBRATION_ELIGIBLE. **Capacity stays 0; Phases 7.1 /
7.2 / 8.1 remain BLOCKED; this charter is BUILT / RATIFIABLE / UNRATIFIED, and exactly one read-only one-shot acquisition
slice becomes eligible only upon independent external ratification of this committed charter. Committing it builds no
collector and acquires no data.**
