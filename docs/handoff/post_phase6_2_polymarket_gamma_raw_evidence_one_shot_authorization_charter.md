# Post-Phase 6.2 — Polymarket Gamma Raw-Evidence One-Shot Authorization Charter

> Status: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
> This is a **docs-only** charter. **By itself it authorizes no execution.** No outbound request may
> occur until this charter is independently ratified **and** separately commanded by the
> user/operator. This document is an authorization *gate*, not an acquisition.

---

## 1. Status and purpose

- **Status:** BUILT / RATIFIABLE / UNRATIFIED pending Gemini + Codex review.
- This charter is **docs-only**. It writes no runtime, runs no test, makes no network call, parses no
  payload, and touches no S1.
- It **authorizes no immediate execution by itself.** Execution becomes *eligible* only after (a) this
  charter is independently ratified, and (b) a separate explicit operator command is issued.
- **Purpose:** authorize — after ratification and separate operator command — exactly **one** raw
  Polymarket Gamma market-evidence capture, which is the source evidence required for the later **B3
  Market/Instrument Binding**.
- This charter exists **only because** the RATIFIED evidence-first sequencing at commit `60c2454`
  (§8 of the Timestamped Book-Pair Source-Sufficiency Amendment) requires durable raw Gamma evidence
  **before** any Market/Instrument Binding Charter may be authored.

---

## 2. Exact source authority

- **Source authority:** `POLYMARKET_GAMMA_MARKET_BY_SLUG_V1`.
- **Endpoint:**

  ```
  GET https://gamma-api.polymarket.com/markets?slug=<exact_charter_slug>
  ```

- The request **must** use the **already-RATIFIED current raw runtime variant only**
  (`PolymarketGammaMarketBySlugV1Request`).
- **No new runtime variant** is authorized.
- **No `l2Book` runtime** is authorized.
- **No fourth runtime variant** is authorized.

---

## 3. Exact slug discipline

- This charter carries exactly one explicit slug field: **`exact_charter_slug`** (placeholder —
  **unfilled** in this docs commit).
- Before any physical execution, **`exact_charter_slug` must be filled with one exact lowercase
  Polymarket slug chosen by the user/operator**.
- The following are **forbidden**: search, discovery, list-markets query, autocomplete, fuzzy
  matching, UI scraping, slug inference, case-folding, alias mapping, fallback slug, or any multi-slug
  loop.
- If `exact_charter_slug` is **absent, empty, malformed, or not explicitly supplied**, execution is
  **BLOCKED**.
- **No concrete slug is invented here.** The user has **not** supplied one in this command; therefore
  `exact_charter_slug` remains an unfilled placeholder and physical execution remains BLOCKED.

---

## 4. Strict one-shot scope

After ratification **and** a separate user/operator command, this authorization permits exactly
**one** outbound HTTPS request:

```
GET https://gamma-api.polymarket.com/markets?slug=<exact_charter_slug>
```

with all of the following **prohibited**:

- No retry.
- No fallback.
- No second request.
- No loop.
- No scheduler.
- No continuous collection.
- No hidden preflight network request.
- No localhost network.
- No additional Polymarket endpoint.
- No Hyperliquid endpoint.
- No concurrent capture.

If the single request fails, the RATIFIED runtime records the one resulting outcome and stops; it is
**never** retried under any condition.

---

## 5. Zero projection / raw-only

- The payload is written **only** to the raw-capture ledger (`raw_capture.sqlite3`) by the RATIFIED
  raw-acquisition runtime.
- **No** S1 write / read / init / open / attach / query.
- **No** projection.
- **No** normalization.
- **No** parsing during the acquisition step.
- **No** field extraction during acquisition.
- **No** JSON decoding for decision-making during acquisition.
- **No** B3 binding during acquisition.
- **No** B1 or B2 assertion.
- **No** response-body printing.
- Persisted content is limited to **raw bytes + request metadata + hashes + forensic timestamps only**.

---

## 6. Forensic intent

- The **sole** forensic purpose is to create immutable raw evidence for a **later, separate,
  read-only** Gamma field-authority audit.
- That later audit may inspect whether the captured Gamma payload contains source evidence for:
  - `slug`
  - `condition_id` / `conditionId` (or exact source equivalent)
  - `outcomes`
  - `clobTokenIds` / `token_id` / `asset_id` relationship, **if present**
  - market identifier fields, **if present**
- The audit **must not** be performed by this charter.
- The audit **must not** invent missing fields.
- The audit **must not** normalize, repair, infer, or substitute.
- This charter does **not** prove B3; it only makes B3 **evidence acquisition ELIGIBLE** after
  ratification and an explicit execution command.

---

## 7. B1 / B2 / B3 status

- **B1** gross-magnitude authority: **BLOCKED**.
- **B2** event-time authority: **BLOCKED**.
- **B3** canonical mapping: **BLOCKED**.
- Hyperliquid **meta** source-side identifier evidence remains **PROVEN only on the meta side**.
- Gamma evidence is **not yet captured** by this docs commit.
- The Market/Instrument Binding Charter remains **BLOCKED** until durable Gamma raw capture **plus**
  the read-only field-authority audit both exist.

---

## 8. OS / operator safety requirements for the later physical one-shot

This section is **operator guidance, not execution.** When the later one-shot is separately ratified
and commanded, it should run in a hardened one-shot shell context:

- a dedicated evidence directory created with mode **0700**;
- **`umask 077`** applied before the runtime call;
- a clean proxy environment or an explicit no-proxy environment for the Python process (without
  destroying PATH/HOME/locale/system TLS-CA discovery);
- `PYTHONPATH` pinned to the repository root if needed;
- a precondition check that `HEAD == origin/master` at the ratified authorization commit;
- a precondition check that the target raw-ledger path for this Gamma capture is **absent**, unless a
  later operator charter explicitly chooses append semantics;
- TLS verification must **not** be disabled.

Nothing in this section authorizes a request; it constrains a future, separately-commanded execution.

---

## 9. Post-state

- This Gamma authorization charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini + Codex review.
- Timestamped Book-Pair Source-Sufficiency Amendment: **RATIFIED through `60c2454`**.
- Source-Authority / Raw-Ledger charter: **RATIFIED**.
- Existing raw one-shot runtime: **RATIFIED for current three variants only**.
- Gamma physical one-shot capture: **ELIGIBLE only after this charter is ratified and separately
  commanded; NOT STARTED by this docs commit**.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **UNBUILT + BLOCKED**.
- Data collection: **STARTED — exactly one existing RAW_CAPTURED sample from Hyperliquid meta**.
- Projection / S1 ingestion: **BLOCKED**.
- HYPOTHETICAL_OUTCOME: **BLOCKED**.
- Calibration and Phase 7.1 / 7.2 / 8.1: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
