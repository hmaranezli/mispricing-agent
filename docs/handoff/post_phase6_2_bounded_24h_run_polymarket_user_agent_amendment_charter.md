# Post-Phase 6.2 Bounded 24h Run — Polymarket Explicit User-Agent Amendment Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It pins exactly one fixed User-Agent literal for the Polymarket CLOB GET leg and
  records the required next gates before a runtime fix may proceed.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request and **no** live re-probe.
- It reads / writes **no** raw ledger or S1 DB.
- It creates **no** run directory, scheduler, daemon, or background process.
- It appends **nothing** to S1. No calibration, no trading, no actionability.
- **HTTPS transport header fix runtime: RATIFIED but Polymarket 403-blocked.**
- **First bounded 24h run: NOT STARTED / NOT ELIGIBLE.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `23abfbae39ee69002dff41ffc6dc7ca18377bd27`.
- Parent chain:
  - `23abfbae39ee69002dff41ffc6dc7ca18377bd27` = **RATIFIED** HTTPS transport per-source header
    fix runtime (`phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py`, 37 tests green).
  - `21efdc61e97bee97d3951365b7e080bb22575610` = **RATIFIED** HTTPS transport header-correctness
    amendment charter (docs-only).
  - `63e2ef43aef10834ed39417c690ccd9416c90e3d` = **RATIFIED** Bounded 24h Run Execution-Wiring
    runtime.
- Current blocking state:
  - Hyperliquid transport: **FIXED AND VERIFIED** — POST `/info` with
    `Accept: application/json` + `Content-Type: application/json` → **200 OK, 1579 bytes**.
  - Polymarket transport: **403-BLOCKED** — GET `/book` with `Accept: application/json` only →
    **403 Forbidden**. Polymarket CLOB WAF rejects requests without an explicit browser-like
    `User-Agent` header.
  - First bounded 24h run: **NOT STARTED / NOT ELIGIBLE**.

## Section 2 — Live Re-Probe Evidence (from prior commit)

The prior header-fix re-probe (commit `23abfba`, no body dump, no ledger, no S1) established:

| Leg | Method | Headers sent | HTTP Status | Byte length |
|-----|--------|-------------|-------------|-------------|
| Hyperliquid `POST /info` | POST | `Accept: application/json`, `Content-Type: application/json` | **200 OK** | 1579 |
| Polymarket `GET /book` | GET | `Accept: application/json` | **403 Forbidden** | — (not read) |

The header-correctness amendment charter (Section 4) explicitly required:

> _"If Polymarket 403 persists after adding `Accept: application/json` (e.g. due to WAF
> User-Agent filtering), a fixed explicit `User-Agent` string must be chartered and added to this
> amendment before being implemented. No User-Agent string may be chosen at implementation time
> without a docs-only amendment recording the rationale and exact value."_

This charter fulfils that gate.

## Section 3 — Root Cause

Polymarket's CLOB API (`clob.polymarket.com`) is fronted by a WAF (Cloudflare or equivalent) that
blocks requests whose `User-Agent` matches the Python `urllib` default fingerprint
(`Python-urllib/3.x`). The 403 is issued at the WAF layer before the request reaches the CLOB
server, so adding `Accept: application/json` alone is insufficient.

The `raw_acquisition/public_raw_capture.py` one-shot runtime, which obtains 200 OK from the
Polymarket CLOB endpoint, uses a standard browser-like User-Agent string via its underlying HTTP
client. This is the ratified evidence that a browser-like User-Agent resolves the 403.

## Section 4 — Ratified Polymarket User-Agent Literal (binding)

Exactly one fixed User-Agent string is chartered for the Polymarket CLOB GET leg:

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
```

**Binding rules (all mandatory):**

1. This exact string — no variation, no version bumping, no randomisation, no rotation — must be
   set as the `User-Agent` header on every `urllib.request.Request` object issued to
   `clob.polymarket.com`.
2. This User-Agent applies **only** to the ratified Polymarket CLOB YES-token book GET leg
   (`host == "clob.polymarket.com"`). It must **not** be applied to Hyperliquid or any other
   host unless separately chartered.
3. The Polymarket Accept header `Accept: application/json` (ratified in the prior amendment) must
   be **preserved** alongside this User-Agent.
4. **No** rotating or dynamic User-Agent logic may be introduced.
5. **No** cookies, session tokens, or authentication headers may be added.
6. **No** Cloudflare bypass tooling (e.g. `cloudscraper`, `tls-client`, Playwright) may be used.
7. **No** proxy, relay, or anonymisation layer may be introduced.
8. **No** retry or backoff logic may be added at implementation time without a separate charter.
9. **No** response body may be printed, decoded, or dumped by the transport.
10. **No** raw ledger or S1 writes occur during or because of this header change.

## Section 5 — Complete Ratified Per-Leg Header Set (post-amendment, binding)

The complete ratified header set for `https_transport` after this amendment is ratified:

### Hyperliquid — `POST https://api.hyperliquid.xyz/info`

```
Accept: application/json
Content-Type: application/json
```

*(Unchanged from prior amendment. No User-Agent addition unless separately chartered.)*

### Polymarket — `GET https://clob.polymarket.com/book?token_id=<YES_TOKEN>`

```
Accept: application/json
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
```

## Section 6 — Required TDD Fix Scope (Future RED→GREEN Gate)

After this amendment is independently ratified, the next gate is a **unit-test-only offline fix**
of `https_transport` in `phase6_2_shadow_intent/bounded_24h_run_execution_wiring.py`. The fix:

1. Must add `User-Agent` to the Polymarket header dict only, keyed on `"clob.polymarket.com"` in
   the URL (matching the existing host-based dispatch pattern).
2. The resulting Polymarket header dict must be exactly:
   ```python
   {
       "Accept": "application/json",
       "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
   }
   ```
3. The Hyperliquid header dict must remain unchanged:
   ```python
   {"Accept": "application/json", "Content-Type": "application/json"}
   ```
4. The `https_transport` signature `(method, url, request_body)` must not change.
5. No other headers may be added without a separate docs-only amendment.

## Section 7 — Required TDD Tests for the Fix

Tests must be added to `tests/test_phase6_2_bounded_24h_run_execution_wiring.py`. The new tests
must:

- Assert that when `https_transport` is called with the Polymarket URL, the
  `urllib.request.Request` object carries **exactly**:
  - `get_header("Accept") == "application/json"`
  - `get_header("User-agent") == "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"`
  (Note: urllib normalises `User-Agent` to `User-agent` via `.capitalize()`)
- Assert that the Hyperliquid request does **not** carry `User-agent` (absent or `None`).
- Assert that `urllib.request.urlopen` is intercepted via `unittest.mock.patch` — **no live
  network** in any test.
- All existing 37 tests must remain green after the fix.
- The initial RED must fail because `get_header("User-agent")` currently returns `None`, not
  the pinned literal.

## Section 8 — Post-Fix Live Re-Probe Gate

After the unit fix is ratified (all tests green, committed), perform a bounded live re-probe:

- Two read-only public requests only (one HL POST, one Poly GET), using the updated
  `https_transport` function directly from a minimal probe script.
- Record only: HTTP status codes and response byte lengths. No body dump. No ledger. No S1.
- Both must return **200 OK** before the bounded 24h run is authorized to start.
- If Polymarket remains 403 after this User-Agent fix, **STOP** and report — do not patch
  further without a new docs-only amendment.

## Section 9 — Capacity / Actionability Firewall

- Capacity remains **0** before, during, and after this amendment.
- No trading / order / balance / account / position calls.
- No alerts / advice / signals / profitability / ranking / sizing.
- No calibration. No paper / live / canary. No private endpoints. No S1 append.

## Section 10 — Next Gates

Only next safe gates:

1. Independent review of this Polymarket User-Agent amendment charter.
2. If ratified: **RED→GREEN offline unit fix** adding the pinned `User-Agent` to the Polymarket
   header dict in `https_transport` with assertion tests (Section 6 + Section 7). No live network
   in tests.
3. After fix commits green: **bounded live re-probe** (status/length only — Section 8).
4. If both HL and Polymarket return 2xx: issue a **separate explicit bounded raw-only 24h
   operator command**.
5. After the 24h run: **Read-Only Continuous Ledger Audit Charter**.

## Post-state

- Polymarket User-Agent amendment: **BUILT / RATIFIABLE / UNRATIFIED**.
- HTTPS transport header fix runtime: **RATIFIED** — Hyperliquid leg verified 200 OK;
  Polymarket leg 403-blocked pending this amendment.
- First bounded 24h run: **NOT STARTED / NOT ELIGIBLE**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
