# Post-Phase 6.2 — Read-Only Real-World Evidence Acquisition Boundary Charter

> **This is a docs-only ingress-boundary charter** (corrective revision over base `a76cc6d`, created as a normal
> follow-up commit — the prior commit is **not** amended, rebased, or force-pushed). It reconciles the as-built
> Option-B → S5 → S1 → Phase 6.2 topology with the stale planning text, pins **one categorical end-to-end
> direction** (not an exact, executable acquisition topology), splits **raw acquisition** from **economic
> projection**, and makes — only after independent external ratification of this committed charter — **exactly one**
> next docs-only gate ELIGIBLE: the **"Public Source-Authority & Raw-Capture-Ledger Exact-Shape Charter."** It
> **builds nothing and authorizes nothing executable**: no runtime code, no collector, no tests, no fixtures, no
> adapter, no config, no locks, no package exports, no tracking files, no generated files, no pytest, no graphify,
> and **no network call**. Committing it performs **no data acquisition** and builds **no collector**. It is
> subordinate to the Phase 6.2 Slice-G closeout charter, the Phase 6.1 / Phase 5 charter chain, and `CLAUDE.md`;
> where any conflict arises those govern, **except** that this charter is expressly authorized to supersede the
> single stale "in-memory-only persistence" planning statement (§5) and to record the stale roadmap/B1 topology
> statements (§2).

**Base:** `a76cc6d0117a696bdd54ae14067c8893fb5a744f`

---

## 1. As-Built Evidence Reconciliation (source-verified, not planning text)

Inspected and reconciled against the live tree (not against stale planning prose):

| Reality | As-built finding (verified) |
|---|---|
| `phase6_1_s1_storage/s1_durable_sqlite_sink.py` | `S1DurableSqliteSink(*, database_path)` durably appends genuine frozen `ObservationScoreRecord` / `ObservationHaltRecord` via one ACID INSERT; `replay()` returns append-order rows; `append_sequence` (rowid) is ordering only, omitted from INSERT, never surfaced. **S1 durable storage/replay is COMPLETE.** |
| `phase6_1/s5_runner.py` | `run_in_memory_shadow_pipeline(*, text_stream, artifact_locator, market_provenance_context, gross_edge_binding_label_context, evidence_epoch_tolerance_ms, observation_sink)` drives one passive run to natural EOF and calls `observation_sink.record_observation(...)`. **S5 imports no `sqlite3` and no durable package**; it consumes a **caller-injected** Option-B text stream + one caller-supplied provenance context + one binding-label context. **S5 is not a network collector.** |
| `phase6_1/option_b_event_stream_reader.py` | `read_option_b_event_stream(*, text_stream, artifact_locator)` is a **dumb** per-physical-line `json.loads` parser emitting `OptionBEventEnvelope(parsed_payload_or_local_halt, artifact_locator, physical_record_position)` or an `OptionBLocalParseHalt(raw_line)`; medium metadata is carried verbatim, never sourced from the payload. |
| `phase6_1/cell3_passive_cost_context_source.py` | A **factory-only, hermetic, zero-cost test substrate** built exclusively through the frozen Phase 5 factories; cost magnitude is a carried constant `"0"` with an explicit honest declared zero-cost evidence string — **not** a real fee model. |
| `phase6_1/s1_in_memory_observation_sink.py` | A `record_observation` sink used in tests; the durable sink satisfies the same `record_observation` shape (duck-typed sink contract). |
| Phase 6.2 Slice-G closeout charter | Phase 6.2 is the deterministic, replay-only, quarantined **reconstruction** runtime (six behavior-bearing modules + inert initializer) in its **offline audit-reconstruction** scope. |
| `data/*.py` (e.g. `hyperliquid.py`, `hl_candles.py`, `polymarket.py`, `shortterm.py`, `orderbook_snapshot.py`, `chainlink_streams.py`, `ws_prices.py`, `fair_value.py`, `fee_rate.py`, `depth_enricher.py`, `clob_*`, `model_telemetry.py`, `shadow_quote.py`) | **Untrusted legacy candidates only** — not automatically authorized dependencies; gated behind §6 reuse proofs. |

Mandatory explicit records:

1. **S1 durable storage/replay is COMPLETE, but real-world acquisition is NOT built.** No authorized network-reading
   collector and no proven public-source → raw-capture path exist.
2. **The old B1 charter (`docs/handoff/phase6_1_live_public_read_adapter_charter.md`) is planning-only** ("authorizes
   NO runtime, NO tests, NO network"; "Live public reads are deferred"). It **predates** the current Option-B → S5 →
   S1 → Phase 6.2 topology, **cannot authorize network reads**, and **cannot prove a valid source-to-S1 path.**
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
| "Phase 6.2 = Quantitative Calibration from shadow logs" | `phase5_to_live_canary_roadmap.md` | **STALE.** As-built Phase 6.2 is the deterministic offline **reconstruction** runtime, **not** calibration. *(Recorded only; the roadmap file is not edited here.)* |
| "Live public reads are deferred … not authorized"; planning-only B1 | `phase6_1_live_public_read_adapter_charter.md` | **STALE/SUPERSEDED as an authority.** B1 is planning-only and predates the current topology; it neither authorizes network reads nor proves a source→S1 path. *(B1 file not edited here.)* |
| Persistence is "in-memory sink only" | planning text / the `run_in_memory_shadow_pipeline` *name* | **SUPERSEDED (§5).** The live S5 callable already accepts a **caller-supplied `record_observation` sink** (DI); durable persistence is achieved by injecting `S1DurableSqliteSink`. **S5 is NOT modified in this docs task.** |

No other stale statement is superseded; no planning text is treated as current implementation.

---

## 3. Categorical End-to-End Direction (one direction, not an exact topology)

This charter pins **one categorical direction** — not an exact, executable acquisition topology, and **not** a claim
that the unresolved Option-B field mapping is executable:

```
public, unauthenticated read-only source
  -> one-shot fetch + immutable append-only RAW capture WITH retrieval provenance     [== ACQUISITION BOUNDARY ==]
  ---------------------------------------------------------------------- terminates at RAW_CAPTURED
  -> (LATER, SEPARATE projection / S1-ingestion boundary — BLOCKED behind B-1/B-2/B-3)
       source-specific projection into the already-ratified Option-B physical event shape
  -> one homogeneous bounded batch per exact (market / provenance / binding) context
  -> existing Option-B reader  (read_option_b_event_stream)
  -> existing S2 / B2 / Cell-3 / B3 / B4 / S4 / S5 chain  (run_in_memory_shadow_pipeline; UNMODIFIED)
  -> exact frozen SCORE / HALT records
  -> caller-injected S1DurableSqliteSink  (dependency injection)                        [== S1-INGESTION BOUNDARY ==]
  -> append-order S1 replay  (replay())
  -> existing Phase 6.2 reconstruction  (verify_artifact -> reconstruct_shadow_intent_state)
```

The **acquisition boundary** is a strictly separate, earlier boundary from the **projection / S1-ingestion**
boundary. Only the categorical direction is pinned here; the projection/ingestion specifics are deferred to later,
separately-ratified charters.

---

## 4. Acquisition Boundary — Owns Raw Capture Only (split from economic projection)

The acquisition boundary owns **only**:

- one-shot **public, unauthenticated fetch**;
- the **exact raw response bytes**;
- the **retrieval timestamp / provenance**;
- **immutable, append-only raw capture**;
- **explicit network / resource failure reporting**.

It **must not** own:

- `gross_magnitude`;
- gross-edge calculation;
- Option-B projection;
- `venue` / `pair` canonicalization;
- event-time selection;
- S1 writing;
- scoring, costs, outcomes, calibration, or actionability.

**The acquisition boundary terminates at `RAW_CAPTURED`.** Everything beyond it (projection, S1 ingestion, scoring,
outcomes, calibration) belongs to later, separately-ratified boundaries.

---

## 5. The One Authorized Supersession (docs-only)

The stale "in-memory sink only" persistence statement is **superseded** because the live callable already supports
caller-supplied `record_observation` sinks: `run_in_memory_shadow_pipeline` calls
`observation_sink.record_observation(...)` on a caller-injected sink and imports no storage. Therefore **durable
persistence is the caller injecting `S1DurableSqliteSink`**, not a code change to S5.

- This supersession is **documentary only**. **`phase6_1/s5_runner.py` is NOT modified in this docs task** (no rename
  of `run_in_memory_shadow_pipeline` is implied or authorized).
- No other persistence/topology statement is superseded.

### 5.1 Required proofs for the later S1-ingestion TDD slice (preserve the DI conclusion)

The future, separately-authorized S1-ingestion runtime/TDD slice must prove:

- **direct `S1DurableSqliteSink` injection** (caller constructs `S1DurableSqliteSink(database_path=…)` and passes it
  as `observation_sink`);
- **exact SCORE/HALT preservation** (genuine frozen records, unaltered);
- **append-order preservation**;
- **no S5 storage imports and no internal persistence state** (S5 stays storage-ignorant);
- **deterministic resource closure and fail-fast propagation**.

**S5 is not modified in this docs task.**

---

## 6. Public-Source Quarantine & Reuse-Gating

- **Only public, unauthenticated market-data reads** may become eligible.
- **Forbidden:** private/account/wallet/balance/order/trade endpoints; API signing; credentials; secrets; execution
  modules; Telegram; broker clients; any authenticated or stateful-session surface.
- **Existing `data/` modules are legacy candidates only.** Reuse of any one may be authorized **only after** separately
  proving, per module: (1) public and unauthenticated; (2) no private/execution imports; (3) no fallback/default
  manufacturing; (4) no cache-derived stale substitution; (5) exact source-field authority; (6) exact raw-response
  preservation.
- **No endpoint response or field mapping is invented here.** The future charters must inventory exact endpoint
  families / response fields and prove the six gates before any reuse.

### 6.1 Blocker Ownership (reclassified)

- **Raw acquisition runtime is BLOCKED only until** the exact **public source/endpoint authority**, the
  **raw-capture carrier / storage shape**, **durability**, **resource ownership**, and **recovery law** are
  ratified (the next docs gate, §8 step 2). Raw-byte capture itself does **not** depend on B-1/B-2/B-3.
- **B-1 — `gross_magnitude` (+ `unit`) authority**, **B-2 — event-time (`observed_at_epoch_ms`) authority**, and
  **B-3 — `venue` / `pair` canonical-token mapping** block the **later Option-B projection / S1-ingestion boundary**,
  **not raw-byte capture itself**. `gross_magnitude` is a gross-edge quantity, not a verbatim public field; event-time
  vs retrieval-time authority is unresolved; instrument→token mapping must be exact-source-field with no fabricated
  normalization.
- **B-4 — real fee/cost/slippage authority** blocks **`CALIBRATION_ELIGIBLE`**, **not** raw capture or structural S1
  audit.

No endpoint, source schema, field mapping, or economic formula is invented in this correction.

---

## 7. Raw Evidence Failure Law (principles only — no concrete ledger schema invented)

- **Successfully committed raw evidence is permanent.**
- It **must never be rolled back or deleted** because projection, S5, S1, outcome generation, or calibration **later
  fails**.
- **No distributed atomic transaction** between the raw ledger and S1 is claimed.
- **Raw-only / incompletely-processed evidence is legitimate audit state, not corruption.**
- Downstream failure and retry history must eventually be represented through a **separate append-only processing
  journal** owned by the future raw-ledger exact-shape charter. **No concrete journal DTOs, enums, fields, or database
  tables are invented in this amendment.**
- **Retry must replay the same preserved raw evidence**; it must **never refetch and substitute new bytes as if they
  were the original observation**.
- **Exactly-once / duplicate handling remains BLOCKED** until that future charter pins its identity and recovery law.

---

## 8. Sequence — Complete Fast Path to Phase 7.1 (pinned)

1. **Corrected acquisition charter ratification** (independent Gemini + Codex review of this committed charter).
2. **Public Source-Authority & Raw-Capture-Ledger Exact-Shape Charter** (the one next docs-only gate, eligible only
   after step 1).
3. **Raw-only one-shot acquisition runtime/TDD** (separately authorized; §9 lifecycle).
4. **Genuine `RAW_CAPTURED` evidence begins accumulating immediately.**
5. While raw evidence accumulates:
   - the **Source-to-Option-B / gross-edge field-authority charter** closes **B-1, B-2, and B-3**;
   - its separately-authorized **projection / S1-ingestion runtime** is built.
6. **Genuine `S1_AUDITED` evidence begins accumulating.**
7. While S1 evidence accumulates:
   - the **`HYPOTHETICAL_OUTCOME` exact field-shape charter**;
   - a separately-authorized **inert `HYPOTHETICAL_OUTCOME` runtime/TDD**;
   - **real fee/cost/slippage authority work closing B-4**;
   - the **external calibration-eligibility manifest charter**.
8. **Quality / baseline measurement.**
9. **Threshold ratification and data-sufficiency verdict.**
10. **Calibration / analytics charter.**
11. **Offline calibration and out-of-sample / long-horizon replay.**
12. **Phase 7.1 Internal Paper Simulator eligibility review.**

**`HYPOTHETICAL_OUTCOME`** is pinned to be: computed from **later audited evidence as data accumulates**; **inert and
transition-non-driving**; **not** a fill, position, wallet state, realized PnL, or action signal; and it **must exist
before** sufficiency/calibration can use outcome-labelled cohorts.

---

## 9. Execution Lifecycle of the First Acquisition Slice (bounded, one-shot, raw-only)

- exactly **one caller-triggered acquisition**;
- **no** daemon, cron, scheduler, reconnect loop, polling loop, background worker, thread, or async supervisor;
- **explicit timeout and fail-fast** network behavior;
- **no retry and no fallback** in the first slice;
- **raw response captured before parsing** (`RAW_CAPTURED` precedes any projection);
- **natural completion closes all network and database resources**;
- **no partial synthetic success** after any failure — a failed fetch yields a clean failure, never a fabricated or
  partial record.

---

## 10. S1 Remains Frozen

- **Add no S1 field, bitmask, discriminator, eligibility flag, or schema change.**
- **S1 remains immutable append-only audit evidence.**
- **Calibration inclusion/exclusion is performed OUTSIDE S1**, through a **separately-ratified eligibility manifest**
  based on exact provenance, source authority, cost evidence, and outcome evidence.
- The eligibility manifest **must never delete, rewrite, hide, or filter** the underlying S1 audit trail.
- **Current Cell-3 zero-cost records remain structural S1 evidence only and are never calibration-eligible.**

---

## 11. Append Order & Provenance Time

- **Append order exclusively controls S1 replay order.**
- **Provenance / event-time reversal is measured evidence of arrival order, not a replay-order contradiction.**
- **Never reorder S1 by provenance timestamp.**
- **Never silently replace event time with retrieval time.**

---

## 12. Calibration-Eligibility Firewall (three distinct evidence classes)

- **RAW_CAPTURED** — a genuine public response preserved verbatim with retrieval/source provenance, before any
  projection (the acquisition boundary's terminal state).
- **S1_AUDITED** — genuine `ObservationScoreRecord` / `ObservationHaltRecord`s produced through the **ratified,
  unmodified** Option-B→S5 chain and durably appended via `S1DurableSqliteSink`.
- **CALIBRATION_ELIGIBLE** — **forbidden** until **all** of: real cost/fee/slippage context (not Cell-3 zero-cost);
  resolved source authority (B-1/B-2/B-3 closed); data-quality thresholds; outcome evidence
  (`HYPOTHETICAL_OUTCOME`); and an **independent sufficiency ratification** exist.

**Current zero-cost Cell-3 output may reach RAW_CAPTURED / S1_AUDITED for structural observation only, and MUST NEVER
be labeled CALIBRATION_ELIGIBLE.**

---

## 13. Capacity & Authority

- **Capacity remains exactly 0.** No capacity pass or validation exists.
- **No** paper, canary, live trading, execution, routing, order, sizing, allocation, wallet, balance, or
  actionability surface exists or is authorized.
- **"Live" in this charter means public read-only observation only — never live trading.**
- **Phase 6.2 is COMPLETE + RATIFIED in its narrow deterministic offline audit-reconstruction scope.** (Slice A–F
  remain RATIFIED + SEALED as separate historical evidence; no aggregate SEALED label is asserted.)
- **Phase 7.1, Phase 7.2, and Phase 8.1 remain BLOCKED.**
- **Committing this charter builds no collector and performs no data acquisition.**

---

## 14. Frozen / Unchanged Surfaces

This charter changes **none** of: `phase6_1/` (Option-B reader, S5 runner, Cell-3, in-memory sink);
`phase6_1_s1_storage/`; `phase6_2_shadow_intent/` (runtime + `__init__.py`); S1 / S5; the frozen DTOs; `config.py`;
any `data/` module; existing charters (roadmap and B1 included); lock tests; capacity boundaries; analytics/export
boundaries. It modifies **only** the single existing docs file
`docs/handoff/post_phase6_2_read_only_real_world_evidence_acquisition_boundary_charter.md`.

---

## 15. Exact Post-State (after this corrective commit)

- **Corrected charter:** BUILT / RATIFIABLE / **UNRATIFIED**, pending Gemini and Codex review.
- **Next source-authority / raw-ledger docs gate** ("Public Source-Authority & Raw-Capture-Ledger Exact-Shape
  Charter"): **ELIGIBLE only after ratification** of this charter.
- **Raw acquisition runtime:** **BLOCKED.**
- **Option-B projection / S1-ingestion runtime:** **BLOCKED.**
- **Data collection:** **NOT STARTED.**
- **`HYPOTHETICAL_OUTCOME` field shape / runtime:** **UNBUILT + BLOCKED.**
- **Calibration eligibility:** **BLOCKED.**
- **Phase 7.1 / 7.2 / 8.1:** **BLOCKED.**
- **Capacity:** **0.**

**Conclusion:** S1 durable storage/replay is complete, but real-world acquisition is unbuilt; the old B1 charter is
planning-only and cannot authorize network reads or prove a source→S1 path; S5 is a storage-ignorant, caller-injected
pipeline (not a collector); `S1DurableSqliteSink` has no acquisition coordinator; and Cell-3 is an honest zero-cost
substrate that is never calibration-grade. The **one categorical end-to-end direction** is *public unauthenticated
read → immutable append-only raw capture with provenance (terminating at RAW_CAPTURED)* as the **acquisition
boundary**, strictly separate from the **later projection / S1-ingestion boundary** (existing Option-B reader →
unmodified S2/B2/Cell-3/B3/B4/S4/S5 chain → exact SCORE/HALT → caller-injected `S1DurableSqliteSink` → append-order
replay → existing Phase 6.2 reconstruction). The acquisition boundary owns only one-shot public fetch, exact raw
bytes, retrieval provenance, immutable append-only raw capture, and explicit failure reporting — never
`gross_magnitude` / gross-edge calc / Option-B projection / `venue`-`pair` canonicalization / event-time selection /
S1 writing / scoring / costs / outcomes / calibration / actionability. Raw acquisition is blocked only until the
public source/endpoint authority, raw-capture carrier/storage shape, durability, resource ownership, and recovery law
are ratified; **B-1/B-2/B-3 block the later projection/S1-ingestion boundary, not raw capture; B-4 blocks
CALIBRATION_ELIGIBLE only.** Committed raw evidence is permanent and never rolled back for downstream failure; no
distributed atomic raw↔S1 transaction is claimed; retry replays the same preserved bytes (never refetch-substitute);
exactly-once/duplicate handling stays blocked pending the future raw-ledger charter (whose journal DTOs/enums/tables
are **not** invented here). S1 stays immutable append-only with calibration include/exclude performed outside S1 via a
separately-ratified eligibility manifest that never deletes/rewrites/hides/filters the audit trail; append order alone
controls replay order; provenance-time reversal is measured arrival evidence, never silently replaced by retrieval
time. **Phase 6.2 is COMPLETE + RATIFIED in its narrow deterministic offline audit-reconstruction scope** (A–F remain
separately RATIFIED + SEALED; no aggregate SEALED label). **Capacity stays 0; Phases 7.1 / 7.2 / 8.1 remain BLOCKED;
this corrected charter is BUILT / RATIFIABLE / UNRATIFIED, and exactly one next docs-only gate — the Public
Source-Authority & Raw-Capture-Ledger Exact-Shape Charter — becomes eligible only upon independent external
ratification of this committed charter. Committing it builds no collector and acquires no data.**
