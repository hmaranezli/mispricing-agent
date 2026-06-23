# Post-Phase 6.2 Hyperliquid BTC l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter

## 1. Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It grants **no** runtime, **no** network, **no** S1/projection, **no** scheduler, **no**
  calibration, **no** capacity.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **RATIFIED**.
- l2Book physical capture: **COMPLETE**.
- l2Book field-authority audit: **COMPLETE**.
- B1: **BLOCKED**. B2: **BLOCKED**. Projection / S1 ingestion: **BLOCKED**. Capacity: **0**.

This document records, from completed read-only evidence, the *candidate* source paths for an eventual
B1 (gross-magnitude) and B2 (event-time) authority. It selects **no** formula, **no** unit, **no** side,
and authorizes **no** implementation.

---

## 2. Evidence

**Capture (read-only, complete):**

- `source_authority = HYPERLIQUID_L2_BOOK_BY_COIN_V1`
- request = `POST https://api.hyperliquid.xyz/info`
- `request_body = b'{"type":"l2Book","coin":"BTC"}'`
- `response_body_sha256 = a0093a5be765dabb3df9df2f7716046c2bcf54efe65d3ba4e4c9c3f4b17d752d`
- response_body length = `1583` bytes; transport encoding = **identity** (not gzip)
- `raw_capture_log = 1`, `raw_fetch_attempt_log = 1`, `raw_processing_journal = 0`
- S1 absent / untouched.

**Read-only field-authority audit (complete):**

- top-level JSON type = **object**; ordered top-level keys = `['coin', 'time', 'levels']`
- duplicate-key result = **NONE**
- `$.coin` = string `'BTC'`
- `$.time` = int `1782184456289`
- `$.levels` = array length `2`
- `$.levels[0]` = array length `20`; `$.levels[1]` = array length `20`
- `$.levels[0][0]` object keys `['px','sz','n']` → `px` string, `sz` string, `n` int
- `$.levels[1][0]` object keys `['px','sz','n']` → `px` string, `sz` string, `n` int
- timestamp-candidate keys = `[('$.time', 'int')]`
- **no explicit bid/ask side labels** observed; only positional `levels[0]` / `levels[1]`
- no arithmetic, no depth/notional/magnitude, no string-number normalization performed
- pre/post SHA unchanged; no body dump; no writes; no projection; no S1.

> No value beyond the audit is invented here; the full response body is not reproduced.

---

## 3. Strict candidate-status rule

- `time`, `levels`, `px`, `sz`, `n` are **candidate source paths only**.
- Their existence does **not** authorize: formula selection, time semantics, S1 projection, trading,
  ranking, actionability, scheduler, calibration, or capacity.
- **B1 and B2 remain BLOCKED regardless of field presence.**

---

## 4. B1 candidate section (gross-magnitude)

**Candidate paths (evidence only):**

```
$.levels
$.levels[0][i].px
$.levels[0][i].sz
$.levels[0][i].n
$.levels[1][i].px
$.levels[1][i].sz
$.levels[1][i].n
```

- Path/type/shape evidence: `px` **string**, `sz` **string**, `n` **int**; both `levels` arrays length
  **20** in this capture (`capture_sequence=1`).
- **No** `gross_magnitude` authority.
- **No** orderbook depth / notional / size formula.
- **No** aggregation rule.
- **No** side mapping.
- **No** arithmetic.
- **No** string-number normalization.

---

## 5. String-to-number parse prerequisite

- `px` and `sz` are **exact source strings**, not JSON numbers.
- Any future projection or formula must use **explicit precision-preserving decimal parsing**.
- **Direct `float` / `float64` conversion is forbidden** unless a future separately-ratified charter
  explicitly allows it — which this charter does **not**.
- **No** scientific-notation rewriting, rounding, truncation, BigInt-like reinterpretation, locale
  parsing, or implicit numeric coercion is allowed.
- This charter **does not implement or authorize parsing**; it only records the prerequisite.

---

## 6. Positional side axiom warning

- The observed source provides **no explicit bid/ask side labels**.
- `levels[0]` and `levels[1]` are **positional arrays only**.
- Any future side interpretation must be treated as a **separately-ratified architectural axiom**, not as
  a directly observed JSON fact.
- Until such an axiom is ratified, **side authority remains BLOCKED**.
- If a future axiom is ratified and later source shape violates its guards, the system must **fail closed**.

---

## 7. B2 candidate section (event-time)

**Candidate path (evidence only):** `$.time`

- Type/value evidence: **int** `1782184456289` in `capture_sequence=1`.
- **No** source-issued unit semantics selected.
- **No** self-describing unit observed.
- **Do not** infer milliseconds / microseconds / nanoseconds merely from magnitude.
- **No** tolerance, clock alignment, cross-source alignment, freshness window, or event-time
  admissibility rule selected.
- Retrieval timestamps must **not** substitute for source event time.
- **B2 remains BLOCKED** pending separately-ratified time-unit semantics and alignment/admissibility rules.

---

## 8. B3 / identity boundary

- `$.coin = 'BTC'` is **consistent with** the ratified manual BTC binding, but this charter **does not
  change** the Option-B mapping.
- **No** mapping into S1 or any DTO.
- **No** new coin inference, aliasing, or discovery.

---

## 9. Explicit denials

This charter denies all of:

- runtime / network authorization;
- another capture;
- S1 ingestion / projection;
- parsing implementation;
- formula implementation;
- time-unit binding;
- side-binding;
- bid/ask inference;
- trading / actionability;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- capacity increase.

---

## 10. Next gates

1. Independent review and **ratification of this charter**.
2. Only **after** ratification, a separate **docs-only B1/B2 authority/binding charter** may decide:
   - precision decimal parsing law;
   - the l2Book positional side axiom;
   - the gross-magnitude formula, if any;
   - time-unit semantics;
   - cross-source alignment / tolerance;
   - S1 projection eligibility.
3. **No runtime / S1 work before those gates.**

---

## 11. Post-state

- l2Book Source-Sufficiency / B1-B2 Candidate Authority Charter: **BUILT / RATIFIABLE / UNRATIFIED**
  pending Gemini + Codex review.
- l2Book runtime: **RATIFIED**.
- l2Book physical capture: **COMPLETE**.
- l2Book field-authority audit: **COMPLETE**.
- B1: **BLOCKED**.
- B2: **BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
