# Post-Phase 6.2 Bounded 24h Run — HTTPS Transport Header-Correctness Amendment Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It records the live-probe defect, the ratified per-source header set, and the
  required next gates before a runtime fix may proceed.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request. It reads / writes **no** raw ledger or S1 DB.
- It creates **no** run directory, scheduler, daemon, or background process.
- It appends **nothing** to S1. No calibration, no trading, no actionability.
- **Execution-wiring runtime: RATIFIED but live-transport header-blocked.**
- **First bounded 24h run: NOT STARTED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `63e2ef43aef10834ed39417c690ccd9416c90e3d`.
- Parent chain:
  - `63e2ef43aef10834ed39417c690ccd9416c90e3d` = **RATIFIED** Bounded 24h Run Execution-Wiring
    runtime (`phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py`).
  - `a7c29cdb...` = **RATIFIED** Bounded 24h Run Execution-Wiring TDD Charter.
  - `8d017838...` = **RATIFIED** Bounded 24h Raw Collection Run Authorization Charter.
  - `f3d377ca...` = **RATIFIED** Continuous Raw Collection / Scheduler runtime.
- Current blocking state:
  - Execution-wiring runtime: **RATIFIED** — source code present and all 32 tests green.
  - Live transport layer: **HEADER-DEFECTIVE** — see Section 2.
  - First bounded 24h run: **NOT STARTED** — blocked by this defect.

## Section 2 — Live Pre-Flight Probe Evidence

A status/length-only read-only public probe was conducted against the two ratified endpoints prior
to the first bounded run attempt. No body was dumped, no ledger was written, no S1 was accessed,
no run directory was created.

Results:

| Leg                            | Method | URL                                              | HTTP Status               |
|--------------------------------|--------|--------------------------------------------------|---------------------------|
| Hyperliquid L2Book BTC (`/info`) | POST   | `https://api.hyperliquid.xyz/info`               | **415 Unsupported Media Type** |
| Polymarket CLOB YES-token book | GET    | `https://clob.polymarket.com/book?token_id=...`  | **403 Forbidden**          |

Both requests were issued via the current `https_transport(method, url, request_body)` function
in `phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py` (lines 130–144, commit
`63e2ef43`).

## Section 3 — Root Cause

`https_transport` constructs a `urllib.request.Request` object with **no request headers**:

```python
# Current (defective) implementation — lines 130–144 of bounded_24h_run_execution_wiring.py
request = urllib.request.Request(url=url, data=data, method=method)
# ↑ No headers= argument supplied; urllib default User-Agent only.
```

Without explicit headers:

- **Hyperliquid POST `/info`** receives a request with no `Content-Type`.  Hyperliquid requires
  `Content-Type: application/json` for JSON-body POST requests, and rejects absent or incorrect
  media types with **415 Unsupported Media Type**.
- **Polymarket GET `/book`** receives a request with no `Accept` header and only the stdlib
  default `User-Agent`.  Polymarket CLOB rejects such requests with **403 Forbidden**.

## Section 4 — Ratified Header Set (Source of Authority)

The ratified header set is derived from `raw_acquisition/public_raw_capture.py` lines 450–460
(the one-shot acquisition runtime, proven to obtain 200 OK from both endpoints):

```python
# raw_acquisition/public_raw_capture.py lines 451–460 (source of authority)

if type(request) is PolymarketClobBookByTokenV1Request:
    return (_CLOB, "GET", "https", "clob.polymarket.com", target, b"",
            {"Accept": "application/json"})

if type(request) is HyperliquidL2BookBtcV1Request:
    return (_HL_L2, "POST", "https", "api.hyperliquid.xyz", "/info", body,
            {"Accept": "application/json", "Content-Type": "application/json"})
```

**Ratified per-source header sets (binding):**

### Hyperliquid — `POST https://api.hyperliquid.xyz/info`

```
Accept: application/json
Content-Type: application/json
```

### Polymarket — `GET https://clob.polymarket.com/book?token_id=<YES_TOKEN>`

```
Accept: application/json
```

If Polymarket 403 persists after adding `Accept: application/json` (e.g. due to WAF User-Agent
filtering), a fixed explicit `User-Agent` string must be chartered and added to this amendment
before being implemented. No User-Agent string may be chosen at implementation time without a
docs-only amendment recording the rationale and exact value.

## Section 5 — Safety Consequence

Without the header fix:

- Every Hyperliquid cycle returns HTTP 415. The leg is non-2xx → counts as a pair failure.
- Every Polymarket cycle returns HTTP 403. The leg is non-2xx → counts as a pair failure.
- Every cycle becomes a `no_leg_failure`, consuming one unit of `failure_budget`.
- With `failure_budget = 100` and `sleep_interval = 10s`, the failure budget would be exhausted
  in approximately 1000 seconds (~17 minutes), long before the 24h / 8640-cycle bound.
- The run would commit **zero pairs**, write **zero valid raw rows**, and terminate via
  `SCHED_FAILURE_BUDGET_EXCEEDED`.
- **Therefore the live run must remain NOT STARTED until the fix is ratified and re-probed.**

## Section 6 — Required Fix Scope (Future RED→GREEN Gate)

After this amendment is independently ratified, the next gate is a **unit-test-only offline fix**
of `https_transport` in `phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py`. The fix:

1. Must supply the exact ratified header dict to `urllib.request.Request(headers=...)`.
2. Must be **leg-aware**: the Hyperliquid POST leg receives `{Accept, Content-Type}`;
   the Polymarket GET leg receives `{Accept}` only.
3. The `https_transport` signature may not change (it is called with `(method, url, request_body)`
   by `ExecutionWiring._capture`).
4. Header selection must derive from the URL (or leg method), not from a runtime-decoded payload.

## Section 7 — Required TDD Tests for the Fix

Tests must be added to `tests/test_phase6_2_bounded_24h_run_execution_wiring.py`. The new tests
must:

- Assert that when the injected transport receives a call with a Hyperliquid URL, the
  `urllib.request.Request` object (intercepted at construction) carries exactly:
  - `headers["Accept"] == "application/json"`
  - `headers["Content-Type"] == "application/json"`
- Assert that when the injected transport receives a call with a Polymarket URL, the
  `urllib.request.Request` object carries exactly:
  - `headers["Accept"] == "application/json"`
  - `"Content-Type"` is **absent** (GET with no body must not add Content-Type)
- Tests must use **no live network**. The real `urlopen` must be monkeypatched or the transport
  tested via a `urllib.request.Request` constructor interceptor (e.g. `unittest.mock.patch`).
- All existing 32 tests must remain green after the fix.
- The initial RED must fail because the header assertions are not yet met, not due to test errors.

## Section 8 — Post-Fix Live Re-Probe Gate

After the unit fix is ratified (all tests green, committed), perform a bounded live re-probe:

- Two read-only public requests only (one HL POST, one Poly GET), using the updated
  `https_transport` function directly from a minimal probe script.
- Record only: HTTP status codes and response byte lengths. No body dump. No ledger. No S1.
- Both must return **200 OK** before the bounded 24h run is authorized to start.
- If Polymarket remains 403 after the header fix, the User-Agent amendment path (Section 4) must
  be followed before proceeding.

## Section 9 — Capacity / Actionability Firewall

- Capacity remains **0** before, during, and after this amendment.
- No trading / order / balance / account / position calls.
- No alerts / advice / signals / profitability / ranking / sizing.
- No calibration.
- No paper / live / canary.
- No private endpoints.
- No S1 append.

## Section 10 — Next Gates

Only next safe gates:

1. Independent review of this header-correctness amendment charter.
2. If ratified: **RED→GREEN offline unit fix** of `https_transport` with header-assertion tests
   (Section 6 + Section 7). No live network in tests.
3. After fix commits green: **bounded live re-probe** (status/length only — Section 8).
4. If re-probe returns 200/200: issue a **separate explicit bounded raw-only 24h operator command**.
5. After the 24h run: **Read-Only Continuous Ledger Audit Charter**.

## Post-state

- HTTPS transport header-correctness amendment: **BUILT / RATIFIABLE / UNRATIFIED**.
- Execution-wiring runtime: **RATIFIED** — source present, all unit tests green, live transport
  header-blocked.
- First bounded 24h run: **NOT STARTED** — blocked by live-transport header defect.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
