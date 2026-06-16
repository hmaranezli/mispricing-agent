# Phase 5 Friction-Component Schema Contract

<!-- FRAMING-START -->
## Status and framing

This document defines a **contract only** — it is **offline, observation and planning only**. It
follows the [Phase 5 Planning-Only Protocol / Design Gate](phase5_planning_gate.md) and refines §2
("Friction component schema") of the [Phase 5 Offline Interface Contract](phase5_interface_contract.md).

This contract:

- **must not** authorize implementation; no implementation is authorized by this document;
- **must not** build a net-edge calculator or any aggregation engine;
- **must not** connect to any live order path or execution path;
- **defines** the field-level shape of a friction-cost taxonomy so schema drift is detectable later;
- **is not a mathematical proof** and **does not** assign economic meaning to any field.

**Implementation still requires separate TDD and explicit authorization.** Any future Phase 5
implementation must be separately authorized and TDD/offline first.
<!-- FRAMING-END -->

## 1. Scope

This schema is **observation and planning only**. It enumerates named friction-component slots and
the per-component fields each slot must declare. It reserves structure; it **must not** populate any
value, and it **must not** be read as an economic result.

## 2. Required friction components

The following component placeholders are **required** by this contract. Each is a named slot only;
no value is authorized here.

- `spread_cost`
- `fee_cost`
- `slippage_cost`
- `depth_cost`
- `discovery_cost`
- `latency_or_staleness_cost`
- `uncertainty_buffer`

## 3. Required per-component fields

Every component above **must** declare all of the following fields:

- `name` — the component identifier.
- `unit` — the unit of measure for the component (declared, not assumed).
- `numeric_representation` — the representation rule for the value (see §4).
- `sign_convention` — the sign rule for the value (see §5).
- `source_artifact` — the read-only artifact the value is observed/derived from (see §6).
- `source_field` — the exact field within `source_artifact` (see §6).
- `deterministic_formula_or_blocked_reason` — the deterministic, evidence-backed formula, **or** an
  explicit blocked reason when no such formula is yet authorized.
- `status` — one of `observed | derived | blocked`.

### Per-component status table (contract-only; all values to be populated under later authorization)

| component | provisional unit | status | source_artifact | source_field | deterministic_formula_or_blocked_reason |
|---|---|---|---|---|---|
| `spread_cost` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: deterministic formula not yet authorized |
| `fee_cost` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: evidence source not yet fixed |
| `slippage_cost` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: evidence source not yet fixed |
| `depth_cost` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: evidence source not yet fixed |
| `discovery_cost` | mechanical count → cost (Decimal) | blocked | (required evidence) | (required evidence) | blocked: deterministic mapping not yet authorized |
| `latency_or_staleness_cost` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: deterministic formula not yet authorized |
| `uncertainty_buffer` | price-fraction (Decimal) | blocked | (required evidence) | (required evidence) | blocked: deterministic formula not yet authorized |

Status values are sample/contract labels only; a `blocked` status records absent evidence, not a
zero value.

## 4. Numeric representation

- Money and edge math **must not** use binary floating-point authority. **Binary floating-point**
  values **must not** carry money/edge authority in any future implementation.
- The contract **prefers Decimal or integer-scaled units** (for example, integer micro-units) for
  every monetary or edge quantity. Each `numeric_representation` field **must** declare Decimal or an
  integer-scaled unit, never a bare binary float.

## 5. Sign convention

- Every friction component is a **non-negative deduction** from gross edge. A component value
  **must** be `>= 0`; it reduces gross edge and **must not** be negative.
- Each `sign_convention` field **must** restate this: the component is a non-negative deduction from
  gross edge, never an addition.

## 6. Provenance

- Every component **must** declare both `source_artifact` and `source_field` pointing at read-only
  Phase 3D5/4A/4B evidence.
- **Missing provenance** (absent `source_artifact` or `source_field`) **must** yield
  `BLOCKED_NEEDS_EVIDENCE`. Provenance **must not** be inferred, defaulted, or fabricated.
- Generated `data/output` artifacts are read-only evidence; they remain **untracked** and are never
  staged or committed.

## 7. Fail-closed behavior

- The contract **must fail closed**. Any missing component, missing `source_artifact`/`source_field`,
  or missing `deterministic_formula_or_blocked_reason` **must** yield `BLOCKED_NEEDS_EVIDENCE` —
  **never zero**, never a default, never a guessed value.
- A `blocked` component **must** halt aggregation (see §9); it **must not** be silently treated as
  `0`.

## 8. No fixed, default, floor, guessed, or baseline costs

- **No fixed cost, no default cost, no floor cost, no guessed constant, and no baseline overhead** is
  authorized by this contract. No value, constant, or overhead **is authorized** here.
- Every component value **must** be either `observed` or `derived` from declared evidence, or else
  `blocked`. There is no authorized middle path of assumed numbers.

## 9. Aggregation rule (contract-only)

- Aggregation is **deferred** and **must not** be implemented by this document; this contract builds
  no net-edge calculator.
- Contract rule: **No net-edge aggregation may proceed unless every required component is observed or derived with evidence**; otherwise the aggregation result **must** be `BLOCKED_NEEDS_EVIDENCE`.
- A single `blocked` component **must** block the whole aggregation. Partial aggregation over a
  subset **must not** proceed.

## 10. uncertainty_buffer

- `uncertainty_buffer` is a **required** component, but it **may remain blocked** (status `blocked`)
  until a deterministic, evidence-backed formula is separately authorized.
- While blocked, `uncertainty_buffer` **must** block aggregation per §9; it **must not** be defaulted
  to zero or to any guessed constant.

## 11. No live execution connection

- This contract defines **no live order** path and **no execution connection**. It connects to no
  CLOB client, no order intent, no council execution authority, and no trading path.

<!-- PROHIBITED-OUTPUTS-START -->
### Forbidden outputs and claims

This contract, and any artifact that claims to satisfy it, must produce **none** of:

- no profitability score; no alpha/edge claim;
- no trade recommendation; no deployment, execution, or order instruction;
- no paper/live readiness verdict;
- no system-ready or ready-to-fly statement;
- no edge/PnL/economics readiness claim.
<!-- PROHIBITED-OUTPUTS-END -->

## 12. Open Backlog / Deferred Decisions

The following decisions are **deferred** and require separate, explicitly authorized TDD/offline work
before any implementation:

- exact deterministic formula for uncertainty_buffer (currently blocked; no formula authorized).
- exact units/scaling for final implementation (Decimal vs integer-scaled choice to be fixed).
- evidence source for fee_cost (artifact + field not yet fixed).
- evidence source for slippage_cost (artifact + field not yet fixed).
- evidence source for depth_cost (artifact + field not yet fixed).
- aggregation implementation is deferred (no net-edge calculator authorized here).
- production/live usage is blocked until separate authorization.

<!-- NO-CLAIMS-START -->
## No-claims statement

This contract makes **no edge, no PnL, no paper readiness, no economics readiness, no execution
readiness, no profitability, no alpha, no live readiness, no system-ready, no ready-to-fly, and no
ready claim** of any kind. It asserts no statistical significance, no stationarity proof, and no
economic inference. It is not a mathematical proof and does not guarantee correctness. Every
component slot is structural only; populating any value requires separately authorized, evidence-backed,
TDD/offline work.
<!-- NO-CLAIMS-END -->

## 13. Next allowed step

- Only a **separate, explicitly authorized TDD/offline Phase 5 implementation task** may follow, one
  component at a time, each with failing tests first and declared evidence provenance.
- **No implementation is authorized by this document.** Implementation still requires separate TDD
  and explicit authorization.

## Safety note

This file is docs/tests only. The `data/output/phase4c_batch_*` directories remain **untracked** and
are never committed; generated artifacts are never staged.
