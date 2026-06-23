# Post-Phase 6.2 Polymarket CLOB Timestamp Authority Charter — YES-Token Book / Exact Integer-String / Epoch-ms Binding

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It **proposes** Polymarket-side B2 source-time authority for the YES-token CLOB book.
- It does **not** implement parsing.
- It does **not** implement cross-source alignment.
- It does **not** define DTO / schema / runtime.
- It does **not** authorize S1 ingestion / projection.
- It grants **no** network, **no** new capture, **no** scheduler, **no** calibration, **no** capacity
  increase.
- Until this charter is independently ratified, **Polymarket timestamp binding remains PENDING** and
  **B2 remains BLOCKED**.
- **Even if ratified, Projection / S1 ingestion remains BLOCKED** pending a future DTO / failure-surface /
  runtime authorization.
- Capacity remains **0**.

## Source basis

- RATIFIED Polymarket CLOB Book YES-Token One-Shot Raw-Evidence Authorization Charter.
- Completed Polymarket CLOB YES-token physical one-shot capture.
- Completed read-only Polymarket CLOB YES-token field-authority audit.
- Audit evidence:
  - `source_authority = POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`; `capture_sequence = 1`
  - `response_body_sha256 = 3b9b74e23a9dc796a6e1d9baa7994531550f74b3a6c70353b95690d4d9b25940`
  - top-level type = object; ordered keys =
    `['market', 'asset_id', 'timestamp', 'hash', 'bids', 'asks', 'min_order_size', 'tick_size', 'neg_risk', 'last_trade_price']`
  - duplicate-key result = NONE
  - timestamp candidate **FOUND**: `path = $.timestamp`, `type = string`, value summary `'1782189645718'`
  - no unit/event-time semantics inferred by the audit; retrieval timestamps not used; no body dump,
    no S1, no projection.

---

## Section 1 — Source Timestamp Evidence

```
source_authority      = POLYMARKET_CLOB_BOOK_BY_TOKEN_V1
token side            = YES
token_id              = "13433573766910980267981622064090484781359464703732825845886677588040916221533"
timestamp_path        = $.timestamp
timestamp_source_type = string
observed_value        = "1782189645718"
response_body_sha256  = 3b9b74e23a9dc796a6e1d9baa7994531550f74b3a6c70353b95690d4d9b25940
```

- This is a **source-issued timestamp field observed in the CLOB payload**.
- This charter does **not** claim NO-token timestamp authority.
- This charter does **not** claim Gamma timestamp authority.
- This charter does **not** claim that all Polymarket endpoints carry this timestamp.
- Scope is **only** the ratified BTC YES-token CLOB book evidence.

## Section 2 — Strict Type & Parsing Law

- `$.timestamp` arrived as a **string**, not a JSON int.
- Future implementation must use **exact integer-string parsing**. Allowed lexical form is pinned:
  - ASCII digits only, regex `^[0-9]+$`;
  - no sign; no decimal point; no exponent; no whitespace; no thousands separators; no locale parsing;
    no empty string; no NaN/Infinity.
- **Direct `float` / `float64` conversion is forbidden.**
- Implicit coercion is forbidden.
- Rounding / truncation / scientific-notation rewriting is forbidden.
- Parsing must be **lossless** and must preserve exact decimal digits before converting to an integer
  timestamp representation.
- If parsing fails, future code must **fail closed**.
- This charter does **not** implement parsing; it only ratifies the law.

## Section 3 — Epoch Unit Manual Binding

```
binding_authority              = MANUAL_TIME_UNIT_BINDING
polymarket_clob_timestamp_path = $.timestamp
polymarket_clob_timestamp_unit = epoch_milliseconds
observed_value                 = "1782189645718"
```

- `epoch_milliseconds` is a **manual / operator architectural binding**, **not** self-describing in JSON
  and **not** inferred merely from magnitude.
- **Do not** infer milliseconds from 13 digits alone.
- **Do not** bind nanoseconds / microseconds / seconds.
- Future implementation must **fail closed** if the unit binding is absent, changed, or ambiguous.

## Section 4 — Anti-Substitution Reinforcement

- `retrieval_started_epoch_ms` and `retrieval_completed_epoch_ms` remain **collector-side forensic
  metadata only**.
- They must **never** substitute for `$.timestamp`.
- They must **never** be used for Polymarket event time.
- They must **never** be used for cross-source alignment with Hyperliquid `$.time`.
- Any future pair construction using retrieval time as source event time must **fail closed**.

## Section 5 — B2 Polymarket-Side Authority Boundary

- This charter, **if ratified**, may change:
  - Polymarket timestamp binding: **PENDING → RATIFIED** for this scoped YES-token CLOB source;
  - Polymarket-side B2 source-time authority: **RATIFIED** for path `$.timestamp` with the exact
    integer-string + epoch-ms law.
- This does **not** by itself make full paired B2 projection runtime-eligible.
- Full B2 paired alignment **still requires**:
  - a ratified Hyperliquid `$.time` epoch-ms binding;
  - a ratified Polymarket `$.timestamp` epoch-ms binding;
  - `max_cross_source_event_time_delta_ms = 1000`;
  - a future exact DTO / failure-surface / runtime implementation;
  - fail-closed tests.
- Cross-source alignment remains **unimplemented**.
- **Projection / S1 remains BLOCKED.**

## Section 6 — Explicit Denials

This charter denies all of:

- S1 ingestion / projection;
- DTO / schema / runtime / DDL changes;
- parsing implementation;
- cross-source alignment implementation;
- another capture;
- network calls;
- NO-token timestamp authority;
- Gamma timestamp authority;
- retrieval-time substitution;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 7 — Next Gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, the next safe **docs-only** gate is an **S1 Projection DTO / Failure-Surface Charter**.
3. That later charter must still **separately** define:
   - exact DTO fields;
   - exact validation / failure codes;
   - exact no-float / no-coercion tests;
   - exact integer-string timestamp parser tests;
   - exact `Decimal` `px`/`sz` parser tests;
   - exact paired-state guards;
   - exact cross-source delta enforcement;
   - exact stale-pair rejection;
   - no scheduler;
   - no trading / actionability.
4. Runtime / TDD remains **blocked** until that later charter is ratified.

## Post-state

- Polymarket CLOB Timestamp Authority Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex
  review.
- Polymarket CLOB YES-token field-authority audit: **COMPLETE**.
- Polymarket CLOB YES-token physical capture: **COMPLETE**.
- Until ratified: Polymarket timestamp binding: **PENDING**.
- Until ratified: **B2 remains BLOCKED**.
- If later ratified: Polymarket-side B2 timestamp authority may be **RATIFIED**, but **Projection / S1
  remains BLOCKED** pending future DTO / failure-surface / runtime authorization.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
