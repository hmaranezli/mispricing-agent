# Post-Phase 6.2 Semantic Projection Validation — TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only.** It defines the **exact RED test requirements** for a future semantic projection
  validation implementation. It **implements nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** S1 append, calibration, trading, paper, canary, live, routing, execution,
  or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Continuous Ledger Audit: RATIFIED boundary + TDD; implementation BLOCKED / UNSTARTED.**
- **Semantic Projection Validation Boundary Charter: RATIFIED at `905ee75`.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `905ee7591111c45ce501977e1063e3edb2051a30`.
- Parent chain:
  - `905ee7591111c45ce501977e1063e3edb2051a30` = **RATIFIED** Semantic Projection Validation
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
  - `133363cd57735c0de9aff53a1cab1a687476a3a2` = **RATIFIED** S1 Stream Authorization Eligibility
    & Safety Preconditions Charter.
- Already-ratified runtime referenced (not modified here):
  - `phase6_2_shadow_intent/s1_paired_projection.py` — **RATIFIED** projection runtime + failure
    literals.
  - `phase6_2_shadow_intent/s1_production_ingestion_adapter.py` — **RATIFIED** adapter / durable
    writer.

## Section 2 — RED-before-GREEN Law

- The future semantic projection validation implementation must begin with **failing tests first**.
- The initial RED must fail because the semantic validation unit is **absent** (`ImportError` /
  unresolved symbol), **not** due to malformed tests.
- Tests must use **in-memory fixtures only** — never the live run ledger, never the network,
  never S1.
- This charter **introduces no new domain logic**. The future tests must bind to the
  **already-ratified** `s1_paired_projection` rules and failure literals — they may not invent
  new thresholds, types, side axioms, or literals.

---

## Section 3 — Future RED Test Groups

### Group A — Preconditions

Future tests / harness must encode (as guards or documented skip conditions):

**A1.** The raw-only 24h run must be **completed / stopped** before any semantic validation
implementation or execution.

**A2.** The Read-Only Continuous Ledger Audit must return **CLEAN** before semantic projection
validation becomes eligible.

**A3.** A **DIRTY** audit blocks semantic projection validation.

**A4.** A CLEAN audit **does not auto-enable** S1 or production — it only makes semantic
validation eligible.

(These are procedural preconditions; the unit tests themselves run on in-memory fixtures and must
not depend on the live ledger.)

### Group B — Raw-vs-Semantic Separation

**B1.** Tests must assert the semantic validation unit operates on **in-memory candidate inputs**,
not on a raw ledger connection (no `sqlite3.connect` in the validation unit's hot path; assert via
AST import/call inspection).

**B2.** Tests must assert **no raw body dump** — the candidate record and any test output must not
contain a printed/decoded raw response body.

**B3.** Tests must assert **no payload analytics** and **no trading signal** field is produced.

### Group C — Timestamp Validation

**C1.** Pass when `abs(polymarket_timestamp_ms - hyperliquid_time_ms) == 0`.

**C2.** **Boundary: pass when delta == exactly 1000 ms** (`<= MAX_CROSS_SOURCE_EVENT_TIME_DELTA_MS`).

**C3.** **Boundary: fail when delta == 1001 ms** via literal `S1_TIME_DELTA_EXCEEDS_1000_MS`.

**C4.** **No directional ordering assumption** — test both `poly > hl` and `hl > poly` at the same
absolute delta; both must behave identically (symmetric `abs`).

**C5.** **Retrieval timestamp must never substitute** for source event time — a fixture that
supplies only `retrieval_*_epoch_ms` (no source `$.timestamp` / `$.time`) must fail closed via
`S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED`.

**C6.** **Missing source timestamp fails closed**:
- absent Polymarket `$.timestamp` → `S1_POLYMARKET_TIMESTAMP_MISSING`.
- absent Hyperliquid `$.time` → `S1_HYPERLIQUID_TIME_MISSING`.

### Group D — Exact Type Validation

**D1.** **Decimal string parsing** for prices/sizes: an accepted literal string (e.g. `"0.5234"`)
maps to an exact `decimal.Decimal` with no re-rendering.

**D2.** **Integer parsing** for timestamps / depth counts: epoch-ms parse to `int`; non-integer
forms fail closed (`S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED` / `S1_HYPERLIQUID_TIME_REJECTED`).

**D3.** **Reject `float`** inputs for price/size (`S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED`).

**D4.** **Reject scientific notation** (e.g. `"1e3"`) for price/size.

**D5.** **Reject lossy coercion** (e.g. a Python `float` that cannot round-trip).

**D6.** **Reject `NaN` / `Inf` / `-Inf`** string forms for price/size.

**D7.** **Reject empty string** `""` for any required numeric field.

**D8.** **Reject whitespace-only string** (e.g. `" "`, `"\t"`, `"​"`) for any required
numeric field.

**D9.** **No implicit default values** — a missing required field must fail closed, never silently
default to 0 / "" / None.

### Group E — Paired-Cycle Eligibility

**E1.** Pass when a cycle has **exactly one** Hyperliquid leg and **one** Polymarket leg.

**E2.** **Reject orphan / lone-leg** cycles (HL-only or PM-only) →
`S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING` / `S1_PAIR_POLYMARKET_EVIDENCE_MISSING`.

**E3.** **Reject duplicate legs** (two HL or two PM rows in one cycle).

**E4.** **Reject non-2xx legs** — a cycle with any non-2xx leg produces **no** candidate record.

**E5.** **Reject mismatched cycle ids** between the two legs.

**E6.** **Rejected pairs must not produce candidate projection records** — assert the result set
excludes them entirely (not merely flags them).

### Group F — Top-of-Book and Side Axioms

**F1.** Hyperliquid `levels[0][0]` is **BID**.

**F2.** Hyperliquid `levels[1][0]` is **ASK**.
(Ratified `RATIFIED_SIDE_AXIOM = ("BID", "ASK")`; violations →
`S1_HYPERLIQUID_SIDE_AXIOM_REJECTED`; malformed shape → `S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED`.)

**F3.** **No mid-price / VWAP / depth-traversal / spread analytics** — assert the candidate record
carries only top-of-book BID/ASK, no derived aggregate field.

**F4.** **Polymarket YES-token binding must be explicit and provenance-backed** — the candidate
must carry the ratified YES token id and reject NO / Gamma / alternate tokens.

### Group G — Ratified Failure Literals

**G1.** The future implementation must use **only** the ratified failure literals defined in
`s1_paired_projection.py`:
`S1_PAIR_POLYMARKET_EVIDENCE_MISSING`, `S1_PAIR_HYPERLIQUID_EVIDENCE_MISSING`,
`S1_POLYMARKET_TIMESTAMP_MISSING`, `S1_POLYMARKET_TIMESTAMP_PARSE_REJECTED`,
`S1_HYPERLIQUID_TIME_MISSING`, `S1_HYPERLIQUID_TIME_REJECTED`, `S1_TIME_DELTA_EXCEEDS_1000_MS`,
`S1_HYPERLIQUID_LEVELS_SHAPE_REJECTED`, `S1_HYPERLIQUID_SIDE_AXIOM_REJECTED`,
`S1_HYPERLIQUID_DECIMAL_PARSE_REJECTED`, `S1_PROVENANCE_SHA_MISMATCH`,
`S1_RETRIEVAL_TIME_SUBSTITUTION_REJECTED` (plus the factory guard `S1_PAIR_DIRECT_CONSTRUCTION`).

**G2.** **No ad-hoc exception strings** — a test must assert the rejection `reason` is a member of
the ratified closed set (e.g. by importing the literal names and checking membership).

**G3.** **Scheduler / wiring / system errors must not pollute** the semantic projection failure
taxonomy — `SCHED_*` and `WIRING_*` literals must never appear as a semantic rejection reason.

### Group H — Provenance and Source Authority

**H1.** Candidate projection records must carry **raw ledger / run provenance**: `cycle_id`,
`capture_sequence` (per leg), `source_authority`, `response_body_sha256` (per leg), `http_status`,
`byte_length`.

**H2.** Candidate records must carry the **commit SHA** of the producing run and the **source
endpoint authority** (`HYPERLIQUID_L2_BOOK_BY_COIN_V1`, `POLYMARKET_CLOB_BOOK_BY_TOKEN_V1`).

**H3.** **SQLite `rowid` / `sqlite_sequence` / `capture_sequence` must never become domain
identity** — assert the candidate's identity key is `sha256(poly_sha + "|" + hl_sha)`, not a
rowid.

**H4.** **Deterministic idempotency must be test-pinned** — the same paired raw evidence must
yield the same candidate identity key across repeated calls (pinned expected sha256 in the test).

**H5.** A **SHA mismatch** between recomputed and stored `response_body_sha256` fails closed via
`S1_PROVENANCE_SHA_MISMATCH`.

### Group I — Output Boundary

**I1.** Tests may target **only in-memory semantic candidate records**.

**I2.** **No S1 append** — assert the validation unit never calls `ingest_paired_s1_projection`
and never opens a write-mode DB connection (AST inspection).

**I3.** **No durable write** of any kind from the validation unit.

**I4.** **No calibration dataset** produced.

**I5.** **No signal / actionability** field — the candidate dataclass must not expose
`edge`, `profit`, `rank`, `advice`, `size_recommendation`, `order`, `trade`, `paper`, `live`,
`canary`, `calibrate`.

**I6.** `CAPACITY == 0` constant present in the validation module.

### Group J — Next Gate

**J1.** After this TDD charter is RATIFIED, implementation remains **BLOCKED** until:
1. the raw 24h run **completes / stops**,
2. the Read-Only Continuous Ledger Audit is **CLEAN**,
3. the user gives a **separate explicit implementation command**.

**J2.** Clean semantic projection validation **still does not auto-enable S1**. S1 append remains
behind a separate **S1 Stream Authorization / Production Append Charter** plus a separate operator
command (per the ratified Post-Run Roadmap & No-Auto-Activation Charter).

---

## Section 4 — Minimal GREEN Boundary (future)

A future implementation may add **only**:

- a semantic projection validation module (e.g. reusing/wrapping the ratified
  `project_paired_s1_evidence` — **not** duplicating its formula), producing **in-memory candidate
  records only**;
- a test file with the Groups A–J above.

It must **not** add:

- durable S1 append, S1 activation, or S1 schema creation;
- any new projection formula, threshold, type rule, side axiom, or failure literal;
- calibration / trading / actionability;
- network requests;
- daemon / background process.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this TDD charter.
2. Raw 24h run completes / stops within ratified bounds.
3. RED→GREEN raw audit implementation → CLEAN verdict.
4. Separate explicit operator command → RED→GREEN semantic projection validation implementation.
5. S1 append remains behind a separate S1 Stream Authorization / Production Append Charter.

## Post-state

- Semantic Projection Validation TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit: **RATIFIED** boundary + TDD; implementation **BLOCKED / UNSTARTED**.
- Semantic Projection Validation Boundary Charter: **RATIFIED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
