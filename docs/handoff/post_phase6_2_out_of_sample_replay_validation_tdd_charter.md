# Post-Phase 6.2 Out-of-Sample / Replay Validation — TDD Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the **exact future RED test requirements** for the
  Out-of-Sample / Replay Validation boundary. It **creates no tests now**, **implements nothing**,
  and **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, calibration / trading /
  actionability, or paper / canary / live.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Out-of-Sample / Replay Validation Boundary Charter: RATIFIED at `e57e8cf`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `e57e8cfe03a9ac9b3412215f7fd0c8bbce049024`.
- Parent chain:
  - `e57e8cfe03a9ac9b3412215f7fd0c8bbce049024` = **RATIFIED** Out-of-Sample / Replay Validation
    Boundary Charter.
  - `fdc68c7243fa6d535771b25bb21d2285e6d51316` = **RATIFIED** Calibration / Analysis Offline
    Mathematical Boundary Charter.
  - `dc587fbd22d137ec2094d8d17af727238909c267` = **RATIFIED** Phase G Risk / Capacity Mathematical
    Boundary Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter.
- This charter elaborates the **future RED test requirements** for the ratified Out-of-Sample /
  Replay Validation Boundary Charter. It does not supersede, relax, or accelerate any prior gate.

## Section 2 — RED-before-GREEN Law (future)

- Any future validation implementation must begin with **failing tests first**.
- The initial RED must fail because the validation unit is **absent** (`ImportError` / unresolved
  symbol), **not** due to malformed tests.
- Future tests must use **in-memory fixtures only** — never the live run ledger, never the network,
  never S1.
- This charter **introduces no new runtime behavior** beyond future test requirements. It states
  only what future tests must prove.

---

## Section 3 — Future RED Test Requirements

### Group A — Preconditions for Future RED Tests

Future tests / harness must encode (as guards or documented skip conditions):

**A1.** The prior **Out-of-Sample / Replay Validation Boundary Charter** must be RATIFIED.

**A2.** The raw-only 24h run must be **complete / stopped** before any implementation lane.

**A3.** The Read-Only Continuous Ledger Audit must be **CLEAN**.

**A4.** Semantic projection validation must be **clean**.

**A5.** Calibration and risk/capacity boundaries must remain **non-authorizing** (their ratification
does not unlock implementation here).

**A6.** Any **DIRTY** state blocks all future implementation.

### Group B — Future Test Scope Only

**B1.** Future tests may assert **validation behavior only**.

**B2.** Future tests must **not** construct live trading, paper trading, canary, routing, orders,
signals, or capacity (assert these symbols are absent from the validation module via AST
inspection).

**B3.** Passing future tests must **not auto-enable** implementation or runtime — assert no test
flips a runtime/activation flag.

### Group C — Replay / Holdout RED Test Requirements

Future RED tests must prove:

**C1.** Train / calibration evidence **cannot be reused** as holdout evidence (a fixture reusing a
calibration record as holdout fails closed).

**C2.** Holdout windows are **fixed before evaluation** (windows declared in input; a unit that
derives windows from observed results fails closed).

**C3.** **Post-hoc window selection fails closed** (reselecting windows after metric computation is
rejected).

**C4.** **Missing holdout definition fails closed.**

**C5.** **Contaminated holdout fails closed** (any overlap between calibration and holdout sets is
rejected).

### Group D — Anti-Leakage RED Test Requirements

Future RED tests must prove **fail-closed** behavior for:

**D1.** **Lookahead leakage** (using information after event-time `t`).

**D2.** **Survivorship bias** (silently dropping excluded/failed cycles).

**D3.** **Body-mining** (using unratified raw-body fields).

**D4.** **Future outcome leakage** (outcome entering the computation ahead of its event-time).

**D5.** **Manual cherry-picking** (hand-selected records/windows/metrics).

**D6.** **Timestamp leakage across replay windows** (event-time of one window bleeding into
another).

### Group E — Exact Decimal / int Validation RED Test Requirements

Future RED tests must prove:

**E1.** `sample_size_N` must be **`int`**.

**E2.** `coverage_ratio` must be **exact `decimal.Decimal`**.

**E3.** `confidence_interval` / error band must be **exact `decimal.Decimal`**.

**E4.** `false_positive_rate` and `false_negative_rate` must be **exact `decimal.Decimal`**.

**E5.** `stability` metrics must be **exact `decimal.Decimal`**.

**E6.** **Reject** `float`, scientific notation, `NaN`, `Infinity` / `-Infinity`, empty strings,
whitespace-only strings, and **implicit defaults** — each must fail closed, never silently coerce
or default.

### Group F — Deterministic Replay Provenance RED Test Requirements

Future RED tests must prove:

**F1.** **commit SHA is required** (absent → fail closed).

**F2.** **artifact hashes are required** (absent → fail closed).

**F3.** **config fingerprint is required** (absent → fail closed).

**F4.** **S1 / audit provenance references are required** (absent → fail closed).

**F5.** **deterministic idempotency key is required** (absent → fail closed).

**F6.** **SQLite `rowid` / `append_sequence` cannot be a domain identity** — assert identity derives
from content / provenance hashes only.

**F7.** **Replay output is repeatable** for the same audited input — re-running yields bit-identical
results (pinned in the test).

### Group G — Fail-Closed Literal and Reason Discipline

Future RED tests must require a **closed set** of validation failure reasons:

**G1.** **No ad-hoc failure literals** — the rejection `reason` must be a member of the validation
module's closed reason set (assert via membership import).

**G2.** **Missing / ambiguous provenance fails closed.**

**G3.** **Insufficient sample fails closed.**

**G4.** **Unstable metrics fail closed.**

**G5.** **Temporal leakage fails closed.**

**G6.** **Non-repeatable replay fails closed.**

**G7.** **Contaminated holdout fails closed.**

This charter **does not invent the literal names** — the future implementation defines a closed
validation reason set; these tests only require that such a closed set exists and is exclusively
used. No runtime behavior beyond these future test requirements is specified.

### Group H — Output Boundary RED Test Requirements

Future RED tests must prove:

**H1.** Output is an **offline validation report only**.

**H2.** **No S1 append** — assert the validation unit never calls an S1 append/ingest and never
opens a write-mode DB connection (AST inspection).

**H3.** **No durable production stream.**

**H4.** **No** signal, ranking, advice, trade, route, order, fill, cancel, sizing, allocation, or
capacity output — assert none of these field names exist on the report object.

**H5.** Output remains in the **non-actionable validation domain**.

### Group I — No Capacity / No Activation RED Test Requirements

Future RED tests must prove:

**I1.** Passing validation **does not unlock calibration**.

**I2.** Passing validation **does not unlock risk capacity**.

**I3.** Passing validation **does not unlock paper / canary / live**.

**I4.** Passing validation **does not unlock S1 append**.

**I5.** Passing validation **does not change Capacity from 0** (`CAPACITY == 0` constant asserted
before and after a passing validation).

**I6.** **No "good-validation ⇒ capacity" shortcut** — assert no code path converts a pass into an
activation.

### Group J — Next Gate

**J1.** This TDD charter only makes future RED tests **eligible** after an **explicit operator
command**.

**J2.** It **does not authorize** writing tests now.

**J3.** It **does not authorize** implementation.

**J4.** It **does not authorize** runtime.

**J5.** It **does not authorize** trading / actionability.

**J6.** **Capacity remains 0.**

---

## Section 4 — Minimal GREEN Boundary (future)

A future implementation may add **only**:

- an out-of-sample / replay validation module producing an **offline validation report only**;
- a test file with the Groups A–J above.

It must **not** add:

- durable S1 append, S1 activation, or production stream;
- calibration / trading / actionability / capacity;
- signal / ranking / advice / order / route / fill;
- network requests;
- daemon / background process.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this TDD charter.
2. The full Group A precondition chain, each step separately ratified.
3. Only after an explicit operator command: RED→GREEN out-of-sample / replay validation
   implementation.
4. Risk / capacity remains behind the ratified Phase G charter and a separate Risk / Capacity TDD
   Charter; trading remains behind separate paper → canary → live charters (Phase H).

## Post-state

- Out-of-Sample / Replay Validation TDD Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
