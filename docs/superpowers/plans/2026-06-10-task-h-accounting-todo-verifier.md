# Task H — Accounting TODO & Verifier Spec

Sanitized engineering spec for Faz 2c Task H (fill-confirm atomic accounting). Scope: TODO ordering + verifier checklist + guardrails. Implementation detail lives in the companion plan `2026-06-10-faz2c4-task-h-fill-confirm-accounting.md`.

---

## Accounting Constitution (binding)

> **No real and sufficient fill/cost proof → no position.**

- **Denomination:** FILLED vs PARTIAL_FILLED is decided in **USD** — `makingAmount` (actual USD spent) vs requested `position_usd`. `takingAmount` is **shares** and is never compared against the USD `requested`. Position shares come only from `takingAmount`. All fill arithmetic is `Decimal` / tick-safe.
- **No-fill-proof:** A response that returns `order_id`/accepted but no matched/executed fill leaves the intent in `SUBMITTED_UNKNOWN` (blocking; counted by `has_unresolved_intent`). `ACCEPTED` is not used in the live FAK path.
- **Invariant breach:** A FAK/IOC response showing a resting/open order (`live`/`delayed`/`open`/`resting`) is an invariant breach → `RECOVERY_REQUIRED` + CRITICAL log.
- **Cost missing → no position:** shares present but `makingAmount`/cost absent → do not open a position; never fabricate cost from `position_usd` or limit price → `RECOVERY_REQUIRED` + CRITICAL/ERROR → deferred to 2c-4.
- **Schema:** `positions(order_intent_id)` partial UNIQUE index `WHERE order_intent_id IS NOT NULL`; `positions.shares` nullable column. Migration is backfill-safe (legacy rows preserved), idempotent, and tested.
- **Atomicity:** position INSERT + `order_intents` terminal UPDATE happen in the **same connection, same transaction, same COMMIT**. If the intent terminal UPDATE fails after the INSERT, the whole transaction rolls back — a zombie position is never accepted, and a terminal intent without a position is never accepted. Intent is not marked FILLED/PARTIAL_FILLED unless the position INSERT succeeded.
- **Main loop:** double DB accounting is removed (single source = atomic `execute()`), but telemetry/log/notify visibility is preserved.
- **Duplicate accounting guard:** same `order_intent_id` reprocessed by Task H or 2c-4 reconcile must not open a second position — enforced by DB-level UNIQUE index + app-level precheck + existing monotonic terminal-state guard.

---

## TODO ordering — H0 → H6

| Step | Title | Output |
|------|-------|--------|
| **H0** | Writing-plan / spec | Companion implementation plan + this verifier spec sealed |
| **H1** | Schema / idempotency migration | `shares` column + partial UNIQUE index; backfill-safe, idempotent; migration tests |
| **H2** | Fill classification (denomination) | Pure USD-denominated, Decimal, breach-aware classifier; per-branch RED tests |
| **H3** | Atomic position write helper | Single-transaction INSERT position + UPDATE intent; rollback + duplicate tests |
| **H4** | execute() integration | Wire success path through classifier + atomic confirm + recovery ladder |
| **H5** | main_loop double-accounting cleanup | Remove second DB write, preserve telemetry/notify |
| **H6** | Final verification / checkpoint | Full regression green, graphify update, sealed checkpoint |

---

## Verifier checklist (per task)

- [ ] RED failed for the **correct reason** (feature missing, not a typo) — failure message inspected.
- [ ] GREEN is **minimal** — no over-engineering beyond the test.
- [ ] **Task E/F/G regression** still passes (timeout → SUBMITTED_UNKNOWN, connection/unknown → SUBMITTED_UNKNOWN, no-match → CANCELLED).
- [ ] Relevant suite passes (`test_execute_intent_wiring`, `test_clob_executor`, `test_emergency_pause`, `test_reconciliation`, `test_live_exec_lineage`, `test_fill_confirm`, plus new Task H + migration test files).
- [ ] Diff is confined to the **expected files** (no stray edits to frozen modules: `config.py`, `order_pricing.py`, `emergency_pause.py`, 2c-3 Task A–G logic).
- [ ] `git status --short` clean apart from known untracked artefacts.
- [ ] Operational guardrail: live `dry_run=0` open positions = **0**.
- [ ] No running `main_loop` / `watch` / `pytest` background process.
- [ ] `verification-before-completion` performed — evidence (command output) captured before any success claim.

---

## Guardrails

- No network access in tests; all tests use a temporary DB.
- No live process termination; **no main_loop restart** during development or test.
- Commits and pushes only with explicit human approval.
- Do not touch pre-existing untracked artefacts.
- Frozen modules are read-only references, not edit targets.
