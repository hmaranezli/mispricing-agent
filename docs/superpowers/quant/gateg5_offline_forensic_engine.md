# Gate G.5 — Offline Forensic Measurement Engine

Status: **G.5_OFFLINE_FORENSIC_ENGINE_FEATURE_LOCKED / NOT_RUNNER_LAUNCHED.**

The forensic measurement engine specified below is now implemented and migrated into the
tracked tree as `analysis/forensic/gateg5_forensic_engine.py` (pure/offline). The runner has
**NOT** been launched: the engine's hard execution guard (`GATEG5_ARM`) keeps the armed path
inert, computes nothing on import, and creates no files on import. No real orders, no
wallet/signing/capital, no Live S1 access, no live DB, no API polling.

Tests:
- `tests/test_gateg5_forensic_engine.py` — pure unit suite (sentinel math, terminal_conservative
  residual=0, deterministic holdout, active executable criteria, cost accounting, schema
  no-REAL/FLOAT/DOUBLE, no-lookahead, token binding).
- `tests/test_gateg5_offline_replay.py` — offline synthetic dual-replay fixtures incl.
  FILLED_ACTIVE TP/SL, holdout drawdown→win/loss, blocked/stale terminal, **Toxic Flow Trap**,
  **Stale Oracle Mirage**.
- Combined suite: **54 passed** (33 unit + 21 replay), no shared-state / import / SQLite-mock
  contamination.

Diagnostics implemented: four EV arms (hold/exit × FILLED/HOLDOUT); aggregate `aggregate_arms`,
`delta_diagnostics` (exit_bleed/toxicity/path_toxicity), `diag_cap_selection_bias`,
`diag_admitted_vs_capped`, `diag_effective_n`, `build_dual_axis_summary`; per-signal
`diag_calibration_curve`, `diag_modeled_edge_vs_hold_pnl`, `diag_edge_realization_gap`,
`diag_first_30s_mark_drift`, `diag_reference_age_buckets`, `diag_spread_depth_tte_buckets`.

**G.6 thresholds remain DEFERRED until real G.5 observation data exists.** Active strategy is
frozen at G.4b; G.5 is measurement, never strategy. Any future armed run requires a separate
explicit authorization.

The remainder of this document is the schema/replay/invariant specification (the historical
design, preserved as the engine's contract record).

---

## (Original design/spec — preserved as contract record)

This artifact specifies schemas, replay logic, invariants, summary fields, and failure
classifications. The hard execution guard and detached-launch path follow the G.3/G.4/G.4b
pattern and are NOT exercised here.

## 0. Purpose & non-goals

Goal: build a forensic measurement layer that **separates three failure modes** so we stop conflating them:
1. **MODEL** failure — `fair_yes` mis-calibrated.
2. **EXIT** bleed — TP50/SL30 policy loses value vs hold-to-resolution.
3. **EXECUTION / toxic-price / adverse-selection-like** effects — edge evaporates between signal and realized hold.

NON-GOALS (HARD): G.5 adds **NO predictive/active filters**. cooldown, persistence, momentum, fair_yes-drift,
one-shot, low-edge promotion are **shadow/logging only** and may NEVER gate active fills. Active strategy is
frozen at G.4b: BTC/SOL, NO/Down, edge>=0.15, TP50/SL30. G.5 is measurement, not strategy.

Anti-hallucination & integrity (constitution): every price is live-fetched; all financial columns TEXT/Decimal,
never SQLite REAL; quantiles Decimal-safe; no mid-price/last-trade/infinite-liquidity exit math; never mark a
share sold without executable bid depth; nothing settled without explicit settlement evidence.

---

## 1. Immutable `signal_log` schema (one row per signal — filled, holdout, rejected, or capped)

```sql
CREATE TABLE signal_log(
  signal_id            TEXT PRIMARY KEY,          -- hash(condition_id|token_id|ts_signal_ms)
  ts_signal            TEXT NOT NULL,             -- UTC iso of the decision tick
  ts_signal_ms         INTEGER NOT NULL,
  knowable_ts          INTEGER NOT NULL,          -- max(component knowable_ts); causality anchor
  asset                TEXT NOT NULL,
  side                 TEXT NOT NULL,             -- NO/YES (Down/Up)
  condition_id         TEXT NOT NULL,
  token_id             TEXT NOT NULL,
  outcome_index        INTEGER NOT NULL,          -- 0/1 positional in clobTokenIds
  outcome_label        TEXT NOT NULL,             -- 'Up'/'Down' (G.2c-verified positional binding)
  slug                 TEXT NOT NULL,             -- documentary only; JOINS never use slug
  market_end_ts        INTEGER NOT NULL,          -- position-owned expiry (epoch s); reject if missing
  underlying_spot_price TEXT NOT NULL,
  reference_price      TEXT NOT NULL,             -- HL/Binance ref used by model
  reference_feed_ts    INTEGER NOT NULL,
  reference_age_ms     INTEGER NOT NULL,          -- ts_signal_ms - reference_feed_ts
  fair_yes             TEXT NOT NULL,             -- model P(Up) at ts_signal
  fair_yes_sigma       TEXT NOT NULL,
  fair_model_version   TEXT NOT NULL,
  strike               TEXT NOT NULL,
  tte_s                INTEGER NOT NULL,          -- market_end_ts - ts_signal (position-owned)
  ask_ladder_json      TEXT NOT NULL,             -- FULL ask book snapshot (Decimal strings)
  bid_ladder_json      TEXT NOT NULL,             -- FULL bid book snapshot
  book_hash            TEXT NOT NULL,             -- sha256(ask_ladder_json|bid_ladder_json)
  top_ask_price        TEXT NOT NULL,             -- diagnostic only, NEVER executable math
  top_ask_size         TEXT NOT NULL,
  intended_stake       TEXT NOT NULL,             -- 25.0
  book_ask_vwap        TEXT NOT NULL,             -- full-depth ask VWAP for intended_stake
  book_bid_vwap        TEXT NOT NULL,             -- immediate sell-back full-depth bid VWAP for resulting shares
  exec_ask_vwap        TEXT NOT NULL,             -- the single canonical entry price used by ALL arms
  exec_fill_qty_avail  TEXT NOT NULL,             -- shares fillable for intended_stake
  decision_cost_buffer TEXT NOT NULL,             -- GATE-TIME safety margin ONLY (conservatism reserve); NEVER subtracted in PnL
  realized_entry_cost  TEXT NOT NULL,             -- actual entry slippage realized = (exec_ask_vwap - book_ask_vwap)*qty; real
  realized_fee_cost    TEXT NOT NULL,             -- actual fee realized at exec_ask_vwap (Decimal); real
  cost_components      TEXT NOT NULL,             -- json {realized_entry_cost, realized_fee_cost, decision_cost_buffer} (no overlap)
  entry_edge           TEXT NOT NULL,             -- diagnostic_net_edge at ts_signal
  exit_depth_notional_avail TEXT NOT NULL,        -- immediate bid notional
  exit_depth_required  TEXT NOT NULL,             -- shares*exec price etc
  fill_decision        TEXT NOT NULL,             -- enum below
  fill_reason          TEXT,                      -- exact reason / rejection_reason
  holdout_seed         TEXT,                      -- hash(signal_id) bucket for stratified holdout
  row_hash             TEXT NOT NULL,             -- sha256(canonical row excl row_hash)
  prev_row_hash        TEXT NOT NULL              -- hash-chain (tamper-evident append log)
);
```

**`fill_decision` enum (exact):**
- `FILLED_ACTIVE` — passed all active executable criteria AND selected for the active book.
- `VALID_HOLDOUT_SHADOW` — passed **100%** of active executable criteria (depth OK, edge>=floor, quote fresh,
  sellback OK) but **deterministically/seed-diverted** to holdout. This is the ONLY EV-comparable shadow cohort.
- `UNFILLED_ENTRY_DEPTH_FAIL` — ask depth cannot absorb full intended stake.
- `UNFILLED_EDGE_LOST` — edge fell below floor between probe and book snapshot.
- `UNFILLED_QUOTE_STALE` — quote_age_ms > 2000.
- `UNFILLED_SHADOW_CAP_REACHED` — would-be valid holdout dropped by cap. **EXCLUDED from all EV arms**
  (hold_ev / exit_ev, FILLED and VALID_HOLDOUT_SHADOW); no mark_path is recorded for it. Used ONLY for
  cap-selection-bias and admitted-vs-capped distribution diagnostics (§6, §7).
- `UNSEQUENCEABLE` — missing market_end_ts / token-outcome binding unresolved.
- `UNFILLED_SELLBACK_REJECT` — immediate sellback loss worse than asset floor (-15/-20%).

**INVARIANT:** `VALID_HOLDOUT_SHADOW` must NOT be polluted by ENTRY_DEPTH_FAIL / EDGE_LOST / QUOTE_STALE /
cap-reached. Only holdout signals that would truly have filled enter EV-comparable cohorts.

---

## 2. Immutable `mark_path` schema (live-recorded only; NO offline refetch)

Recorded for `FILLED_ACTIVE` and admitted `VALID_HOLDOUT_SHADOW` only.

```sql
CREATE TABLE mark_path(
  id              INTEGER PRIMARY KEY,
  signal_id       TEXT NOT NULL,
  seq             INTEGER NOT NULL,
  ts_mark         TEXT NOT NULL,
  ts_mark_ms      INTEGER NOT NULL,
  knowable_ts     INTEGER NOT NULL,
  bid_ladder_json TEXT NOT NULL,                  -- FULL bid book (replay source of truth)
  exit_mark_status TEXT NOT NULL,                 -- sentinel enum below; NEVER NULL/empty. Gates readability of exit_mark_vwap.
  exit_mark_vwap  TEXT NOT NULL,                  -- full-depth bid VWAP for held shares; sentinel-text when not computable (see exit_mark_status)
  mark_depth      TEXT NOT NULL,                  -- bid notional
  levels_used     INTEGER NOT NULL,
  executable_flag INTEGER NOT NULL,               -- 1 only if full held shares absorbable
  liquidity_class TEXT NOT NULL,                  -- DEEP_EXECUTABLE/THIN_FILL/BLOCKED_NO_LIQUIDITY/STALE_QUOTE
  spot_price      TEXT NOT NULL,
  spot_age_ms     INTEGER NOT NULL,
  fair_yes_t      TEXT NOT NULL,                  -- SHADOW ONLY (never used by exit replay)
  fair_yes_sigma_t TEXT NOT NULL,                 -- SHADOW ONLY
  tte_s           INTEGER NOT NULL,               -- market_end_ts - ts_mark
  row_hash        TEXT NOT NULL,
  prev_row_hash   TEXT NOT NULL
);
```

Rules: mark_path **terminates at market_end_ts**; replay MUST NOT read any mark with `ts_mark_ms > market_end_ts`.
`fair_yes_t` / edge-decay / order-book-imbalance are **shadow-only** and MUST NOT influence exit replay decisions
(exit replay reads only `exit_mark_vwap` + `exit_mark_status` + `executable_flag` + `liquidity_class` + `tte_s`).

**`exit_mark_status` enum (exact sentinels — NEVER NULL, NEVER empty string):**
- `COMPUTED_EXECUTABLE` — full held shares absorbable by the live bid ladder; `exit_mark_vwap` is a real
  executable Decimal and is the ONLY case where exit replay may transact at this mark. (`executable_flag=1`.)
- `COMPUTED_THIN_PARTIAL` — bids exist but cannot absorb the full held qty; `exit_mark_vwap` holds the
  FAK-walk VWAP of the **available** bids only (partial). NOT a clean exit; usable only by `terminal_conservative()`
  (§5), never as a mid-path TP/SL clean close. (`executable_flag=0`.)
- `NOT_COMPUTED_BLOCKED_NO_LIQUIDITY` — bid ladder empty / no executable depth; `exit_mark_vwap` is set to the
  sentinel string `"NOT_COMPUTED_BLOCKED_NO_LIQUIDITY"` (NOT 0, NOT NULL, NOT ""). Replay MUST skip this mark.
- `NOT_COMPUTED_STALE_QUOTE` — quote age exceeded freshness bound; `exit_mark_vwap` sentinel string
  `"NOT_COMPUTED_STALE_QUOTE"`. Replay MUST skip this mark.

**INVARIANT:** exit replay treats `exit_mark_vwap` as a number ONLY when `exit_mark_status==COMPUTED_EXECUTABLE`.
For `COMPUTED_THIN_PARTIAL` the value is numeric but reserved for `terminal_conservative()` only. For the two
`NOT_COMPUTED_*` states the column is a literal sentinel string and any attempt to coerce it to a price ⇒
`FORENSIC_FAIL_CENSUS_RECONCILIATION` (blocked-mark misuse class). There is no NULL/empty path.

---

## 3. `resolution` schema (joined only after settlement, by `condition_id`, NEVER slug)

```sql
CREATE TABLE resolution(
  condition_id        TEXT PRIMARY KEY,
  resolved_yes        TEXT NOT NULL,              -- '0' / '1' / 'VOID' / 'UNRESOLVED'
  resolution_finalized INTEGER NOT NULL,          -- bool; provisional excluded from final EV
  resolution_ts       INTEGER,
  settlement_ts       INTEGER,
  resolution_source   TEXT NOT NULL,              -- e.g. clob.polymarket.com/markets/<cid> tokens[].winner
  resolution_fetch_ts INTEGER NOT NULL,
  settlement_delay_s  INTEGER,
  token_outcome_assert TEXT NOT NULL              -- PASS / FORENSIC_FAIL_TOKEN_OUTCOME_BINDING
);
```

Rules:
- **Token/outcome binding assertion**: the winner `token_id` must belong to `condition_id` AND map to the expected
  `outcome_index`/`outcome_label` (G.2c positional check). Mismatch ⇒ `FORENSIC_FAIL_TOKEN_OUTCOME_BINDING`.
- `VOID` and `UNRESOLVED` are **separate buckets**; never silently enter win/loss.
- Provisional/unfinalized resolution (`resolution_finalized=0`) MUST NOT be used for final model EV.

---

## 4. Knowable-timestamp / replay causality

- Every field carries or inherits `knowable_ts` (when it could first be known).
- The replay engine, at simulated decision tick `T`, is **forbidden** to read any field whose `knowable_ts > T`.
- Implement an explicit `assert_no_lookahead(field_knowable_ts, decision_tick)` guard; any violation ⇒
  `FORENSIC_FAIL_LOOKAHEAD_RISK` (whole run tagged, not silently dropped).
- `resolved_yes` has `knowable_ts = resolution_ts`; therefore exit replay (which runs over `ts_signal..market_end_ts`)
  can NEVER read resolution. Hold arms read resolution only (resolution is post-expiry).

---

## 5. Replay arms (same canonical entry price across all arms)

| Arm | Cohort | Method |
|-----|--------|--------|
| **A. hold_ev(FILLED)** | FILLED_ACTIVE | hold to finalized resolution; payoff $1 if won else $0 |
| **B. exit_ev(FILLED)** | FILLED_ACTIVE | causal TP50/SL30 replay over recorded mark_path only |
| **C. hold_ev(VALID_HOLDOUT_SHADOW)** | valid holdout | hold to finalized resolution; entry priced as market-taker `exec_ask_vwap` at ts_signal |
| **D. exit_ev(VALID_HOLDOUT_SHADOW)** | valid holdout | causal TP50/SL30 replay over shadow mark_path |

Cohort eligibility: only `FILLED_ACTIVE` and admitted `VALID_HOLDOUT_SHADOW` feed the four EV arms.
`UNFILLED_SHADOW_CAP_REACHED` (and all other `UNFILLED_*` / `UNSEQUENCEABLE` decisions) are **excluded from
hold_ev and exit_ev** entirely and carry no mark_path; cap-reached rows surface only in cap-bias / distribution
diagnostics (§6 holdout/cap, §7 admission). Including a capped row in any EV arm ⇒ `FORENSIC_FAIL_CENSUS_RECONCILIATION`.

Rules / invariants:
- **Entry-parity invariant** (assert): `exit_arm.entry_price == hold_arm.entry_price == signal_log.exec_ask_vwap`
  for every signal_id. Violation ⇒ `FORENSIC_FAIL_CENSUS_RECONCILIATION` (entry mismatch class).
- **Realized-cost rule (NO safety buffer in PnL)**: PnL subtracts ONLY actually-realized cost,
  `realized_cost = realized_entry_cost + realized_fee_cost`. `decision_cost_buffer` is a gate-time conservatism
  reserve and MUST NOT enter any PnL/EV figure — subtracting it would double-count cost (slippage/fee already
  captured inside `exec_ask_vwap`/`realized_*`). `realized_cost` is applied **exactly once** per signal, identically
  across hold and exit arms; double-count or buffer-in-PnL ⇒ `FORENSIC_FAIL_CENSUS_RECONCILIATION` (cost class).
- Exit replay reads only rows with `ts_signal <= ts_mark <= market_end_ts`.
- If a single tick appears to cross BOTH TP and SL ⇒ **SL precedence / worst-case-first**.
- No clean executable exit before `market_end_ts` ⇒ **terminal conservative forced-fill** — see `terminal_conservative()`
  below (status BLOCKED_NEVER_CLEAN / END_TS_FORCED).

### `terminal_conservative(held, cost, marks)` — exact semantics
Triggered only when no `COMPUTED_EXECUTABLE` mark produced a clean TP50/SL30 close before `market_end_ts`.
1. **Mark selection**: use the **last observed bid ladder at or before `market_end_ts`** (the chronologically final
   mark with `ts_mark_ms <= market_end_ts`). Selection is by time only — it MUST NOT search backward for the most
   favorable mark. **Never reuse an earlier favorable executable mark.**
2. **Empty book** (`exit_mark_status==NOT_COMPUTED_BLOCKED_NO_LIQUIDITY`, or no bid levels): the entire held qty is
   unfilled ⇒ proceeds from sale = 0, **residual = 0** (residual shares valued at $0, NOT carried, NOT marked).
3. **Partial book** (`exit_mark_status==COMPUTED_THIN_PARTIAL`): FAK-walk the **available** bids of that final ladder
   only; realize proceeds for the fillable portion at its FAK-walk VWAP; the **unfilled residual = 0** (valued at $0).
4. **Stale-only** (`NOT_COMPUTED_STALE_QUOTE` final mark, no executable depth observable): treated as empty book ⇒
   residual = 0. No optimistic mark substitution.
5. PnL = `(realized_partial_proceeds - cost) / cost * 100`, where `cost` already includes `cost_buffer` counted once
   (§ realized-cost rules). Residual is never re-priced from any earlier mark and never settled at resolution from
   the exit arm. Status tag: `END_TS_FORCED` (+ `BLOCKED_NEVER_CLEAN` if step 2/4 empty).

### Replay pseudocode (exit arm, per signal)
```
marks = mark_path[signal_id] where ts_signal <= ts_mark <= market_end_ts, ordered by seq
held = exec_fill_qty_avail
cost = intended_stake + realized_entry_cost + realized_fee_cost   # realized only, once; decision_cost_buffer EXCLUDED
for m in marks:
    assert_no_lookahead(m.knowable_ts, m.ts_mark_ms)
    if m.liquidity_class in (BLOCKED_NO_LIQUIDITY, STALE_QUOTE) or m.executable_flag==0:
        continue                              # cannot transact; not a free wait — just unexecutable mark
    pnl_pct = (m.exit_mark_vwap*held - cost)/cost*100
    if pnl_pct <= -30: return STOP_LOSS_30 @ m              # SL precedence
    if pnl_pct >= +50: return TAKE_PROFIT_50 @ m
# never cleanly closed -> terminal conservative forced-fill at the LAST mark <= market_end_ts (time-selected)
# empty book -> residual=0; partial book -> FAK-walk available bids then residual=0; never reuse earlier favorable mark
return terminal_conservative(held, cost, marks)   # residual=0 conservative; see terminal_conservative() spec above
```
### hold arm (per signal)
```
require resolution.resolution_finalized == 1 and resolved_yes in {'0','1'}
payoff = held * (1 if won(side, resolved_yes) else 0)
pnl = payoff - (intended_stake + realized_entry_cost + realized_fee_cost)   # realized cost once; buffer EXCLUDED
VOID/UNRESOLVED -> excluded bucket, NOT win/loss
```

---

## 6. Diagnostics

**Model diagnostics:**
- Calibration curve: bucket `fair_yes` (e.g. deciles) vs realized `resolved_yes` rate; reliability/Brier.
- `modeled_edge_bucket` vs `realized_hold_pnl` (does modeled edge predict hold EV?).
- `fair_yes_sigma` / edge-to-uncertainty ratio distribution.

**Exit diagnostics:**
- `exit_bleed = hold_ev(FILLED) - exit_ev(FILLED)` (positive ⇒ exit policy destroys value vs hold).
- `would_have_won` count among SL30 stop-outs (stopped then resolved YES-for-side).
- TP/SL barrier-touch stats; MFE/MAE distributions and giveback (MFE − exit_pnl).

**Execution / toxic-price diagnostics** (do NOT label filled-vs-holdout as direct adverse selection for taker fills):
- `edge_realization_gap = modeled_entry_edge - realized_hold_pnl` (per signal; the core "edge evaporation" metric).
- `realized_hold_pnl` by edge bucket.
- `first_30s_mark_drift` by edge bucket (early post-entry drift).
- `reference_age_ms` bucket vs realized_hold_pnl (stale-feed adverse fills).
- spread / depth / tte bucket vs realized_hold_pnl.
- EDGE_LOST / ENTRY_DEPTH_FAIL / QUOTE_STALE rate diagnostics.

**Holdout / cap diagnostics:**
- `cap_selection_bias = hold_ev(FILLED) - hold_ev(VALID_HOLDOUT_SHADOW)`.
- `path_cap_selection_bias = exit_ev(FILLED) - exit_ev(VALID_HOLDOUT_SHADOW)`.
- admitted-vs-capped distribution by asset, side, edge_bucket, tte_bucket.
- `cap_bias_warning` if admitted and capped cohorts differ materially in strata mix.

---

## 7. Shadow admission (deterministic / seeded stratified holdout — FIFO BANNED)

- FIFO is NOT a valid comparable-shadow rule (time-of-day / regime confound).
- Strata: `(asset, side, edge_bucket, tte_bucket)`.
- Admission: deterministic `hash(signal_id) % N` or seeded RNG within each stratum, target holdout fraction.
- Active fills retain priority; holdout admitted only under path caps.
- If cap reached ⇒ log `UNFILLED_SHADOW_CAP_REACHED`; report dropped % and per-stratum distributions.
- If `>10%` of VALID signals dropped ⇒ classify `FORENSIC_PARTIAL_CAP_BIASED`.

---

## 8. Effective-N / independence warning (summary must compute & print)

- `raw_trade_count`
- `unique_underlying_assets`
- `unique_market_windows` (distinct condition_id / 15m windows)
- `overlap_cluster_count` (concurrently-open same-asset positions)
- `regime_block_count` (contiguous time blocks, if derivable)
- `effective_n` estimate (e.g. raw / mean cluster size) or explicit warning
- `STATISTICAL_INDEPENDENCE_WARNING` if `unique_underlying_assets < 3` OR `unique_time_windows < 3`
- `FORENSIC_INSUFFICIENT_EFFECTIVE_N` if any alpha inference is attempted below threshold.

**HARD:** G.5 may diagnose mechanics/model/exit/execution, but MUST NOT claim alpha validation from clustered
BTC-only short windows (cf. G.4 −22.87% vs G.4b +34.88% = regime noise).

---

## 9. Census / reconciliation

- Census invariant: `opened == closed + open_at_stop + unsequenceable + void + unresolved`.
- PnL reconciliation: `sum(per-arm realized) == reported arm total` (cost counted once) or ⇒
  `FORENSIC_FAIL_CENSUS_RECONCILIATION`.
- No signal or position may vanish silently; every signal_id appears in exactly one terminal bucket.
- Hash-chain (`row_hash`/`prev_row_hash`) verified append-only; break ⇒ tamper flag.

---

## 10. Output classifications (exact)

Two ORTHOGONAL axes — report BOTH independently; never let one mask the other:

**Axis 1 — Schema/integrity validity** (about whether the data & replay are sound):
- `FORENSIC_SCHEMA_PASS` — schemas/causality/census/reconciliation/entry-parity/realized-cost all pass and arms
  computed. **Does NOT depend on effective-N.** A schema pass means the measurement machinery is sound, even when
  the sample is too small to infer alpha.
- `FORENSIC_PARTIAL_CAP_BIASED` — >10% valid signals dropped by cap.
- `FORENSIC_PARTIAL_NOT_EXERCISED` — a designed arm/path had zero qualifying samples (e.g. no holdout admitted).
- `FORENSIC_FAIL_LOOKAHEAD_RISK` — any field read with knowable_ts > decision tick.
- `FORENSIC_FAIL_RESOLUTION_JOIN` — resolution join failed / used slug / used provisional for final EV.
- `FORENSIC_FAIL_TOKEN_OUTCOME_BINDING` — winner token ↮ expected outcome_index/label.
- `FORENSIC_FAIL_CENSUS_RECONCILIATION` — census or PnL reconciliation or entry-parity or realized-cost failed.

**Axis 2 — Alpha-inference eligibility** (about whether any EV/alpha claim is permitted):
- `FORENSIC_INSUFFICIENT_EFFECTIVE_N` — effective-N below independence threshold. This **blocks alpha inference
  only**; it does NOT invalidate `FORENSIC_SCHEMA_PASS`. A run may legitimately be
  `FORENSIC_SCHEMA_PASS` **AND** `FORENSIC_INSUFFICIENT_EFFECTIVE_N` simultaneously — sound schema, no alpha claim.
- `ALPHA_INFERENCE_ELIGIBLE` — effective-N adequate (only meaningful when Axis 1 is `FORENSIC_SCHEMA_PASS`).

Precedence (within Axis 1 only): any `FAIL_*` dominates `PARTIAL_*` dominates `SCHEMA_PASS`. Axis 2 is reported
separately and is NEVER collapsed into Axis 1; low effective-N must never be rendered as a schema failure, and a
schema failure must never be excused by adequate effective-N.

---

## 11. Implementation risk notes (for the future build, not now)

1. **Resolution latency**: 15m markets may settle minutes-to-hours later; hold arms must wait for
   `resolution_finalized` — design a separate post-hoc resolution joiner keyed by condition_id, not inline.
2. **Holdout EV pricing**: holdout never actually fills; pricing it at `exec_ask_vwap` assumes a taker would have
   gotten that fill — document as an assumption; real fills move the book (acceptable for measurement, flag it).
3. **Effective-N is the dominant risk**: BTC-only clustering means even a clean schema yields weak inference.
   Plan multi-asset / multi-day collection BEFORE any EV claim; expect `STATISTICAL_INDEPENDENCE_WARNING` early.
4. **Causality discipline**: the single biggest correctness risk is accidental lookahead (reading fair_yes_t or
   resolution during exit replay). Keep exit replay's readable column set to a hard whitelist.
5. **Cost double-count**: entry-parity + realized-cost-once invariants must be asserted in code, not assumed; and
   `decision_cost_buffer` must never leak into any PnL/EV figure (gate-time reserve only).
6. **Terminal conservative fill**: reuse G.4b `conservative_thin_fill_pnl` (residual=0) so no optimistic settlement.
7. **No REAL columns / Decimal-safe quantiles**: enforce via PRAGMA scan in summary (as G.2b/G.3/G.4b do).
8. **This is measurement, not strategy**: resist scope creep — any predictive filter belongs to a later gate and
   must enter as shadow logging first, validated by THIS forensic layer, before ever gating active fills.

---

## Deliverable status
DESIGN ONLY. No runner, no DB created, no live capture, no strategy change. A future build would implement this
under a separate explicit authorization with a hard execution guard (as G.3/G.4/G.4b) and detached launch.
