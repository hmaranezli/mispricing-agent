# Phase 5 → Live Canary Roadmap (Charter)

> **Purpose:** This document is a repo-durable charter that names the ordered route
> from Phase 5 Capacity Constraint closeout through shadow observation, calibration,
> paper, paper canary, and live canary. It exists to prevent unplanned
> "next component not selected" stops: after each stage completes, the next stage is
> already named here. It does **not** authorize implementation of any future phase by
> itself — see §3, §6, and §7.

---

## 1. Current State

Anchored at master SHA **`e5f543844b8bdf5322ba85e3fe8e8cb90c71886b`**.

- **Phase 5 Capacity Constraint is structurally complete** at
  `e5f543844b8bdf5322ba85e3fe8e8cb90c71886b`.
- **UNDEFINED** remains **defined / reserved / deferred** with **0 emit sites**.
- **`CapacityConstraintEvidenceBoundary`** class is **cancelled / satisfied-by**
  **`CapacityConstraintGate.preflight`**.
- **No** Phase-6, paper, live, production, routing, sizing, allocation,
  wallet/balance runtime, execution, or actionability readiness is implied by the
  current state. None of these exist and none are authorized here except as scoped
  in §3.

---

## 2. Route Selection (ordered)

The route from Phase 5 closeout to live canary is fixed in the following order. No
stage may be skipped or reordered.

| Stage | Name | One-line scope |
|-------|------|----------------|
| **Phase 6.1** | Read-only Live Public-Data Opportunity Observation / Shadow Scoring | Passively observe public market data and score hypothetical opportunities; write durable replayable shadow logs. No account access, no order semantics. |
| **Phase 6.2** | Quantitative Calibration from shadow logs | Derive and calibrate quantitative parameters strictly from Phase 6.1 shadow logs. No live action. |
| **Phase 7.1** | Internal Paper Simulator | Simulate fills/positions internally against recorded/replayed data. No external broker, no wallet. |
| **Phase 7.2** | Paper Canary | Paper trading restricted to sandbox/testnet **or** internal paper broker only. No real funds. |
| **Phase 8.1** | Live Canary | Real wallet, **only** after separate explicit authorization, micro-exposure limits, and a kill-switch. |

---

## 3. Immediate Authorization

- **Authorized now:** Phase 6.1 **read-only readiness extraction** only — i.e.,
  determining and documenting what a read-only shadow observer would require.
- **Not authorized now:** Phase 6.1 **implementation**. Implementation of Phase 6.1
  begins only if separately approved **after** the readiness extraction is reviewed.
- Nothing beyond Phase 6.1 readiness extraction is authorized by this document.

---

## 4. Phase 6.1 Hard Barrier

Phase 6.1 (and its readiness extraction) operate under a hard barrier.

**Allowed:**
- public market-data reads only;
- durable, replayable shadow logs;
- passive scoring;
- no secrets required;
- no private account endpoints.

**Forbidden:**
- wallet;
- private balance;
- order intent;
- order routing;
- execution;
- paper/live trading;
- allocation/sizing as an actionable order quantity;
- candidate/signal/order semantics.

Crossing any item in the Forbidden list is out of scope for Phase 6.1 and requires a
separate phase and separate authorization.

---

## 5. Quantitative Gates (minimum categories before promotion)

Before any stage is promoted to the next, the following gate categories must be
defined, measured, and satisfied. (Concrete thresholds are set per-stage at the time
that stage's gate is authorized; this charter fixes the required categories.)

- **shadow observation duration** — minimum elapsed observation window;
- **minimum opportunity count** — minimum number of observed opportunities;
- **stale/missing-data rate** — bounded rate of stale or missing public data;
- **post-fee/slippage expected value** — expected value remains positive after
  modeled fees and slippage;
- **latency / opportunity lifetime distribution** — characterized and within bounds;
- **replay reproducibility** — shadow logs replay deterministically;
- **crash-free operation** — sustained operation without crashes over the window;
- **out-of-sample calibration check** — calibration validated on held-out data;
- **kill-switch readiness** — verified before any paper/live boundary.

---

## 6. No Automatic Downstream Authorization

Naming a stage in this roadmap is **not** authorization to begin it. The following
remain **separately gated** and require **explicit future authorization**:

- paper;
- paper canary;
- live canary;
- wallet access;
- private exchange endpoints;
- real order placement.

---

## 7. No Surprise Stop Rule

After each completed stage, the next stage is **already named** by this roadmap
(§2), so there is no "next component not selected" stop. However, work on the next
stage may begin **only** when both of the following hold:

1. the documented gate (§5) for that promotion is passed; **and**
2. explicit user authorization for that specific stage is received.

Until both hold, the system waits — without ambiguity about what comes next.
