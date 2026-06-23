# Post-Phase 6.2 S1 Stream Authorization — Eligibility & Safety Preconditions Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It defines the strict preconditions (gates A–J) that must **all** be satisfied
  before any future **S1 Stream Authorization / Production Append Charter** may even be considered.
- It **authorizes no S1 ingestion, no S1 append, no production stream activation, no calibration,
  no trading, no paper/live/canary, no actionability.**
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Continuous Ledger Audit Charter: RATIFIED.**
- **Read-Only Continuous Ledger Audit TDD Charter: RATIFIED.**
- **Post-run audit implementation: BLOCKED / UNSTARTED.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `baee0aacc7b7e235e4754792d173b9d0e726e4cb`.
- Parent chain:
  - `baee0aacc7b7e235e4754792d173b9d0e726e4cb` = **RATIFIED** Read-Only Continuous Ledger Audit
    TDD Charter.
  - `bb7b73b4db4291e96547e72cc9cb332936886ccb` = **RATIFIED** Read-Only Continuous Ledger Audit
    Charter (boundary).
  - `cfd7015585c6a42272861e6f215a5c8e0532f74f` = **RATIFIED** Polymarket User-Agent runtime fix.
  - `63e2ef43aef10834ed39417c690ccd9416c90e3d` = **RATIFIED** Bounded 24h Run Execution-Wiring
    runtime.
- Known run state (from prior operator report — live ledger not read for this charter):
  - 492 paired cycles, 984 rows, 0 failures, HTTP 200 only, `s1_audit.sqlite3` absent,
    permissions 0700/0600, `stream_authorization=None`.

## Section 2 — Charter Intent and Non-Authorization

- This charter is a **precondition specification only**. It enumerates what must be true before
  the question of S1 authorization may be **raised**.
- Satisfying every gate in this charter **does not authorize** S1 append. It only makes a separate
  **S1 Stream Authorization / Production Append Charter** *eligible to be drafted and reviewed*.
- There is **no automatic transition** from precondition satisfaction to S1 activation. A separate
  explicit docs charter **and** a separate explicit operator command are required.

---

## Section 3 — Eligibility & Safety Gates

### Gate A — Raw Ledger Audit Precondition

1. The bounded raw-only 24h run must **complete or stop within ratified bounds**
   (`max_cycles ≤ 8640`, `sleep_interval = 10s`, `max_duration ≤ 86400s`, `failure_budget = 100`),
   with a recorded `stop_reason` of `STOP_TIME`, `MAX_CYCLES`, or `SCHED_FAILURE_BUDGET_EXCEEDED`.
2. The **Read-Only Continuous Ledger Audit** (per the ratified Audit Charter + Audit TDD Charter)
   must be **implemented and executed separately** against the final ledger state.
3. The audit verdict must be **CLEAN** before S1 authorization may be considered.
4. A **NOT_CLEAN** audit keeps S1 **BLOCKED** and requires a corrective charter.
5. A CLEAN audit **does not auto-enable** S1. It only sets `s1_charter_eligible = True`.

### Gate B — Raw vs Semantic Separation

1. The raw audit proves **forensic ledger integrity only** (read-only access, schema, append-only,
   provenance, SHA, permissions, pair structure, endpoint authority).
2. The raw audit **does not assert semantic projection validity**.
3. The `abs(poly_timestamp_ms - hl_time_ms) <= 1000` cross-source delta rule belongs to the
   **ratified S1 projection / adapter layer** (`MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS`), **not** the
   raw ledger audit.
4. **No** semantic parse, **no** `Decimal` conversion, **no** top-of-book interpretation, **no**
   BID/ASK side-axiom application, and **no** price-cross logic is authorized by this charter.
5. Semantic validity is evaluated **only** later, inside the ratified S1 projection runtime, behind
   an explicit `StreamAuthorization` — never here.

### Gate C — Pair Completeness Precondition

1. Every S1 candidate must originate from **exactly one** Hyperliquid leg **and exactly one**
   Polymarket leg under the **same `cycle_id`**.
2. **Lone Hyperliquid**, **lone Polymarket**, **more-than-two-leg**, **mismatched-cycle**, and
   **orphan** rows are **permanently ineligible** for S1.
3. **Non-2xx** captures are **permanently ineligible** for S1.
4. **Failed cycles are never projected** to S1.
5. Pair completeness is a structural property of the raw ledger and must be proven by the raw audit
   (Gate A) before any S1 candidate set is even enumerable.

### Gate D — Source Authority Precondition

1. **Only** the ratified Hyperliquid BTC l2Book source authority
   (`HYPERLIQUID_L2_BOOK_BY_COIN_V1`, `POST https://api.hyperliquid.xyz/info`,
   body `{"type":"l2Book","coin":"BTC"}`) may feed the HL side.
2. **Only** the ratified Polymarket CLOB YES-token /book source authority
   (`POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`, `GET https://clob.polymarket.com/book?token_id=<YES_TOKEN>`)
   may feed the Polymarket side.
3. **Wrong coin / wrong token / wrong method / wrong path / private / auth / order / balance**
   endpoints are **ineligible**.
4. The ratified request headers must have been preserved during capture:
   - Hyperliquid: `Accept: application/json`, `Content-Type: application/json`.
   - Polymarket: `Accept: application/json`, plus the pinned fixed User-Agent
     `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36`.
5. Any evidence of **cookies / auth headers / proxy / rotating or random User-Agent / retry /
   Cloudflare-bypass tooling** makes the affected rows **ineligible**.

### Gate E — Provenance / SHA Precondition

1. **Both legs** must carry `capture_sequence`, `cycle_id`, `source_authority`,
   `response_body_sha256`, `byte_length`, and `http_status` evidence.
2. `response_body_sha256` must be **non-empty, valid 64-character lowercase hex**.
3. SHA linkage must be **preserved into any future S1 append** (the dual-source idempotency key is
   `sha256(poly_sha + "|" + hl_sha)`).
4. **Missing or malformed provenance** makes the pair **ineligible**.
5. `rowid` / `sqlite_sequence` / `capture_sequence` must **never** become a domain identity. The
   ledger sequence is a forensic ordering only.

### Gate F — Adapter Boundary Precondition

1. Future S1 append may **only** route through the already-ratified
   **S1 Production Ingestion Adapter / Durable Writer**
   (`phase6_2_shadow_intent/s1_production_ingestion_adapter.py`).
2. **No parallel projection formula** may be introduced.
3. The ratified **S1 paired projection failure literals** (`S1_PAIR_*`, side-axiom, delta, etc.)
   must **propagate unchanged** — never be swallowed, renamed, or relaxed.
4. **No local wall-clock substitution** for source timestamps. Source event time comes **only**
   from `$.timestamp` (Polymarket CLOB) and `$.time` (Hyperliquid l2Book).
5. **No unratified coercion** of `Decimal` / `int` fields. Prices/sizes remain precision-preserving
   `decimal.Decimal`; timestamps remain `int` epoch-ms.

### Gate G — Idempotency / Replay Precondition

1. Future S1 append must be **deterministic and idempotent**.
2. Duplicate raw evidence must be a **no-op / already-written** outcome, **never** a duplicate S1
   row (`INSERT OR IGNORE` on the dual-source idempotency key).
3. Idempotency must derive from **dual-source evidence identity**
   (`sha256(poly_sha + "|" + hl_sha)`), **never** sqlite `rowid` or insertion order.
4. Replaying the same raw pair must leave the S1 row count unchanged.

### Gate H — S1 Write Firewall

1. This charter **authorizes no S1 write**.
2. `s1_audit.sqlite3` must remain **absent / untouched** until a later explicit
   **S1 Stream Authorization / Production Append Charter** is ratified and an operator command is
   issued.
3. `stream_authorization` remains **None** throughout the raw run and the raw audit.
4. **Production S1 stream remains BLOCKED.**
5. Any accidental S1 mutation is a **hard blocker** that voids eligibility and requires a corrective
   charter.

### Gate I — No Actionability / Capacity Firewall

1. **No calibration.**
2. **No trading.**
3. **No signal.**
4. **No** `edge` / `profit` / `rank` / `advice` / `size` / `order` / `trade` / `paper` / `live` /
   `canary` output.
5. **Capacity remains 0.**
6. A clean audit **plus** this eligibility charter still **does not activate capital** and **does
   not upgrade capacity**.

### Gate J — Next Gate

1. If the raw audit is **CLEAN** and **all** eligibility conditions (Gates A–I) are satisfied, the
   **only** next possible step is a separate **docs-only S1 Stream Authorization / Production Append
   Charter**.
2. If **any** condition fails, S1 remains **BLOCKED** and a **corrective charter** is required.
3. **No automatic transition** is allowed. S1 activation requires a separate explicit charter
   **and** a separate explicit operator command.

---

## Section 4 — Precondition Satisfaction Ledger (to be completed later)

This is a **template only** — no values are asserted now. When the raw run and audit complete, a
future authorization charter must record, per gate, a PASS/FAIL with evidence:

| Gate | Condition | Status | Evidence |
|------|-----------|--------|----------|
| A | Run bounded + audit CLEAN | PENDING | (post-audit) |
| B | Raw/semantic separation honored | PENDING | (post-audit) |
| C | Pair completeness | PENDING | (post-audit) |
| D | Source authority + headers | PENDING | (post-audit) |
| E | Provenance / SHA | PENDING | (post-audit) |
| F | Adapter boundary | PENDING | (design review) |
| G | Idempotency / replay | PENDING | (design review) |
| H | S1 write firewall intact | PENDING | (post-audit) |
| I | No actionability / capacity 0 | PENDING | (design review) |
| J | Next gate is separate charter | PENDING | (procedural) |

All rows must read **PASS** with concrete evidence before an S1 Stream Authorization / Production
Append Charter may be drafted.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this eligibility & safety preconditions charter.
2. 24h run completes or stops (ledger reaches final state).
3. RED→GREEN post-run audit implementation (per the ratified Audit TDD Charter).
4. Execute the post-run audit → produce a CLEAN or NOT_CLEAN verdict.
5. If CLEAN **and** all gates A–I satisfied with evidence: draft a separate **S1 Stream
   Authorization / Production Append Charter**.
6. If NOT_CLEAN or any gate fails: write a corrective charter first.

## Post-state

- S1 Stream Authorization Eligibility & Safety Preconditions Charter: **BUILT / RATIFIABLE /
  UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Continuous Ledger Audit Charter: **RATIFIED**.
- Read-Only Continuous Ledger Audit TDD Charter: **RATIFIED**.
- Post-run audit implementation: **BLOCKED / UNSTARTED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
