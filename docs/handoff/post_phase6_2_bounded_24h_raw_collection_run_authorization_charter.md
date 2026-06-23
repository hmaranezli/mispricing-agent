# Post-Phase 6.2 Bounded 24h Raw Collection Run Authorization Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only / run-authorization design only.** It **performs no network request** and **starts no run**.
- It authorizes — **only after** independent ratification **and** a separate operator execution command —
  a **first bounded real public-network raw-evidence** collection run using the RATIFIED continuous
  scheduler runtime.
- It **explicitly DENIES production S1 append** for that first run.
- It implements **nothing**; it edits **no** runtime / test / schema / config; it reads / writes **no**
  raw ledger or S1 DB; it starts **no** scheduler / collector / daemon / loop / cron / run.
- **Scheduler runtime: RATIFIED.**
- **First bounded real 24h raw collection run: NOT STARTED.**
- Production S1 ingestion stream: **BLOCKED**. S1 append: **DENIED** for the first run.
- Calibration / trading / actionability: **BLOCKED**. Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `f3d377ca2ab632f1875463cb8141ac2acc8e6016`.
- Parent chain:
  - `70d2019a7a94d6bf6740733dd14d154335bab167` = **RATIFIED** S1 Production Ingestion Adapter /
    Durable Writer runtime.
  - `ecec33aeabf2baf3d7360b0a69cd136908a5af27` = **RATIFIED** Continuous Raw Collection / Scheduler
    Boundary Charter.
  - `d9af8d779a9c30a4d16825042064a8784eb0e965` = **RATIFIED** Continuous Raw Collection / Scheduler
    TDD Charter.
  - `f3d377ca2ab632f1875463cb8141ac2acc8e6016` = **RATIFIED** Continuous Raw Collection / Scheduler
    runtime.
- Current state:
  - Scheduler runtime: **RATIFIED**.
  - First bounded real 24h raw collection run: **NOT STARTED**.
  - Production S1 ingestion stream: **BLOCKED**.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — Authorization Intent

- This charter authorizes **only** a future first real public-network raw-evidence collection run, and
  **only after** this charter is independently ratified **and** a separate operator execution command is
  issued.
- **This charter itself performs no network request.**
- **This charter itself starts no run.**
- **This charter is run-authorization design only.**

## Section 3 — S1 Firewall / Absolute Write Denial

The first 24h run must be **raw-evidence-only**. Explicitly **DENY / BLOCK**:

- production S1 DB append;
- `s1_audit.sqlite3` writes;
- S1 stream activation;
- durable projection writer use;
- adapter / writer **production** append;
- schema / DDL mutation;
- S1 backfill;
- analytics mirror / export.

Only **dry-run / shadow** projection summaries may be produced, and **only** from already-captured raw
evidence **inside the run process**. **Dry-run output must not mutate S1.**

## Section 4 — Bounded Network Authority

The future run may call **only** these two public endpoints:

**Hyperliquid:**

```
source_authority = HYPERLIQUID_L2_BOOK_BY_COIN_V1
method           = POST
url              = https://api.hyperliquid.xyz/info
request_body     = b'{"type":"l2Book","coin":"BTC"}'
```

**Polymarket:**

```
source_authority = POLYMARKET_CLOB_BOOK_BY_TOKEN_V1
method           = GET
url              = https://clob.polymarket.com/book?token_id=13433573766910980267981622064090484781359464703732825845886677588040916221533
```

- **YES token only.**

Explicitly **forbid**:

- NO token;
- Gamma fallback;
- search / discovery / alias;
- alternate coins;
- private / authenticated CLOB endpoints;
- orders / balances / accounts / positions;
- Telegram / restart / admin actions;
- any target mutation.

## Section 5 — Hard Execution Bounds

Concrete first-run bounds, recorded:

```
max_duration    = 24 hours maximum
sleep_interval  = 10 seconds between pair cycles
max_cycles      = 8640 maximum pair cycles   # 24h * 60m * 60s / 10s = 8640
failure_budget  = 100 failed pair cycles maximum
```

- **failure_budget policy:** if the failure budget is exceeded before 24h / max_cycles, **stop
  fail-closed**.
- **Stop conditions:**
  - max_duration reached;
  - max_cycles reached;
  - failure_budget exceeded;
  - operator stop file / sentinel (if later implemented);
  - unrecoverable target drift / private endpoint / order / balance attempt;
  - ledger integrity failure;
  - disk / permission failure;
  - clock anomaly evidence.
- **No** autonomous restart, **no** watchdog, **no** systemd, **no** cron persistence, **no** self-healing
  daemon.

## Section 6 — Pair-Cycle Policy

Each cycle must:

- assign a **deterministic `cycle_id`**;
- attempt the Hyperliquid leg **and** the Polymarket leg;
- persist raw response bytes **plus** method / target / body / status / sha256 / timing metadata;
- treat retrieval timestamps as **forensic-only**;
- **never** project lone-leg evidence to S1;
- permit **dry-run** projection **only** when both legs are RAW_COMMITTED and pass validation;
- record the dry-run result **only** as run-report metadata, **not** S1.

## Section 7 — Continuous Ledger Isolation

The future run must use a **fresh independent** continuous-run evidence directory and ledger.

- It must **not** append to one-shot proof ledgers.
- It must **not** mutate prior Hyperliquid / Polymarket / Gamma / l2Book / CLOB ledgers.
- It must preserve the **0700 directory / 0600 sqlite/wal/shm** permission model.
- It must use **append-only** raw capture rows.
- Every row must include `source_authority`, request metadata, `response_body_sha256`, `cycle_id`,
  status, and timing metadata.
- If the target continuous ledger already exists unexpectedly, the run must **fail closed** unless a
  future charter explicitly defines resume behavior.

## Section 8 — Dry-Run Projection Boundary

Dry-run projection **may**:

- call RATIFIED projection / adapter logic **in memory only**;
- calculate pass / fail counts for pair eligibility;
- count `delta <= 1000ms` vs delta failures;
- count duplicate / no-op possibilities.

Dry-run projection must **not**:

- append to S1;
- create S1 tables;
- mutate the production DB;
- create trading signals;
- produce edge / profit / ranking / advice;
- calibrate thresholds.

## Section 9 — Observability / Final Report

The future run may report **only**:

- start / end time;
- elapsed duration;
- cycle count;
- committed Hyperliquid count;
- committed Polymarket count;
- paired cycle count;
- failed cycle count;
- failure_budget remaining / consumed;
- HTTP status counts;
- byte-length summaries;
- SHA summaries or prefixes;
- dry-run projection pass / fail counts;
- stop_reason;
- ledger path;
- permission verification;
- no-S1-write verification.

**No** trading advice, profitability claim, alert, signal, ranking, sizing, calibration, or paper / live
decision.

## Section 10 — Post-Run Next Gate

After the run completes or stops early, the next gate must be a **Read-Only Continuous Ledger Audit
Charter** — **not** S1 stream authorization yet. The audit must inspect:

- row counts;
- pair completeness;
- source targets;
- SHA integrity;
- timestamp candidate consistency;
- delta distribution;
- failure distribution;
- ledger permissions;
- no S1 writes.

Only **after** that audit is ratified may an **S1 Stream Authorization / Production Append Charter** be
considered.

## Section 11 — Capacity / Actionability Firewall

- Capacity remains **0** before, during, and after the run.
- **No** trading / actionability.
- **No** calibration.
- **No** paper / live / canary.
- **No** private endpoints.
- **No** alerts.

## Section 12 — Next Gates

Only next safe gates:

1. Independent Gemini + Codex review of this charter.
2. If ratified: a **bounded operator execution command** for the first raw-only 24h run.
3. After the run: a **Read-Only Continuous Ledger Audit Charter**.
4. Only after a clean audit: **consider** an S1 Stream Authorization / Production Append Charter.

## Post-state

- Bounded 24h Raw Collection Run Authorization Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending
  Gemini + Codex review.
- Scheduler runtime: **RATIFIED**.
- First bounded real 24h raw collection run: **NOT STARTED** until this charter is ratified **and** an
  explicit operator execution command is issued.
- Production S1 ingestion stream: **BLOCKED**.
- S1 append: **DENIED** for the first run.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
