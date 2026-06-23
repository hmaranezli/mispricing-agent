# Post-Phase 6.2 S1 Production Ingestion Adapter / Durable Projection Writer Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines the **boundary** for a future S1 production ingestion adapter / durable
  projection writer. It implements nothing.
- It writes **no** adapter, **no** writer, **no** parser, **no** S1 DB append, **no** scheduler, **no**
  collector, **no** daemon, **no** DDL/schema change, **no** calibration, **no** trading, **no**
  paper/live/canary, **no** network behavior.
- It reads **no** raw ledgers and **no** S1 databases. It runs **no** tests.
- **S1 paired projection computational logic: RATIFIED.**
- **Production S1 ingestion adapter / durable writer: BLOCKED and UNSTARTED.**
- Scheduler / continuous collection: **BLOCKED**. Calibration / trading / actionability: **BLOCKED**.
  Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `53875ee6c425323a2725a14ceeccaa5a59fe8bcd`.
- Parent chain:
  - `d3afaecea28de8ad1b33c9c3b47958b40bade4ab` = **RATIFIED** S1 paired projection runtime logic.
  - `53875ee6c425323a2725a14ceeccaa5a59fe8bcd` = **RATIFIED** runtime closeout / ingestion boundary
    charter.
- Current state:
  - S1 paired projection computational logic: **RATIFIED**.
  - Production S1 ingestion adapter / durable writer: **BLOCKED and UNSTARTED**.
  - Scheduler / continuous collection: **BLOCKED**.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — Adapter Purpose

The future adapter is defined **narrowly**:

- It may **only** bridge already-verified raw evidence ledgers into a durable S1 projection append path.
- It must **not** fetch data from the network.
- It must **not** collect new raw evidence.
- It must **not** schedule or poll.
- It must **not** calculate trading signals, edge, profitability, rankings, alerts, portfolio exposure, or
  actionable decisions.
- It exists **only** to take a **RATIFIED paired projection result** and persist an **audit row**.

## Section 3 — Read Boundary for Future Implementation

Predefined, **not executed** here:

- Future implementation may read raw evidence ledgers **only in explicit read-only mode**.
- Both **Hyperliquid l2Book** evidence and **Polymarket CLOB YES-token** evidence must be **present**.
- Reads must verify:
  - `source_authority`;
  - `capture_sequence`;
  - `response_body_sha256`;
  - request target / method boundary;
  - exactly one committed capture where applicable.
- Retrieval timestamps (`retrieval_started_epoch_ms` / `retrieval_completed_epoch_ms`) must remain
  **forensic-only** and must **never** substitute source event time.

## Section 4 — Durable Write Boundary for Future Implementation

Predefined, **not executed** here:

- A future durable writer may append **only** to a **separately authorized** S1 projection table or
  stream.
- **No** existing durable S1 schema may be mutated by this charter.
- **No** DDL is authorized here.
- The exact destination table / schema must be specified in a **later TDD / implementation charter**.
- Every future S1 projection row must carry **mandatory provenance links**:
  - Hyperliquid `capture_sequence`;
  - Hyperliquid `response_body_sha256`;
  - Polymarket `capture_sequence`;
  - Polymarket `response_body_sha256`;
  - projection runtime version / authority identifier.
- **Orphan rows must be structurally impossible.**

## Section 5 — Idempotency / Replay Boundary

Predefined required future rules:

- Replaying the same paired evidence must **not** create duplicate semantic projections.
- Any idempotency key must be **deterministic** and derived from **both source evidence identities**, not
  rowid alone.
- SQLite `rowid` / `append_sequence` may be **internal ordering only**, **never domain identity**.
- Duplicate handling must **fail closed or no-op** according to a future explicit TDD charter; **this
  charter must not choose implementation mechanics.**

## Section 6 — Failure-Surface Binding

- The future adapter must bind to the **already-ratified S1 Projection DTO / Failure-Surface literals**.
- It must **not** invent new failure literals without a charter amendment.
- Explicitly preserved closed set:

  ```
  S1_PAIR_POLYMARKET_EVIDENCE_MISSING
  S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING
  S1_POLYMARKET_TIMESTAMP_MISSING
  S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED
  S1_HYPERLIQUID_TIME_MISSING
  S1_HYPERLIQUID_TIME_REJECTED
  S1_TIME_DELTA_EXCEEDS_1000_MS
  S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED
  S1_HYPERLIQUID_SIDE_AXIOM_REJECTED
  S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED
  S1_PROVENANCE_SHA_MISMATCH
  S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED
  ```

## Section 7 — Continuous Collection Firewall

Explicitly stated:

- This boundary does **not** authorize continuous data collection.
- It does **not** authorize a scheduler, daemon, poller, cron, long-running process, or loop.
- Continuous collection requires a **later separate Continuous Raw Collection / Scheduler Boundary
  Charter**.
- Even **after** the ingestion adapter is implemented, **capacity remains 0** until a separate
  calibration / actionability chain is ratified.

## Section 8 — Next Gates

The only next safe gates:

1. Independent Gemini + Codex review of this charter.
2. If ratified: an **S1 Production Ingestion Adapter / Durable Writer TDD Charter**.
3. Only after that: **RED→GREEN implementation**.
4. Only after adapter implementation and ratification: a **Continuous Raw Collection / Scheduler Boundary
   Charter**.

## Post-state

- S1 Production Ingestion Adapter / Durable Projection Writer Boundary Charter: **BUILT / RATIFIABLE /
  UNRATIFIED** pending Gemini + Codex review.
- S1 paired projection runtime logic: **RATIFIED**.
- Production S1 ingestion adapter / durable writer: **BLOCKED / UNSTARTED** until this charter is ratified
  **and** a later TDD charter is authorized.
- Scheduler / continuous collection: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
