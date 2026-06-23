# Post-Phase 6.2 — Hyperliquid `l2Book` BTC Raw-Acquisition Amendment Charter

> Status: **BUILT / RATIFIABLE / UNRATIFIED** pending independent Gemini + Codex review.
> **Docs-only.** By itself this charter authorizes **no** runtime implementation, **no** physical
> network capture, and **no** projection / S1 / calibration / scheduler. It defines the exact *future*
> raw-acquisition amendment for a single Hyperliquid **BTC** `l2Book` source, enabled by the RATIFIED
> BTC Market/Instrument Binding Charter.

---

## 1. Status and purpose

- **Status:** BUILT / RATIFIABLE / UNRATIFIED pending Gemini + Codex review.
- **Docs-only.** No runtime/test/fixture/config/lock/dependency/generated/tracking/export change.
- Authorizes **no** runtime implementation by itself.
- Authorizes **no** physical network capture by itself.
- Authorizes **no** projection / S1 / calibration / scheduler.
- **Purpose:** specify the exact future raw-acquisition amendment for one Hyperliquid BTC `l2Book`
  source, made eligible (for design only) by the RATIFIED BTC Market/Instrument Binding Charter.

---

## 2. Evidence / authority anchors (ratified upstream facts)

- **BTC Market/Instrument Binding Charter: RATIFIED through commit
  `81fc960ba140fb02b1f4dc917c7edfced4c31bc8`.**
- Polymarket slug: `will-bitcoin-reach-250000-by-december-31-2026-579-442`
- Polymarket `conditionId`: `0x6fefc043…1092`
- Polymarket `questionID`: `0xd6de635b…5934`
- Polymarket **yes** token ID (exact opaque string):
  `"13433573766910980267981622064090484781359464703732825845886677588040916221533"`
- Polymarket **no** token ID (exact opaque string):
  `"68320692409850091190490975441025843632582876963922128660910974326175304515755"`
- Outcome-token binding axiom: `PARALLEL_SOURCE_ORDERING`
- Hyperliquid canonical coin: `BTC`
- Binding authority: `MANUAL_RATIFIED_CHARTER`

> The token IDs above are **exact opaque string identities** — never numbers, never operands, no
> int/float/round/truncate/separators/scientific-notation, no computation.

**This amendment may NOT infer the coin from slug or question text.** It uses **only** the ratified
hardcoded BTC binding (`MANUAL_RATIFIED_CHARTER`). No regex, keyword search, UI title, fuzzy match, or
external discovery is permitted to derive the coin.

---

## 3. New source authority (exact)

- **Source authority name:** `HYPERLIQUID_L2_BOOK_BY_COIN_V1`
- **Endpoint:** `POST https://api.hyperliquid.xyz/info`
- **Exact logical body:** `{"type":"l2Book","coin":"BTC"}`
- **Exact request byte body** (to be pinned for the future runtime as UTF-8 bytes, no whitespace):

  ```
  b'{"type":"l2Book","coin":"BTC"}'
  ```

- `nSigFigs`: **MUST be omitted.**
- `mantissa`: **MUST be omitted.**
- **No optional fields** allowed.
- **No alternate coin** allowed.
- **No** lowercase `btc`, **no** `XBT`, **no** `wBTC`, **no** alias.
- **No** user-supplied coin at runtime for this exact BTC amendment.
- **No** discovery / listing call.
- **No** fallback endpoint.

---

## 4. Future runtime behavior constraints

If a future runtime amendment is ratified later, it may add **only this exact fourth variant and no
others**. The future runtime path must obey:

- One call = **at most one** outbound request.
- **No** retry.
- **No** fallback.
- **No** scheduler.
- **No** continuous collection.
- **No** concurrent request.
- **No** Hyperliquid `meta` request.
- **No** Polymarket request.
- **No** S1.
- **No** projection.
- **No** JSON parse during acquisition.
- **No** response-body printing.
- **Raw bytes only** into the raw ledger (plus request metadata, hashes, forensic timestamps).

---

## 5. Independent ledger / evidence isolation red-line

Any future physical `l2Book` capture **must**:

- use a **fresh, independent** evidence directory and `raw_capture.sqlite3` ledger, **separate from**:
  - `/root/mispricing_runtime_evidence/raw_capture.sqlite3` (Hyperliquid `meta`)
  - `/root/mispricing_gamma_runtime_evidence/raw_capture.sqlite3` (Polymarket Gamma)
- **not** append into either prior raw ledger;
- **not** share an S1 path with prior captures;
- use its **own isolated `s1_audit.sqlite3` path that must remain absent**.

**Rationale:** `l2Book` is high-frequency / time-sensitive and must **not** pollute the prior
Hyperliquid `meta` or Polymarket Gamma raw-evidence streams.

The future operator command **must require the target `l2Book` evidence directory/ledger to be absent
before the one-shot run**, unless a later ratified charter explicitly authorizes append semantics.
**No append semantics are authorized here.**

---

## 6. Candidate fields only — B1 / B2 denial

The expected `l2Book` response fields are **candidates only**; existence confers no authority:

- `time` is only a **B2 event-time candidate**.
- `levels` is only a **book-shape evidence candidate**.
- `levels[0]` / `levels[1]` side semantics are **candidates only** until captured and audited.
- `px`, `sz`, and `n` are **B1 / source-shape candidates only**.
- **No** gross magnitude, size, volume, depth, spread, midpoint, notional, price, probability, side, or
  economic formula is authorized.
- **No** timestamp unit, semantics, tolerance, or alignment is authorized.
- Retrieval time must **never** substitute for source event time.
- **B1 remains BLOCKED.**
- **B2 remains BLOCKED** until durable `l2Book` raw capture **+** read-only field-authority audit **+**
  a separate source-sufficiency / authority charter.

---

## 7. B3 status

- The narrow **BTC Polymarket-Gamma ↔ Hyperliquid coin binding is RATIFIED**.
- This B3 ratification permits **designing the `l2Book` BTC raw-acquisition amendment only**.
- It does **not** authorize projection / S1.
- It does **not** authorize B1 or B2.
- It does **not** authorize other coins, markets, or tokens.

---

## 8. Future physical `l2Book` capture gate

After **this amendment is ratified**, a **separate** operator command may become eligible for **exactly
one** physical `l2Book` capture with:

- exact body `b'{"type":"l2Book","coin":"BTC"}'`;
- an **isolated** `l2Book` evidence ledger (per §5);
- **no** retry / **no** second request;
- **no** S1;
- **no** parse;
- **no** projection;
- **no** scheduler;
- response body **never** printed.

**This docs commit itself performs none of that.**

---

## 9. Post-state

- This `l2Book` raw-acquisition amendment charter: **BUILT / RATIFIABLE / UNRATIFIED** pending Gemini +
  Codex review.
- BTC Market/Instrument Binding Charter: **RATIFIED**.
- Option-B canonical mapping for this narrow BTC binding: **RATIFIED**.
- `HYPERLIQUID_L2_BOOK_BY_COIN_V1` runtime: **UNBUILT + BLOCKED**.
- `l2Book` physical capture: **NOT STARTED**.
- B1: **BLOCKED**.
- B2: **BLOCKED**.
- Projection / S1 ingestion: **BLOCKED**.
- HYPOTHETICAL_OUTCOME: **BLOCKED**.
- Calibration and Phase 7.1 / 7.2 / 8.1: **BLOCKED**.
- Scheduler / continuous collection: **BLOCKED**.
- Capacity: **0**.
