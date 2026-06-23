# Post-Phase 6.2 Bounded 24h Run Execution-Wiring TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines the **exact RED tests** required **before** implementing the missing
  real-world execution glue for the already-RATIFIED scheduler runtime.
- It implements **no** capture adapter, **no** ledger sink, **no** runner, **no** entrypoint, **no**
  scheduler change, **no** network fetch, **no** raw capture, **no** S1 append, **no** calibration, **no**
  trading, **no** paper/live/canary, **no** alerting, **no** analytics.
- It runs **no** tests, performs **no** network request, reads / writes **no** raw ledger or S1 DB.
- **Scheduler runtime: RATIFIED.** **Bounded 24h raw-only run authorization: RATIFIED.**
- **First bounded 24h run: NOT STARTED** — blocker: execution-wiring runtime absent.
- Production S1 ingestion stream: **BLOCKED**. S1 append: **DENIED** for the first run.
- Calibration / trading / actionability: **BLOCKED**. Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `8d0178381a755a35122daa1365df3b0288054184`.
- Parent chain:
  - `f3d377ca2ab632f1875463cb8141ac2acc8e6016` = **RATIFIED** Continuous Raw Collection / Scheduler
    runtime.
  - `8d0178381a755a35122daa1365df3b0288054184` = **RATIFIED** Bounded 24h Raw Collection Run
    Authorization Charter.
- Current state:
  - Scheduler runtime: **RATIFIED**.
  - Bounded 24h raw-only run authorization: **RATIFIED**.
  - First bounded 24h run: **NOT STARTED**.
  - Blocker: **execution-wiring runtime absent**.
  - Production S1 ingestion stream: **BLOCKED**.
  - S1 append: **DENIED** for the first run.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — Runtime Gap Declaration

Recorded as fact:

- `phase6_2_shadow_intent/continuous_raw_collection_scheduler.py` is a **pure orchestrator** with
  **dependency-injected** capture callables, ledger append, clock, and sleep.
- **No production runner / entrypoint exists.**
- **No real `CaptureOutcome` producer exists outside tests.**
- `raw_acquisition/public_raw_capture.py` is a **one-shot runtime** that builds its **own** ledger and
  does **not** match the scheduler's required `(leg) -> CaptureOutcome` + separate `ledger_append`
  callable interface.
- Therefore the first run **cannot start** until execution wiring is built via **RED→GREEN TDD**.

## Section 3 — RED-before-GREEN Law

- Future implementation must begin with **failing tests first**.
- The **initial RED must fail because the execution-wiring unit is absent** (e.g. `ImportError` /
  unresolved symbol), **not** due to malformed tests.
- No "make it pass" shortcut may relax a ratified charter; if a ratified charter / schema blocks GREEN,
  the implementer must **STOP** and request a docs-only amendment first.

## Section 4 — Required Future TDD Test Groups

### A. Real capture adapter interface tests

Future tests must require:

- `hyperliquid_capture(leg) -> CaptureOutcome`;
- `polymarket_capture(leg) -> CaptureOutcome`;
- both use **only** the ratified public targets:
  - Hyperliquid `POST https://api.hyperliquid.xyz/info` body `b'{"type":"l2Book","coin":"BTC"}'`;
  - Polymarket `GET` the exact YES-token CLOB book URL;
- exact method / body / target / `source_authority` verification;
- response bytes are **not** printed / decoded / dumped;
- `response_body_sha256` is computed over the **raw bytes**;
- retrieval timings are **forensic-only**;
- **no** private / auth endpoints, orders, balances, accounts, Telegram, restart / admin.

### B. Continuous ledger sink tests

Future tests must require:

- a **fresh independent** run directory;
- **reject** an existing run directory unless a future charter defines resume;
- create directory mode **0700**;
- create sqlite / wal / shm mode **0600**;
- **append-only** raw capture rows;
- mandatory `cycle_id`, leg / `source_authority`, method, target, `request_body`, `http_status`,
  `response_body` bytes/blob, `response_body_sha256`, `retrieval_started` / `retrieval_completed`,
  elapsed monotonic, `clock_anomaly_evidence`;
- **no** writes to one-shot proof ledgers;
- **no** S1 DB access;
- **no** schema mutation outside the new continuous ledger.

### C. Runner wiring tests

Future tests must require:

- the runner wires the **RATIFIED scheduler** to the real capture adapters + continuous ledger sink +
  real clock / sleep;
- the runner **refuses to start** unless the HEAD / base / version / charter marker matches the expected
  authorization;
- the runner **refuses** if `/root/mispricing_continuous_raw_24h_run_001` already exists;
- the runner **refuses** if `s1_audit.sqlite3` would be touched;
- the runner enforces `max_duration = 24h`, `sleep_interval = 10s`, `max_cycles = 8640`,
  `failure_budget = 100`;
- the runner can run a **bounded smoke mode** in tests with **fake** capture callables and **fake**
  sleep.

### D. No-S1 firewall tests

Future tests must assert:

- **no** S1 append;
- **no** production S1 stream activation;
- **no** adapter / writer **production** append;
- **no** `s1_audit.sqlite3` creation / read / write;
- dry-run projection is **report-only**, in memory / report metadata.

### E. No-actionability tests

Future tests must assert:

- **no** trading / order / balance / account / position calls;
- **no** alerts / advice / signals / profitability / ranking / sizing;
- **no** calibration;
- Capacity remains **0**.

### F. Stop / failure tests

Future tests must cover:

- target drift → **fail closed**;
- non-2xx leg → counts against the failure budget and **never projects**;
- missing one leg → **never projects**;
- SHA mismatch → **fail closed**;
- disk / permission failure → **fail closed**;
- failure_budget exceeded → **stops the run**;
- stop_time / max_cycles → **stops the run**;
- clock anomaly → stops / fails according to the charter;
- keyboard / operator stop sentinel **may** stop cleanly if implemented, but **no autonomous restart**.

### G. Status / report tests

Future tests must require compact status reports containing **only**:

- elapsed;
- cycles attempted;
- HL committed count;
- Poly committed count;
- paired complete count;
- failed count;
- failure_budget remaining;
- ledger path;
- stop_reason;
- no-S1 verification.

Reports must **not** include raw bodies or decoded payload values.

## Section 5 — Minimal GREEN Boundary

A later implementation may add **only**:

- an `execution_wiring` module;
- real capture adapters;
- a continuous ledger sink;
- a thin runner / entrypoint for raw-only collection;
- tests.

It must **not** add:

- S1 stream append;
- calibration / trading / actionability;
- private endpoints;
- daemon / systemd / cron / watchdog;
- autonomous restart;
- analytics / export / alerts.

## Section 6 — Next Gates

Only next safe gates:

1. Independent Gemini + Codex review of this TDD charter.
2. If ratified: a **RED→GREEN execution-wiring implementation**.
3. If the implementation is ratified: an **explicit bounded raw-only 24h operator command**.
4. After the run: a **Read-Only Continuous Ledger Audit Charter**.

## Post-state

- Bounded 24h Run Execution-Wiring TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini +
  Codex review.
- Scheduler runtime: **RATIFIED**.
- Bounded 24h raw-only run authorization: **RATIFIED**.
- First bounded 24h run: **NOT STARTED**, blocked on execution-wiring implementation.
- S1 append: **DENIED / NOT PERFORMED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
