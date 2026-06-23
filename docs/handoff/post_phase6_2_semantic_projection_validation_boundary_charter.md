# Post-Phase 6.2 Semantic Projection Validation Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It defines the boundary between **raw ledger forensic audit** (evidence integrity
  only) and **semantic S1 projection validation** (ratified domain rules) for the future
  post-audit raw-ledger-to-S1 projection stage.
- It **authorizes no** S1 append, **no** production stream activation, **no** calibration, **no**
  trading, **no** paper/live/canary, **no** actionability.
- It implements **nothing**; it edits **no** runtime / test / schema / config / lock / generated /
  tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Continuous Ledger Audit: RATIFIED boundary + TDD; implementation BLOCKED / UNSTARTED.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `9bdfb88687296f38f1003a21c771736c3a4b4ec2`.
- Parent chain:
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap & No-Auto-Activation
    Charter.
  - `133363cd57735c0de9aff53a1cab1a687476a3a2` = **RATIFIED** S1 Stream Authorization Eligibility
    & Safety Preconditions Charter.
  - `baee0aacc7b7e235e4754792d173b9d0e726e4cb` = **RATIFIED** Read-Only Continuous Ledger Audit
    TDD Charter.
  - `bb7b73b4db4291e96547e72cc9cb332936886ccb` = **RATIFIED** Read-Only Continuous Ledger Audit
    Charter (boundary).
- Already-ratified runtime referenced (not modified here):
  - `phase6_2_shadow_intent/s1_paired_projection.py` — **RATIFIED** S1 paired projection runtime.
  - `phase6_2_shadow_intent/s1_production_ingestion_adapter.py` — **RATIFIED** S1 production
    ingestion adapter / durable writer.

## Section 2 — Charter Intent

- This charter draws the **boundary line**, not the implementation. It states *what* semantic
  validation owns versus *what* the raw audit owns, and binds semantic validation to the
  **already-ratified** projection / adapter rules — introducing **no new** domain logic.
- The raw audit and semantic validation are **disjoint responsibilities**. Neither may absorb the
  other's duties.

---

## Section 3 — Boundary Gates

### Gate A — Entry Preconditions

1. The bounded raw-only 24h run must **complete or stop within ratified bounds**
   (`max_cycles ≤ 8640`, `sleep_interval = 10s`, `max_duration ≤ 86400s`, `failure_budget = 100`),
   with a preserved `stop_reason`.
2. The **Read-Only Continuous Ledger Audit** must be implemented (RED→GREEN per the ratified Audit
   TDD Charter) and must return verdict **CLEAN**.
3. A **DIRTY** audit keeps semantic projection **BLOCKED**.
4. A **CLEAN** audit only makes semantic validation **eligible** — it does **not** auto-run
   projection and does **not** auto-run S1 append.

### Gate B — Raw-vs-Semantic Boundary

1. The raw audit proves **ledger integrity only** (read-only access, schema, append-only,
   provenance presence, SHA, permissions, pair structure, endpoint authority).
2. **Semantic validation owns interpretation** of source payload fields (timestamps, prices,
   sizes, levels, side axiom, outcome label).
3. Semantic validation must **not alter raw evidence** — the continuous ledger remains append-only
   and is opened read-only.
4. Raw response bodies must **not be dumped** in any semantic validation report.

### Gate C — Pair Eligibility

1. Only **audit-clean** pair cycles may enter semantic validation.
2. Each eligible cycle must have **exactly one** Hyperliquid leg **and exactly one** Polymarket
   leg under the **same `cycle_id`**.
3. **Orphan / lone / mismatched / more-than-two-leg / non-2xx** cycles are **permanently
   ineligible**.
4. **Failed cycles are never semantically projected.**

### Gate D — Timestamp Rule

1. Semantic validation applies the **ratified absolute cross-source boundary**:
   `abs(polymarket_timestamp_ms - hyperliquid_time_ms) <= 1000`
   (ratified constant `MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS = 1000`).
2. **Exactly 1000 ms is accepted; 1001 ms is rejected** (`> 1000` rejects via
   `S1_TIME_DELTA_EXCEEDS_1000_MS`).
3. **No directional ordering assumption** is allowed — the rule is symmetric `abs(...)`; neither
   source is assumed to lead.
4. The **retrieval timestamp must never substitute** the source event timestamp. Source event time
   comes **only** from:
   - Polymarket CLOB `$.timestamp` (tagged `POLYMARKET_CLOB_SOURCE_ISSUED_TIMESTAMP`),
   - Hyperliquid l2Book `$.time` (tagged `HYPERLIQUID_L2BOOK_SOURCE_ISSUED_TIME`).
   Any substitution fails closed via `S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED`.
5. A **missing source wall-clock timestamp fails closed**
   (`S1_POLYMARKET_TIMESTAMP_MISSING` / `S1_HYPERLIQUID_TIME_MISSING`).

### Gate E — Type Identity

1. **Price / size values must remain exact `decimal.Decimal`** parsed from accepted literal
   strings — never `float`.
2. **Time / depth integer values must remain `int`** (epoch-ms).
3. **Floats, scientific notation, lossy coercions** are **rejected**
   (`S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED`,
   `S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED`, `S1_HYPERLIQUID_TIME_REJECTED`).
4. **Exact literal mapping must be preserved** — the accepted string is the source of truth for
   the `Decimal`; no normalization or re-rendering.

### Gate F — Top-of-Book / Side Axiom

1. Hyperliquid `levels[0][0]` is **BID**.
2. Hyperliquid `levels[1][0]` is **ASK**.
   (Ratified `RATIFIED_SIDE_AXIOM = ("BID", "ASK")`; violations fail closed via
   `S1_HYPERLIQUID_SIDE_AXIOM_REJECTED`; malformed shape via
   `S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED`.)
3. **No depth traversal, mid-price, VWAP, or spread analytics** at this layer — top-of-book only.
4. The Polymarket outcome label must remain the **ratified YES binding** (the ratified YES-token
   CLOB book), never NO, Gamma, or an alternate token.

### Gate G — Provenance / SHA / Source Authority

1. **Both legs** require `source_authority`, `capture_sequence` / `cycle_id`,
   `response_body_sha256`, `http_status`, and `byte_length`.
2. **SHA linkage must be preserved** into any future S1 candidate (dual-source idempotency key
   `sha256(poly_sha + "|" + hl_sha)`); a SHA mismatch fails closed via
   `S1_PROVENANCE_SHA_MISMATCH`.
3. **Wrong coin / token / method / path / header / private / auth / order / balance** evidence
   fails closed (raw audit Gate D + projection evidence-missing literals
   `S1_PAIR_POLYMARKET_EVIDENCE_MISSING` / `S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING`).
4. **`rowid` / `sqlite_sequence` / `capture_sequence` cannot be a domain identity** — they are
   forensic ordering only.

### Gate H — Failure Surface

1. Semantic rejection must use **only the ratified S1 projection / adapter failure literals**:
   - `S1_PAIR_POLYMARKET_EVIDENCE_MISSING`
   - `S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING`
   - `S1_POLYMARKET_TIMESTAMP_MISSING`
   - `S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED`
   - `S1_HYPERLIQUID_TIME_MISSING`
   - `S1_HYPERLIQUID_TIME_REJECTED`
   - `S1_TIME_DELTA_EXCEEDS_1000_MS`
   - `S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED`
   - `S1_HYPERLIQUID_SIDE_AXIOM_REJECTED`
   - `S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED`
   - `S1_PROVENANCE_SHA_MISMATCH`
   - `S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED`
   (plus the factory `S1_PAIR_DIRECT_CONSTRUCTION` guard).
2. **No ad-hoc exception strings** may be introduced.
3. **Scheduler / wiring failure literals** (`SCHED_*`, `WIRING_*`) must **not pollute** the S1
   projection failure surface.
4. **Projection errors must propagate unchanged** — never swallowed, renamed, downgraded, or
   wrapped in a different surface.

### Gate I — Output Boundary

1. Semantic validation may produce **in-memory candidate projection records only**.
2. This charter authorizes **no durable S1 append**.
3. **No** calibration, signal, edge, profit, rank, advice, size, order, trade, or paper/live/canary
   output.
4. **Capacity remains 0.**

### Gate J — Next Gate

1. If this semantic validation boundary is ratified, the **only** next future step after a CLEAN
   raw audit may be a separate **Semantic Projection Validation TDD Charter**.
2. **S1 append remains BLOCKED** until a separate **S1 Stream Authorization / Production Append
   Charter** is ratified.
3. **No automatic transition** is allowed (per the ratified Post-Run Roadmap & No-Auto-Activation
   Charter, Section 4).

---

## Section 4 — Ownership Matrix (raw audit vs semantic validation)

| Concern | Raw Ledger Audit | Semantic Projection Validation |
|---------|------------------|-------------------------------|
| Read-only open, permissions, append-only | **OWNS** | inherits (must not weaken) |
| Schema / column presence | **OWNS** | inherits |
| SHA present + valid hex | **OWNS** (presence) | **OWNS** (recompute linkage) |
| Pair structure (1 HL + 1 PM per cycle) | **OWNS** (structural) | inherits as precondition |
| Source event timestamp parse | n/a | **OWNS** |
| `abs(delta) <= 1000ms` rule | n/a | **OWNS** |
| Decimal/int type identity | n/a | **OWNS** |
| BID/ASK side axiom, top-of-book | n/a | **OWNS** |
| YES outcome binding | endpoint authority only | **OWNS** (semantic) |
| Durable S1 append | forbidden | forbidden (this charter) |
| Calibration / actionability | forbidden | forbidden |

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this semantic projection validation boundary charter.
2. Phase A: 24h run completes/stops within ratified bounds.
3. Phase B: RED→GREEN raw audit implementation → CLEAN verdict.
4. If CLEAN and this charter ratified: a separate **Semantic Projection Validation TDD Charter**.
5. S1 append remains behind a separate **S1 Stream Authorization / Production Append Charter**.

## Post-state

- Semantic Projection Validation Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit: **RATIFIED** boundary + TDD; implementation **BLOCKED / UNSTARTED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
