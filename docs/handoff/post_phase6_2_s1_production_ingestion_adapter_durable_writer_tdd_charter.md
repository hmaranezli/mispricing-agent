# Post-Phase 6.2 S1 Production Ingestion Adapter / Durable Writer TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines the **exact RED tests** required **before** implementing the adapter / writer.
- It implements **no** adapter, **no** writer, **no** parser, **no** S1 append, **no** scheduler, **no**
  collector, **no** daemon, **no** calibration, **no** trading, **no** paper/live/canary, **no** network
  behavior, **no** DDL/schema change.
- It reads **no** raw ledgers and **no** S1 databases. It runs **no** tests.
- **S1 paired projection runtime logic: RATIFIED.**
- **Production S1 ingestion adapter / durable writer: BLOCKED / UNSTARTED.**
- Scheduler / continuous collection: **BLOCKED**. Calibration / trading / actionability: **BLOCKED**.
  Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `b0cdb612a72868253f86c80c3063c1831f4fc45b`.
- Parent chain:
  - `d3afaecea28de8ad1b33c9c3b47958b40bade4ab` = **RATIFIED** S1 paired projection runtime logic.
  - `53875ee6c425323a2725a14ceeccaa5a59fe8bcd` = **RATIFIED** runtime closeout / ingestion boundary.
  - `b0cdb612a72868253f86c80c3063c1831f4fc45b` = **RATIFIED** S1 production-ingestion adapter /
    durable-writer boundary.
- Current state:
  - S1 paired projection runtime logic: **RATIFIED**.
  - Production S1 ingestion adapter / durable writer: **BLOCKED / UNSTARTED**.
  - Scheduler / continuous collection: **BLOCKED**.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — RED-before-GREEN Law

- Future implementation must begin with **failing tests first**.
- The **first RED failure must prove absence of the adapter / writer unit** (e.g. `ImportError` /
  unresolved symbol), **not** a pre-existing partial implementation.
- **No production code may be written before the RED tests are committed / executed** in the
  implementation task.
- No "make it pass" shortcut may relax a ratified charter. If a ratified charter or schema blocks GREEN,
  the implementer must **STOP** and request a docs-only amendment first.

## Section 3 — Required TDD Test Groups

### A. Read-only raw-ledger access tests

Future tests must assert:

- raw evidence ledgers are opened **read-only**;
- any attempted write / append / mutation to raw ledgers **fails**;
- Hyperliquid l2Book **and** Polymarket CLOB YES-token evidence must **both** be present;
- `source_authority` must match the ratified values;
- `capture_sequence` must be present for **both** sides;
- `response_body_sha256` must be present for **both** sides;
- request target / method boundary must match ratified evidence;
- exactly **one** committed capture row must be selected where applicable;
- `retrieval_started_epoch_ms` / `retrieval_completed_epoch_ms` are **never** used as source event time.

### B. Adapter pairing tests

Future tests must assert:

- lone Hyperliquid evidence **fails closed**;
- lone Polymarket evidence **fails closed**;
- wrong `token_id` / wrong `coin` / wrong `source_authority` **fails closed**;
- missing timestamp / missing l2Book `$.time` **fails closed**;
- mismatched SHA **fails closed**;
- the adapter invokes **only** the RATIFIED S1 paired projection runtime logic, **not** a parallel
  projection formula.

### C. Durable writer schema-boundary tests

Future tests must assert:

- **no** existing S1 durable schema is mutated implicitly;
- any destination projection table / stream must be **explicitly created only** by separately authorized
  implementation logic;
- the writer **cannot** append rows missing Hyperliquid `capture_sequence` + `response_body_sha256`;
- the writer **cannot** append rows missing Polymarket `capture_sequence` + `response_body_sha256`;
- the writer **cannot** append orphan projection rows;
- SQLite `rowid` / `append_sequence` **cannot** be used as domain identity.

### D. Idempotency / replay tests

Future tests must assert:

- replaying the same paired evidence does **not** create duplicate semantic projections;
- the deterministic idempotency key must derive from **both source evidence identities**;
- duplicate behavior must be **explicit** — **fail-closed or no-op** — and the implementation must
  **never silently append duplicates**;
- idempotency must **not** depend only on `rowid`, wall-clock time, or insertion order.

### E. Failure-surface tests

Future tests must assert that failures use **only** already-ratified literals unless a separate charter
amendment is made:

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

### F. No-network / no-scheduler tests

Future tests must assert:

- the adapter / writer performs **no** network calls;
- **no** scheduler, daemon, polling loop, cron, retry loop, background task, or long-running process
  exists;
- **no** data collection is triggered by ingestion;
- **no** calibration / trading / actionability side effect exists;
- Capacity remains **0**.

### G. Transaction / atomicity tests

Future tests must assert:

- durable append is **atomic**;
- partial writes **fail closed**;
- if projection validation succeeds but the DB append fails, **no orphan / partial projection** is left;
- transaction **rollback** behavior is explicitly tested;
- the writer must **not** commit before **all** provenance and projection invariants pass.

## Section 4 — Minimal GREEN Implementation Boundary

- A later RED→GREEN implementation may implement **only the minimum** adapter / writer logic to satisfy
  these tests.
- It must **not** implement scheduler / continuous collection, calibration, trading, alerts, analytics,
  export, or network acquisition.

## Section 5 — Continuous Collection Firewall

- This TDD charter does **not** authorize continuous data collection.
- Continuous raw collection / scheduler remains a **later separate boundary** after adapter / writer
  implementation is ratified.
- Capacity remains **0** even if future adapter tests pass.

## Section 6 — Next Gates

Only next gates:

1. Independent Gemini + Codex review of this TDD charter.
2. If ratified: a **bounded RED→GREEN implementation** of the S1 Production Ingestion Adapter / Durable
   Writer.
3. After implementation and ratification: a **Continuous Raw Collection / Scheduler Boundary Charter**.

## Post-state

- S1 Production Ingestion Adapter / Durable Writer TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending
  Gemini + Codex review.
- S1 Production Ingestion Adapter / Durable Writer Boundary Charter: **RATIFIED**.
- Production S1 ingestion adapter / durable writer implementation: **BLOCKED / UNSTARTED** until this TDD
  charter is ratified **and** an explicit implementation command is issued.
- Scheduler / continuous collection: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
