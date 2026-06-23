# Post-Phase 6.2 BTC S1 Paired Projection Runtime Closeout / Ingestion Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It records the closeout of the S1 paired projection **runtime logic** and locks the
  **production ingestion boundary**.
- It implements **no** code, **no** schema/DDL, **no** ingestion adapter, **no** writer, **no** daemon,
  **no** collector, **no** DTO change.
- It grants **no** network, **no** data collection, **no** raw-ledger reads, **no** S1 DB writes, **no**
  scheduler, **no** calibration, **no** graph/export, **no** trading/actionability.
- **S1 paired projection runtime logic: RATIFIED.**
- **Production S1 ingestion stream: BLOCKED.**
- Scheduler / continuous collection: **BLOCKED**. Calibration: **BLOCKED**. Trading / actionability:
  **BLOCKED**. Capacity: **0**.

---

## Section 1 — Base / Provenance

- Exact base / head at chartering: `d3afaecea28de8ad1b33c9c3b47958b40bade4ab`.
- Parent: `350f176309ef0369330bae9be42d7d6dab342935`.
- Latest commit message: `feat: Implement BTC S1 paired CLOB-YES + l2Book projection (TDD)`.
- Files introduced by `d3afaece`:
  - `phase6_2_shadow_intent/s1_paired_projection.py`
  - `tests/test_phase6_2_s1_paired_projection.py`

## Section 2 — Ratified Runtime Facts

Recorded as **RATIFIED**, not merely built:

- **RED evidence:** the tests were written **first** and failed via `ImportError` because the unit under
  test (`phase6_2_shadow_intent.s1_paired_projection`) was absent — the correct missing-feature failure.
- **GREEN evidence:** the focused S1 paired projection tests passed (43 focused tests).
- **Regression evidence:** the required regression subset passed (`tests/test_public_raw_capture.py`,
  `tests/test_phase6_1_s1_durable_sqlite_sink.py`, `tests/test_phase6_2_s1_evidence_projection.py`).
- **Independent verdict:** Gemini + Codex review of `d3afaece` → **RATIFIED**.
- The runtime is **bounded, memory-bound / stateless projection logic only** — a pure, stdlib-only
  dependency leaf with no network, filesystem, ledger, S1 DB, scheduler, or global state.

## Section 3 — Ratified Behavioral Boundaries

The ratified runtime carries exactly these properties:

- `px` / `sz` parse into **`decimal.Decimal`**, **never `float`** (and never `Decimal` from `float`).
- The Polymarket timestamp **string** parses into **`int`** only through **exact integer-string parsing**
  (`^[0-9]+$`).
- The Hyperliquid time is an **`int` epoch milliseconds** value.
- `abs(polymarket_timestamp_ms - hyperliquid_time_ms) <= 1000` is **accepted**.
- `999ms` and `1000ms` **pass**; `1001ms` **fails closed** (`S1_TIME_DELTA_EXCEEDS_1000_MS`).
- `retrieval_started_epoch_ms` / `retrieval_completed_epoch_ms` must **never** substitute source event
  time (`S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED`).
- Both Polymarket and Hyperliquid `capture_sequence` + `response_body_sha256` provenance are **carried**
  on every projected carrier.
- Missing / wrong paired evidence **fails closed** (`S1_PAIR_POLYMARKET_EVIDENCE_MISSING` /
  `S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING`; provenance SHA mismatch `S1_PROVENANCE_SHA_MISMATCH`).
- Only **top-of-book** is surfaced, under the ratified manual side axiom:
  - Hyperliquid `levels[0][0] = BID`;
  - Hyperliquid `levels[1][0] = ASK`.
- **No** depth traversal, **no** VWAP, **no** mid, **no** spread, **no** notional, **no**
  cross-edge / actionable calculation. Deeper levels are discarded; side-axiom / levels-shape /
  decimal divergences fail closed.

## Section 4 — Ingestion Boundary Lock

Explicitly recorded:

- S1 paired projection runtime logic being **RATIFIED** does **NOT** authorize **production S1
  ingestion**.
- **No** production S1 DB append / write stream is opened.
- **No** durable projection writer exists yet.
- **No** raw-ledger-to-S1 ingestion adapter is authorized yet.
- **No** scheduler / continuous collection / calibration / trading / paper / live / canary / actionability
  is authorized.
- Capacity remains **0**.

The ratified runtime is a **pure projection function returning a test-only / audit-only carrier**; it has
**zero emit sites** into any durable S1 store.

## Section 5 — Phase / State Reconciliation

Preserved split:

- **Phase 6.1** passive in-memory + durable audit substrate: **COMPLETE + RATIFIED** in its narrow scope.
- **Aggregate Phase 6.2** deterministic offline audit-reconstruction: **COMPLETE + RATIFIED** in its old
  replay-only scope.
- **Post-Phase-6.2 real-evidence chain:**
  - Hyperliquid l2Book runtime / capture / audit: **COMPLETE / RATIFIED** as applicable.
  - Polymarket CLOB YES-token capture / audit / timestamp authority: **COMPLETE / RATIFIED** as
    applicable.
  - S1 paired projection runtime logic: **RATIFIED**.
  - Production S1 ingestion stream: **BLOCKED**.
  - Scheduler / continuous collection: **BLOCKED**.
  - Calibration: **BLOCKED**.
  - Capacity: **0**.

## Section 6 — Next Gate

The next safe gate is **separate and unstarted**:

- **S1 Production Ingestion Adapter / Durable Projection Writer Boundary Charter.**

It must be **docs-only first** and must specify:

- whether / how raw evidence ledgers are read;
- whether / how projected rows may append to S1;
- exact provenance foreign-key / capture linkage;
- fail-closed behavior;
- **no** scheduler / continuous collection until later.

Runtime ingestion work remains **BLOCKED** until that separate charter is ratified **and** explicitly
commanded.

## Post-state

- S1 paired projection runtime closeout / boundary charter: **BUILT / RATIFIABLE / UNRATIFIED** pending
  Gemini + Codex review.
- S1 paired projection runtime logic: **RATIFIED**.
- Production S1 ingestion stream: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
