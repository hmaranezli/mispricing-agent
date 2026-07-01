#!/usr/bin/env python3
"""
Gate G8 — Forward Paper Dual-Book Capture (entry-only; NO resolution, NO orders).

Connects the committed bidirectional fee-aware paper selector (analysis.forensic.
gateg7_paper_pnl) to real entry-time YES and NO CLOB books so a future bounded run can
create genuine paper decisions. PAPER/SHADOW ONLY.

HARD BOUNDARIES:
  * PUBLIC read-only GET only (Gamma market listing reused from the caller; CLOB book x2).
    NO auth, NO wallet, NO signing, NO capital, NO orders.
  * NO resolution fetch anywhere in this module. NO terminal PnL computed here.
  * NO S1 access. Live S1 stays CREATED_EMPTY_LOCKED_CONTAINER; append DENIED.
  * Exactly TWO CLOB book GETs per evaluated market (YES + NO), SEQUENTIAL (no existing
    async CLOB client to reuse -- building one would be new infrastructure, out of scope).
    No retry.
  * Inert unless armed: GATEG8_PAPER_ARM=BIDIRECTIONAL-PAPER-CONFIRMED (default OFF).
  * This module does NOT authorize or perform a live run. PAPER_OPEN is the first
    position-taking artifact and requires a SEPARATE, explicitly reviewed authorization.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import time
from decimal import Decimal

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg7_paper_pnl as pp
from tools import gateg5_telemetry_runner as runner
from tools.gateg5_telemetry_runner import (
    CLOB_BOOK, TARGET_INTERVAL_S, TransportError,
    _hl_price_feedts as _default_hl_price_feedts,
    _hl_sigma_annual as _default_hl_sigma_annual,
    _public_get as _default_public_get,
)

PAPER_ARM_ENV = "GATEG8_PAPER_ARM"
PAPER_ARM_TOKEN = "BIDIRECTIONAL-PAPER-CONFIRMED"
DEFAULT_STAKE = Decimal("25")
POLL_INTERVAL_S = runner.POLL_INTERVAL_S  # reused G5 cadence; never redefined independently

_LEDGER_COLS = [
    "condition_id", "slug", "asset", "window", "paper_decision_ts", "fair_yes",
    "reference_age_ms", "tte_s", "yes_token_id", "no_token_id", "yes_quote_ts_ms",
    "no_quote_ts_ms", "yes_capture_started_ms", "yes_capture_completed_ms",
    "no_capture_started_ms", "no_capture_completed_ms", "dual_book_skew_ms",
    "hl_capture_started_ms", "hl_capture_completed_ms",
    "yes_exec_ask_vwap", "yes_filled_qty", "no_exec_ask_vwap", "no_filled_qty",
    "fee_rate", "fee_exponent", "yes_gross_edge", "yes_net_edge", "no_gross_edge",
    "no_net_edge", "selected_side", "selected_token_id", "no_entry_reason",
    "selected_filled_qty", "selected_entry_notional", "status",
    # --- diagnostic evidence (evidence-only; never feeds capture/economic decisions) ---
    "stale_side", "quote_age_at_capture_ms", "quote_age_at_decision_ms",
    "failure_stage", "exception_class", "exception_message", "stage_timings_json",
    "window_start_ms", "probe_now_ms", "window_start_delta_ms", "window_start_in_future",
]

_INTEGER_COLS = frozenset({
    "paper_decision_ts", "reference_age_ms", "tte_s", "yes_quote_ts_ms", "no_quote_ts_ms",
    "yes_capture_started_ms", "yes_capture_completed_ms", "no_capture_started_ms",
    "no_capture_completed_ms", "dual_book_skew_ms", "hl_capture_started_ms",
    "hl_capture_completed_ms", "fee_exponent",
    # diagnostic integer evidence
    "quote_age_at_capture_ms", "quote_age_at_decision_ms", "window_start_ms",
    "probe_now_ms", "window_start_delta_ms", "window_start_in_future",
})


def is_armed() -> bool:
    return os.environ.get(PAPER_ARM_ENV, "") == PAPER_ARM_TOKEN


def _require_armed() -> None:
    """Hard arm gate: raises BEFORE any network call or DB write. Called at the top of
    every entrypoint (capture_and_decide, run, main) -- is_armed() alone is observational
    and must never be trusted as the sole guard."""
    if not is_armed():
        raise PermissionError(
            f"{PAPER_ARM_ENV} != {PAPER_ARM_TOKEN!r}. G8 UNARMED -- refusing any network "
            "I/O or DB write.")


def init_paper_ledger(conn) -> None:
    """Fresh isolated paper table (TEXT/INTEGER only; never REAL). This is paper evidence
    ONLY -- never signal_log, never Live S1, never wallet/order code.

    A partial UNIQUE index enforces AT MOST ONE PAPER_OPEN row per condition_id at the
    SQLite level itself (not only via the Python-list enforce_one_entry_per_condition):
    persists on disk, so the guarantee survives process restart / DB reopen."""
    cols_sql = ",".join(f"{c} INTEGER" if c in _INTEGER_COLS else f"{c} TEXT" for c in _LEDGER_COLS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg8_paper_ledger(id INTEGER PRIMARY KEY, {cols_sql})")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_gateg8_paper_open_condition "
        "ON gateg8_paper_ledger(condition_id) WHERE status='PAPER_OPEN'")
    conn.commit()


def write_paper_ledger(conn, decision: dict) -> str:
    """Persist one paper decision row. Never touches signal_log/mark_path/S1.

    Atomic dedup: attempts the insert as-given inside a SAVEPOINT. If the partial unique
    index rejects a second PAPER_OPEN for the same condition_id, the failed insert is
    rolled back to the savepoint (never poisoning the connection) and retried with
    status downgraded to DUPLICATE_CONDITION_SKIPPED -- so a repeated condition NEVER
    produces a second PAPER_OPEN row, even under reentrant/repeated calls or DB reopen.
    Returns the status actually persisted.
    """
    row = dict(decision)
    insert_sql = (f"INSERT INTO gateg8_paper_ledger({','.join(_LEDGER_COLS)}) "
                  f"VALUES ({','.join('?' for _ in _LEDGER_COLS)})")
    conn.execute("SAVEPOINT g8_ledger_write")
    try:
        conn.execute(insert_sql, tuple(row.get(c) for c in _LEDGER_COLS))
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK TO g8_ledger_write")
        conn.execute("RELEASE g8_ledger_write")
        if row.get("status") != pp.PAPER_OPEN:
            raise
        row["status"] = pp.DUPLICATE_CONDITION_SKIPPED
        conn.execute("SAVEPOINT g8_ledger_write")
        conn.execute(insert_sql, tuple(row.get(c) for c in _LEDGER_COLS))
        conn.execute("RELEASE g8_ledger_write")
        conn.commit()
        return row["status"]
    conn.execute("RELEASE g8_ledger_write")
    conn.commit()
    return row["status"]


def _fetch_book(token_id: str, *, now_ms_provider, public_get) -> dict:
    """One CLOB book GET; records capture-start/complete around it. No retry."""
    started = now_ms_provider()
    raw = public_get(CLOB_BOOK, {"token_id": token_id})
    completed = now_ms_provider()
    ts = raw.get("timestamp", completed)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = completed
    asks = [[lvl["price"], lvl["size"]] for lvl in raw.get("asks", [])]
    return {"asks": asks, "quote_ts_ms": ts,
            "capture_started_ms": started, "capture_completed_ms": completed}


def capture_and_decide(market: dict, *, now_ms_provider, max_skew_ms: int,
                       book_fetch_client=None, hl_price_feedts=None, hl_sigma_annual=None,
                       intended_stake: Decimal = DEFAULT_STAKE,
                       cost_buffer: Decimal = Decimal("0")) -> dict:
    """One full entry-time decision cycle for one market. `market` must already carry the
    Gamma fields needed for binding/fees (conditionId, slug, asset, outcomes, clobTokenIds,
    market_end_ts, feesEnabled, feeSchedule) -- NO extra Gamma fetch happens here.

    Exactly TWO CLOB book GETs (YES then NO, sequential -- no existing async CLOB client to
    reuse), then HL fair-value inputs (timed via hl_capture_started_ms/completed_ms), THEN
    `paper_decision_ts` is stamped -- only after every entry input above is available.
    Delegates all edge/fee/selection math to the COMMITTED
    analysis.forensic.gateg7_paper_pnl.build_paper_decision (never duplicated here).

    HARD ARM GATE: refuses before any network call or DB write when unarmed.
    """
    _require_armed()
    public_get = book_fetch_client or _default_public_get
    hl_pf = hl_price_feedts or _default_hl_price_feedts
    hl_sig = hl_sigma_annual or _default_hl_sigma_annual

    # --- evidence-only instrumentation: per-stage start/completed/duration + window facts.
    # Never changes the decision. On an EXPECTED stage exception the ORIGINAL exception is
    # re-raised (preserving the raise contract) with the failing stage + partial timings
    # attached, so run()'s handler can persist diagnosable CAPTURE_FAILED evidence.
    stage_timings: dict = {}
    probe_now_ms = now_ms_provider()
    window_start_ms = (market["market_end_ts"] - TARGET_INTERVAL_S) * 1000
    window_evidence = {
        "window_start_ms": window_start_ms, "probe_now_ms": probe_now_ms,
        "window_start_delta_ms": window_start_ms - probe_now_ms,
        "window_start_in_future": int(window_start_ms > probe_now_ms),
    }
    capture_start_ms: int | None = None

    def _run_stage(name, fn):
        nonlocal capture_start_ms
        start = now_ms_provider()
        if capture_start_ms is None:
            capture_start_ms = start
        try:
            result = fn()
        except _EXPECTED_STAGE_EXC as e:
            completed = now_ms_provider()
            stage_timings[name] = {"start_ts": start, "completed_ts": completed,
                                   "duration_ms": completed - start}
            stage_timings[STAGE_TOTAL] = {"start_ts": capture_start_ms, "completed_ts": completed,
                                          "duration_ms": completed - capture_start_ms}
            e._g8_failure_stage = name
            e._g8_stage_timings = dict(stage_timings)
            e._g8_window_evidence = dict(window_evidence)
            e._g8_partial = {"condition_id": market.get("conditionId"),
                             "slug": market.get("slug"), "asset": market.get("asset")}
            raise
        completed = now_ms_provider()
        stage_timings[name] = {"start_ts": start, "completed_ts": completed,
                               "duration_ms": completed - start}
        return result

    binding = _run_stage(STAGE_OUTCOME_BINDING,
                         lambda: pp.bind_yes_no_tokens(market["outcomes"], market["clobTokenIds"]))
    yes_book = _run_stage(STAGE_YES_CLOB_FETCH,
                          lambda: _fetch_book(binding["yes_token_id"], now_ms_provider=now_ms_provider,
                                              public_get=public_get))   # GET #1
    no_book = _run_stage(STAGE_NO_CLOB_FETCH,
                         lambda: _fetch_book(binding["no_token_id"], now_ms_provider=now_ms_provider,
                                             public_get=public_get))     # GET #2 (sequential; no retry)

    now_ms = max(yes_book["capture_completed_ms"], no_book["capture_completed_ms"])
    p_now, feed_ts = _run_stage(STAGE_HL_CURRENT_PRICE, lambda: hl_pf(market["asset"], now_ms))
    strike, _ = _run_stage(STAGE_HL_WINDOW_STRIKE, lambda: hl_pf(market["asset"], window_start_ms))
    sigma_annual = _run_stage(STAGE_HL_SIGMA, lambda: hl_sig(market["asset"], now_ms))

    def _model():
        tte_s = market["market_end_ts"] - (now_ms_provider() // 1000)
        if tte_s <= 0:
            raise gm.ModelInputError("nonpositive tte for market window")
        tte_years = Decimal(tte_s) / gm.SECONDS_PER_YEAR
        return tte_s, gm.fair_yes_gbm(p_now, strike, sigma_annual, tte_years)
    tte_s, fair_yes = _run_stage(STAGE_MODEL_CALCULATION, _model)

    # preserve the exact no-lookahead HL bracketing semantics: hl_capture_started_ms is the
    # first HL clock read; hl_capture_completed_ms covers the full HL acquisition + fair calc.
    hl_capture_started_ms = stage_timings[STAGE_HL_CURRENT_PRICE]["start_ts"]
    hl_capture_completed_ms = stage_timings[STAGE_MODEL_CALCULATION]["completed_ts"]

    decision_ts = now_ms_provider()   # stamped ONLY after every input above is available
    stage_timings[STAGE_TOTAL] = {"start_ts": capture_start_ms, "completed_ts": decision_ts,
                                  "duration_ms": decision_ts - capture_start_ms}

    decision = pp.build_paper_decision(
        market=market, yes_book=yes_book, no_book=no_book, fair_yes=fair_yes, feed_ts=feed_ts,
        tte_s=tte_s, max_skew_ms=max_skew_ms, decision_ts=decision_ts,
        hl_capture_started_ms=hl_capture_started_ms,
        hl_capture_completed_ms=hl_capture_completed_ms,
        intended_stake=intended_stake, cost_buffer=cost_buffer)
    # evidence-only enrichment (adds diagnostic keys; never mutates economic fields)
    decision["stage_timings_json"] = json.dumps(stage_timings, separators=(",", ":"))
    decision.update(window_evidence)
    return decision


CAPTURE_FAILED = "CAPTURE_FAILED"   # orchestrator-level classification; not an edge-model status

# stages a capture can fail in (persisted as failure_stage; also keyed in stage_timings)
STAGE_OUTCOME_BINDING = "OUTCOME_BINDING"
STAGE_YES_CLOB_FETCH = "YES_CLOB_FETCH"
STAGE_NO_CLOB_FETCH = "NO_CLOB_FETCH"
STAGE_HL_CURRENT_PRICE = "HL_CURRENT_PRICE"
STAGE_HL_WINDOW_STRIKE = "HL_WINDOW_STRIKE"
STAGE_HL_SIGMA = "HL_SIGMA"
STAGE_MODEL_CALCULATION = "MODEL_CALCULATION"
STAGE_TOTAL = "TOTAL_CAPTURE_TO_DECISION"

_EXPECTED_STAGE_EXC = (pp.OutcomeBindingError, TransportError, gm.ModelInputError)
_URL_RE = re.compile(r"https?://\S+")
_HEX_RE = re.compile(r"0x[0-9a-fA-F]{12,}")
_LONGNUM_RE = re.compile(r"\d{16,}")


def _sanitize_exception_message(exc, cap: int = 200) -> str:
    """Redact full URLs, 0x-hashes and long token/condition IDs, collapse whitespace, and
    length-cap. NEVER let a raw URL, token ID, payload or book leak into persisted evidence
    or the log line."""
    msg = str(exc)
    msg = _URL_RE.sub("[URL]", msg)
    msg = _HEX_RE.sub("[HEX]", msg)
    msg = _LONGNUM_RE.sub("[ID]", msg)
    msg = " ".join(msg.split())
    if len(msg) > cap:
        msg = msg[:cap] + "...[truncated]"
    return msg


def _map_gamma_market(raw: dict) -> dict:
    """Map a raw Gamma market listing into the shape capture_and_decide needs (both token
    IDs, not a single selected side). Reuses runner._end_to_epoch_s for market_end_ts."""
    import json
    toks = raw.get("clobTokenIds")
    if isinstance(toks, str):
        toks = json.loads(toks)
    outs = raw.get("outcomes")
    if isinstance(outs, str):
        outs = json.loads(outs)
    slug = raw.get("slug", "") or ""
    return {
        "conditionId": raw.get("conditionId"), "slug": slug,
        "asset": (slug.split("-")[0].upper() if slug else "UNKNOWN"),
        "outcomes": outs, "clobTokenIds": toks,
        "market_end_ts": runner._end_to_epoch_s(raw),
        "feesEnabled": raw.get("feesEnabled"), "feeSchedule": raw.get("feeSchedule"),
    }


def _require_env_int(name: str) -> int:
    """Fail closed: no silent default, and no zero/negative bound. The five-blocker
    authorization requires GATEG8_MAX_OBSERVATIONS/GATEG8_MAX_ELAPSED_S/GATEG8_MAX_SKEW_MS
    to be set EXPLICITLY to a POSITIVE integer -- checked before any network call or DB
    creation/write (called at the top of run(), ahead of sqlite3.connect and the loop)."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        raise PermissionError(f"{name} must be set explicitly (no default) to run the G8 driver")
    try:
        value = int(raw)
    except ValueError:
        raise PermissionError(f"{name} must be an integer, got {raw!r}") from None
    if value <= 0:
        raise PermissionError(f"{name} must be a positive integer, got {value!r}")
    return value


def _capture_failed_decision(exc, market: dict) -> dict:
    """Build a fully-diagnosable CAPTURE_FAILED ledger row from a stage-instrumented
    exception: failure_stage, exception class, SANITIZED message, partial stage timings,
    window evidence, and the identifiers available before the failure."""
    partial = getattr(exc, "_g8_partial", None) or {}
    decision = {
        "status": CAPTURE_FAILED,
        "condition_id": partial.get("condition_id", market.get("conditionId")),
        "slug": partial.get("slug", market.get("slug")),
        "asset": partial.get("asset", market.get("asset")),
        "failure_stage": getattr(exc, "_g8_failure_stage", "UNCLASSIFIED"),
        "exception_class": type(exc).__name__,
        "exception_message": _sanitize_exception_message(exc),
    }
    stages = getattr(exc, "_g8_stage_timings", None)
    if stages is not None:
        decision["stage_timings_json"] = json.dumps(stages, separators=(",", ":"))
    window = getattr(exc, "_g8_window_evidence", None)
    if window is not None:
        decision.update(window)
    return decision


def _emit_observation_log(n: int, decision: dict) -> None:
    """One concise, FLUSHED structured stderr line per persisted observation. Never prints
    a full order book, URL, or token ID -- only status + sanitized diagnostic summary."""
    status = decision.get("status")
    ts = decision.get("paper_decision_ts") or decision.get("probe_now_ms")
    try:
        utc = datetime.datetime.fromtimestamp((ts or 0) / 1000, datetime.timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        utc = "NA"
    parts = ["[g8obs]", f"n={n}", f"utc={utc}", f"asset={decision.get('asset')}",
             f"slug={decision.get('slug')}", f"status={status}"]
    if status == pp.PAPER_OPEN:
        side = decision.get("selected_side")
        net_edge = decision.get("yes_net_edge") if side == "YES" else decision.get("no_net_edge")
        parts += [f"selected_side={side}", f"selected_net_edge={net_edge}"]
    elif status == pp.STALE_QUOTE_REJECTED:
        parts += [f"stale_side={decision.get('stale_side')}",
                  f"age_cap_ms={decision.get('quote_age_at_capture_ms')}",
                  f"age_dec_ms={decision.get('quote_age_at_decision_ms')}"]
    elif status == CAPTURE_FAILED:
        parts += [f"stage={decision.get('failure_stage')}",
                  f"exc={decision.get('exception_class')}",
                  f"msg={decision.get('exception_message')}"]
    print(" ".join(str(p) for p in parts), file=sys.stderr, flush=True)


def run(db_path: str, *, now_ms_provider=lambda: int(time.time() * 1000),
       monotonic_provider=time.monotonic, abort_check=None,
       public_get=None, hl_price_feedts=None, hl_sigma_annual=None) -> dict:
    """Bounded single-pass paper forward-capture driver (PAPER/SHADOW ONLY; NO orders, NO
    resolution fetch). Requires GATEG8_PAPER_ARM + GATEG8_MAX_OBSERVATIONS +
    GATEG8_MAX_ELAPSED_S + GATEG8_MAX_SKEW_MS explicitly set -- fails closed otherwise,
    before any network call or DB write. Reuses the COMMITTED G5 market discovery
    (runner._target_slugs), target-asset parsing, public GET client, and poll cadence --
    no new infrastructure. Stops on MAX_OBSERVATIONS OR monotonic MAX_ELAPSED_S. No retry,
    daemon, scheduler, watcher, or background service. Every attempted market decision
    (including a token-integrity/transport failure) writes exactly ONE isolated
    gateg8_paper_ledger row.
    """
    _require_armed()
    max_observations = _require_env_int("GATEG8_MAX_OBSERVATIONS")
    max_elapsed_s = _require_env_int("GATEG8_MAX_ELAPSED_S")
    max_skew_ms = _require_env_int("GATEG8_MAX_SKEW_MS")

    if abort_check is None:
        abort_check = lambda: runner._ABORT_REQUESTED   # noqa: E731

    runner._require_under_tmp(db_path, "DB")
    runner._refuse_existing(db_path, "DB")

    public_get = public_get or _default_public_get
    hl_pf = hl_price_feedts or _default_hl_price_feedts
    hl_sig = hl_sigma_annual or _default_hl_sigma_annual

    conn = sqlite3.connect(db_path)
    init_paper_ledger(conn)

    start_mono = monotonic_provider()
    observations = 0
    stop_reason = "UNSET"

    while True:
        elapsed_s = int(monotonic_provider() - start_mono)
        if abort_check():
            stop_reason = "OPERATOR_ABORT"
            break
        if observations >= max_observations:
            stop_reason = "MAX_OBSERVATIONS"
            break
        if elapsed_s >= max_elapsed_s:
            stop_reason = "MAX_ELAPSED"
            break

        now_ms = now_ms_provider()
        for slug in runner._target_slugs(now_ms):
            if abort_check():
                stop_reason = "OPERATOR_ABORT"
                break
            if observations >= max_observations:
                break
            try:
                hits = public_get(runner.GAMMA_MARKETS, {"slug": slug})
            except TransportError:
                continue
            markets = [m for m in (hits if isinstance(hits, list) else [hits])
                      if m and m.get("conditionId")]
            for raw in markets:
                if observations >= max_observations:
                    break
                market = _map_gamma_market(raw)
                try:
                    decision = capture_and_decide(
                        market, now_ms_provider=now_ms_provider, max_skew_ms=max_skew_ms,
                        book_fetch_client=public_get, hl_price_feedts=hl_pf,
                        hl_sigma_annual=hl_sig)
                except (pp.OutcomeBindingError, TransportError, gm.ModelInputError) as e:
                    decision = _capture_failed_decision(e, market)
                write_paper_ledger(conn, decision)
                observations += 1
                _emit_observation_log(observations, decision)
        if stop_reason == "OPERATOR_ABORT":
            break
        time.sleep(POLL_INTERVAL_S)

    conn.close()
    return {"stop_reason": stop_reason, "observations": observations, "db_path": db_path}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate G8 bounded paper forward-capture driver (PAPER/SHADOW ONLY; no orders).")
    parser.add_argument("--db", required=True, help="SQLite path for the isolated G8 paper ledger")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if not is_armed():
        sys.stderr.write(
            f"[GUARD] {PAPER_ARM_ENV} != {PAPER_ARM_TOKEN!r}. G8 driver UNARMED -- refusing "
            "any network I/O or DB write. No fetch, no DB, no loop.\n")
        return 2
    try:
        result = run(args.db)
    except PermissionError as e:
        sys.stderr.write(f"[GUARD] refusing to run: {e}\n")
        return 2
    sys.stderr.write(f"[gateg8] done: {result}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
