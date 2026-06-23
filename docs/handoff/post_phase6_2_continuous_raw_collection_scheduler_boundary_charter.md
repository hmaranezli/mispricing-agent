# Post-Phase 6.2 Continuous Raw Collection / Scheduler Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines the **boundary** for a future continuous raw-collection scheduler. It
  implements nothing.
- It writes **no** scheduler, **no** collector, **no** daemon, **no** poller, **no** cron, **no** loop,
  **no** background task, **no** network fetch, **no** raw capture, **no** S1 append, **no** calibration,
  **no** trading, **no** paper/live/canary, **no** alerting, **no** analytics.
- It runs **no** tests, reads **no** raw ledgers and **no** S1 databases, and performs **no** network
  request.
- **S1 paired projection runtime logic: RATIFIED.**
- **S1 Production Ingestion Adapter / Durable Writer runtime: RATIFIED.**
- **S1 production ingestion stream: BLOCKED** pending explicit stream authorization.
- **Continuous raw collection / scheduler: BLOCKED / UNSTARTED.**
- Calibration / trading / actionability: **BLOCKED**. Capacity: **0**.

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `70d2019a7a94d6bf6740733dd14d154335bab167`.
- Parent chain:
  - `d3afaecea28de8ad1b33c9c3b47958b40bade4ab` = **RATIFIED** S1 paired projection runtime logic.
  - `db7c9f4bd24ba596594c476014af1a5a409ba305` = **RATIFIED** S1 Production Ingestion Adapter /
    Durable Writer TDD Charter.
  - `70d2019a7a94d6bf6740733dd14d154335bab167` = **RATIFIED** S1 Production Ingestion Adapter /
    Durable Writer runtime.
- Current state:
  - S1 paired projection runtime logic: **RATIFIED**.
  - S1 Production Ingestion Adapter / Durable Writer runtime: **RATIFIED**.
  - S1 production ingestion stream: **BLOCKED** pending explicit stream authorization.
  - Continuous raw collection / scheduler: **BLOCKED / UNSTARTED**.
  - Calibration / trading / actionability: **BLOCKED**.
  - Capacity: **0**.

## Section 2 — Purpose

The future scheduler is defined **narrowly**:

- It may coordinate **repeated public raw evidence acquisition** for the **already-ratified BTC pair
  only**.
- It may **not** trade, quote, route, size, rank, alert, calibrate, or decide actionability.
- It may **not** touch private / authenticated Polymarket CLOB endpoints.
- It may **not** use secrets, wallets, balances, orders, positions, or account state.
- It exists **only** to repeatedly collect public raw evidence and — **only after separately authorized
  stream wiring** — feed the already-ratified S1 adapter / writer.

## Section 3 — Source Target Lock

Future continuous collection may **only** target these two public evidence sources unless a later charter
amends them:

**Hyperliquid:**

```
source_authority = HYPERLIQUID_L2_BOOK_BY_COIN_V1
method           = POST
url              = https://api.hyperliquid.xyz/info
request_body     = b'{"type":"l2Book","coin":"BTC"}'
```

- No optional fields, no alternate coin, no retry target mutation.

**Polymarket:**

```
source_authority = POLYMARKET_CLOB_BOOK_BY_TOKEN_V1
method           = GET
url              = https://clob.polymarket.com/book?token_id=13433573766910980267981622064090484781359464703732825845886677588040916221533
```

- **YES token only.**
- NO-token capture, Gamma fallback, discovery / search / alias, and private CLOB auth / order / balance
  endpoints are **forbidden**.

## Section 4 — Scheduler Cadence Boundary

Predefined, **not executed** here:

- A future scheduler may run for a **bounded observation window**, initially **at most 24 hours**.
- Cadence must be **explicitly configured** in a later TDD / implementation charter.
- **No** infinite / unbounded daemon is authorized by this document.
- **Start time, stop time, max cycles, sleep interval, and failure budget must be explicit.**
- The scheduler must **fail closed** if any bound is missing.
- **No** autonomous restart, watchdog, self-healing daemon, systemd service, cron, or background
  persistence is authorized here.

## Section 5 — Pair-Cycle Atomicity

Future collection must treat one observation cycle as a **bounded pair attempt**:

- Hyperliquid l2Book raw capture **and** Polymarket CLOB YES raw capture must **both** be attempted under
  an explicit **cycle id**.
- Each raw response must be persisted as **raw bytes** with method / target / body / status / sha256 /
  timing metadata.
- Projection / S1 append may occur **only if both** raw captures are committed and pass **read-only**
  projection validation.
- **Lone-leg capture must not be projected into S1.**
- Retrieval timestamps remain **forensic-only** and never source event time.

## Section 6 — Ledger Isolation and Append Policy

Predefined, **not executed** here:

- Continuous collection must use a **new independent** continuous-collection evidence directory / ledger,
  **not** mutate the one-shot proof ledgers.
- The continuous raw ledger must be **append-only**.
- Existing one-shot ledgers are **historical evidence** and must **not** be appended to.
- File / directory permission rules must be specified later, **preserving the prior 0700/0600 isolation
  model**.
- Every capture row must carry `source_authority`, request metadata, `response_body_sha256`, and `cycle
  id`.
- Any S1 projection row must carry **both** source capture references and `sha256` values **through the
  ratified adapter / writer**.

## Section 7 — S1 Stream Authorization Boundary

Explicitly stated:

- This document does **not** yet authorize the **production S1 ingestion stream**.
- It only defines the **scheduler / continuous-collection boundary**.
- A later **S1 Stream Authorization / Continuous Ingestion Wiring Charter** is required before scheduler
  output can append to durable S1 in production.
- The already-ratified adapter / writer runtime remains **available but not automatically activated** as a
  live stream.

## Section 8 — Failure and Stop Conditions

Future scheduler TDD must require **fail-closed** behavior for:

- source target drift;
- method / body / token mismatch;
- non-2xx HTTP status;
- malformed raw ledger row;
- SHA mismatch;
- missing one leg of a pair;
- projection validation failure;
- S1 append failure;
- max-cycle exceeded;
- stop-time exceeded;
- repeated network failures beyond the explicit failure budget;
- any attempt to use private / authenticated endpoints;
- any attempt to trade or query balances / orders.

## Section 9 — Observability Without Actionability

Future run reports may include **only**:

- counts;
- cycle ids;
- capture ids;
- HTTP statuses;
- byte lengths;
- SHA summaries;
- failure literals;
- timing metadata;
- S1 append success / no-op counts **if separately authorized**.

Reports must **not** include trading advice, edge ranking, profitability claims, alerts, position sizing,
or paper / live decisions.

## Section 10 — Capacity / Calibration Firewall

- Capacity remains **0**.
- Continuous raw collection does **not** authorize calibration.
- It does **not** authorize paper trading, live trading, signal generation, or actionability.
- Phase 7.1 / paper or calibration gates remain **separate future boundaries** after sufficient data is
  collected and audited.

## Section 11 — Next Gates

Only next safe gates:

1. Independent Gemini + Codex review of this boundary charter.
2. If ratified: a **Continuous Raw Collection / Scheduler TDD Charter**.
3. Then a **bounded RED→GREEN scheduler implementation**.
4. Then a **separate S1 Stream Authorization / Bounded 24h Run Charter** before any real 24h run starts.

## Post-state

- Continuous Raw Collection / Scheduler Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending
  Gemini + Codex review.
- S1 Production Ingestion Adapter / Durable Writer runtime: **RATIFIED**.
- S1 production ingestion stream: **BLOCKED** pending explicit stream authorization.
- Continuous raw collection / scheduler implementation: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
