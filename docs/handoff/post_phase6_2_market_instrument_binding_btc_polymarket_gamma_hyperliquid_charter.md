# Post-Phase 6.2 — Market/Instrument Binding Charter: BTC (Polymarket Gamma ↔ Hyperliquid)

> Status: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
> **Docs-only.** This charter authorizes **no** runtime implementation, **no** network, **no**
> `l2Book` capture, **no** projection, **no** S1 ingestion, **no** calibration, and **no** scheduler.
> It proposes a single candidate B3 binding from audited Polymarket Gamma source evidence to a
> **manually-ratified hardcoded** Hyperliquid canonical coin candidate. It does **not** prove B1 or B2.

---

## 1. Status and purpose

- **Status:** BUILT / RATIFIABLE / UNRATIFIED pending Gemini + Codex review.
- **Docs-only.** No runtime/test/fixture/config/lock/dependency/generated/tracking/export change.
- Authorizes no runtime implementation, no network, no `l2Book` capture, no projection, no S1
  ingestion, no calibration, no scheduler.
- **Purpose:** define a *candidate* B3 Market/Instrument Binding from the audited Polymarket Gamma
  source evidence (capture_sequence=1) to a **hardcoded Hyperliquid canonical coin candidate: BTC**.
- This charter does **not** prove B1 or B2.

---

## 2. Evidence anchors

- Gamma raw ledger path: `/root/mispricing_gamma_runtime_evidence/raw_capture.sqlite3`
- `capture_sequence = 1`
- `source_authority = POLYMARKET_GAMMA_MARKET_BY_SLUG_V1`
- `request_target = /markets?slug=will-bitcoin-reach-250000-by-december-31-2026-579-442`
- `response_body_sha256 = 04a37c839d617fbb027bde036e2255a3388a087afb8872a6699669532a0cad41`
- The stored body is a **gzip transport entity** (`1f 8b 08 00`, 2355 B); the SHA authority is over the
  exact compressed bytes. JSON inspection used **in-memory decompression only** (inflated 5651 B);
  stored bytes were never modified and nothing decoded was persisted.
- Duplicate keys: **NONE**.
- Top-level JSON shape: **array length 1**; element 0 is a market **object with 90 ordered keys**.
- S1 ledger: **absent / untouched**.

---

## 3. Polymarket source-side evidence (audited, verbatim)

| Field | Source path | Type | Value / shape summary |
|---|---|---|---|
| slug | `$[0].slug` | string(53) | `will-bitcoin-reach-250000-by-december-31-2026-579-442` |
| question | `$[0].question` | string(49) | `"Will Bitcoin reach $250,000 by December 31, 2026?"` |
| conditionId | `$[0].conditionId` | string(66) | `0x6fefc043…1092` (66-char `0x…` hex) |
| questionID | `$[0].questionID` | string(66) | `0xd6de635b…5934` (66-char `0x…` hex) |
| id (market id) | `$[0].id` | string(7) | `"1057883"` |
| active | `$[0].active` | bool | `true` |
| closed | `$[0].closed` | bool | `false` |
| acceptingOrders | `$[0].acceptingOrders` | bool | `true` |
| market | — | — | **ABSENT** |
| marketId | — | — | **ABSENT** |
| outcomes | `$[0].outcomes` | **stringified JSON** scalar | decodes in memory to exactly `["Yes", "No"]` (array len 2, both string) |
| clobTokenIds | `$[0].clobTokenIds` | **stringified JSON** scalar | decodes in memory to exactly **two** string token IDs, **each length 77** |

- **Cardinality:** `len(outcomes) == len(clobTokenIds) == 2`.

### 3.1 Full token extraction — COMPLETE (read-only)

> The prior "full token extraction pending" blocker is **CLOSED**. A separate **read-only** targeted
> extraction has captured the exact full token IDs from the existing Gamma raw ledger.

- **Full token extraction: COMPLETE.**
- Extraction was **read-only** from `/root/mispricing_gamma_runtime_evidence/raw_capture.sqlite3`,
  `capture_sequence=1`.
- **No network, no writes, no S1, no projection, no git changes** occurred during extraction.
- Guarded nested parse **passed** all guards:
  - `outcomes == ["Yes", "No"]`
  - `clobTokenIds` length `== 2`
  - token IDs **distinct**
  - each token ID is a **string**
  - each token ID matches `^[0-9]{1,80}$`
  - each token ID length `== 77`
  - SHA-256 over the original stored bytes **unchanged**:
    `04a37c839d617fbb027bde036e2255a3388a087afb8872a6699669532a0cad41`
- **Exact extracted token IDs (opaque string identities — see the red-line in §7.1):**
  - `polymarket_yes_token_id` =
    `"13433573766910980267981622064090484781359464703732825845886677588040916221533"`
  - `polymarket_no_token_id` =
    `"68320692409850091190490975441025843632582876963922128660910974326175304515755"`
- No token ID is invented; each was read verbatim from source and every digit is preserved exactly.

---

## 4. Critical axiom — parallel source ordering

- The raw JSON does **NOT** contain an explicit key-value object binding outcome labels to token IDs.
- Therefore `outcomes[0] ↔ clobTokenIds[0]` and `outcomes[1] ↔ clobTokenIds[1]` is **NOT** treated as a
  directly observed JSON fact.
- It is a **proposed ratified system axiom for this binding only — the "parallel source ordering
  axiom"**.
- The axiom may be used **only if** all guards hold:
  - both guarded decoded arrays have **equal length 2**;
  - `outcomes` decode exactly to `["Yes", "No"]`;
  - `clobTokenIds` decode to exactly **two non-empty decimal-string** token IDs.
- If **any** guard fails, the binding **fails closed**.
- **No** sorting, reordering, normalization, case-folding, aliasing, fuzzy matching, or fallback.
- **No** automatic outcome↔token binding may be inferred outside this exact charter.

---

## 5. Critical nested parsing rule

- `outcomes` and `clobTokenIds` are **stringified JSON source scalars**, not native arrays.
- Any future projection/binding code must treat them as **untrusted source strings** and perform a
  **guarded second-layer JSON parse in memory**. The guarded parse must require:
  - top-level decoded value is an **array**;
  - **no duplicate JSON keys** if objects ever appear;
  - **exact length 2**;
  - every outcome is a **string**;
  - every token ID is a **string**;
  - token IDs match a **closed decimal-string grammar** `^[0-9]{1,80}$` — this is the grammar already
    pinned by the existing raw runtime token field (`PolymarketClobBookByTokenV1Request` /
    `_TOKEN_GRAMMAR`); **do not invent a wider grammar**.
- Parse failure or type mismatch ⇒ **fail-closed**; **no S1 row**; **no fabricated mapping**.
- Decoded arrays must **not** be stored as a replacement for raw source; **raw evidence remains
  authoritative**.

---

## 6. Human/manual semantic binding to Hyperliquid

- The Gamma payload **does not** contain a Hyperliquid coin field and **does not** contain a standalone
  BTC canonical exchange symbol.
- The mapping from the Polymarket slug/question semantics to Hyperliquid coin **"BTC"** is a **manual,
  operator-ratified hardcoded canonical mapping** — **not** algorithmic discovery.
- The system must **never** infer the coin from slug text, question text, regex, keyword search, UI
  title, fuzzy match, or external discovery.
- This charter proposes **exactly one** manual mapping:

  ```
  Polymarket Gamma market:
    slug        = will-bitcoin-reach-250000-by-december-31-2026-579-442
    conditionId = 0x6fefc043…1092
    questionID  = 0xd6de635b…5934
    id          = 1057883
  binds to Hyperliquid canonical coin candidate:
    BTC
  ```

- This binding is **not executable** until the charter is ratified.
- **No** other coin, market, slug, token, or condition is authorized.

---

## 7. Binding record shape (docs-only, not runtime)

```
polymarket_slug                     = will-bitcoin-reach-250000-by-december-31-2026-579-442
polymarket_market_id                = 1057883
polymarket_condition_id             = 0x6fefc043…1092
polymarket_question_id              = 0xd6de635b…5934
polymarket_question                 = "Will Bitcoin reach $250,000 by December 31, 2026?"
polymarket_outcomes_source_path     = $[0].outcomes
polymarket_clob_token_ids_source_path = $[0].clobTokenIds
polymarket_outcome_token_binding_axiom = PARALLEL_SOURCE_ORDERING
polymarket_yes_outcome_label        = "Yes"
polymarket_no_outcome_label         = "No"
polymarket_yes_token_id             = "13433573766910980267981622064090484781359464703732825845886677588040916221533"
polymarket_no_token_id              = "68320692409850091190490975441025843632582876963922128660910974326175304515755"
hyperliquid_coin                    = "BTC"
binding_authority                   = MANUAL_RATIFIED_CHARTER
source_capture_sha256               = 04a37c839d617fbb027bde036e2255a3388a087afb8872a6699669532a0cad41
status                              = UNRATIFIED
```

- Both per-outcome token IDs are now **filled with the exact extracted values** (§3.1). The prior
  `BLOCKED_PENDING_FULL_TOKEN_EXTRACTION` placeholders are removed. `status` remains **UNRATIFIED**
  until Gemini + Codex review ratifies this updated record.

### 7.1 Red-line — token IDs are exact opaque strings, never numbers

- `polymarket_yes_token_id` and `polymarket_no_token_id` are **exact opaque string identities**.
- They MUST be represented and described as **strings only**.
- **Do not** represent them as numeric literals; **do not** convert to `int`; **do not** convert to
  `float`; **do not** round; **do not** truncate; **do not** format with separators; **do not** use
  scientific notation; **do not** treat them as quantities.
- If "BigInt" is ever mentioned, it is clarified here that **computation is forbidden** — these are
  **identity-only exact strings**, never operands. Every digit is preserved exactly (length 77 each).

---

## 8. What remains blocked

- B1 gross-magnitude authority: **BLOCKED**.
- B2 event-time authority: **BLOCKED**.
- Option-B projection / S1 ingestion: **BLOCKED**.
- `l2Book` runtime: **UNBUILT + BLOCKED** until this binding charter is ratified **and** a separate
  `l2Book` raw-acquisition amendment is written and ratified.
- HYPOTHETICAL_OUTCOME: **BLOCKED**.
- Calibration and Phase 7.1 / 7.2 / 8.1: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.

---

## 9. Next eligible gate after ratification

- The read-only full-token extraction gate is **SATISFIED**: the exact full token IDs are now present
  in this docs file (§3.1, §7) — captured read-only from the existing Gamma raw ledger
  (`capture_sequence=1`), **not** via any network request.
- Only **after** this updated binding record is **ratified** (Gemini + Codex) may a **docs-only
  `l2Book` raw-acquisition amendment** become eligible.
- **No `l2Book` physical capture is authorized by this charter.** This update does **not** ratify the
  binding, does **not** authorize the `l2Book` runtime or capture, and does **not** authorize
  projection / S1 / B1 / B2 / calibration / scheduler.

---

## 10. Post-state

- This Market/Instrument Binding Charter (BTC): **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini +
  Codex review.
- Gamma physical one-shot capture: **COMPLETE**. Gamma field-authority audit: **COMPLETE**.
- **Full token extraction: COMPLETE.**
- Source-side Polymarket Gamma B3 evidence: **PROVEN** (slug, condition, outcomes, clob-token shape,
  parallel cardinality 2≡2).
- Proposed Option-B canonical mapping record: **BUILT / RATIFIABLE / UNRATIFIED**.
- B1 / B2: **BLOCKED**.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **UNBUILT + BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- HYPOTHETICAL_OUTCOME: **BLOCKED**.
- Calibration and Phase 7.1 / 7.2 / 8.1: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
