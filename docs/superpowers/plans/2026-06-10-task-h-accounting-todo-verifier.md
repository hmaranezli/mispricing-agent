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

> **H6 checkpoint durumu (2026-06-11):** Step 3 regression **green** (curated H6 suite **109 passed**, pollution yok; H4+H5 isolated 58, mainloop 7) + Step 4 graphify **done**, sealed **`e2cd152`** (pushed; 4241 nodes / 6594 edges / 313 communities, AST-only). Step 1 `H6_STEP1_ALREADY_COVERED_BY_EXISTING_TESTS` ile kapandı (`b326f93`). Step 3 regression green + Step 4 graphify done sealed `e2cd152`; H6 final checkpoint evidence captured; code/test unchanged (`bba2aaa..HEAD` `*.py` diff boş; yalnız docs + graphify-out). **ACCEPTANCE (2026-06-11):** H6 accepted with traceability exception recorded — item 1 TRACEABILITY_ACCEPTED; items 2–9 PASS via independent LLM verifier + independent adversarial code-review subagent (not Gemini); sealed verifier evidence `11fb9c4`; raw FULL_PASS not claimed. See section "B. H6 Final Software Checkpoint — Acceptance".

> **H6 Step 1 — `H6_STEP1_ALREADY_COVERED_BY_EXISTING_TESTS` (2026-06-11):** literal `test_repeated_response_processing_no_second_position` testi **gerekmiyor / yazılmadı.** "Duplicate-on-repeat → ikinci position YOK (D6)" invariant'ı merkezi idempotency guard üzerinden mevcut testlerle kapsanmış: `test_task_h_fill_confirm.py::test_duplicate_intent_second_confirm_is_noop_readback_proof` + `::test_integrity_error_readback_existing_duplicate_is_noop`, `test_execute_intent_wiring.py::test_duplicate_returns_existing_position_id_not_candidate_uuid` (+ H4-9 readback-empty recovery), `test_mainloop_accounting.py::test_mainloop_duplicate_warning_no_append_no_ws_no_write`. `confirm_fill_atomic` duplicate guard, `order_intent_id` precheck ile fill classification'dan ÖNCE çalışır → `FILLED`/`PARTIAL_FILLED` farkı sonucu değiştirmez. Literal test direct-green olur → no-fake-RED disiplinine aykırı. Detay: companion plan H6 Step 1.

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

## B. H6 Final Software Checkpoint — Acceptance (2026-06-11)

> Sealed verifier evidence: `docs/superpowers/evidence/2026-06-11-h6-verifier-current-session.txt` @ commit **`11fb9c4`**. Raw FULL_PASS is **not** claimed; accepted with the item-1 traceability exception below.

- [x] **Independent read-only LLM verifier** — fresh-context subagent (same model family, not the implementer's context); re-ran the gating commands read-only instead of trusting prose. Verdict: items 3–9 PASS; items 1–2 BLOCKED at that time.
  - _Note: 8/9 PASS + item 1 TRACEABILITY_ACCEPTED; raw FULL_PASS iddia edilmiyor; sealed evidence: `11fb9c4`._
- [x] **Independent adversarial code-review subagent (NOT Gemini)** — item 2 "GREEN minimal / no over-engineering" scope (`git diff 19e5aa5..bba2aaa`). Verdict: PASS — every added production construct traces to a named test; no over-engineering. (No Gemini review was run; this was an independent code-review subagent.)
  - _Note: No blocker after TRACEABILITY_ACCEPTED decision; independent code-review subagent, not Gemini; sealed evidence: `11fb9c4`._
- [x] **H6 PASS acceptance + memory update** — item 1 "RED failed for the correct reason" closed by human/architectural decision **TRACEABILITY_ACCEPTED**: raw historical RED output does not exist and cannot be reliably reconstructed; H3b test-first commit (`b8c638a`) + per-task plan "Step 2: Run→FAIL" + H6 no-fake-RED note are accepted as sufficient traceability. The gap is explicitly acknowledged, not papered over.
  - _Note: H6 accepted with traceability exception recorded; sealed evidence: `11fb9c4`._

> **Net gate:** item 1 = TRACEABILITY_ACCEPTED; items 2–9 = PASS (8/9 PASS). No item FAIL. No fabricated evidence. This is acceptance with a recorded exception — **not** a raw H6_VERIFIER_GATE_FULL_PASS.

---

## Guardrails

- No network access in tests; all tests use a temporary DB.
- No live process termination; **no main_loop restart** during development or test.
- Commits and pushes only with explicit human approval.
- Do not touch pre-existing untracked artefacts.
- Frozen modules are read-only references, not edit targets.
