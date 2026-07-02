#!/usr/bin/env python3
"""
Gate G8 — one-shot outcome-enrichment adapter (PAPER/SHADOW; NO orders, NO wallet, NO capital).

Reads a completed G8 paper-capture SQLite DB strictly READ-ONLY (mode=ro), reuses the COMMITTED
G6 Gamma+CLOB resolution evaluator (tools.gateg6_terminal_evaluator) WITHOUT modifying it, and
writes exactly ONE immutable JSON evidence artifact describing the HYPOTHETICAL hold-to-resolution
outcome of the single canonical PAPER_OPEN row.

HARD BOUNDARIES:
  * One Gamma GET attempt + one CLOB GET attempt, no retry/poll/sleep/loop/daemon.
  * Both sources attempted once even if the first fails; each parsed payload OR normalized
    transport error is captured and injected into the evaluator so it performs NO second fetch.
  * Source DB opened READ-ONLY; never written. Artifact written once via an exclusive
    no-overwrite publish; a pre-existing artifact path is refused before any fetch.
  * Inert unless armed: GATEG6_EVAL_ARM=PUBLIC-READONLY-EVAL-CONFIRMED (reuses G6's arm token;
    the G6 arm gate lives only in its main(), so this adapter re-checks it for library calls).
  * effective_n=1. This is NOT realized PnL, NOT alpha, NOT a fill. No order is ever placed.

Token identity is read from the DB (selected_token_id), never inferred from payload array
position. PnL is emitted ONLY when the reused evaluator returns status RESOLVED, and only from
stored Decimal-TEXT held_qty / entry_cost under a raised-precision Decimal context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sqlite3
import sys
import time
import uuid
from decimal import Decimal, localcontext

from tools import gateg6_terminal_evaluator as ev

ARTIFACT_KIND = "g8_hypothetical_hold_to_resolution_enrichment"
SCHEMA_VERSION = 1
SUPPORTED_SIDES = ("YES", "NO")
WINDOW_S = 900                      # one 15m up/down window, seconds
PNL_PRECISION = 60                  # Decimal ctx prec; default 28 silently rounds held_qty-entry_cost
PNL_SEMANTICS = (
    "hypothetical hold-to-resolution outcome; won: held_qty - entry_cost; "
    "lost: -entry_cost; settlement fee zero; simulated only; no order and no fill occurred.")

# adapter-authored narrative fields must never carry these terms (external payloads are exempt).
_BANNED_NARRATIVE = ("realized", "alpha", "risk-free", "risk free", "guaranteed", "locked profit")

_LEDGER_COLS = ("id", "condition_id", "slug", "asset", "window", "window_start_ms",
                "selected_side", "selected_token_id", "yes_token_id", "no_token_id",
                "selected_filled_qty", "no_exec_ask_vwap", "yes_exec_ask_vwap",
                "no_net_edge", "yes_net_edge", "paper_decision_ts")
_HELD_COLS = ("entry_ledger_id", "held_token_id", "held_qty", "entry_cost", "entry_ask_vwap",
              "fee_rate", "entry_notional", "entry_fee", "entry_ts_ms")


class EnrichmentRefused(Exception):
    """Raised for any pre-fetch local-guard violation. Fail-closed: no network, no artifact."""


# ---------------------------------------------------------------------------
# local guards (all BEFORE any fetch)
# ---------------------------------------------------------------------------
def _require_armed() -> None:
    if os.environ.get(ev.EVAL_ARM_ENV, "") != ev.EVAL_ARM_TOKEN:
        raise EnrichmentRefused(
            f"{ev.EVAL_ARM_ENV} != {ev.EVAL_ARM_TOKEN!r}: UNARMED, refusing any fetch")


def _read_source(db_path: str) -> tuple[dict, dict]:
    """Read the single canonical PAPER_OPEN row + its one immutable held tuple, READ-ONLY."""
    real = os.path.abspath(db_path)
    conn = sqlite3.connect(f"file:{real}?mode=ro", uri=True)
    try:
        open_rows = conn.execute(
            f"SELECT {','.join(_LEDGER_COLS)} FROM gateg8_paper_ledger "
            "WHERE status='PAPER_OPEN'").fetchall()
        if len(open_rows) != 1:
            raise EnrichmentRefused(
                f"expected exactly one PAPER_OPEN row, found {len(open_rows)}")
        ledger = dict(zip(_LEDGER_COLS, open_rows[0]))
        held = conn.execute(
            f"SELECT DISTINCT {','.join(_HELD_COLS)} FROM gateg8_exit_evidence "
            "WHERE entry_ledger_id=?", (ledger["id"],)).fetchall()
    finally:
        conn.close()
    if len(held) != 1:
        raise EnrichmentRefused(
            f"expected exactly one distinct held tuple for ledger id {ledger['id']}, "
            f"found {len(held)}")
    return ledger, dict(zip(_HELD_COLS, held[0]))


def _bind_and_check(ledger: dict, held: dict, now_s: int) -> dict:
    """Validate identity/finality and build the frozen candidate. Fail-closed on any mismatch."""
    side = ledger["selected_side"]
    if side not in SUPPORTED_SIDES:
        raise EnrichmentRefused(f"unsupported selected_side {side!r}")
    expected_token = ledger["no_token_id"] if side == "NO" else ledger["yes_token_id"]
    if str(ledger["selected_token_id"]) != str(expected_token):
        raise EnrichmentRefused("selected_token_id != side token_id (identity mismatch)")
    if str(held["held_token_id"]) != str(ledger["selected_token_id"]):
        raise EnrichmentRefused("held_token_id != selected_token_id (identity mismatch)")

    # market end: derive from window_start_ms and cross-check the slug + window columns.
    ws_ms = ledger["window_start_ms"]
    if ws_ms is None:
        raise EnrichmentRefused("missing window_start_ms")
    start_s = int(ws_ms) // 1000
    slug_window = ev.window_of(ledger["slug"])
    if slug_window is None or int(slug_window) != start_s or int(ledger["window"]) != start_s:
        raise EnrichmentRefused("window/slug/window_start_ms disagree (identity cross-check)")
    market_end_ts = start_s + WINDOW_S
    if now_s < market_end_ts:
        raise EnrichmentRefused(
            f"market not ended: now_s {now_s} < market_end_ts {market_end_ts}")

    exec_ask = ledger["no_exec_ask_vwap"] if side == "NO" else ledger["yes_exec_ask_vwap"]
    entry_edge = ledger["no_net_edge"] if side == "NO" else ledger["yes_net_edge"]
    cand = {
        "signal_id": f"g8-ledger-id-{ledger['id']}",
        "asset": ledger["asset"],
        "slug": ledger["slug"],
        "condition_id": ledger["condition_id"],
        "outcome_label": side,                      # label binding; never positional
        "outcome_index": None,
        "token_id": ledger["selected_token_id"],    # from DB, not from payload
        "exec_ask_vwap": exec_ask,
        "exec_fill_qty_avail": ledger["selected_filled_qty"],
        "entry_edge": entry_edge,
        "market_end_ts": market_end_ts,
        "ts_signal": ledger["paper_decision_ts"],
    }
    return cand


# ---------------------------------------------------------------------------
# fetch (exactly once each) + evaluator injection
# ---------------------------------------------------------------------------
def _fetch_once(fn, *args):
    """One attempt; capture parsed payload OR the raised exception. Never retries. Catches
    Exception (fail-closed capture of any fetcher failure) but NOT BaseException, so
    KeyboardInterrupt/SystemExit still propagate. The original exception is retained for the
    artifact evidence; normalization for the evaluator happens in _evaluate."""
    try:
        return fn(*args), None
    except Exception as exc:   # noqa: BLE001 - deliberate fail-closed capture; see docstring
        return None, exc


def _evaluate(cand: dict, g_payload, g_err, c_payload, c_err) -> dict:
    """Inject constant closures that replay the already-captured results, so the reused
    evaluator consumes them and performs NO second fetch (raising the same transport error
    the live fetch would have raised)."""
    def _as_transport(err):
        # the evaluator only fail-closes on ev.TransportError; a TransportError passes through
        # unchanged, any other captured exception is normalized (message preserved) so an
        # unexpected fetcher failure becomes a fail-closed status rather than a crash.
        if isinstance(err, ev.TransportError):
            return err
        return ev.TransportError(f"{type(err).__name__}: {err}")

    def gamma_const(_slug, _cid):
        if g_err is not None:
            raise _as_transport(g_err)
        return g_payload

    def clob_const(_cid):
        if c_err is not None:
            raise _as_transport(c_err)
        return c_payload

    return ev.evaluate_candidate(cand, gamma_fetch=gamma_const, clob_fetch=clob_const)


# ---------------------------------------------------------------------------
# PnL (only on RESOLVED) — Decimal TEXT only, raised precision
# ---------------------------------------------------------------------------
def _hypothetical_pnl(held: dict, result: dict) -> dict:
    with localcontext() as ctx:
        ctx.prec = PNL_PRECISION
        held_qty = Decimal(str(held["held_qty"]))
        entry_cost = Decimal(str(held["entry_cost"]))
        pnl_won = held_qty - entry_cost
        pnl_lost = -entry_cost
        for_outcome = None
        if result.get("status") == ev.ST_RESOLVED and "matched" in result:
            for_outcome = pnl_won if result["matched"] else pnl_lost
        return {
            "semantics": PNL_SEMANTICS,
            "decimal_context": {"prec": PNL_PRECISION, "rounding": ctx.rounding},
            "pnl_if_won": str(pnl_won),
            "pnl_if_lost": str(pnl_lost),
            "pnl_for_outcome": (str(for_outcome) if for_outcome is not None else None),
        }


# ---------------------------------------------------------------------------
# artifact assembly + atomic no-overwrite publish
# ---------------------------------------------------------------------------
def _json_safe(obj):
    """Deterministically JSON-normalize evaluator output for the artifact WITHOUT changing
    evaluator behavior: sets -> sorted arrays; nested dict/list recursed. Records nothing here;
    the caller flags that normalization is applied to the preserved g6_evaluation echo."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, set):
        return sorted(_json_safe(v) for v in obj)
    return obj


def _default_out_path(ledger: dict) -> str:
    cid = str(ledger["condition_id"])
    return f"/tmp/g8_outcome_enrichment_{ledger['slug']}_{cid[:18]}.json"


def _atomic_publish(out_path: str, data: bytes) -> None:
    """Exclusive, no-overwrite publish: write a unique same-dir temp (O_EXCL), fsync, then claim
    the final name with os.link (fails if it exists). Never os.replace/rename as an overwrite
    guard. The temp is always removed; a race on the final name leaves any existing file intact."""
    d = os.path.dirname(os.path.abspath(out_path)) or "."
    tmp = os.path.join(d, f".{os.path.basename(out_path)}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)             # fd always closes, even on write/fsync failure
        os.link(tmp, out_path)       # FileExistsError if out_path already exists (never overwrite)
    finally:
        # single encompassing cleanup: every exception path (write/fsync/link) AND the success
        # path drops the temp name; on success out_path is a separate hardlink that survives.
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _assert_clean_narrative(*fields: str) -> None:
    for f in fields:
        low = (f or "").lower()
        for term in _BANNED_NARRATIVE:
            if term in low:
                raise EnrichmentRefused(f"adapter narrative contains banned term {term!r}")


def _build_artifact(db_path, ledger, held, cand, result, gamma_ev, clob_ev, pnl,
                    checkpoint_sha, now_ms) -> dict:
    real = os.path.abspath(db_path)
    resolved = result.get("status") == ev.ST_RESOLVED
    held_side_won = bool(result["matched"]) if (resolved and "matched" in result) else None
    return {
        "artifact_kind": ARTIFACT_KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_ts_ms": now_ms,
        "checkpoint_sha": checkpoint_sha,
        "effective_n": 1,
        "no_order_no_fill_no_realized_pnl": True,
        "identity": {
            "condition_id": ledger["condition_id"], "slug": ledger["slug"],
            "asset": ledger["asset"], "window": ledger["window"],
            "entry_ledger_id": held["entry_ledger_id"],
            "held_side": ledger["selected_side"], "held_token_id": held["held_token_id"],
            "selected_token_id": ledger["selected_token_id"],
            "yes_token_id": ledger["yes_token_id"], "no_token_id": ledger["no_token_id"],
            "market_end_ts": cand["market_end_ts"], "signal_id": cand["signal_id"],
        },
        "source_db": {
            "path": real,
            "sha256": hashlib.sha256(open(real, "rb").read()).hexdigest(),
            "read_ts_ms": now_ms,
        },
        "held_position": {c: held[c] for c in
                          ("held_qty", "entry_cost", "entry_ask_vwap", "fee_rate",
                           "entry_notional", "entry_fee", "entry_ts_ms")},
        "resolution_evidence": {
            "payload_note": "parsed JSON objects consumed by the evaluator, NOT raw wire bytes",
            "gamma": gamma_ev, "clob": clob_ev,
        },
        "g6_evaluation": {"result": _json_safe(result),
                          "normalization": "sets serialized as sorted arrays"},
        "g6_status": result.get("status"),
        "outcome": {"resolved": resolved, "held_side_won": held_side_won},
        "hypothetical_hold_to_resolution_pnl": pnl,
    }


def _git_head() -> str:
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def run(db_path: str, *, out_path: str | None = None,
        gamma_fetch=None, clob_fetch=None,
        now_s_provider=None, now_ms_provider=None, checkpoint_sha=None) -> dict:
    """One-shot enrichment. Local guards -> exactly one fetch per source -> reused evaluation ->
    immutable JSON artifact. Returns {'artifact_path', 'g6_status', 'artifact'}."""
    gamma_fetch = gamma_fetch or ev.gamma_fetch_live
    clob_fetch = clob_fetch or ev.clob_fetch_live
    now_s_provider = now_s_provider or (lambda: int(time.time()))
    now_ms_provider = now_ms_provider or (lambda: int(time.time() * 1000))

    _require_armed()
    ledger, held = _read_source(db_path)
    cand = _bind_and_check(ledger, held, now_s_provider())

    out = out_path or _default_out_path(ledger)
    if os.path.lexists(out):                       # refuse a pre-existing artifact BEFORE any fetch
        raise EnrichmentRefused(f"artifact already exists: {out}")

    # exactly one attempt per source; both attempted even if the first fails; no retry.
    g_payload, g_err = _fetch_once(gamma_fetch, cand["slug"], cand["condition_id"])
    c_payload, c_err = _fetch_once(clob_fetch, cand["condition_id"])

    result = _evaluate(cand, g_payload, g_err, c_payload, c_err)
    pnl = _hypothetical_pnl(held, result)
    _assert_clean_narrative(pnl["semantics"], ARTIFACT_KIND)

    now_ms = now_ms_provider()
    gamma_ev = {"url": ev.GAMMA_MARKETS,
                "params": {"slug": cand["slug"], "closed": "true"},
                "fetch_ts_ms": now_ms, "parsed_payload": g_payload,
                "error": (f"{type(g_err).__name__}: {g_err}" if g_err else None)}
    clob_ev = {"url": f"{ev.CLOB_MARKETS}/{cand['condition_id']}",
               "params": None, "fetch_ts_ms": now_ms, "parsed_payload": c_payload,
               "error": (f"{type(c_err).__name__}: {c_err}" if c_err else None)}
    checkpoint = checkpoint_sha or _git_head()

    artifact = _build_artifact(db_path, ledger, held, cand, result, gamma_ev, clob_ev, pnl,
                               checkpoint, now_ms)
    _atomic_publish(out, json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8"))
    return {"artifact_path": out, "g6_status": result.get("status"), "artifact": artifact}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate G8 one-shot outcome enrichment (PAPER/SHADOW; no orders).")
    parser.add_argument("--db", required=True, help="completed G8 paper-capture SQLite (read-only)")
    parser.add_argument("--out", default=None, help="artifact path (default: deterministic /tmp)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run(args.db, out_path=args.out)
    except EnrichmentRefused as e:
        sys.stderr.write(f"[GUARD] refusing to enrich: {e}\n")
        return 2
    sys.stderr.write(f"[gateg8-enrich] {result['g6_status']} -> {result['artifact_path']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
