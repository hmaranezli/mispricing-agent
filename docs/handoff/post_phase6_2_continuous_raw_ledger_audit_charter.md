# Post-Phase 6.2 Read-Only Continuous Raw Ledger Audit Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It defines the complete post-run read-only audit procedure for the continuous
  raw capture ledger produced by the first bounded 24h raw-only collection run.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads **no** live ledger and writes **no** ledger or S1 DB.
- It does **not** stop, restart, or disturb the running tmux session `mispricing_run_001`.
- **First bounded raw-only 24h run: RUNNING / NOT DISTURBED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `cfd7015585c6a42272861e6f215a5c8e0532f74f`.
- Parent chain:
  - `cfd7015585c6a42272861e6f215a5c8e0532f74f` = **RATIFIED** Polymarket User-Agent runtime fix
    (39 wiring tests green, 140 regression tests green).
  - `6debb64da0e9cd082ab3ac6d3ff17a139701885c` = **RATIFIED** Polymarket User-Agent amendment
    charter.
  - `23abfbae39ee69002dff41ffc6dc7ca18377bd27` = **RATIFIED** HTTPS transport header fix runtime.
  - `21efdc61e97bee97d3951365b7e080bb22575610` = **RATIFIED** HTTPS transport header-correctness
    amendment charter.
  - `63e2ef43aef10834ed39417c690ccd9416c90e3d` = **RATIFIED** Bounded 24h Run Execution-Wiring
    runtime.
- Known early run state (from operator status report, not live ledger read):
  - tmux session `mispricing_run_001`: **RUNNING**
  - run_dir: `/root/mispricing_continuous_raw_24h_run_001`
  - ledger: `/root/mispricing_continuous_raw_24h_run_001/raw_capture.sqlite3`
  - table: `continuous_raw_capture`
  - At report time: 25 paired cycles / 50 rows / 100% HTTP 200 / 0 failures /
    `s1_audit.sqlite3` absent / dir `0700` / db `0600`.
  - `stream_authorization=None` — S1 append DENIED.

## Section 2 — Audit Scope and Trigger

This audit procedure must be executed **only after** the bounded 24h run has fully completed or
stopped (via `STOP_TIME`, `MAX_CYCLES`, `SCHED_FAILURE_BUDGET_EXCEEDED`, or operator stop).

The audit must **not** be executed against a live running ledger. The ledger must be in its final
committed state before audit begins.

The audit is **read-only throughout**: the ledger must be opened via `file:?mode=ro` URI and
**no** INSERT / UPDATE / DELETE / DDL may be issued at any point.

**Output is audit report text only.** No S1 writes, no schema mutations, no file creation in the
run directory.

## Section 3 — Run Bounds Verification

The audit must verify:

1. **`max_cycles`**: total row count ÷ 2 (legs per cycle) must be ≤ 8640. If `total_rows / 2 > 8640`,
   record a **BOUNDS_VIOLATION**.
2. **`sleep_interval`**: derived from inter-cycle timing. The median elapsed time between the
   `retrieval_completed_epoch_ms` of one cycle's last leg and the `retrieval_started_epoch_ms` of
   the next cycle's first leg should be approximately 10 s. Record the observed median and p95
   inter-cycle gap in the audit report (forensic metadata only — not used for projection).
3. **`max_duration`**: elapsed from first `retrieval_started_epoch_ms` to last
   `retrieval_completed_epoch_ms` must be ≤ 86 400 000 ms (24h in ms). Record the observed
   elapsed duration.
4. **`failure_budget`**: the count of cycles where at least one leg returned non-2xx must be ≤ 100.
   If > 100, a `SCHED_FAILURE_BUDGET_EXCEEDED` stop must have been recorded; otherwise record a
   **BUDGET_ACCOUNTING_INCONSISTENCY**.
5. **`stop_reason`**: the `CollectionReport.stop_reason` (from runner log or run report if
   persisted) must be one of `STOP_TIME`, `MAX_CYCLES`, or `SCHED_FAILURE_BUDGET_EXCEEDED`.
   Any other stop reason must be recorded as **UNEXPECTED_STOP**.

## Section 4 — Ledger Integrity Verification

The audit must verify:

1. **Read-only access**: the ledger connection must be opened as
   `sqlite3.connect("file:<path>?mode=ro", uri=True)`. Any attempt to write must raise an error.
   Record as **LEDGER_OPEN_MODE_VERIFIED** on success.
2. **Directory permission**: `stat(run_directory)` mode must be `0o700`. Record as
   **DIR_PERM_OK** or **DIR_PERM_VIOLATION**.
3. **DB file permission**: `stat(ledger_path)` mode must be `0o600`. Record as
   **DB_PERM_OK** or **DB_PERM_VIOLATION**.
4. **`capture_sequence` monotonicity**: `SELECT capture_sequence FROM continuous_raw_capture ORDER
   BY capture_sequence ASC` must yield a gapless sequence starting at 1. Any gap records a
   **SEQUENCE_GAP** violation.
5. **Append-only trigger presence**: `SELECT name FROM sqlite_master WHERE type='trigger'` must
   include `trg_continuous_raw_capture_no_update` and `trg_continuous_raw_capture_no_delete`.
   Missing triggers record a **TRIGGER_ABSENT** violation.
6. **No UPDATE/DELETE evidence**: attempt `UPDATE continuous_raw_capture SET http_status=http_status
   WHERE 0=1` (a no-op) in a transaction that is immediately rolled back; the append-only trigger
   must fire and raise an error even on the vacuous update. If it does not, record
   **APPEND_ONLY_BREACH**.
7. **Schema match**: `PRAGMA table_xinfo(continuous_raw_capture)` must match the ratified DDL
   column set:
   `capture_sequence, cycle_id, source_authority, method, scheme, host, request_target,
   request_body, http_status, response_body, response_body_sha256, byte_length,
   retrieval_started_epoch_ms, retrieval_completed_epoch_ms, retrieval_elapsed_monotonic_ns,
   clock_anomaly_evidence`.
   Any missing or extra column records a **SCHEMA_DRIFT** violation.
8. **No rowid as domain identity**: the `capture_sequence` AUTOINCREMENT primary key is a ledger
   sequence only. The domain idempotency key is `sha256(poly_sha + "|" + hl_sha)` — not rowid.
   Confirm that no downstream query references `rowid` as a join or projection key.

## Section 5 — Pair-Cycle Completeness Verification

The audit must verify:

1. **Cycle leg count**: for each distinct `cycle_id`, count legs by `source_authority`. Each cycle
   must have exactly one `HYPERLIQUID_L2_BOOK_BY_COIN_V1` row and one
   `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1` row. Any cycle with a different count records
   **ORPHAN_CYCLE**.

   ```sql
   SELECT cycle_id,
          SUM(CASE WHEN source_authority='HYPERLIQUID_L2_BOOK_BY_COIN_V1' THEN 1 ELSE 0 END) AS hl_legs,
          SUM(CASE WHEN source_authority='POLYMARKET_CLOB_BOOK_BY_TOKEN_V1' THEN 1 ELSE 0 END) AS pm_legs
   FROM continuous_raw_capture
   GROUP BY cycle_id
   HAVING hl_legs != 1 OR pm_legs != 1;
   ```

   Must return zero rows. Any result records **ORPHAN_CYCLE**.

2. **Cycle ordering**: within each `cycle_id`, the Hyperliquid leg `capture_sequence` must precede
   the Polymarket leg `capture_sequence` (i.e. HL is fetched first per the scheduler). Violations
   record **CYCLE_LEG_ORDER_ANOMALY** (informational only — does not block S1 authorization alone).

3. **Committed-pair count**: `COUNT(DISTINCT cycle_id) WHERE http_status BETWEEN 200 AND 299` for
   both legs must equal the `paired_complete` count reported by the runner. Discrepancy records
   **PAIR_COUNT_MISMATCH**.

4. **No S1 eligibility for non-2xx cycles**: any cycle with at least one non-2xx leg must not
   appear as a committed pair. The audit confirms this by asserting:

   ```sql
   SELECT cycle_id FROM continuous_raw_capture
   GROUP BY cycle_id
   HAVING MIN(http_status) < 200 OR MAX(http_status) >= 300;
   ```

   Each returned cycle_id must have `paired_complete` status of `false` in any downstream view.
   Any contradiction records **INVALID_PROJECTION_ELIGIBILITY**.

## Section 6 — Endpoint / Request Authority Verification

The audit must verify (read from `method`, `scheme`, `host`, `request_target`, `request_body`
columns — no body decode or print):

1. **Hyperliquid authority**: every row with `source_authority='HYPERLIQUID_L2_BOOK_BY_COIN_V1'`
   must have:
   - `method = 'POST'`
   - `scheme = 'https'`
   - `host = 'api.hyperliquid.xyz'`
   - `request_target = '/info'`
   - `request_body = b'{"type":"l2Book","coin":"BTC"}'`
   Any deviation records **HL_TARGET_DRIFT**.

2. **Polymarket authority**: every row with `source_authority='POLYMARKET_CLOB_BOOK_BY_TOKEN_V1'`
   must have:
   - `method = 'GET'`
   - `scheme = 'https'`
   - `host = 'clob.polymarket.com'`
   - `request_target` matching `/book?token_id=13433573766910980267981622064090484781359464703732825845886677588040916221533`
   - `request_body = b''`
   Any deviation records **PM_TARGET_DRIFT**.

3. **No forbidden authorities**: the set of distinct `source_authority` values must be exactly
   `{'HYPERLIQUID_L2_BOOK_BY_COIN_V1', 'POLYMARKET_CLOB_BOOK_BY_TOKEN_V1'}`. Any other value
   records **UNAUTHORIZED_SOURCE_AUTHORITY**.

4. **No forbidden hosts**: the set of distinct `host` values must be exactly
   `{'api.hyperliquid.xyz', 'clob.polymarket.com'}`. Any other value records
   **UNAUTHORIZED_HOST**.

5. **Header verification** (headers are not stored in the ledger schema — this is a code-path
   audit, not a row audit): confirm via source inspection that `https_transport` in
   `bounded_24h_run_execution_wiring.py` at commit `cfd7015` applies the ratified header sets:
   - Hyperliquid: `Accept: application/json`, `Content-Type: application/json`
   - Polymarket: `Accept: application/json`, `User-Agent: Mozilla/5.0 (X11; Linux x86_64)
     AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36`
   Confirm no cookies, no auth headers, no proxy, no rotating UA, no Cloudflare-bypass tooling.

## Section 7 — Response Evidence Verification

The audit must verify (metadata columns only — raw bodies must **not** be printed, decoded, or
dumped):

1. **SHA256 presence**: every row must have a non-null, non-empty `response_body_sha256` value of
   exactly 64 lowercase hex characters. Violations record **SHA256_MALFORMED**.

2. **SHA256 consistency** (optional, read-only): for a random sample of ≤ 100 rows, verify
   `hashlib.sha256(response_body).hexdigest() == response_body_sha256`. Any mismatch records
   **SHA256_MISMATCH**. Raw body bytes must be loaded for this check but **not** printed or
   decoded.

3. **Byte length**: every row must have `byte_length > 0` and `byte_length == len(response_body)`.
   Violations record **BYTE_LENGTH_MISMATCH**.

4. **HTTP status**: every row must have `http_status` between 100 and 599 inclusive. Any row
   outside this range records **HTTP_STATUS_MALFORMED**.

5. **Non-2xx rows**: record the count and distribution of non-2xx statuses. These rows represent
   soft failures. They must never be projected to S1 (verified in Section 5).

## Section 8 — Timing Metadata Verification

The audit must verify:

1. **Retrieval timestamps forensic-only**: `retrieval_started_epoch_ms` and
   `retrieval_completed_epoch_ms` are wall-clock acquisition times only. They must never be
   substituted for source event timestamps (`$.timestamp` for Polymarket,
   `$.time` for Hyperliquid). The audit confirms this by verifying that projection logic (if any
   dry-run output exists) uses the JSON-embedded event timestamps, not the retrieval columns.

2. **Timestamp ordering**: for each row, `retrieval_completed_epoch_ms >= retrieval_started_epoch_ms`.
   Any row violating this records a non-zero `clock_anomaly_evidence` value; the audit counts
   these and records the total.

3. **Elapsed monotonic**: `retrieval_elapsed_monotonic_ns >= 0` for all rows. Negative values
   record **NEGATIVE_MONOTONIC_ELAPSED**.

4. **`clock_anomaly_evidence` distribution**: count rows where `clock_anomaly_evidence = 1`.
   Record count. Elevated counts (> 5% of rows) should be flagged as **CLOCK_ANOMALY_ELEVATED**
   for human review.

5. **Cross-source timing**: for each committed pair, compute
   `|hl_completed_epoch_ms - pm_started_epoch_ms|` as an approximation of cross-source delta.
   Record median and p95. Values exceeding 1000 ms in the majority of pairs should be flagged
   as **CROSS_SOURCE_DELTA_ELEVATED** (informational — the ratified `MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS`
   constraint applies to source-event timestamps, not retrieval timestamps).

## Section 9 — S1 Firewall Verification

The audit must verify:

1. **`s1_audit.sqlite3` absent**: `os.path.exists` on the run directory and its parent must
   confirm no `s1_audit.sqlite3` file was created. Record as **S1_AUDIT_ABSENT_OK** or
   **S1_AUDIT_PRESENT_VIOLATION**.

2. **No S1 tables in continuous ledger**: `SELECT name FROM sqlite_master WHERE type='table'`
   against the continuous ledger must return only `continuous_raw_capture` (and
   `sqlite_sequence`). Any table named `s1_*` or matching the production S1 schema records
   **S1_TABLE_IN_CONTINUOUS_LEDGER_VIOLATION**.

3. **`stream_authorization=None` confirmed**: the runner log (`/tmp/mispricing_run_001.log`)
   must contain `stream_authorization=None  S1_append=DENIED`. If absent, record
   **S1_AUTHORIZATION_UNVERIFIABLE**.

4. **No S1 imports at runtime**: confirm via `ast.parse` inspection of
   `bounded_24h_run_execution_wiring.py` that no production S1 append call is reachable when
   `stream_authorization=None` (the scheduler's `if stream_authorization is not None` guard
   ensures this statically).

## Section 10 — Failure Surface Verification

The audit must verify:

1. **Failure count consistency**: count rows by cycle_id where any leg has `http_status < 200` or
   `http_status >= 300`. This is the soft failure count. Must be ≤ 100 (failure budget).
2. **Non-2xx never projected**: confirmed by Section 5 item 4.
3. **No drift/private endpoint evidence**: `SELECT DISTINCT request_target FROM continuous_raw_capture`
   must contain only `/info` and the ratified Polymarket token path. Any other target records
   **TARGET_DRIFT_EVIDENCE**.
4. **No auth/order/balance targets**: verify none of the `request_target` values match
   `(auth|order|balance|account|position|private|secret|wallet)` (case-insensitive).
5. **Failure budget enforcement**: if `stop_reason == 'SCHED_FAILURE_BUDGET_EXCEEDED'`, the soft
   failure count must be exactly 101 (budget=100, stops after exceeding). Any other count with
   this stop reason records **BUDGET_STOP_ACCOUNTING_ERROR**.

## Section 11 — Audit Report Output Constraints

The audit report must contain **only**:

- run metadata: `run_directory`, `ledger_path`, `audit_timestamp`, `run_elapsed_ms`
- bounds verification results: each item from Section 3 as PASS / FAIL / value
- integrity verification results: each item from Section 4 as PASS / FAIL
- pair-cycle summary: total cycles, committed pairs, orphan cycles, failed cycles
- endpoint authority results: each item from Section 6 as PASS / FAIL
- response evidence summary: SHA presence, byte length, HTTP status distribution
- timing metadata summary: forensic-only, no event-time substitution
- S1 firewall results: each item from Section 9 as PASS / FAIL
- failure surface results: counts and PASS / FAIL per Section 10
- overall audit verdict: **CLEAN** (all checks pass) or **NOT CLEAN** (list of violations)

The audit report must **not** contain:

- raw response bodies or decoded payloads
- trading signals, edge estimates, profit claims, rank scores, sizing advice
- paper / live / canary recommendations
- calibration thresholds or analytics
- any S1 write or projection result

## Section 12 — Next Gate

After the audit is completed:

1. If audit verdict is **CLEAN**: a separate **S1 Stream Authorization / Production Append
   Charter** may be considered. This is the next gate — not the audit itself.
2. If audit verdict is **NOT CLEAN**: S1 remains **BLOCKED** and a corrective charter addressing
   each violation must be written and ratified before S1 authorization is considered.
3. The audit report itself **does not authorize S1 append**. Authorization requires a separate
   explicit charter and operator command.

## Section 13 — Capacity / Actionability Firewall

- Capacity remains **0** before, during, and after the audit.
- No trading / order / balance / account / position calls.
- No alerts / advice / signals / profitability / ranking / sizing.
- No calibration. No paper / live / canary. No private endpoints.
- No S1 append from the audit procedure.

## Post-state

- Read-Only Continuous Ledger Audit Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **RUNNING / NOT DISTURBED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
