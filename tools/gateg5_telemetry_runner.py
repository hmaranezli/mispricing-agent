#!/usr/bin/env python3
"""
Gate G.5 — Bounded READ-ONLY Telemetry Runner (DRAFT — DO NOT RUN).

Acquires forensic telemetry for BTC/SOL short-window markets via PUBLIC,
read-only market-data GETs, normalizes each observation through the verified
G.5 plumbing, and appends to its OWN G.5 telemetry SQLite DB (signal_log /
mark_path). It NEVER touches Live S1.

HARD BOUNDARIES:
  * PUBLIC market-data GET only. NO auth, NO wallet, NO signing, NO capital.
  * NO order placement. NO S1 access. Live S1 stays CREATED_EMPTY_LOCKED_CONTAINER.
  * Writes ONLY to an operator-specified DB path, or a /tmp default — NEVER the
    Live S1 path (asserted; refuses any var/s1 / live container path).
  * BOUNDED: hard stop at 100 normalized observations OR 6 hours elapsed.
    No unbounded loop. Heartbeat each bounded interval.
  * Sentinel-safe: a toxic API payload becomes a normalized rejection record or a
    skipped diagnostic — never a raw crash.
  * Hash-chain verification hook runs after each per-signal append batch.
  * Inert unless armed: GATEG5_TELEMETRY_ARM=PUBLIC-READONLY-TELEMETRY-CONFIRMED.
    This DRAFT is NOT to be executed in this gate.

Placed under tools/ (not analysis/forensic/) so the forensic package stays a
pure offline, network-free, import-safe library; this runner is the
network-capable operator utility, guarded.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from analysis.forensic import gateg5_plumbing as plumbing

engine = plumbing.engine

# --- arming + hard bounds (constitution) ---
TELEMETRY_ARM_ENV = "GATEG5_TELEMETRY_ARM"
TELEMETRY_ARM_TOKEN = "PUBLIC-READONLY-TELEMETRY-CONFIRMED"
DB_ENV = "GATEG5_TELEMETRY_DB"
DEFAULT_DB = "/tmp/gateg5_telemetry.sqlite3"

MAX_OBSERVATIONS = 100          # hard stop (count)
MAX_ELAPSED_S = 6 * 60 * 60     # hard stop (6 hours)
POLL_INTERVAL_S = 30            # bounded inter-poll gap
HEARTBEAT_EVERY_S = 300         # log a heartbeat at least this often
TARGET_ASSETS = ("BTC", "SOL")  # BTC/SOL scope only

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CLOB_BOOK = "https://clob.polymarket.com/book"
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Live S1 container — the runner must NEVER write here.
_LIVE_S1_DIR = "/root/mispricing_agent/var/s1"


class TransportError(Exception):
    """Normalized read-only transport failure (never a raw traceback)."""


class TelemetryIntegrityError(engine.ForensicError):
    """Hash-chain verification failed after an append batch."""


# =============================================================================
# DB path safety — refuse the Live S1 path outright
# =============================================================================
def _assert_not_live_s1(db_path: str) -> None:
    real = os.path.realpath(db_path)
    if real.startswith(os.path.realpath(_LIVE_S1_DIR)) or "var/s1" in db_path:
        raise PermissionError(
            f"refusing Live-S1 path for telemetry DB: {db_path!r}. "
            "Telemetry writes ONLY to an isolated /tmp or operator DB.")


def _init_telemetry_tables(conn) -> None:
    """Runner-owned side tables (TEXT/INTEGER only; never REAL)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS gateg5_telemetry_rejections("
        "  id INTEGER PRIMARY KEY, ts_ms INTEGER NOT NULL, kind TEXT NOT NULL,"
        "  reason TEXT NOT NULL, payload_digest TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS gateg5_telemetry_heartbeat("
        "  id INTEGER PRIMARY KEY, ts_ms INTEGER NOT NULL, observations INTEGER NOT NULL,"
        "  elapsed_s INTEGER NOT NULL, note TEXT NOT NULL)")
    conn.commit()


# =============================================================================
# Read-only public transport (native urllib, browser UA, normalized errors)
# =============================================================================
def _public_get(url: str, params: dict | None = None):
    if params:
        url = f"{url}?{urlencode(params)}"
    req = urllib.request.Request(url, method="GET", headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:   # noqa: S310 (public URL)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise TransportError(f"HTTP {e.code} {e.reason} from {url}") from None
    except urllib.error.URLError as e:
        raise TransportError(f"URLError {e.reason} from {url}") from None
    except json.JSONDecodeError as e:
        raise TransportError(f"non-JSON body from {url}: {e}") from None


def _select_btc_sol(markets):
    """In-memory BTC/SOL binary-market selection (no extra GET)."""
    out = []
    for m in (markets if isinstance(markets, list) else [markets]):
        slug = (m.get("slug") or "").lower()
        if not any(a.lower() in slug for a in TARGET_ASSETS):
            continue
        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except json.JSONDecodeError:
                continue
        if isinstance(toks, list) and len(toks) == 2 and (m.get("conditionId")):
            out.append(m)
    return out


def _record_rejection(conn, kind: str, reason: str, now_ms: int, digest: str = None) -> None:
    conn.execute(
        "INSERT INTO gateg5_telemetry_rejections(ts_ms,kind,reason,payload_digest) "
        "VALUES (?,?,?,?)", (now_ms, kind, reason, digest))
    conn.commit()


def _heartbeat(conn, observations: int, elapsed_s: int, now_ms: int, note: str) -> None:
    conn.execute(
        "INSERT INTO gateg5_telemetry_heartbeat(ts_ms,observations,elapsed_s,note) "
        "VALUES (?,?,?,?)", (now_ms, observations, elapsed_s, note))
    conn.commit()
    sys.stderr.write(f"[heartbeat] obs={observations} elapsed={elapsed_s}s {note}\n")


def _marks_for(conn, signal_id: str):
    rows = conn.execute(
        f"SELECT {','.join(plumbing._MARK_COLS)} FROM mark_path "
        "WHERE signal_id=? ORDER BY seq", (signal_id,)).fetchall()
    return [dict(zip(plumbing._MARK_COLS, r)) for r in rows]


# =============================================================================
# Bounded polling loop — the heart of the runner (DRAFT; NOT executed)
# =============================================================================
def run(db_path: str, *, now_ms_provider=lambda: int(time.time() * 1000)) -> dict:
    _assert_not_live_s1(db_path)                       # NO S1 PATH (refused here)
    conn = sqlite3.connect(db_path)
    plumbing.init_mock_db(conn)                        # G.5 signal_log / mark_path schema
    _init_telemetry_tables(conn)

    start_ms = now_ms_provider()
    last_hb_ms = start_ms
    observations = 0
    sig_prev = "GENESIS"
    stop_reason = "UNSET"

    while True:
        now_ms = now_ms_provider()
        # ---------- HARD STOP (count OR elapsed; whichever first) ----------
        if observations >= MAX_OBSERVATIONS:
            stop_reason = "MAX_OBSERVATIONS"
            break
        if (now_ms - start_ms) // 1000 >= MAX_ELAPSED_S:
            stop_reason = "MAX_ELAPSED_6H"
            break

        # ---------- API READ-ONLY BOUNDARY (public GET; no auth/order/wallet) ----------
        try:
            markets = _public_get(GAMMA_MARKETS,
                                  {"active": "true", "closed": "false", "limit": "50"})
            targets = _select_btc_sol(markets)
        except TransportError as te:                   # toxic transport -> rejection, not crash
            _record_rejection(conn, "TRANSPORT", str(te), now_ms)
            time.sleep(POLL_INTERVAL_S)
            continue

        for m in targets:
            if observations >= MAX_OBSERVATIONS:
                break
            obs_now = now_ms_provider()
            try:
                market, book = _fetch_market_and_book(m, obs_now)   # read-only GET only
                ns = plumbing.normalize_signal(market, book, _context(obs_now),
                                               capture_ts_ms=obs_now)
                # ---------- DB WRITER BOUNDARY (own telemetry DB; NEVER Live S1) ----------
                sig_prev = plumbing.write_signal(conn, ns, prev_hash=sig_prev)
                mark_prev = "GENESIS"
                for i, snap in enumerate(_marks_from_book(book, ns.signal, obs_now), start=1):
                    nm = plumbing.normalize_mark(snap, ns.signal, seq=i)
                    mark_prev = plumbing.write_mark(conn, nm, prev_hash=mark_prev)
                conn.commit()
                # ---------- HASH-CHAIN VERIFICATION HOOK (after each append batch) ----------
                if not engine.verify_hash_chain(_marks_for(conn, ns.signal.signal_id)):
                    raise TelemetryIntegrityError(
                        f"hash-chain broken for {ns.signal.signal_id}")
                observations += 1
            except engine.ForensicError as fe:         # toxic payload -> normalized rejection
                _record_rejection(conn, "NORMALIZER", f"{type(fe).__name__}: {fe}", obs_now)
            except Exception as e:                      # last-resort: skip, never crash the loop
                _record_rejection(conn, "UNEXPECTED", f"{type(e).__name__}: {e}", obs_now)

        # ---------- bounded heartbeat ----------
        if (now_ms - last_hb_ms) >= HEARTBEAT_EVERY_S * 1000:
            _heartbeat(conn, observations, (now_ms - start_ms) // 1000, now_ms, "tick")
            last_hb_ms = now_ms
        time.sleep(POLL_INTERVAL_S)

    _heartbeat(conn, observations, (now_ms_provider() - start_ms) // 1000,
               now_ms_provider(), f"STOP:{stop_reason}")
    conn.close()
    return {"stop_reason": stop_reason, "observations": observations, "db_path": db_path}


def _fetch_market_and_book(raw_market: dict, now_ms: int):
    """Map a Gamma market + fetch its CLOB book (read-only). Returns (market, book)."""
    toks = raw_market.get("clobTokenIds")
    if isinstance(toks, str):
        toks = json.loads(toks)
    outs = raw_market.get("outcomes")
    if isinstance(outs, str):
        outs = json.loads(outs)
    idx = 1 if len(toks) > 1 else 0
    slug = raw_market.get("slug", "") or ""
    market = {
        "asset": (slug.split("-")[0].upper() if slug else "UNKNOWN"),
        "side": "NO",
        "condition_id": raw_market.get("conditionId"),
        "token_id": toks[idx], "outcome_index": idx, "outcome_label": outs[idx],
        "slug": slug, "market_end_ts": _end_to_epoch_s(raw_market),
        "clobTokenIds": toks, "outcomes": outs,
    }
    raw_book = _public_get(CLOB_BOOK, {"token_id": market["token_id"]})
    ts = raw_book.get("timestamp", now_ms)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = now_ms
    book = {
        "asks": [[l["price"], l["size"]] for l in raw_book.get("asks", [])],
        "bids": [[l["price"], l["size"]] for l in raw_book.get("bids", [])],
        "quote_ts_ms": ts,
    }
    return market, book


def _end_to_epoch_s(raw: dict):
    import datetime
    end = raw.get("endDate") or raw.get("end_date")
    if not end:
        return None
    try:
        return int(datetime.datetime.fromisoformat(
            str(end).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _marks_from_book(book: dict, sig, now_ms: int):
    """One telemetry mark from the current book snapshot (read-only)."""
    return [{
        "ts_mark_ms": now_ms, "bids": book["bids"], "quote_ts_ms": book["quote_ts_ms"],
        "spot_price": "0", "spot_age_ms": 0, "fair_yes_t": "0.50", "fair_yes_sigma_t": "0.05",
    }]


def _context(now_ms: int) -> dict:
    """Placeholder model context (no model run here; shape-only)."""
    return {
        "reference_feed_ts": now_ms, "intended_stake": "25", "decision_cost_buffer": "0",
        "realized_entry_cost": "0", "realized_fee_cost": "0", "fair_yes": "0.50",
        "fair_yes_sigma": "0.05", "fair_model_version": "telemetry-shape-only",
        "strike": "0", "reference_price": "0", "underlying_spot_price": "0", "entry_edge": "0",
    }


def _banner() -> str:
    return (
        "Gate G.5 Bounded Telemetry Runner (DRAFT)\n"
        "  PUBLIC read-only GET only. NO auth/wallet/capital/orders. NO S1.\n"
        "  Hard stop: 100 obs OR 6h. Writes only to isolated telemetry DB.\n"
        "  Live S1: CREATED_EMPTY_LOCKED_CONTAINER; append DENIED / NOT PERFORMED; capacity 0.\n"
    )


def main(argv=None) -> int:
    sys.stderr.write(_banner())
    if os.environ.get(TELEMETRY_ARM_ENV, "") != TELEMETRY_ARM_TOKEN:
        sys.stderr.write(
            f"[GUARD] {TELEMETRY_ARM_ENV} != {TELEMETRY_ARM_TOKEN!r}. Runner UNARMED — "
            "refusing any network I/O or DB write. No fetch, no DB, no loop.\n")
        return 2
    argv = sys.argv[1:] if argv is None else argv
    db_path = (argv[0] if argv else os.environ.get(DB_ENV, DEFAULT_DB))
    result = run(db_path)
    sys.stderr.write(f"[telemetry] done: {result}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
