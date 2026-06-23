# Post-Phase 6.2 BTC S1 Projection DTO / Failure-Surface Charter — Paired Top-of-Book / Epoch-ms / Fail-Closed

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines **future DTO / failure-surface requirements only**.
- It does **not** implement DTO / runtime / S1 / projection / parsing.
- It defines **no** code, **no** schema, **no** DDL, **no** ingestion function.
- It grants **no** network, **no** capture, **no** ledger access, **no** scheduler, **no** calibration,
  **no** trading/actionability, **no** capacity increase.
- **Projection / S1 ingestion remains BLOCKED.**
- Calibration / scheduler / continuous collection remain **BLOCKED**.
- Capacity remains **0**.

## Source basis

- RATIFIED Polymarket CLOB Timestamp Authority Charter.
- RATIFIED BTC S1 Projection Eligibility Charter.
- RATIFIED BTC B1/B2 Authority-Binding Design Charter.
- RATIFIED l2Book candidate / authority chain.
- Polymarket CLOB YES timestamp authority:
  - `timestamp_path = $.timestamp`
  - `timestamp_source_type = exact integer-string`
  - `timestamp_unit = epoch_milliseconds` (manual binding)
  - `observed_value = "1782189645718"`
  - `response_body_sha256 = 3b9b74e23a9dc796a6e1d9baa7994531550f74b3a6c70353b95690d4d9b25940`
- Hyperliquid l2Book evidence:
  - `time_path = $.time`, type **int**, `time_unit = epoch_milliseconds` (manual binding)
  - `levels[0] = BID`, `levels[1] = ASK` (manual axiom), **top-of-book only**
  - `px` / `sz` are **exact source strings**
  - `response_body_sha256 = a0093a5be765dabb3df9df2f7716046c2bcf54efe65d3ba4e4c9c3f4b17d752d`
- `max_cross_source_event_time_delta_ms = 1000`.

This charter sets the **DTO requirements and failure-surface literals** under which a future,
separately-authorized and separately-commanded projection layer *could* be implemented via strict
RED→GREEN TDD. It implements nothing and authorizes no runtime.

---

## Section 1 — Future DTO Conceptual Shape

The following are **proposed DTO field requirements at charter level only**. They are **not** implemented
code, **not** a class, **not** a schema, **not** field-name locks for any storage table. Final names,
types, ordering, and storage representation must be **separately chartered and ratified** by the future
TDD charter.

```
polymarket_source_authority
polymarket_token_id
polymarket_outcome_label
polymarket_timestamp_ms
polymarket_timestamp_raw_string
polymarket_capture_sha256
hyperliquid_source_authority
hyperliquid_coin
hyperliquid_time_ms
hyperliquid_best_bid_px_decimal
hyperliquid_best_bid_sz_decimal
hyperliquid_best_bid_order_count
hyperliquid_best_ask_px_decimal
hyperliquid_best_ask_sz_decimal
hyperliquid_best_ask_order_count
hyperliquid_capture_sha256
event_time_delta_ms
binding_authority_references
provenance_references
```

- `polymarket_timestamp_raw_string` must retain the **exact source string**; `polymarket_timestamp_ms` is
  the parsed integer derived under §2.
- `hyperliquid_best_*_px_decimal` / `*_sz_decimal` must retain **precision-preserving decimal** semantics,
  never IEEE-754 floats.
- `*_capture_sha256` fields are **provenance anchors** back to the ratified raw-evidence captures.
- `binding_authority_references` and `provenance_references` are **conceptual lineage pointers** (manual
  bindings, axioms, ratified charters, capture SHAs), not free-form text.
- **These names are proposed DTO requirements, not implemented code.**

## Section 2 — Parsing Laws

- Polymarket timestamp must parse from an **exact integer string**, regex `^[0-9]+$`:
  - ASCII digits only; no sign; no decimal point; no exponent; no whitespace; no thousands separators; no
    locale parsing; no empty string; no NaN/Infinity.
- Hyperliquid `$.time` must be a **JSON int**.
- Hyperliquid `px` / `sz` must parse with **precision-preserving `Decimal` only**.
- **Direct `float` / `float64` conversion is forbidden.**
- Implicit coercion, rounding, truncation, scientific-notation rewriting, and locale parsing are
  **forbidden**.
- Parsing must be **lossless**.
- **Any parse ambiguity fails closed.**
- This charter does **not** implement parsing; it only ratifies the laws.

## Section 3 — Pairing and Alignment

- A projection candidate requires **both**:
  - Polymarket CLOB YES-token evidence, **and**
  - Hyperliquid l2Book evidence.
- Both source times must be **epoch milliseconds**.
- `event_time_delta_ms = abs(polymarket_timestamp_ms - hyperliquid_time_ms)`.
- The pair is eligible **only if** `event_time_delta_ms <= 1000`.
- The pair must **fail closed** on any of:
  - missing side;
  - missing timestamp;
  - wrong / ambiguous unit;
  - parse failure;
  - `event_time_delta_ms > 1000`.
- **Retrieval timestamps must never substitute** for source-issued event time, and must never be used for
  cross-source alignment.

## Section 4 — Top-of-Book Only

- Use **only** Hyperliquid `levels[0][0]` (BID) and `levels[1][0]` (ASK):

  ```
  best_bid_px_source          = $.levels[0][0].px
  best_bid_sz_source          = $.levels[0][0].sz
  best_bid_order_count_source = $.levels[0][0].n
  best_ask_px_source          = $.levels[1][0].px
  best_ask_sz_source          = $.levels[1][0].sz
  best_ask_order_count_source = $.levels[1][0].n
  ```

- `levels[0] = BID` and `levels[1] = ASK` is a **ratified manual axiom, not a JSON fact**.
- `levels[0][1:]` and `levels[1][1:]` are **out-of-scope / discarded**.
- **No** depth, summation, VWAP, mid, spread, notional, cross-edge, or trading signal.
- Future code must **fail closed** if `levels` shape, side arrays, per-level keys, or `px`/`sz`/`n` types
  diverge from the audited/ratified constraints.

## Section 5 — Failure Surface

The following are **future failure-code literals at docs level only**. They are **design targets**, not
implemented enums, exceptions, or strings. No implementation is authorized.

```
S1_PAIR_POLYMARKET_EVIDENCE_MISSING
S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING
S1_POLYMARKET_TIMESTAMP_MISSING
S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED
S1_HYPERLIQUID_TIME_MISSING
S1_HYPERLIQUID_TIME_REJECTED
S1_TIME_DELTA_EXCEEDS_1000_MS
S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED
S1_HYPERLIQUID_SIDE_AXIOM_REJECTED
S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED
S1_PROVENANCE_SHA_MISMATCH
S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED
```

- Each literal denotes a **fail-closed** outcome; none denotes a recoverable best-effort fallback.
- **These literals are design targets only; no implementation is authorized.**

## Section 6 — Explicit Denials

This charter denies all of:

- runtime / S1 implementation;
- schema / DDL change;
- actual DTO class creation;
- parsing implementation;
- network / capture / ledger access;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 7 — Next Gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, the next gate may be a **strict RED→GREEN TDD charter for S1 projection implementation**.
3. That later charter must still **separately** define and prove:
   - exact DTO fields / types;
   - exact validation and failure-code literals;
   - exact no-float / no-coercion tests;
   - exact integer-string timestamp parser tests;
   - exact `Decimal` `px`/`sz` parser tests;
   - exact paired-state guards;
   - exact cross-source delta enforcement;
   - exact stale-pair rejection;
   - exact provenance-SHA checks;
   - no scheduler;
   - no trading / actionability.
4. **Runtime remains blocked** until that separate TDD charter is ratified **and** explicitly commanded.

## Post-state

- S1 Projection DTO / Failure-Surface Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex
  review.
- Polymarket-side timestamp authority: **RATIFIED**.
- Full paired B2 design: **docs-ratified only**, runtime **BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
