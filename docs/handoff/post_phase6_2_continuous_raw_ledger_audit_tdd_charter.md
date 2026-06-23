# Post-Phase 6.2 Read-Only Continuous Raw Ledger Audit — TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It defines the exact RED tests required **before** implementing the post-run
  read-only audit module.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, or disturb the running tmux session `mispricing_run_001`.
- **Read-Only Continuous Ledger Audit Charter (boundary): RATIFIED at `bb7b73b`.**
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Post-run audit implementation: BLOCKED / UNSTARTED.**
- **S1 append: DENIED / NOT PERFORMED.**
- **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `bb7b73b4db4291e96547e72cc9cb332936886ccb`.
- Parent chain:
  - `bb7b73b4db4291e96547e72cc9cb332936886ccb` = **RATIFIED** Read-Only Continuous Ledger Audit
    Charter (boundary).
  - `cfd7015585c6a42272861e6f215a5c8e0532f74f` = **RATIFIED** Polymarket User-Agent runtime fix.
  - `63e2ef43aef10834ed39417c690ccd9416c90e3d` = **RATIFIED** Bounded 24h Run Execution-Wiring
    runtime.
- Known run state (from prior operator report — live ledger not read for this charter):
  - 128 paired cycles, 256 rows, 0 failures, all HTTP 200.
  - `s1_audit.sqlite3` absent. `stream_authorization=None`. Permissions 0700/0600.

## Section 2 — RED-before-GREEN Law

- The future audit implementation must begin with **failing tests first**.
- The initial RED must fail because the audit module is absent (`ImportError` / unresolved
  symbol), **not** due to malformed tests.
- Tests must use only **tmp_path SQLite fixtures** — never the live run ledger.
- The audit module must be implemented under a **new** file
  (`phase6_2_shadow_intent/continuous_raw_ledger_audit.py` or equivalent). No existing runtime
  file may be modified to satisfy these tests.
- No "make it pass" shortcut may relax a ratified charter constraint; if a ratified boundary
  blocks GREEN, the implementer must **STOP** and request a docs-only amendment first.

## Section 3 — Test Fixture Requirements

All test fixtures must:

- Use `pytest` `tmp_path` for all SQLite files — **never** the live run ledger at
  `/root/mispricing_continuous_raw_24h_run_001/raw_capture.sqlite3`.
- Use the **exact** ratified DDL schema for `continuous_raw_capture` (from
  `bounded_24h_run_execution_wiring._CONTINUOUS_LEDGER_DDL`), including both append-only triggers.
- Provide builder helpers (`_make_ledger`, `_insert_row`, `_insert_pair`) to construct minimal
  valid and intentionally invalid ledger states.
- Use only real `os.chmod` calls to set directory/DB permissions in fixtures.
- Never call real HTTPS endpoints.
- Never access S1.

**Ratified row field constants for fixtures:**

```python
_HL_AUTHORITY  = "HYPERLIQUID_L2_BOOK_BY_COIN_V1"
_PM_AUTHORITY  = "POLYMARKET_CLOB_BOOK_BY_TOKEN_V1"
_HL_HOST       = "api.hyperliquid.xyz"
_PM_HOST       = "clob.polymarket.com"
_HL_TARGET     = "/info"
_PM_TARGET     = ("/book?token_id="
                  "13433573766910980267981622064090484781359464703732825845886677588040916221533")
_HL_BODY       = b'{"type":"l2Book","coin":"BTC"}'
_PM_BODY       = b""
_PINNED_UA     = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
```

---

## Section 4 — Required RED Test Groups

### Group A: Read-only open / no mutation

Future tests must require that the audit module:

**A1.** Opens `raw_capture.sqlite3` using `file:<path>?mode=ro` URI — a plain `sqlite3.connect`
without `uri=True` + `mode=ro` must not be acceptable.

**A2.** Raises a closed failure when an `INSERT` is attempted against the opened connection
(SQLite read-only mode must propagate — the audit must not wrap this in try/except silently).

**A3.** Raises a closed failure when `UPDATE` is attempted against the opened connection.

**A4.** Raises a closed failure when `DELETE` is attempted against the opened connection.

**A5.** Raises a closed failure (e.g. `AUDIT_LEDGER_NOT_FOUND`) when the ledger path does not
exist.

**A6.** Raises a closed failure (e.g. `AUDIT_DB_PERM_VIOLATION`) when the SQLite file does not
have mode `0o600`. The test must use `os.chmod(ledger, 0o644)` to simulate and confirm the
failure.

**A7.** Raises a closed failure (e.g. `AUDIT_DIR_PERM_VIOLATION`) when the run directory does
not have mode `0o700`. The test must use `os.chmod(run_dir, 0o755)` to simulate and confirm.

**A8.** Returns a successful open result (`AUDIT_LEDGER_OPEN_VERIFIED`) when path exists, DB is
`0o600`, and directory is `0o700`.

### Group B: Schema and append-order integrity

**B1.** Fails closed (`AUDIT_TABLE_MISSING`) when `continuous_raw_capture` is absent from
`sqlite_master`.

**B2.** Fails closed (`AUDIT_SCHEMA_DRIFT`) when any ratified column is missing from
`continuous_raw_capture` (test each column individually by omitting it from a fixture DDL).

**B3.** Fails closed (`AUDIT_SCHEMA_DRIFT`) when an unexpected extra column is present.

**B4.** Confirms that `capture_sequence` is `INTEGER PRIMARY KEY AUTOINCREMENT` — the audit must
not accept a ledger where `capture_sequence` was renamed or removed.

**B5.** Confirms that `capture_sequence` is **not** used as a domain identity in any audit output
— the audit report must not carry a field named `domain_id`, `projection_key`, or similar that
aliases `capture_sequence` as a primary business key.

**B6.** Passes monotonicity check when rows are inserted with sequence 1, 2, 3 (no gaps).

**B7.** Fails closed (`AUDIT_SEQUENCE_GAP`) when `capture_sequence` has a gap (e.g. rows 1, 2, 4
— missing 3). The fixture must delete row 3 **after** closing the connection (bypassing triggers
using a raw DDL workaround in the fixture, NOT in the audit module itself).

**B8.** Confirms that both append-only triggers `trg_continuous_raw_capture_no_update` and
`trg_continuous_raw_capture_no_delete` are present in `sqlite_master` (`AUDIT_TRIGGER_ABSENT`
if either is missing).

### Group C: Pair-cycle completeness

**C1.** Passes when every `cycle_id` in the fixture has exactly one HL row and one PM row.

**C2.** Fails closed (`AUDIT_ORPHAN_CYCLE`) when a fixture `cycle_id` has only a HL row and no
PM row.

**C3.** Fails closed (`AUDIT_ORPHAN_CYCLE`) when a fixture `cycle_id` has only a PM row and no
HL row.

**C4.** Fails closed (`AUDIT_ORPHAN_CYCLE`) when a fixture `cycle_id` has two HL rows and one
PM row (leg count > 2 per authority).

**C5.** The `paired_complete` count in the audit report must equal the count of `cycle_id`s
where both legs return `http_status BETWEEN 200 AND 299`. Test with a mix of 2xx and non-2xx
cycles.

**C6.** The `paired_complete` count must equal `hl_committed` count and `pm_committed` count
when all pairs are successful (all 2xx). Discrepancy triggers `AUDIT_PAIR_COUNT_MISMATCH`.

**C7.** A cycle where one leg is non-2xx must contribute to `failed_cycles`, not
`paired_complete`, regardless of the other leg's status.

### Group D: Endpoint and header authority

**D1.** Passes for a fixture HL row with exact:
`source_authority=_HL_AUTHORITY`, `method='POST'`, `scheme='https'`, `host=_HL_HOST`,
`request_target=_HL_TARGET`, `request_body=_HL_BODY`.

**D2.** Fails closed (`AUDIT_HL_TARGET_DRIFT`) for any HL row with a mutated `request_target`
(e.g. `/info2`), wrong `method` (e.g. `GET`), wrong `host`, or wrong `request_body`.

**D3.** Passes for a fixture PM row with exact:
`source_authority=_PM_AUTHORITY`, `method='GET'`, `scheme='https'`, `host=_PM_HOST`,
`request_target=_PM_TARGET`, `request_body=b""`.

**D4.** Fails closed (`AUDIT_PM_TARGET_DRIFT`) for any PM row with a wrong token ID, wrong
method (`POST`), wrong host, or non-empty `request_body`.

**D5.** Fails closed (`AUDIT_UNAUTHORIZED_SOURCE_AUTHORITY`) when a row carries any
`source_authority` other than `_HL_AUTHORITY` or `_PM_AUTHORITY`.

**D6.** Fails closed (`AUDIT_UNAUTHORIZED_HOST`) when a row carries any `host` other than
`_HL_HOST` or `_PM_HOST`.

**D7.** Fails closed (`AUDIT_PRIVATE_ENDPOINT`) when a row's `request_target` matches any of
`auth`, `order`, `balance`, `account`, `position`, `private`, `secret`, `wallet`
(case-insensitive substring check).

**D8.** Source-code header audit (AST inspection, not ledger row check): the audit module must
verify that `https_transport` in `bounded_24h_run_execution_wiring` at the ratified commit
carries `Accept + Content-Type` for HL and `Accept + _PINNED_UA` for PM. The test asserts this
check returns `AUDIT_HEADER_VERIFIED` and does not invoke real network.

**D9.** Fails closed (`AUDIT_HEADER_VIOLATION`) if the source-code header check detects missing
`Content-Type` on HL or missing `User-Agent` on PM (simulate by monkeypatching the header dict
lookup in the audit, not by modifying production code).

### Group E: Response evidence and no body dump

**E1.** Passes when every row has a `response_body_sha256` matching `[0-9a-f]{64}`.

**E2.** Fails closed (`AUDIT_SHA256_MALFORMED`) when a row has a `response_body_sha256` that is
not 64 lowercase hex characters (e.g. wrong length, uppercase, or null).

**E3.** Passes when every row has `byte_length > 0`.

**E4.** Fails closed (`AUDIT_BYTE_LENGTH_ZERO`) when any row has `byte_length == 0`.

**E5.** Passes when `byte_length == len(response_body)` for all sampled rows (read-only SHA
recomputation fixture, no body printing).

**E6.** Fails closed (`AUDIT_BYTE_LENGTH_MISMATCH`) when `byte_length != len(response_body)` in
a fixture row.

**E7.** Passes read-only SHA consistency check: `hashlib.sha256(response_body).hexdigest() ==
response_body_sha256` for a fixture row.

**E8.** Fails closed (`AUDIT_SHA256_MISMATCH`) when `hashlib.sha256(response_body).hexdigest()
!= response_body_sha256` in a fixture row (simulate by writing a wrong sha256 value to the
fixture ledger).

**E9.** Audit report must not contain a field named `response_body`, `body`, `raw_bytes`,
`decoded_payload`, or any field whose value is a `bytes` or `str` decoded response. Test by
asserting the audit result dataclass has no field of type `bytes` or `bytearray`, and no field
value containing a decoded JSON payload.

### Group F: Timing and event-time firewall

**F1.** Passes when all rows have `retrieval_completed_epoch_ms >= retrieval_started_epoch_ms`
and `clock_anomaly_evidence == 0`.

**F2.** Records `clock_anomaly_count > 0` (not fails closed) when a fixture row has
`retrieval_completed_epoch_ms < retrieval_started_epoch_ms` and `clock_anomaly_evidence == 1`.
The audit must not reject these rows — it must count and report them.

**F3.** Fails closed (`AUDIT_CLOCK_ANOMALY_FIELD_MISSING`) when a row has
`clock_anomaly_evidence` not in `{0, 1}`.

**F4.** Fails closed (`AUDIT_RETRIEVAL_TIME_AS_EVENT_TIME`) if any downstream projection
component (AST-inspected) substitutes `retrieval_started_epoch_ms` or
`retrieval_completed_epoch_ms` for the source event timestamp fields (`$.timestamp` for
Polymarket, `$.time` for Hyperliquid). This is an AST/source check, not a ledger-row check.

**F5.** Passes when `retrieval_elapsed_monotonic_ns >= 0` for all rows.

**F6.** Fails closed (`AUDIT_NEGATIVE_MONOTONIC_ELAPSED`) when a fixture row has
`retrieval_elapsed_monotonic_ns < 0`.

### Group G: S1 firewall

**G1.** Returns `AUDIT_S1_ABSENT_OK` when `s1_audit.sqlite3` is absent from the run directory
and its parent (`tmp_path`).

**G2.** Fails closed (`AUDIT_S1_PRESENT_VIOLATION`) when `s1_audit.sqlite3` is present in the
run directory (fixture: `(tmp_path / "s1_audit.sqlite3").touch()`).

**G3.** Returns `AUDIT_S1_LOG_VERIFIED` when `/tmp/mispricing_run_001.log` (or an injected log
path) contains `stream_authorization=None  S1_append=DENIED`.

**G4.** Fails closed (`AUDIT_S1_AUTHORIZATION_UNVERIFIABLE`) when the runner log is absent or
does not contain the expected denial line.

**G5.** Fails closed (`AUDIT_S1_TABLE_IN_CONTINUOUS_LEDGER`) when a table named `s1_audit` or
`s1_*` exists in the continuous ledger's `sqlite_master` (fixture: inject such a table).

**G6.** Passes when `sqlite_master` in the continuous ledger contains only `continuous_raw_capture`
and `sqlite_sequence` (plus the two ratified triggers) — no other tables, views, or indexes.

### Group H: Failure budget and stop reason

**H1.** Passes when zero fixture rows are non-2xx and `failed_cycles == 0`,
`failure_budget_remaining == 100`.

**H2.** Counts `failed_cycles == 1` when one fixture cycle has a non-2xx HL leg (regardless of
PM status).

**H3.** Counts `failed_cycles == 1` when one fixture cycle has a non-2xx PM leg (regardless of
HL status).

**H4.** Fails closed (`AUDIT_BUDGET_EXCEEDED_NOT_STOPPED`) when `failed_cycles > 100` but the
runner's `stop_reason` is not `SCHED_FAILURE_BUDGET_EXCEEDED` (inconsistent accounting).

**H5.** Non-2xx cycle must not appear in `paired_complete` count. The audit asserts:
`paired_complete + failed_cycles == total_cycles`.

**H6.** Records the `stop_reason` from the `CollectionReport` (injected as a parameter to the
audit function, since it is not persisted in the ledger schema). Valid values:
`STOP_TIME`, `MAX_CYCLES`, `SCHED_FAILURE_BUDGET_EXCEEDED`. Any other value records
`AUDIT_UNEXPECTED_STOP`.

**H7.** When `stop_reason == 'SCHED_FAILURE_BUDGET_EXCEEDED'`, asserts `failed_cycles > 100`.
If `failed_cycles <= 100` with this stop_reason, records `AUDIT_BUDGET_STOP_ACCOUNTING_ERROR`.

### Group I: Report shape / no actionability

**I1.** The audit result object (dataclass or namedtuple) must expose these fields and no others
beyond audit metadata:
`total_rows`, `total_cycles`, `paired_complete`, `failed_cycles`, `failure_budget_remaining`,
`hl_committed`, `pm_committed`, `http_status_distribution`, `clock_anomaly_count`,
`sha256_sample_passed`, `sequence_gap_count`, `orphan_cycle_count`, `stop_reason`,
`s1_absent`, `s1_log_verified`, `audit_verdict` (`CLEAN` or `NOT_CLEAN`), `violations`.

**I2.** The audit result must not contain any of:
`edge`, `profit`, `rank`, `signal`, `advice`, `size`, `order`, `trade`, `paper`, `live`,
`canary`, `calibrate`. Test by asserting none of these strings appear as field names on the
result dataclass.

**I3.** The audit result must not contain any field of type `bytes` or `bytearray` (raw bodies
must never be in the report).

**I4.** `CAPACITY == 0` must be a module-level constant in the audit module.

**I5.** The audit module must not import or call any trading / order / balance / position /
signal / calibration module. Test via AST import walker (same pattern as the existing
`test_adapter_has_no_network_or_scheduler_imports` test).

### Group J: Post-audit gate

**J1.** When `audit_verdict == 'CLEAN'`, the result carries a field `s1_charter_eligible = True`
— meaning a separate S1 Stream Authorization Charter **may** be considered. The field is
informational only; it does not trigger S1 append.

**J2.** When `audit_verdict == 'NOT_CLEAN'`, the result carries `s1_charter_eligible = False` —
S1 remains blocked.

**J3.** The audit module must not contain any callable that activates S1 append, opens an S1
connection, calls the S1 ingestion adapter, or writes to any DB other than its own (read-only)
connection. Assert via AST inspection that no call to `ingest_paired_s1_projection` or
`sqlite3.connect` with a write-mode path exists in the audit module's non-fixture code.

**J4.** A `CLEAN` result combined with `s1_charter_eligible = True` must still require a separate
explicit operator command and a separate S1 Stream Authorization Charter before any S1 append
occurs. The audit module must not issue that command autonomously. Assert the audit module
contains no `os.system`, `subprocess`, `exec`, `eval` call that could trigger downstream
activation.

---

## Section 5 — Minimal GREEN Boundary

A future implementation may add **only**:

- `phase6_2_shadow_intent/continuous_raw_ledger_audit.py` — the audit module.
- `tests/test_phase6_2_continuous_raw_ledger_audit.py` — the test file.

It must **not** add:

- S1 stream append, S1 activation, or S1 schema creation.
- Any write to the continuous ledger or any other DB beyond test tmp fixtures.
- Calibration / trading / actionability.
- Network requests.
- Daemon / background process / cron.

## Section 6 — Next Gates

Only next safe gates:

1. Independent review of this TDD charter.
2. 24h run completes or stops (ledger reaches final state).
3. If charter is ratified and run complete: **RED→GREEN post-run audit implementation**.
4. If audit implementation is ratified: **execute the post-run audit** against the final ledger.
5. If audit verdict is `CLEAN`: consider a separate **S1 Stream Authorization / Production Append
   Charter**.
6. If audit verdict is `NOT_CLEAN`: write a corrective charter first.

## Post-state

- Read-Only Continuous Ledger Audit TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- Read-Only Continuous Ledger Audit Charter (boundary): **RATIFIED** at `bb7b73b`.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Post-run audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
