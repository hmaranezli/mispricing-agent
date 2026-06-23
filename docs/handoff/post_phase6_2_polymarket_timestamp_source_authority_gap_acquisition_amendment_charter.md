# Post-Phase 6.2 Polymarket Timestamp Source-Authority Gap / Acquisition Amendment Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It records a **timestamp source-authority gap**.
- It does **not** prove Polymarket event-time authority.
- It does **not** authorize a network call by itself — unless separately ratified **and** separately
  commanded in a future one-shot operator step.
- It grants **no** runtime / S1 / projection / calibration / scheduler / capacity.
- **B2 remains BLOCKED.**
- Projection / S1 ingestion remains **BLOCKED**.
- Capacity remains **0**.

## Source basis

- RATIFIED BTC S1 Projection Eligibility Charter.
- RATIFIED BTC B1/B2 Authority-Binding Design Charter.
- RATIFIED l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter.
- RATIFIED BTC Market/Instrument Binding Charter.
- Completed Polymarket Gamma one-shot capture and read-only field audit.
- Completed l2Book one-shot capture and read-only field audit.

This charter exists because the S1 Projection Eligibility gate requires a **paired** cross-source
observation with a **source-issued Polymarket event timestamp**, and no such timestamp authority has been
established. It records the gap, hard-denies retrieval-time substitution, and lays out the evidence-first
documentation path — nothing more.

---

## Section 1 — Gamma Timestamp Deficit

- **Source-evidence fact:** the completed Polymarket Gamma read-only field-authority audit did **not**
  establish a source-issued event timestamp suitable for cross-source B2 alignment.
- The Gamma `slug` / `conditionId` / `outcomes` / `clobTokenIds` evidence is useful for **B3**, but is
  **not sufficient for B2 event-time authority**.
- **No** timestamp path is invented in Gamma.
- Market creation/update-style fields are **not** reinterpreted as event time; the Gamma audit did not
  establish any such source-issued event-time field, so any such fields are **out-of-scope** here.
- **B2 remains BLOCKED.**

## Section 2 — Anti-Substitution Law

- `retrieval_started_epoch_ms` and `retrieval_completed_epoch_ms` are **collector-side** timestamps.
- They must **never** substitute for source-issued Polymarket event time.
- They must **never** be used for cross-source alignment with Hyperliquid `$.time`.
- They may be retained **only** as forensic retrieval metadata in raw ledgers.
- Any future projection or pair construction that uses retrieval timestamps as event time must
  **fail closed**.
- This rule exists to prevent **lookahead bias, latency drift, collector-clock contamination, and false
  simultaneity**.

## Section 3 — Targeted Discovery Candidate

- Existing source-authority candidate: `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`.
- Candidate endpoint: `GET https://clob.polymarket.com/book?token_id=<ratified_exact_token_id>`.
- Candidate timestamp field: `timestamp`.
- This is a **candidate only**, **not** proven authority. The earlier source-sufficiency work selected the
  Polymarket CLOB book `timestamp` as a candidate, but it must **not** be asserted to be source-issued
  event time until physically captured and audited.
- Candidate token IDs must come **only** from the RATIFIED BTC Market/Instrument Binding Charter:

  ```
  polymarket_yes_token_id = "13433573766910980267981622064090484781359464703732825845886677588040916221533"
  polymarket_no_token_id  = "68320692409850091190490975441025843632582876963922128660910974326175304515755"
  ```

- **No** token discovery, search, aliasing, fuzzy matching, or market lookup is authorized.

## Section 4 — Evidence-First Sequence

1. Ratify this timestamp-gap / amendment charter.
2. Draft and ratify a **separate** docs-only **Polymarket CLOB Book One-Shot Raw-Evidence Authorization
   Charter**.
3. That future authorization must choose **exactly one** ratified `token_id` — YES **or** NO — **or**
   explicitly require **two separate** one-shot captures if both sides are needed. **Do not silently
   capture both.**
4. Only **after** separate authorization and a separate operator command may **one blind raw capture** be
   executed into a **fresh independent** Polymarket CLOB evidence ledger.
5. After RAW_COMMITTED evidence exists, perform a **read-only field-authority audit** of that CLOB payload.
6. Only **if** a source-issued timestamp field is present and typed may a later **Polymarket Timestamp
   Authority Charter** be drafted.
7. Only **after** timestamp authority is ratified may S1 Projection DTO / failure-surface chartering
   continue.

## Section 5 — Future CLOB raw-capture constraints (pre-committed, NOT executed here)

- one-shot only;
- blind capture;
- no retry;
- no fallback;
- no search / discovery;
- no scheduler / loop / daemon;
- no S1;
- no projection;
- no body dump;
- raw bytes only;
- fresh independent evidence directory and `raw_capture.sqlite3` ledger;
- **no append** to the Gamma, l2Book, or Hyperliquid `meta` ledgers;
- OS isolation: directory mode `0700`, sqlite/WAL/SHM mode `0600`;
- SHA-256 over stored bytes required;
- `request_target` exact must include the selected ratified `token_id`;
- retrieval timestamps remain **forensic metadata only**.

## Section 6 — Explicit denials

This charter denies all of:

- Polymarket timestamp authority proven now;
- B2 authority;
- S1 projection eligibility;
- S1 ingestion / projection;
- runtime / network execution by this charter;
- another capture by this charter alone;
- DTO / schema / runtime / DDL changes;
- calibration / Phase 7.1 / 7.2 / 8.1;
- scheduler / continuous collection;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 7 — Next gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, the next docs-only gate is a **Polymarket CLOB Book One-Shot Raw-Evidence Authorization
   Charter**.
3. That next charter must explicitly select whether to capture the **YES** token book, the **NO** token
   book, or **two separately authorized** captures.
4. Runtime or actual network capture remains **blocked** until that separate charter is ratified and the
   operator issues a separate command.

## Post-state

- Polymarket Timestamp Source-Authority Gap / Acquisition Amendment Charter: **BUILT / RATIFIABLE /
  UNRATIFIED** pending Gemini + Codex review.
- BTC S1 Projection Eligibility Charter: **RATIFIED**.
- BTC B1/B2 Authority-Binding Design Charter: **RATIFIED**.
- l2Book runtime / capture / audit: **RATIFIED / COMPLETE / COMPLETE**.
- Polymarket timestamp binding: **PENDING**.
- B2: **BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
