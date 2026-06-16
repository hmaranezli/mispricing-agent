# Manual Order Script Guard (`analysis/test_order.py`)

## Status

`analysis/test_order.py` is a standalone, manually-run script that can post a real $1 CLOB order via
`client.create_and_post_order(..., FOK)`. It was flagged `BLOCKED_NEEDS_FOLLOWUP` by the post-bypass
authority scan (see `docs/protocols/council_decision_authority_bypass.md`) as a **non-council**
execution path. It now has a **default-safe guard**: by default it posts nothing.

## Guard

- Env flag `MANUAL_ORDER_SCRIPT_ENABLED` (default unset → disabled).
- `_manual_order_enabled()` returns True only when the env value is one of `1` / `true` / `yes` /
  `on` (case-insensitive).
- `run_test()` checks the guard **first** and, when disabled, prints a `[manual_order_guard] BLOCKED`
  line and returns `False` **before** constructing any client and **before** any
  `create_and_post_order` call. No balance read, no market fetch, no order.

## Behavior

- **Default (flag unset):** the script blocks before posting; importing the module posts nothing
  (posting lives inside `run_test()` under `__main__`).
- **Explicit opt-in (`MANUAL_ORDER_SCRIPT_ENABLED=1`):** the script proceeds along its original path.
- This guard is independent of `DRY_RUN`, the council bypass, and `NEW_ENTRIES_ENABLED`; it does not
  enable any automated path and is not reachable from `main_loop`/council. The only trigger is a
  manual run plus an explicit opt-in env value.

## Tests

`tests/test_manual_order_script_guard.py` (offline, fake client only):
- flag defaults disabled;
- importing the module posts nothing;
- default path blocks before client construction / `create_and_post_order`;
- the explicit opt-in path uses only the fake client (no network).

## No-claims

This guard makes no edge / PnL / profitability / alpha / readiness claim and authorizes no trading,
paper, or live deployment. It only prevents a manual script from posting orders by default. Any live
use remains a separate, explicitly-authorized operator action.
