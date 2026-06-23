# Post-Phase 6.2 Polymarket CLOB Book YES-Token One-Shot Raw-Evidence Authorization Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It authorizes **no** physical network call by itself.
- It creates **no** runtime, **no** ledger; performs **no** parsing; performs **no** S1
  ingestion/projection.
- It only makes a future **separately-commanded** one-shot CLOB YES-token raw capture **ELIGIBLE** after
  ratification.
- Physical CLOB capture remains **NOT STARTED**.
- Polymarket timestamp binding remains **PENDING**.
- **B2 remains BLOCKED.**
- Projection / S1 ingestion remains **BLOCKED**.
- Capacity remains **0**.

## Source basis

- RATIFIED Polymarket Timestamp Source-Authority Gap / Acquisition Amendment Charter.
- RATIFIED BTC Market/Instrument Binding Charter.
- RATIFIED Gamma full-token extraction:
  - `polymarket_yes_outcome_label = Yes`
  - `polymarket_yes_token_id = "13433573766910980267981622064090484781359464703732825845886677588040916221533"`
  - `polymarket_outcome_token_binding_axiom = PARALLEL_SOURCE_ORDERING`
- Polymarket timestamp binding remains **PENDING**; B2 remains **BLOCKED**; Projection/S1 remains
  **BLOCKED**.

This charter authorizes, at documentation level only, the future **single blind** raw capture needed to
test whether `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1` physically carries a source-issued `timestamp` candidate
for the ratified BTC **YES** token book. It executes nothing.

---

## Section 1 — Target Lock

If, and only if, this charter is ratified and a separate operator command is issued, the future request
must be **exactly**:

```
method          = GET
scheme          = https
host            = clob.polymarket.com
request_target  = /book?token_id=13433573766910980267981622064090484781359464703732825845886677588040916221533
full URL        = https://clob.polymarket.com/book?token_id=13433573766910980267981622064090484781359464703732825845886677588040916221533
source_authority = POLYMARKET_CLOB_BOOK_BY_TOKEN_V1
```

- **No** query-parameter changes.
- **No** alternate `token_id`.
- **No** NO-token capture.
- **No** second token capture.
- **No** market lookup.
- **No** search / discovery.
- **No** slug / condition / outcome inference.
- **No** aliasing, normalization, or token repair.
- The target token is an **exact opaque string identity**, not a numeric value: no `int`/`float`/coercion,
  no scientific notation, no truncation, no rounding. Every digit is preserved exactly.

## Section 2 — One-Shot / Blind Capture Constraints

- exactly **one** outbound HTTPS request;
- no retry;
- no fallback;
- no second request;
- no loop;
- no scheduler;
- no daemon;
- no concurrent capture;
- no body dump;
- no decode;
- no parse;
- no JSON load;
- no field extraction during capture;
- no S1 access;
- no projection;
- raw bytes only;
- request body must be **empty** because method is GET.

## Section 3 — Independent Ledger Isolation

- The future capture must use a **fresh independent** evidence directory, for example:

  ```
  /root/mispricing_polymarket_clob_yes_runtime_evidence
  ```

- It must create/use **only** its own `raw_capture.sqlite3` ledger.
- It must **not** append to or access:
  - `/root/mispricing_runtime_evidence`
  - `/root/mispricing_gamma_runtime_evidence`
  - `/root/mispricing_l2book_runtime_evidence`
- It must **not** create/open/use `s1_audit.sqlite3`.
- Directory mode must be **0700**.
- `raw_capture.sqlite3` and any `-wal`/`-shm` files must be **0600**.
- If the target evidence directory already contains previous capture evidence, the future operator must
  **STOP**.

## Section 4 — Forensic Commit Requirements

The future operator report must include **only** metadata / invariants (never the response body):

- `capture_sequence`
- `attempt_sequence`
- `source_authority`
- `method` / `scheme` / `host` / `request_target`
- `request_body` length = `0`
- `http_status`
- `response_body` byte length
- `response_body_sha256` full value
- `retrieval_started_epoch_ms`
- `retrieval_completed_epoch_ms`
- `retrieval_elapsed_monotonic_ns`
- `clock_anomaly_evidence`
- `raw_capture_log` count
- `raw_fetch_attempt_log` count
- `raw_processing_journal` count
- stored SHA-256 == freshly recomputed SHA-256 over stored bytes
- OS modes for directory and sqlite/wal/shm files
- `s1_audit.sqlite3` absent
- prior ledgers untouched
- git tracked state unchanged
- response body never printed / decoded / parsed

## Section 5 — Timestamp Candidate Boundary

- The future capture is intended **only** to obtain raw evidence for the candidate field: `timestamp`.
- This charter does **not** prove the timestamp exists.
- This charter does **not** prove timestamp unit, semantics, event-time admissibility, tolerance, or
  cross-source alignment.
- After RAW_COMMITTED evidence exists, a **separate read-only CLOB field-authority audit** must inspect
  **path / type / shape only**.
- Only **if** a source-issued timestamp candidate is observed may a later **Polymarket Timestamp Authority
  Charter** be drafted.
- Retrieval timestamps remain **forensic metadata only** and must **not** substitute for source event time.

## Section 6 — Explicit Denials

This charter denies all of:

- network execution by this charter alone;
- another capture without a separate operator command;
- NO-token capture;
- two-token capture;
- search / discovery / fallback;
- timestamp authority proven now;
- B2 authority;
- Projection / S1 ingestion;
- DTO / schema / runtime / DDL changes;
- parsing implementation;
- calibration / Phase 7.1 / 7.2 / 8.1;
- scheduler / continuous collection;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 7 — Next Gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, a separate **bounded operator command** may perform **exactly one** blind YES-token CLOB
   raw capture.
3. After physical RAW_COMMITTED capture, a **read-only CLOB field-authority audit** is required.
4. Timestamp authority remains **PENDING** until that audit proves a `timestamp` path/type/shape and a
   later **Timestamp Authority Charter** is ratified.
5. The S1 Projection DTO / failure-surface charter remains **blocked** until Polymarket timestamp authority
   is ratified.

## Post-state

- Polymarket CLOB Book YES-Token One-Shot Raw-Evidence Authorization Charter: **BUILT / RATIFIABLE /
  UNRATIFIED** pending Gemini + Codex review.
- Polymarket Timestamp Source-Authority Gap / Acquisition Amendment Charter: **RATIFIED**.
- Physical CLOB YES-token capture: **NOT STARTED**.
- Polymarket timestamp binding: **PENDING**.
- B2: **BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
