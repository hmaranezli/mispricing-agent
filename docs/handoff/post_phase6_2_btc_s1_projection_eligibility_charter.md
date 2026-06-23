# Post-Phase 6.2 BTC S1 Projection Eligibility Charter — Paired-State / Decimal / Top-of-Book / Fail-Closed Gate

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines **eligibility conditions only**.
- It does **not** define an exact DTO shape.
- It does **not** implement projection.
- It does **not** authorize runtime / S1 ingestion.
- It grants **no** network, **no** capture, **no** parsing implementation, **no** scheduler, **no**
  calibration, **no** trading/actionability, **no** capacity increase.
- Projection / S1 ingestion remains **BLOCKED**.
- **B1 remains BLOCKED** for runtime/S1 until a future projection implementation is separately authorized.
- **B2 remains BLOCKED** because the Polymarket timestamp binding is **PENDING**.
- Capacity remains **0**.

## Source basis

- RATIFIED BTC Market/Instrument Binding Charter.
- RATIFIED l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter.
- RATIFIED BTC B1/B2 Authority-Binding Design Charter.
- l2Book runtime **RATIFIED**; l2Book physical capture **COMPLETE**; l2Book field-authority audit
  **COMPLETE**.
- B1/B2 authority design laws ratified at docs level:
  - Decimal parsing law for `px`/`sz`.
  - `MANUAL_AXIOM`: `levels[0] = BID`, `levels[1] = ASK`.
  - Top-of-book-only B1 source selection.
  - `MANUAL_TIME_UNIT_BINDING`: `$.time = epoch_milliseconds`.
  - `max_cross_source_event_time_delta_ms = 1000`.
  - Polymarket timestamp binding = **PENDING**.

This charter sets the **gate conditions** under which a future, separately-authorized projection layer
*could become* eligible to write into S1. It implements nothing and defines no DTO.

---

## Section 1 — Strict Paired-State Requirement

- S1 projection for Option-B requires a **paired cross-source observation**, not a single l2Book
  observation.
- A valid future S1 projection candidate must have **all** of:
  1. Polymarket side evidence for the ratified BTC market/instrument binding;
  2. Hyperliquid l2Book side evidence for the ratified BTC l2Book source;
  3. a **source-issued Polymarket event timestamp**, ratified separately;
  4. a **source-issued Hyperliquid l2Book `$.time`**, ratified as epoch milliseconds;
  5. cross-source event-time delta **≤ 1000 ms**.
- Until the Polymarket timestamp binding is separately ratified, **every** attempted paired projection
  must **fail closed**.
- A lone Hyperliquid l2Book capture, **even with a valid `$.time`**, is **not** S1-eligible.
- Retrieval timestamps must **never** substitute for source-issued event time.
- Missing one side of the pair must **fail closed**.

## Section 2 — Type & Parsing Enforcement

- `px` and `sz` must remain **exact source strings** until the future projection layer applies
  **precision-preserving decimal** parsing.
- Future implementation must use `Decimal` or equivalent exact decimal semantics.
- **Direct `float` / `float64` / binary floating arithmetic is forbidden.**
- Implicit numeric coercion, rounding, truncation, locale parsing, scientific-notation rewriting, and
  lossy normalization are **forbidden**.
- Future tests must include **no-float proofs** and **exact string-preservation proofs** before any S1
  projection can be ratified.
- Any malformed decimal, empty `px`/`sz`, non-string `px`/`sz`, NaN/Infinity, or parse ambiguity must
  **fail closed**.
- This charter does **not** implement parsing and does **not** define DTO fields.

## Section 3 — Boundary & Axiom Strictness

- Future S1 eligibility may use **only** top-of-book source paths:

  ```
  best_bid_px_source          = $.levels[0][0].px
  best_bid_sz_source          = $.levels[0][0].sz
  best_bid_order_count_source = $.levels[0][0].n
  best_ask_px_source          = $.levels[1][0].px
  best_ask_sz_source          = $.levels[1][0].sz
  best_ask_order_count_source = $.levels[1][0].n
  ```

- `levels[0][1:]` and `levels[1][1:]` are **out-of-scope** for S1 eligibility under this charter.
- **No** depth, **no** summation, **no** VWAP, **no** mid, **no** spread, **no** notional depth, **no**
  impact price, **no** synthetic orderbook metric.
- `levels[0] = BID` and `levels[1] = ASK` is a **ratified manual axiom, not a JSON fact**.
- Future implementation must **fail closed** if the `levels` shape, side arrays, per-level keys, or
  `px`/`sz`/`n` types diverge from the audited/ratified constraints.
- Attempts to use deeper levels or non-top-of-book data must be **rejected, not silently ignored**.

## Section 4 — Time Alignment Eligibility

- Hyperliquid l2Book time path: `$.time`
- Hyperliquid l2Book time unit: `epoch_milliseconds`
- Cross-source delta rule:

  ```
  abs(polymarket_event_time_ms - hyperliquid_l2book_time_ms) <= 1000
  ```

- The Polymarket timestamp **path / unit / admissibility is PENDING** and must be ratified **before**
  projection is eligible.
- If the Polymarket timestamp is absent, retrieval-only, non-source-issued, unit-ambiguous, malformed, or
  not ratified, projection must **fail closed**.
- If Hyperliquid `$.time` is missing, non-int, negative, unit-ambiguous, or violates ratified bounds,
  projection must **fail closed**.
- This charter does **not** authorize event-time conversion code.

## Section 5 — Zero DTO / Zero Runtime

- This charter must **not** define final DTO class names, field names, storage table names, schema DDL, or
  runtime interfaces.
- It may name **conceptual eligibility inputs only**.
- The exact DTO shape, the S1 schema/projection operation, and the failure-code literals must be
  **separately chartered and ratified later**.
- **No** Pydantic model, dataclass, SQLite projection schema, or ingestion function is authorized here.

## Section 6 — Explicit denials

This charter denies all of:

- S1 ingestion / projection;
- exact DTO shape;
- schema / DDL change;
- runtime implementation;
- parsing implementation;
- `Decimal` implementation;
- another capture;
- network calls;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- HYPOTHETICAL_OUTCOME runtime;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 7 — Next gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, the next safe **docs-only** gate is a **Polymarket timestamp source-authority
   investigation / charter**, because the Polymarket timestamp binding is **PENDING**.
3. Only **after** the Polymarket timestamp authority is ratified may a future **exact S1 Projection
   DTO / Failure-Surface Charter** be drafted.
4. Runtime / TDD remains **blocked** until those docs gates are ratified.

## Post-state

- BTC S1 Projection Eligibility Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex review.
- BTC B1/B2 Authority-Binding Design Charter: **RATIFIED**.
- l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter: **RATIFIED**.
- l2Book runtime: **RATIFIED**.
- l2Book physical capture: **COMPLETE**.
- l2Book field-authority audit: **COMPLETE**.
- Polymarket timestamp binding: **PENDING**.
- Projection / S1 ingestion: **BLOCKED**.
- B1: **BLOCKED** for runtime/S1 pending future projection authorization.
- B2: **BLOCKED** because the Polymarket timestamp binding is PENDING.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
