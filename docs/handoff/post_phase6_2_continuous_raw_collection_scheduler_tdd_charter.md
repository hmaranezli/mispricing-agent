# Post-Phase 6.2 Continuous Raw Collection / Scheduler TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines the **exact RED tests** required **before** implementing the bounded
  scheduler / continuous collector.
- It implements **no** scheduler, **no** collector, **no** daemon, **no** poller, **no** cron, **no**
  loop, **no** background task, **no** network fetch, **no** raw capture, **no** S1 append, **no**
  calibration, **no** trading, **no** paper/live/canary, **no** alerting, **no** analytics.
- It runs **no** tests, reads **no** raw ledgers and **no** S1 databases, and performs **no** network
  request.
- **S1 Production Ingestion Adapter / Durable Writer runtime: RATIFIED.**
- **Continuous Raw Collection / Scheduler implementation: BLOCKED / UNSTARTED.**
- Production S1 ingestion stream: **BLOCKED** pending explicit stream authorization.
- Calibration / trading / actionability: **BLOCKED**. Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `ecec33aeabf2baf3d7360b0a69cd136908a5af27`.
- Parent chain:
  - `70d2019a7a94d6bf6740733dd14d154335bab167` = **RATIFIED** S1 Production Ingestion Adapter /
    Durable Writer runtime.
  - `ecec33aeabf2baf3d7360b0a69cd136908a5af27` = **RATIFIED** Continuous Raw Collection / Scheduler
    Boundary Charter.
- Current state:
  - S1 Production Ingestion Adapter / Durable Writer runtime: **RATIFIED**.
  - Continuous Raw Collection / Scheduler implementation: **BLOCKED / UNSTARTED**.
  - Production S1 ingestion stream: **BLOCKED** pending explicit stream authorization.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — RED-before-GREEN Law

- Future implementation must write **failing tests first**.
- The **first RED must fail because the scheduler / collector unit is absent** (e.g. `ImportError` /
  unresolved symbol), **not** because of malformed tests.
- **No scheduler runtime code may be written before RED evidence exists.**
- No "make it pass" shortcut may relax a ratified charter. If a ratified charter or schema blocks GREEN,
  the implementer must **STOP** and request a docs-only amendment first.

## Section 3 — Required Future TDD Test Groups

### A. Target-lock tests

Future tests must assert that the scheduler can **only** create capture attempts for:

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

Tests must **reject**:

- NO token;
- Gamma fallback;
- discovery / search / alias;
- alternate coin;
- private / authenticated CLOB endpoints;
- order / balance / account paths;
- method / body / target mutation.

### B. Bounded scheduler configuration tests

Future tests must assert:

- the run window is **explicit** and initially **<= 24h**;
- `start_time`, `stop_time`, `max_cycles`, `sleep_interval`, and `failure_budget` are **all required**;
- a missing bound **fails closed**;
- `stop_time <= start_time` **fails closed**;
- negative / zero sleep interval **fails closed**;
- `max_cycles <= 0` **fails closed**;
- `failure_budget < 0` **fails closed**;
- **no** unbounded / infinite daemon mode exists;
- **no** autonomous restart / watchdog / systemd / cron / background persistence exists.

### C. Pair-cycle atomicity tests

Future tests must assert:

- each cycle has a **deterministic `cycle_id`**;
- each cycle attempts **both** Hyperliquid and Polymarket legs;
- raw bytes + method / target / body / status / sha256 / timing metadata are recorded **per leg**;
- **lone-leg success does not project to S1**;
- **both legs must be RAW_COMMITTED** before projection may be considered;
- retrieval timestamps are stored as **forensic metadata only** and **never** source event time.

### D. Raw ledger isolation tests

Future tests must assert:

- continuous collection uses a **new independent** evidence ledger / directory, **not** the one-shot
  proof ledgers;
- one-shot ledgers are **never** appended or mutated;
- raw capture rows are **append-only**;
- `source_authority`, request metadata, `response_body_sha256`, and `cycle_id` are **mandatory**;
- the permission model follows the previous **0700 directory / 0600 sqlite** pattern in future
  implementation.

### E. S1 stream firewall tests

Future tests must assert:

- the scheduler / collector does **not** directly write durable S1 **unless** a separate **stream
  authorization object / config** is explicitly passed;
- **absent stream authorization => no S1 append**;
- the scheduler may call the ratified adapter / writer **only behind** an explicit stream-authorization
  boundary;
- the scheduler must **not** bypass the ratified adapter / writer;
- the production S1 ingestion stream remains **BLOCKED** until later explicit authorization.

### F. Stop / failure condition tests

Future tests must assert **fail-closed** behavior for:

- source target drift;
- method / body / token mismatch;
- non-2xx HTTP status;
- malformed raw ledger row;
- SHA mismatch;
- missing one leg;
- projection validation failure;
- S1 append failure;
- max-cycle exceeded;
- stop-time exceeded;
- repeated network failures beyond the explicit failure budget;
- private endpoint use;
- any attempt to trade or query balances / orders.

### G. No-actionability / observability tests

Future tests must assert run reports may include **only**:

- counts;
- cycle ids;
- capture ids;
- HTTP statuses;
- byte lengths;
- SHA summaries;
- failure literals;
- timing metadata;
- S1 append success / no-op counts **only if separately authorized**.

Tests must **reject**:

- edge / profitability / ranking / advice;
- alerts;
- position sizing;
- paper / live decisions;
- signal generation;
- calibration metrics.

### H. No network in unit tests

- Future scheduler unit tests must **not** use real network.
- The network layer must be **dependency-injected / faked**.
- Any actual real network capture requires a later **Bounded 24h Run Charter** and an explicit operator
  command.

### I. Capacity firewall tests

Future tests must assert:

- capacity remains **0**;
- **no** trading / actionability API exists;
- **no** scheduler success state upgrades capacity;
- **no** calibration / paper / live flag is enabled.

## Section 4 — Minimal GREEN Implementation Boundary

A later RED→GREEN implementation may implement **only**:

- bounded scheduler configuration validation;
- deterministic cycle planning;
- dependency-injected capture-callable interfaces;
- raw-ledger append through the already-ratified public raw-capture primitives or narrowly wrapped test
  doubles;
- an **optional** call to the ratified S1 adapter / writer **only if** an explicit stream-authorization
  object is supplied.

It must **not** implement:

- a real 24h run;
- an autonomous service / daemon;
- production S1 stream activation;
- calibration / trading / actionability;
- private endpoints;
- alerts / analytics / export.

## Section 5 — Next Gates

Only next safe gates:

1. Independent Gemini + Codex review of this TDD charter.
2. If ratified: a **bounded RED→GREEN implementation** of the scheduler / collector.
3. After implementation and ratification: an **S1 Stream Authorization / Bounded 24h Run Charter**.
4. Only after that: an **explicitly commanded bounded real 24h run**.

## Post-state

- Continuous Raw Collection / Scheduler TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini +
  Codex review.
- Continuous Raw Collection / Scheduler Boundary Charter: **RATIFIED**.
- Continuous Raw Collection / Scheduler implementation: **BLOCKED / UNSTARTED** until this TDD charter is
  ratified **and** an explicit implementation command is issued.
- Production S1 ingestion stream: **BLOCKED** pending explicit stream authorization.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
