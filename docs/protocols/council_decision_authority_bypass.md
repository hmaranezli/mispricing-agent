# Council Decision-Authority Bypass

<!-- FRAMING-START -->
## Status

Council **decision authority is disconnected from execution authority**. Following the de-risk gate
result `FOLLOW_UP_REMOVE_OR_BYPASS`, a council/multi-agent PASS can no longer, by default, reach
`execute()`, the executors (`_dry_execute` / `_clob_execute`), or order-intent creation. The council
is **not** a runtime LLM, but it **was** trade-path connected; it now runs **diagnostic-only**.

This bypass **enforces a narrower authority model** and **reduces ambiguity before Phase 5**. It
**does not** prove system safety, and it authorizes nothing.
<!-- FRAMING-END -->

## What changed (narrowest scope)

- `config.py`: added a default-disabled kill switch `COUNCIL_DECISION_AUTHORITY_ENABLED = False`.
- `main_loop.py`: immediately after a council PASS is unpacked (before any entry-gate logic), a guard
  short-circuits when `COUNCIL_DECISION_AUTHORITY_ENABLED` is False — logging a `[council_bypass]`
  diagnostic line and skipping the candidate. `execute()` / `_dry_execute` / `_clob_execute` and
  `execution/order_intent.py` were **not** modified.
- No council file was deleted or refactored; the council package remains imported and is exercised as
  **diagnostic-only** (it still runs scout→verifier→redteam→risk→gate and writes candidate/shadow
  telemetry), but its output is disconnected from execution authority.

## Default-safe behavior (proven by tests)

By default (`COUNCIL_DECISION_AUTHORITY_ENABLED = False`):

- a council PASS **cannot call `execute()`**;
- a council PASS **cannot reach `_dry_execute` or `_clob_execute`**;
- a council PASS **cannot create an order intent** (`order_intent.create_intent`);
- a council gate `pass` / `confidence_score` **cannot authorize execution**;
- council `risk` / Kelly / veto output **cannot override** execution authority;
- the council still runs (diagnostic), but opens no position.

Enabling the flag is the **sole opt-in control** that restores routing; even when enabled,
execution routing **still obeys `DRY_RUN`** and never selects the live (`_clob_execute`) path while
`DRY_RUN` is true. The flag **cannot bypass `DRY_RUN`** and introduces no new live/paper path. The
`DRY_RUN` default and all existing safety defaults are unchanged.

<!-- RED-LINES-START -->
## Red lines (unchanged, restated)

LLM/council components must not: approve trades; approve edge; create order intents; override risk;
authorize execution; or authorize paper/live readiness. They must make no profitability / alpha /
edge / readiness claims.
<!-- RED-LINES-END -->

## Remaining council role

Any remaining council code is **legacy / read-only / diagnostic** unless separately reauthorized by
tests and operator approval. The intended authority model remains **deterministic risk/verification
plus the operator gate** (and the `DRY_RUN` default); the evidence verifier checks scoped invariants
only.

## Post-bypass authority scan (read-only)

Scan of non-test call sites of `execute()` / `_dry_execute` / `_clob_execute` / `create_intent` /
`order_intent` / council / gate at the bypass commit:

- The automated executor path (`execute()` → `_dry_execute`/`_clob_execute` → `clob_executor` →
  `order_intent.create_intent`) has a single non-test entry in the runtime loop at
  `main_loop.py` (the `_scan_and_execute` call site), now behind the council bypass guard;
  `create_intent` is reachable only via `_clob_execute`, i.e. only when `DRY_RUN` is false.
- `data/shadow_quote.py` and `council/redteam.py` reference `clob_executor` only in **comments**
  (constant alignment), not as execution calls.

**BLOCKED_NEEDS_FOLLOWUP** — a separate, non-council execution path exists:
`analysis/test_order.py` (a standalone manual script) calls
`client.create_and_post_order(order_args, order_type=OrderType.FOK)` at lines ~112 and ~144,
posting orders directly via the CLOB client, independent of the council and of the bypass guard. It
is **not** part of the automated `main_loop` runtime and was **not modified** in this task (it is not
council and not required for the council bypass). A separate authorized task should review whether
this manual script needs its own guard. This scan does not claim that no other such path exists in
any absolute sense.

<!-- NO-CLAIMS-START -->
## No-claims statement

This bypass makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no system-ready, no ready-to-fly, and no
ready claim**. It does not prove the system is safe or deterministic, does not guarantee correctness,
and does not authorize trading, paper deployment, or live deployment. The deterministic risk
contract is **not** implemented in this task, and no Kelly/risk model was migrated or validated here.
<!-- NO-CLAIMS-END -->

## Future work (separate authorization required)

- The **deterministic risk contract** remains a separate, later task.
- Any council re-authorization, or guarding of the `analysis/test_order.py` manual path, is a
  separate task gated by tests and operator approval.
- **Future Phase 5 work still requires separate authorization, TDD, and review**; Phase 5
  implementation remains unauthorized and must be TDD/offline first.
