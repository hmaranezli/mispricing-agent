# Post-Phase 6.2 BTC S1 Projection Runtime TDD Charter — Paired Raw-Ledger Inputs / Decimal / Epoch-ms / Fail-Closed

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
- **Docs-only.** It defines a **future RED→GREEN TDD plan only**.
- It does **not** implement runtime / S1 / projection / schema / parsers / tests.
- It writes **no** DTO, **no** DDL, **no** ingestion function, **no** fixtures.
- It grants **no** network, **no** capture, **no** ledger access, **no** scheduler, **no** calibration,
  **no** trading/actionability, **no** capacity increase.
- **Projection / S1 ingestion runtime remains BLOCKED** until this charter is ratified **and** a separate
  implementation command is given.
- Calibration / scheduler / continuous collection remain **BLOCKED**.
- Capacity remains **0**.

## Source basis

- RATIFIED S1 Projection DTO / Failure-Surface Charter.
- RATIFIED Polymarket CLOB Timestamp Authority Charter.
- RATIFIED BTC S1 Projection Eligibility Charter.
- RATIFIED BTC B1/B2 Authority-Binding Design Charter.
- RATIFIED l2Book and CLOB raw evidence chain:
  - Polymarket CLOB YES timestamp authority: `$.timestamp`, exact integer-string, `epoch_milliseconds`,
    capture sha `3b9b74e23a9dc796a6e1d9baa7994531550f74b3a6c70353b95690d4d9b25940`.
  - Hyperliquid l2Book: `$.time` int (`epoch_milliseconds` manual binding), `levels[0]=BID` /
    `levels[1]=ASK` manual axiom, top-of-book only, `px`/`sz` exact source strings, capture sha
    `a0093a5be765dabb3df9df2f7716046c2bcf54efe65d3ba4e4c9c3f4b17d752d`.
  - `max_cross_source_event_time_delta_ms = 1000`.

This charter defines the **non-negotiable tests and TDD ordering** for a future, separately-commanded S1
projection implementation. It implements nothing and authorizes no runtime.

---

## Section 1 — Strict RED→GREEN TDD Order

- The future implementer must first write **failing RED tests** for **every** rule in this charter.
- **RED evidence must be shown** (test output proving the test fails for the correct missing-behavior
  reason) **before** any production code changes.
- Only **after** RED is proven may production code be written.
- GREEN must include **focused tests** and **selected regressions**.
- **No "make it pass" shortcut may relax a ratified charter.** A test must never be weakened to fit
  convenient code.
- If an existing schema/charter prevents GREEN, the implementer must **STOP** and request a **docs-only
  amendment first** — never mutate a ratified locked artifact to force GREEN.

## Section 2 — Zero-Network Test Boundary

- S1 projection tests must **not** mock HTTP, because this module must **not** touch the network at all.
- Forbidden in these tests: `aioresponses`, `localhost`, `requests` / `httpx` / `urllib`, fake web
  servers, or any socket-level stand-in.
- Test inputs must be **locked `raw_capture.sqlite3` ledger rows** or **minimal in-memory SQLite
  fixtures** that faithfully mirror the ratified raw-ledger row shape.
- The future projection reads **only already-captured raw ledgers**:
  - Hyperliquid l2Book raw ledger;
  - Polymarket CLOB YES raw ledger.
- **No** live acquisition, **no** scheduler, **no** API-client invocation anywhere in the projection path
  or its tests.

## Section 3 — Type Identity Tests

- Tests must assert **type identity**, not only value equality.
- `px` / `sz` projection fields must be **`Decimal` instances**.
- timestamp fields must be **`int`** after exact integer-string parse.
- order count `n` must be **`int`**.
- **Any `float` anywhere** in projected price / size / time fields must **fail**.
- Tests must explicitly **reject**:
  - `float`;
  - `Decimal` created from `float`;
  - implicit coercion;
  - rounded / truncated value;
  - scientific-notation rewriting;
  - locale parsing;
  - whitespace;
  - signed timestamp;
  - decimal timestamp;
  - exponent timestamp;
  - NaN / Infinity.

## Section 4 — Boundary Condition Matrix for 1000ms Alignment

Future RED tests must include **exactly**:

- `delta == 999ms` → **accepted**;
- `delta == 1000ms` → **accepted**;
- `delta == 1001ms` → **fail closed**;
- `polymarket_time_ms > hyperliquid_time_ms` by valid abs delta → **accepted if `abs(delta) <= 1000`**;
- `hyperliquid_time_ms > polymarket_time_ms` by valid abs delta → **accepted if `abs(delta) <= 1000`**;
- negative raw timestamp value → **fail closed**;
- missing timestamp on either side → **fail closed**;
- retrieval-timestamp substitution attempt → **fail closed**.

Important:

- **Do not** define `delta < 0` as a failure when delta is computed as `abs(poly_ms - hl_ms)`.
- Instead, **raw negative timestamp values** and **retrieval-time substitution** are the failures.
- If a future charter wants **directional ordering**, it must be **separately ratified**; this charter
  uses **absolute delta**.

## Section 5 — Provenance Linkage / No Orphan Data

Future tests must require **every** projected S1 row to carry explicit provenance references:

- `polymarket_source_authority`;
- `polymarket_capture_sequence`;
- `polymarket_response_body_sha256`;
- `hyperliquid_source_authority`;
- `hyperliquid_capture_sequence`;
- `hyperliquid_response_body_sha256`;
- binding-authority references for:
  - BTC market/instrument binding;
  - Polymarket timestamp authority;
  - Hyperliquid l2Book side / time / B1 authority;
  - S1 Projection DTO / Failure-Surface Charter.
- A projected row **missing either raw-capture reference** must **fail closed**.
- A projected row with **SHA mismatch** must **fail closed**.
- **No orphaned S1 projection row is permitted.**

## Section 6 — Paired-State Guards

Future RED tests must prove:

- valid l2Book + missing CLOB → **fail closed**;
- valid CLOB + missing l2Book → **fail closed**;
- valid l2Book + CLOB with missing timestamp → **fail closed**;
- valid CLOB timestamp + l2Book missing `$.time` → **fail closed**;
- stale pair `delta > 1000ms` → **fail closed**;
- wrong Polymarket `token_id` → **fail closed**;
- wrong Hyperliquid `coin` → **fail closed**;
- wrong `source_authority` on either side → **fail closed**;
- attempt to use Gamma retrieval time → **fail closed**;
- attempt to use CLOB retrieval time → **fail closed**;
- attempt to use l2Book retrieval time → **fail closed**.

## Section 7 — Top-of-Book and Side Axiom Tests

Future RED tests must enforce:

- `levels[0][0]` maps **only** to BID top-of-book;
- `levels[1][0]` maps **only** to ASK top-of-book;
- deeper levels are **not** used;
- missing `levels[0][0]` or `levels[1][0]` → **fail closed**;
- malformed `levels` length → **fail closed**;
- `px` / `sz` type divergence → **fail closed**;
- `n` type divergence → **fail closed**;
- **no** depth / sum / VWAP / mid / spread / notional / cross-edge fields are produced.

## Section 8 — Failure Surface

Future tests must assert **exact failure literals** from the ratified DTO / Failure-Surface Charter,
including:

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

- Tests must assert the **exact literal**, not a substring or a generic exception type.
- Each literal denotes a **fail-closed** outcome; none denotes a recoverable best-effort fallback.

## Section 9 — Explicit Denials

This charter denies all of:

- runtime / S1 / projection implementation;
- DTO class creation;
- schema / DDL change;
- parser implementation;
- fixture / test authoring (this charter only **specifies** required tests; it does not write them);
- network / capture / ledger access;
- scheduler / continuous collection;
- calibration / Phase 7.1 / 7.2 / 8.1;
- trading / actionability / ranking / advice;
- capacity increase.

## Section 10 — Next Gates

1. Independent Gemini + Codex review of this charter.
2. If ratified, a **separate explicit implementation command** may authorize the strict RED→GREEN TDD
   build of the S1 projection module, under exactly this test plan.
3. The implementer must, in order:
   - write and show **RED** evidence for every rule above;
   - write **minimal** production code to reach **GREEN**;
   - run focused tests plus selected regressions;
   - STOP and request a docs-only amendment if any ratified charter blocks GREEN.
4. **Runtime remains BLOCKED** until this charter is ratified **and** that separate implementation command
   is issued.

## Post-state

- S1 Projection Runtime TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex review.
- S1 Projection DTO / Failure-Surface Charter: **RATIFIED**.
- Polymarket-side timestamp authority: **RATIFIED**.
- Full paired B2 design: **docs-ratified only**, runtime **BLOCKED**.
- Projection / S1 ingestion runtime: **BLOCKED**.
- Calibration / scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
