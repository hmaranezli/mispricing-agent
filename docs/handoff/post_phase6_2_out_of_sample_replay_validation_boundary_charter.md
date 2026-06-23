# Post-Phase 6.2 Out-of-Sample / Replay Validation Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only.** It defines the requirements any future out-of-sample and
  deterministic replay validation stage must satisfy. It **implements nothing** and
  **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** implementation, S1 append, production S1 stream, paper / canary / live /
  trading / routing / actionability, or capacity.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Calibration / Analysis Offline Boundary Charter: RATIFIED at `fdc68c7`.**
- **S1 append: DENIED.** **Production S1 stream: BLOCKED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `fdc68c7243fa6d535771b25bb21d2285e6d51316`.
- Parent chain:
  - `fdc68c7243fa6d535771b25bb21d2285e6d51316` = **RATIFIED** Calibration / Analysis Offline
    Mathematical Boundary Charter.
  - `dc587fbd22d137ec2094d8d17af727238909c267` = **RATIFIED** Phase G Risk / Capacity Mathematical
    Boundary Charter.
  - `68b0d9c47490a3a208a8735d8ed89e595284b054` = **RATIFIED** Semantic Projection Validation TDD
    Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter (Phase G step 7: out-of-sample / replay validation).
- This charter elaborates the **out-of-sample / replay validation** precondition (Phase G step 7 of
  the ratified Post-Run Roadmap). It does not supersede, relax, or accelerate any prior gate.

## Section 2 — Charter Intent

- This charter draws the **validation boundary**: what evidence may be held out, how replay must be
  deterministic, what mathematics must be pre-defined, what conditions force fail-closed, and what
  the validation may never emit.
- It exists to make **train/test contamination, lookahead, post-hoc window selection, and
  "good-validation⇒capacity" drift structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Validation Scope

1. This charter defines **requirements only**.
2. It authorizes **no** tests, **no** implementation, **no** runtime, **no** S1 append, **no**
   trading, **no** capacity.
3. Any future validation must run **fully offline**, against already-captured, already-ratified
   evidence — never against live feeds, never during a live run.

### Gate B — Preconditions

Out-of-sample / replay validation may only be **considered** after **all** of the following are
separately complete and ratified, in order:

1. prior raw-only 24h run **complete / stopped** within ratified bounds;
2. Read-Only Continuous Ledger Audit **CLEAN**;
3. semantic projection validation **clean**;
4. Calibration / Analysis Offline Boundary Charter **ratified** (and calibration completed under
   it);
5. Phase G Risk / Capacity Mathematical Boundary Charter **ratified**;
6. an **explicit future operator command**.

Any unsatisfied precondition **blocks** validation.

### Gate C — Replay / Holdout Separation

1. Define **train / calibration evidence** versus **holdout / out-of-sample evidence** as
   **disjoint, pre-declared sets**.
2. **No train/test contamination** — no record may appear in both the calibration set and the
   holdout set.
3. **No post-hoc window selection** — holdout windows must be declared **before** any metric is
   computed; windows may not be reselected to flatter results.
4. The split rule must be **deterministic and temporal** (holdout strictly after / disjoint from
   the calibration window, per the ratified event-time alignment).

### Gate D — Anti-Leakage Rules

1. **No lookahead** — validation at event-time `t` may use only information available at or before
   `t` (event-time, not retrieval-time).
2. **No survivorship bias** — excluded / failed cycles must be accounted for, not silently dropped.
3. **No body-mining** — only ratified semantic fields may be used; no mining of raw bodies for
   unratified signals.
4. **No future outcome leakage** — no target/outcome value may enter the feature/computation path
   ahead of its event-time.
5. **No manual cherry-picking** — no record, window, or metric may be hand-selected to improve the
   reported result.

### Gate E — Mandatory Explicit Mathematical Validation Definitions

The future validation must define **all** of the following as **explicit, deterministic
mathematics** (`Decimal` / `int` compatible; **none** may create signal or trade authority):

| Definition | Requirement |
|------------|-------------|
| `sample_size_N` | explicit integer count of holdout observations, formula pinned |
| `coverage_ratio` | explicit ratio (covered / expected), `Decimal`, with denominator-zero fail-closed |
| `holdout_window_count` | explicit integer count of disjoint replay windows |
| `confidence_interval` | explicit method + level (two-sided, stated alpha), error band formula |
| `false_positive_rate` | explicit `Decimal` formula over the holdout |
| `false_negative_rate` | explicit `Decimal` formula over the holdout |
| `stability_across_replay_windows` | explicit deterministic dispersion metric across windows + threshold |

Every definition must be reproducible from inputs + a fixed key; no value may be chosen
interactively. **No formula may emit a tradeable signal, ranking, or sizing.**

### Gate F — Deterministic Replay Requirements

Any future replay must be **bit-reproducible** and carry:

- the ratified **commit SHA**;
- input **artifact hashes**;
- a **config fingerprint** (exact parameter set);
- **S1 / audit provenance references**;
- a **deterministic idempotency key**.

Re-running with the same inputs + key must reproduce **bit-identical** validation results.
**SQLite `rowid` / `sqlite_sequence` must never be a domain identity** — identity derives from
content / provenance hashes only.

### Gate G — Fail-Closed Validation Doctrine

Validation must **fail closed** (no pass, no downstream eligibility) for any of:

- **insufficient sample** (`sample_size_N` below the pre-declared minimum);
- **missing provenance**;
- **unstable metrics** (stability metric beyond the pre-declared threshold);
- **replay non-repeatability** (results not bit-identical on re-run);
- **temporal leakage** detected;
- **contaminated holdout** (overlap with calibration set);
- **missing artifact hash**;
- **ambiguous source authority**.

The default in every ambiguous or error state is **FAIL** — never a permissive pass.

### Gate H — Output Boundary

1. Validation may produce an **offline validation report only**.
2. **No durable production stream.**
3. **No S1 append.**
4. **No** signal / ranking / advice.
5. **No** trading / actionability / capacity output.

### Gate I — Separation from Calibration, Risk, and Capacity

1. Passing validation **does not unlock calibration**.
2. Passing validation **does not unlock risk capacity**.
3. Passing validation **does not unlock paper / canary / live**.
4. **No "good validation ⇒ capacity" shortcut.** A clean validation is an **input** to later gates,
   never a trigger.

### Gate J — Next Gate / No Auto-Activation

1. The next step can only be a future **TDD or implementation charter** after an **explicit operator
   command**.
2. **Clean validation does not auto-enable anything.**
3. Each subsequent step requires its own boundary charter, review, TDD charter, RED→GREEN
   implementation, and explicit operator command (per the ratified Post-Run Roadmap &
   No-Auto-Activation Charter).
4. **Capacity remains 0.**

---

## Section 4 — Validation Definition Ledger (template, to be completed later)

No value is asserted now. A future Out-of-Sample / Replay Validation TDD Charter must populate this
with explicit deterministic definitions, pre-registered before any metric is computed:

| Definition | Formula / Rule | Type | Pre-registered | Status |
|------------|----------------|------|----------------|--------|
| sample_size_N | PENDING | int | PENDING | PENDING |
| coverage_ratio | PENDING | Decimal | PENDING | PENDING |
| holdout_window_count | PENDING | int | PENDING | PENDING |
| confidence_interval | PENDING | Decimal | PENDING | PENDING |
| false_positive_rate | PENDING | Decimal | PENDING | PENDING |
| false_negative_rate | PENDING | Decimal | PENDING | PENDING |
| stability_across_replay_windows | PENDING | Decimal | PENDING | PENDING |

All rows must carry an explicit deterministic formula and be pre-registered before results are
computed.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this out-of-sample / replay validation boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only then: a separate **Out-of-Sample / Replay Validation TDD Charter**.
4. Risk / capacity remains behind the ratified Phase G charter and a separate Risk / Capacity TDD
   Charter; trading remains behind separate paper → canary → live charters (Phase H).

## Post-state

- Out-of-Sample / Replay Validation Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 append: **DENIED / NOT PERFORMED**.
- Production S1 stream: **BLOCKED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
