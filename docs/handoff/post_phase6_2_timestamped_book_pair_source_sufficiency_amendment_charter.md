# Post-Phase 6.2 — Timestamped Book-Pair Source-Sufficiency Amendment Charter

> Status: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
> This is a **docs-only** amendment. It authorizes **no** implementation, **no** further network
> request, **no** projection, and **no** S1 ingestion. It selects, at a categorical level only, the
> timestamp-bearing public book-source direction that must be acquired and audited before B1–B3
> projection can even be *designed*.

---

## 0. Anchor and provenance

- Runtime commit (exact base): `8c4313e511d4667dc3cad6d0f006a282ef8af83f`.
- Governing parent charter (RATIFIED): `docs/handoff/post_phase6_2_public_source_authority_raw_capture_ledger_exact_shape_charter.md`.
- Evidence sample under audit: RAW capture `capture_sequence = 1`,
  `source_authority = HYPERLIQUID_META_AND_ASSET_CTXS_V1`,
  `response_body_sha256 = 7a572197f40ffb854f724747cb88abf6dd21f9128e2925374efe09c75c0b1fc9`.
- Data collection: **STARTED** with exactly one RAW_CAPTURED sample.
- S1 ledger: **absent / untouched**.

This amendment is a written record of an evidence result plus a *direction selection*. It does not
move money, does not open a connection, and does not bind any concrete instrument.

---

## 1. Evidence result that motivates this amendment

The offline, read-only field-authority audit of `capture_sequence = 1` established:

1. **No source-issued event timestamp.** The `metaAndAssetCtxs` body is a 2-element array
   `[meta, assetCtxs]`. Neither the top-level object (`universe`, `marginTables`, `collateralToken`),
   nor any `universe[i]` metadata entry, nor any `assetCtxs[i]` context entry carries a source-issued
   event time/epoch field. The only key whose name superficially matched a time token was
   `collateralToken` (an integer asset-id token, semantically not a time value).
2. **B1 remains BLOCKED.** Magnitude-related candidate fields exist (`openInterest`, `dayNtlVlm`,
   `dayBaseVlm`, `prevDayPx`, `oraclePx`, `markPx`, `midPx`, `impactPxs`, `funding`, `premium`), all
   carried as JSON **string** scalars (with `impactPxs` a 2-element string array). Existence does not
   confer gross-magnitude authority.
3. **Hyperliquid source identifier evidence is PROVEN (meta side only).** Identifier path is
   `$[0].universe[i].name` (string, present in all entries; 230 distinct identifiers in the captured
   sample). The `assetCtxs` array carries no embedded identifier and is joined to `universe`
   **positionally by index** under an equal-cardinality contract.
4. **Option-B canonical venue/pair mapping remains BLOCKED.**

**Conclusion:** `metaAndAssetCtxs` is *source-insufficient for B2*. It cannot anchor any event-time
reasoning because it issues no event timestamp. A timestamp-bearing book source is required.

---

## 2. Selected book-pair direction (categorical only)

This amendment selects a **pair of timestamp-bearing public order-book sources**, one per venue. The
selection is categorical/directional; it pins no instrument, no coin, no token, and authorizes no
request.

### 2.1 Existing source (already a ratified runtime variant)

```
POLYMARKET_CLOB_BOOK_BY_TOKEN_V1
GET https://clob.polymarket.com/book?token_id=<caller-supplied>
```

Official response **authority candidates** (to be confirmed against captured evidence + docs, not
assumed here):

- `market`
- `asset_id`
- `timestamp`
- `bids[].price` / `bids[].size`
- `asks[].price` / `asks[].size`
- `hash`
- `min_order_size`
- `tick_size`
- `last_trade_price`

### 2.2 New candidate source direction (NOT yet a runtime variant)

```
HYPERLIQUID_L2_BOOK_BY_COIN_V1
POST https://api.hyperliquid.xyz/info
```

Logical request shape (illustrative; **not** an executable byte-pinned body):

```json
{"type":"l2Book","coin":<exact-ratified-coin>}
```

- `nSigFigs` and `mantissa` **MUST be omitted**.
- Official response **authority candidates** (to be confirmed, not assumed):
  - `coin`
  - `time`
  - `levels[0][].px` / `sz` / `n`
  - `levels[1][].px` / `sz` / `n`
  - at most 20 levels per side.

### 2.3 Official sources to cite directly

- Hyperliquid Info endpoint: <https://hyperliquid.gitbook.io/Hyperliquid-docs/for-developers/api/info-endpoint>
- Polymarket order book: <https://docs.polymarket.com/api-reference/market-data/get-order-book>

---

## 3. Critical limitations (binding on this amendment)

- This amendment selects a **categorical timestamped book-pair direction only**.
- **Do not** claim either timestamp's exact unit until proven from authoritative documentation **and**
  captured evidence.
- **Do not** claim the two timestamps are automatically comparable.
- **Do not** define `evidence_epoch_tolerance_ms` yet.
- **Do not** authorize retrieval-time substitution.
- **Do not** invent a Hyperliquid coin grammar, a coin value, a Polymarket slug, `token_id`,
  `condition_id`, outcome, or market.
- The new Hyperliquid request body is **not executable** until an exact ratified coin binding exists.
- **No fourth runtime variant** is authorized by this UNRATIFIED docs commit.

---

## 4. B1 status — gross-magnitude authority

- Book `price` / `size` (and any volume / open-interest / depth) fields are **source candidates only**.
- Price, size, volume, open interest, or depth is **not** `gross_magnitude` merely because it exists.
- Repo evidence states `gross_edge_value` is an **already-computed economic edge**, and `observed_size`
  is a **separate** field; neither is re-derived or conflated here.
- **No** subtraction, midpoint, spread, probability conversion, notional calculation, unit conversion,
  side selection, or cross-venue formula is authorized.
- **B1 remains BLOCKED** pending a separate exact economic-derivation and unit-authority charter.

---

## 5. B2 status — event-time sufficiency

- `metaAndAssetCtxs` remains **insufficient** because it carries no source-issued event timestamp.
- The Polymarket book `timestamp` and the Hyperliquid `l2Book` `time` are **selected source-issued
  timestamp candidates**.
- Exact units, semantic meaning, admissibility, tolerance, and cross-source alignment remain
  **BLOCKED** pending captured evidence and ratification.
- Collector retrieval timestamps remain **provenance only** and can **never** substitute for event time.
- **B2 remains BLOCKED.**

---

## 6. B3 status — identifier / canonical mapping

- Hyperliquid **meta** source-side identifier evidence is **PROVEN only**: `universe[i].name` plus
  positional `assetCtxs` alignment.
- Hyperliquid `l2Book` `coin` and Polymarket `market` / `asset_id` are **candidate** source identifiers.
- Option-B venue/pair canonical mapping remains **BLOCKED**.
- **No** case-folding, aliases, fuzzy matching, UI remapping, token inference, or default mapping.
- **No** mapping table or DTO may be invented in this amendment.

---

## 7. Journal discipline

- The existing `raw_processing_journal` schema remains **unchanged**.
- **Do not** name or invent failure-code literals.
- Stage-specific failure taxonomy, attempt-ordinal retry policy, and S1 commit-uncertainty handling
  remain **BLOCKED** for the later projection / S1 charter.
- Raw evidence is **never** deleted or rewritten.
- Projection failure will eventually block S1 output, **not** destroy RAW_CAPTURED evidence — but **no
  projection is authorized here**.

---

## 8. Exact sequencing after independent ratification (evidence-first, mapping-second)

> **Correction (resolves the §8 source-authority paradox):** the prior ordering authored an
> "Exact market/instrument binding charter" *before* any raw Polymarket Gamma/market evidence
> existed. That would have forced the system to invent or hardcode the relationship between `slug`,
> `condition_id`, `outcomes`, `clobTokenIds` / `token_id`, and the eventual Hyperliquid coin — a
> zero-trust / no-invention violation. The sequence below is rewritten so that **captured source
> evidence precedes any mapping**: nothing binds an instrument until the Gamma payload that defines
> those identifiers has itself been durably captured and audited from source.

1. **Gamma raw-evidence acquisition authorization (docs-only, separate, future).** A docs-only
   Polymarket Gamma/markets raw-evidence acquisition authorization/amendment must first be ratified
   for the **already-existing** current runtime variant:

   ```
   POLYMARKET_GAMMA_MARKET_BY_SLUG_V1
   GET https://gamma-api.polymarket.com/markets?slug=<caller-supplied>
   ```

   That step authorizes **only** a separately executed one-shot capture for a **specific
   caller-supplied slug**. It must **not** infer or select a market by search, discovery, or fuzzy
   matching. (This amendment does **not** authorize that Gamma one-shot; it only names this gate.)

2. **Read-only Gamma field-authority audit.** After that one-shot Gamma raw evidence is durably
   captured, perform a read-only field-authority audit of the captured Gamma payload to prove, **if
   present**, the exact source paths and types for:
   - `slug`
   - `condition_id` / `conditionId` (or equivalent source key), if present
   - `outcomes`
   - `clobTokenIds` / `token_id` / `asset_id` relationship, if present
   - any market identifier fields

   The audit must **not** invent missing fields and must **not** normalize, guess, or repair source
   data.

3. **Exact Market/Instrument Binding Charter** — authored **only after** durable Gamma evidence and
   its audit exist. It may bind Polymarket market/token evidence to a Hyperliquid coin **only from
   captured source evidence and ratified closed mapping rules**. No heuristic mapping, UI assumption,
   case-folding, aliasing, fuzzy match, or hardcoded relationship.

4. **New Hyperliquid `l2Book` raw-acquisition amendment** — authored **only after** the binding
   charter is ratified. It may then pin:

   ```
   HYPERLIQUID_L2_BOOK_BY_COIN_V1
   POST https://api.hyperliquid.xyz/info
   body {"type":"l2Book","coin":<exact-ratified-coin>}   # nSigFigs / mantissa omitted
   ```

   Until then, `l2Book` remains **UNBUILT + BLOCKED** and **no fourth runtime variant** is authorized.

5. **Timestamped book captures + offline audit** — only after those timestamped captures are
   separately authorized and executed may an offline field-authority audit prove timestamp
   units/shapes and book-side semantics.

6. **Exact B1 economic formula/unit + B2 tolerance + B3 canonical mapping charter** — only after the
   audits of step 5.

7. **Projection / S1-ingestion TDD** — eligible only after B1–B3 ratification.

### 8.1 Explicit denials carried by this correction

- This amendment remains **docs-only**.
- This correction does **not** authorize a network request.
- This correction does **not** authorize the Gamma one-shot itself; it only fixes the required
  ordering and names the next evidence-first gate (step 1).
- This correction does **not** authorize the `l2Book` runtime or a fourth raw runtime variant.
- This correction does **not** authorize projection, S1 ingestion, calibration, scheduler, continuous
  collection, paper, live, or HYPOTHETICAL_OUTCOME.
- **B1 remains BLOCKED.**
- **B2 remains BLOCKED.**
- **B3** source-side Hyperliquid **meta** evidence remains **PROVEN only on the meta side**; B3
  **canonical mapping remains BLOCKED**.
- Data collection remains **STARTED** with exactly one RAW_CAPTURED sample.
- Capacity remains **0**.

---

## 9. Post-state

- This amendment charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex review.
- Existing Source-Authority / Raw-Ledger charter: **RATIFIED**.
- Existing raw one-shot runtime: **RATIFIED for its current three variants only**.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **UNBUILT + BLOCKED**.
- Data collection: **STARTED** with exactly one RAW_CAPTURED sample.
- Projection / S1 ingestion: **BLOCKED**.
- HYPOTHETICAL_OUTCOME: **BLOCKED**.
- Calibration and Phase 7.1 / 7.2 / 8.1: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
