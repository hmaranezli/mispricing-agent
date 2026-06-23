# Post-Phase 6.2 Calibration / Analysis Offline Mathematical Boundary Charter

## Status

- This charter: **BUILT / RATIFIABLE / UNRATIFIED** pending independent review.
- **Docs-only, future-only, offline-only.** It defines the mathematical and provenance boundaries
  any future calibration / analysis stage must satisfy. It **implements nothing** and
  **authorizes nothing**.
- It edits **no** runtime / test / schema / config / lock / generated / tracking / export file.
- It performs **no** network request, **no** test run, **no** code modification.
- It reads / writes **no** live ledger or S1 DB.
- It does **not** stop, restart, inspect, or disturb the running tmux session `mispricing_run_001`.
- It **authorizes no** S1 append, signal generation, paper trading, canary, live trading, routing,
  execution, orders, or capital use.
- **First bounded raw-only 24h run: ALIVE / IN PROGRESS / NOT DISTURBED.**
- **Read-Only Audit implementation: BLOCKED / UNSTARTED.**
- **Phase G Risk / Capacity Mathematical Boundary Charter: RATIFIED at `dc587fb`.**
- **S1 Stream Authorization / Production Append: BLOCKED / UNSTARTED.**
- **Calibration / trading / actionability: BLOCKED.**
- **Capacity: 0.**

---

## Section 1 — Base / Status Lock

- Base / head at chartering: `dc587fbd22d137ec2094d8d17af727238909c267`.
- Parent chain:
  - `dc587fbd22d137ec2094d8d17af727238909c267` = **RATIFIED** Phase G Risk / Capacity Mathematical
    Boundary Charter.
  - `68b0d9c47490a3a208a8735d8ed89e595284b054` = **RATIFIED** Semantic Projection Validation TDD
    Charter.
  - `9bdfb88687296f38f1003a21c771736c3a4b4ec2` = **RATIFIED** Post-Run Roadmap &
    No-Auto-Activation Charter (Phase F is sequenced there).
- This charter elaborates **Phase F** (Calibration / Analysis) of the ratified Post-Run Roadmap. It
  does not supersede, relax, or accelerate any prior gate, and it sits **before** the Phase G
  risk/capacity gate in actionability terms (analysis never unlocks capacity).

## Section 2 — Charter Intent

- This charter draws the **offline analytical boundary**: what calibration / analysis may consume,
  what it may never mutate, what mathematics must be pre-defined, and what it may never emit.
- It exists to make **lookahead, leakage, data mining, and "profitable-backtest⇒capacity" drift
  structurally impossible**.

---

## Section 3 — Boundary Gates

### Gate A — Future-Only Offline Scope

1. This charter is **future-only** and **offline-only**.
2. It creates **no** calibration runtime, analysis runtime, signal logic, or actionability.
3. It authorizes **no** live data access, **no** trading, **no** capacity.
4. Any future calibration / analysis must run **fully offline**, against already-captured,
   already-ratified evidence — **never** against live feeds, **never** during a live run.

### Gate B — Preconditions

Calibration / analysis may only be **considered** after **all** of the following are separately
complete and ratified, in order:

1. raw-only 24h run **completed / stopped** within ratified bounds;
2. Read-Only Continuous Ledger Audit **CLEAN**;
3. S1 Stream Authorization **separately ratified**;
4. S1 append / projection **separately ratified and clean**;
5. semantic projection validation **separately implemented and clean**.

A DIRTY audit, an unratified S1 authorization, or unvalidated projection **blocks** calibration.

### Gate C — Calibration Inputs Must Be Ratified / Provenance-Backed Only

1. Calibration may consume **only** ratified, provenance-backed inputs:
   - audited raw ledger evidence (read-only),
   - ratified S1 projection records (read-only),
   - explicitly versioned parameter sources.
2. **No** input may originate from an unratified source, an ad-hoc scrape, or a hand-edited file.
3. Every input must carry **commit SHA + content hash + run id** provenance (Gate H).

### Gate D — No Mutation (read-only inputs)

1. The **raw ledger** is **read-only** during calibration (`file:?mode=ro`); calibration must never
   INSERT / UPDATE / DELETE / DDL it.
2. The **S1 database** is **read-only** during calibration; calibration must never mutate it.
3. **Audit artifacts** are **read-only** and immutable; calibration must never overwrite them.
4. Calibration outputs must be written **only** to a **separate** offline analysis artifact store —
   never back into raw, S1, or audit stores.

### Gate E — Mathematical Definitions Required Before Analysis

The future calibration must define **all** of the following as **explicit, deterministic
mathematics** (no prose-only or discretionary definitions):

| Definition | Requirement |
|------------|-------------|
| `sampling_window` | explicit time window + boundary inclusivity (open/closed) |
| `event_time_alignment` | explicit rule using source event time (`$.timestamp` / `$.time`), never retrieval time |
| `missing_data_policy` | explicit deterministic handling of absent legs/fields (fail-closed default) |
| `outlier_policy` | explicit numeric rule (e.g. fixed bound / quantile), pre-registered, not tuned post hoc |
| `confidence_interval` | explicit method + level (e.g. two-sided, stated alpha) |
| `train_test_split` | explicit deterministic split rule with no temporal overlap |
| `leakage_controls` | explicit enumerated controls (Gate F) |

Each must be reproducible from inputs + a fixed seed/key; no value may be chosen interactively
during analysis.

### Gate F — Bias / Leakage Prevention

1. **No lookahead** — analysis at time `t` may use only information available at or before `t`
   (event-time, not retrieval-time, governs ordering).
2. **No survivorship shortcut** — excluded/failed cycles must be accounted for, not silently
   dropped to flatter the result.
3. **No endpoint / body mining outside ratified fields** — analysis may use **only** the ratified
   semantic fields (timestamps, top-of-book BID/ASK, ratified provenance); it may not data-mine raw
   bodies for unratified signals.
4. Train/test boundaries must be **temporally disjoint**; no record may appear in both.
5. Outlier and missing-data policies must be **pre-registered** in the calibration charter before
   results are computed — never tuned to the observed outcome.

### Gate G — Output Boundary

1. Calibration / analysis may produce an **offline report only**.
2. **No** signal, **no** ranking, **no** advice, **no** trade trigger, **no** sizing, **no** order.
3. **No** edge/profit claim may be presented as actionable; any estimate is **explicitly
   non-actionable** unless a separate later charter authorizes it.
4. The report must not write to any execution, routing, or capacity path.

### Gate H — Reproducibility / Provenance

Any future calibration result must be **fully reproducible** and carry:

- the ratified **commit SHA**,
- the input **data hash(es)**,
- the **run id** of the producing raw run,
- a **config fingerprint** (exact parameter set used),
- a **deterministic replay key**.

Re-running with the same inputs + key must reproduce **bit-identical** report results.
**SQLite `rowid` / `sqlite_sequence` must never be a domain identity** — identity derives from
content/provenance hashes only.

### Gate I — Separation from Risk / Capacity

1. A **profitable analysis does not unlock capacity.** Capacity remains 0 regardless of any
   favorable calibration outcome.
2. Calibration **may estimate distributions** but is **never, by itself, an authorization** for
   risk, capacity, or trading.
3. The Phase G risk/capacity gate and any future capacity charter remain **strictly separate** and
   downstream; calibration is an **input** to them, never a trigger.
4. **No "profitable backtest therefore capacity" shortcut.**

### Gate J — Next Gate

1. This charter only makes a future **Calibration TDD Charter** *eligible* — and only after the
   full Gate B precondition chain is separately satisfied and ratified.
2. It **does not authorize** implementation, tests, S1, signal, trading, paper, canary, live, or
   capacity.
3. **No auto-activation.** Each subsequent step requires its own boundary charter, review, TDD
   charter, RED→GREEN implementation, and explicit operator command (per the ratified Post-Run
   Roadmap & No-Auto-Activation Charter).
4. **Capacity remains 0.**

---

## Section 4 — Calibration Definition Ledger (template, to be completed later)

No value is asserted now. A future Calibration TDD Charter must populate this with explicit
deterministic definitions before any analysis may be computed:

| Definition | Formula / Rule | Source | Pre-registered | Status |
|------------|----------------|--------|----------------|--------|
| sampling_window | PENDING | PENDING | PENDING | PENDING |
| event_time_alignment | PENDING | PENDING | PENDING | PENDING |
| missing_data_policy | PENDING | PENDING | PENDING | PENDING |
| outlier_policy | PENDING | PENDING | PENDING | PENDING |
| confidence_interval | PENDING | PENDING | PENDING | PENDING |
| train_test_split | PENDING | PENDING | PENDING | PENDING |
| leakage_controls | PENDING | PENDING | PENDING | PENDING |

All rows must carry an explicit deterministic definition and a ratified source, pre-registered
before results are computed.

## Section 5 — Next Gates

Only next safe gates:

1. Independent review of this Calibration / Analysis offline boundary charter.
2. The full Gate B precondition chain, each step separately ratified.
3. Only then: a separate **Calibration TDD Charter**.
4. Risk / capacity remains behind the ratified Phase G charter and a separate Risk / Capacity TDD
   Charter; trading remains behind separate paper → canary → live charters (Phase H).

## Post-state

- Calibration / Analysis Offline Mathematical Boundary Charter: **BUILT / RATIFIABLE / UNRATIFIED**.
- First bounded raw-only 24h run: **ALIVE / IN PROGRESS / NOT DISTURBED**.
- Read-Only Audit implementation: **BLOCKED / UNSTARTED**.
- S1 Stream Authorization / Production Append: **BLOCKED / UNSTARTED**.
- Calibration / trading / actionability: **BLOCKED**.
- Capacity: **0**.
