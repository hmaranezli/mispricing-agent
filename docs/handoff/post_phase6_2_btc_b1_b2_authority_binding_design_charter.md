# Post-Phase 6.2 BTC B1/B2 Authority-Binding Design Charter — Top-of-Book / Manual Side Axiom / Epoch-ms Time Binding

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It may *propose* authority-binding rules, but it **does not implement** them.
- It grants **no** runtime execution, **no** network, **no** new capture, **no** S1 ingestion/projection,
  **no** scheduler, **no** calibration, **no** trading/actionability, **no** capacity increase.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **RATIFIED**.
- l2Book physical capture: **COMPLETE**. l2Book field-authority audit: **COMPLETE**.
- l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter: **RATIFIED**.
- Until this charter is independently ratified, **B1 remains BLOCKED** and **B2 remains BLOCKED**.
- Projection / S1: **BLOCKED**. Capacity: **0**.

## Source basis

- RATIFIED BTC Market/Instrument Binding Charter.
- RATIFIED l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter.
- l2Book capture/audit evidence:
  - `source_authority = HYPERLIQUID_L2_BOOK_BY_COIN_V1`
  - `response_body_sha256 = a0093a5be765dabb3df9df2f7716046c2bcf54efe65d3ba4e4c9c3f4b17d752d`
  - top-level keys = `['coin', 'time', 'levels']`; `$.coin = 'BTC'` (string); `$.time = 1782184456289` (int)
  - `$.levels` = array length 2; `$.levels[0]` = length 20; `$.levels[1]` = length 20
  - per-level shape = `{'px': string, 'sz': string, 'n': int}`
  - **no explicit bid/ask side labels** in the JSON; no prior B1/B2 authority proven by shape alone.

## Core design decision — narrowest B1

Use the **narrowest** B1 design: **top-of-book only**. This charter does **not** authorize:
full-book depth, level summation, VWAP, notional-depth aggregation, mid-price, impact-price
calculation, or any synthetic orderbook metric.

---

## Section 1 — Decimal Parsing Law

- Hyperliquid l2Book `px` and `sz` are **exact source strings**, not JSON numbers.
- Future S1/projection/formula code, **if separately authorized later**, must parse `px` and `sz` using
  **precision-preserving decimal** semantics.
- **Direct IEEE 754 `float` / `float64` conversion is forbidden.**
- **Implicit numeric coercion is forbidden.**
- Rounding, truncation, locale parsing, scientific-notation rewriting, and binary floating arithmetic are
  **forbidden**.
- `decimal.Decimal` (Python) or an equivalent exact decimal type is the **required class of
  implementation** — but this charter **does not implement code**.
- `n` is a JSON int and may be treated only as an **order-count candidate**; `n` does **not** create
  magnitude authority by itself.
- Any parse failure, non-string `px`/`sz`, non-int `n`, empty string, malformed decimal, NaN/Infinity,
  negative size where not explicitly allowed, or unexpected exponent/format must **fail closed** in future
  code.

## Section 2 — Positional Side Axiom

- The audited JSON contains **no explicit bid/ask side labels**.
- Therefore `levels[0]` / `levels[1]` side interpretation is **not** a directly observed JSON fact.
- Proposed manual axiom (operator-owned, risk-accepted; **not** inferred by code):

  ```
  binding_authority                    = MANUAL_AXIOM
  hyperliquid_l2book_levels_0_side     = BID
  hyperliquid_l2book_levels_1_side     = ASK
  ```

- Future runtime/projection must **fail closed** if:
  - `levels` is not length 2;
  - either side array is empty when top-of-book is required;
  - per-level keys are not exactly/at least `px`, `sz`, `n` as required by the future implementation
    charter;
  - `px`/`sz`/`n` types diverge from the audited shape;
  - side arrays cannot be interpreted under this axiom.
- This charter **proposes** the axiom but **does not implement** it. Until ratified, **side authority
  remains BLOCKED**.

## Section 3 — B1 Gross-Magnitude Formula (Top-of-Book only)

- Proposed narrow B1 authority = **top-of-book only**, under the manual side axiom (§2).
- Candidate source paths:

  ```
  best_bid_px_source          = $.levels[0][0].px
  best_bid_sz_source          = $.levels[0][0].sz
  best_ask_px_source          = $.levels[1][0].px
  best_ask_sz_source          = $.levels[1][0].sz
  best_bid_order_count_source = $.levels[0][0].n
  best_ask_order_count_source = $.levels[1][0].n
  ```

- **Only level index 0 on each side is in-scope.** `levels[0][1:]` and `levels[1][1:]` are explicitly
  **out-of-scope / discarded for B1** in this charter.
- Do **not** compute: book depth, total size, notional depth, weighted-average price, mid price, spread
  (unless a future charter separately authorizes it), or cross-venue gross-edge (yet).
- This charter may define source-authority paths for top-of-book price/size, but must **not** declare S1
  projection eligible.
- **B1 remains BLOCKED** until this charter is independently ratified **and** a later S1
  projection/runtime charter is separately authorized.

## Section 4 — Time Unit & Alignment Law

- Proposed time-unit binding (manual/operator; **not** self-describing in JSON and **not** inferred from
  magnitude):

  ```
  binding_authority                = MANUAL_TIME_UNIT_BINDING
  hyperliquid_l2book_time_path     = $.time
  hyperliquid_l2book_time_unit     = epoch_milliseconds
  observed_value                   = 1782184456289
  ```

- Retrieval timestamps must **never** substitute for source event time.
- Future code must **reject** missing `$.time`, non-int `$.time`, negative time, or values outside
  separately-ratified admissible bounds.
- **Cross-source alignment is the B2 lock:** a future paired observation must contain a Polymarket
  source-issued timestamp **and** a Hyperliquid l2Book source-issued `$.time`.
- Proposed initial maximum cross-source delta:

  ```
  max_cross_source_event_time_delta_ms = 1000
  ```

- If `abs(polymarket_event_time_ms - hyperliquid_l2book_time_ms) > 1000`, the pair is **stale/invalid**
  and must **fail closed**.
- If either timestamp is missing, non-source-issued, unit-ambiguous, unparsable, or not manually bound to
  epoch milliseconds, the pair must **fail closed**.
- This charter does **not** authorize the Polymarket timestamp source path unless already separately
  ratified; it is **not** separately ratified at this time, so **Polymarket timestamp binding = PENDING**
  (its exact source path/unit must be proven and bound by a separate ratified charter before any pairing).
- **B2 remains BLOCKED** until this charter is independently ratified **and** a future
  projection/runtime charter enforces the alignment law.

## Section 5 — B3 / identity boundary

- BTC identity remains governed by the **RATIFIED manual BTC binding**.
- This charter does **not** change Polymarket token IDs, `conditionId`, `slug`, or the Option-B mapping.
- **No** new coin inference, aliasing, normalization, or discovery is authorized.

## Section 6 — Explicit denials

This charter denies all of:

- runtime / network authorization;
- another capture;
- S1 ingestion / projection;
- implementation of decimal parsing;
- implementation of the side axiom;
- implementation of time alignment;
- implementation of formula computation;
- cross-venue gross-edge computation;
- trading / actionability / ranking / advice;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- capacity increase.

## Section 7 — Next gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, a separate **S1 Projection Eligibility Charter** may be drafted. That later charter must
   still **separately** authorize:
   - exact DTO fields;
   - fail-closed validation;
   - the `Decimal` parse implementation;
   - side-axiom enforcement;
   - time-unit enforcement;
   - cross-source delta enforcement;
   - no-float tests;
   - stale-pair rejection tests;
   - no scheduler;
   - no trading/actionability.
3. **No runtime / S1 work before those gates.**

## Post-state

- BTC B1/B2 Authority-Binding Design Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex
  review.
- l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter: **RATIFIED**.
- l2Book runtime: **RATIFIED**.
- l2Book physical capture: **COMPLETE**.
- l2Book field-authority audit: **COMPLETE**.
- B1: **BLOCKED** until this charter is ratified and later S1/projection is separately authorized.
- B2: **BLOCKED** until this charter is ratified and later S1/projection is separately authorized.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
