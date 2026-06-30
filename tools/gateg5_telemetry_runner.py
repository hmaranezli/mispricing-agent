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
import math
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal
from urllib.parse import urlencode

from analysis.forensic import gateg5_model as gm
from analysis.forensic import gateg5_plumbing as plumbing

engine = plumbing.engine

# --- arming + hard bounds (constitution; bounds overridable via env for a run) ---
TELEMETRY_ARM_ENV = "GATEG5_TELEMETRY_ARM"
TELEMETRY_ARM_TOKEN = "PUBLIC-READONLY-TELEMETRY-CONFIRMED"
DB_ENV = "GATEG5_TELEMETRY_DB"
DEFAULT_DB = "/tmp/gateg5_telemetry.sqlite3"

MAX_OBSERVATIONS = int(os.environ.get("GATEG5_MAX_OBSERVATIONS", "100"))  # hard stop (count)
MAX_ELAPSED_S = int(os.environ.get("GATEG5_MAX_ELAPSED_S", str(6 * 60 * 60)))  # hard stop (s)
POLL_INTERVAL_S = 30            # bounded inter-poll gap
HEARTBEAT_EVERY_S = 300         # log a heartbeat at least this often
def _parse_target_assets(raw, default=("BTC", "SOL")):
    """Parse GATEG5_TARGET_ASSETS (comma list): strip, uppercase, drop empties.
    Fail closed to the default if nothing valid remains."""
    if not raw:
        return tuple(default)
    assets = tuple(t.strip().upper() for t in raw.split(",") if t.strip())
    return assets if assets else tuple(default)


TARGET_ASSETS = _parse_target_assets(os.environ.get("GATEG5_TARGET_ASSETS"))  # default BTC,SOL
TARGET_INTERVAL_S = 900         # 15m up/down window
INTENDED_STAKE = "25"           # diagnostic stake (paper-only)
REFERENCE_SOURCE = "HL_DIAGNOSTIC_BASIS"  # HL reference is diagnostic, not the Chainlink oracle

# Hyperliquid public read-only info endpoint (no auth, no wallet).
HL_INFO = "https://api.hyperliquid.xyz/info"
SIGMA_FALLBACK = 0.80           # mirrors data/hl_candles.calculate_realized_volatility fallback
SIGMA_CLAMP = (0.30, 3.00)      # mirrors hl_candles guardrail

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


def _window_start_epoch(now_s: int, interval_s: int = TARGET_INTERVAL_S) -> int:
    """Align an epoch-second to the current interval boundary."""
    return (now_s // interval_s) * interval_s


def _target_slugs(now_ms: int):
    """Exact BTC/SOL 15m up/down slugs for the current AND next window.

    Bounded: len(TARGET_ASSETS) * 2 == 4 slugs per cycle. No broad scan.
    """
    now_s = now_ms // 1000
    start = _window_start_epoch(now_s)
    for asset in TARGET_ASSETS:
        a = asset.lower()
        yield f"{a}-updown-15m-{start}"               # current window
        yield f"{a}-updown-15m-{start + TARGET_INTERVAL_S}"  # next window (about to open)


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

        # ---------- API READ-ONLY BOUNDARY: exact slug-targeted fetches ----------
        # Bounded: <=4 slug market GETs/cycle (BTC/SOL x current/next window) + a
        # book GET per hit. Public GET only; no auth/order/private/wallet endpoints.
        for slug in _target_slugs(now_ms):
            if observations >= MAX_OBSERVATIONS:
                break
            obs_now = now_ms_provider()
            try:
                hits = _public_get(GAMMA_MARKETS, {"slug": slug})   # 0-1 market
            except TransportError as te:               # toxic transport -> rejection, not crash
                _record_rejection(conn, "TRANSPORT", f"{slug}: {te}", obs_now)
                continue
            markets = [m for m in (hits if isinstance(hits, list) else [hits])
                       if m and m.get("conditionId")]
            if not markets:                            # slug not live this window -> diagnostic
                _record_rejection(conn, "TARGET_MISS", f"no live market for slug {slug}", obs_now)
                continue
            for m in markets:
                if observations >= MAX_OBSERVATIONS:
                    break
                try:
                    market, book = _fetch_market_and_book(m, obs_now)   # read-only GET only
                    # ---------- HL-basis READ-ONLY model context (no order/wallet/S1) ----------
                    context = _model_context(market["asset"], market, book, obs_now)
                    ns = plumbing.normalize_signal(market, book, context, capture_ts_ms=obs_now)
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
                except (TransportError, gm.ModelInputError) as me:  # reference/model unavailable
                    _record_rejection(conn, "MODEL_CONTEXT", f"{slug}: {type(me).__name__}: {me}", obs_now)
                except engine.ForensicError as fe:     # toxic payload -> normalized rejection
                    _record_rejection(conn, "NORMALIZER", f"{slug}: {type(fe).__name__}: {fe}", obs_now)
                except Exception as e:                  # last-resort: skip, never crash the loop
                    _record_rejection(conn, "UNEXPECTED", f"{slug}: {type(e).__name__}: {e}", obs_now)

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


# =============================================================================
# Hyperliquid public read-only reference (sync urllib; NO auth/wallet/order)
# =============================================================================
def _hl_post(payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(HL_INFO, data=data, method="POST",
                                 headers={**_HEADERS, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:   # noqa: S310 (public URL)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise TransportError(f"HL HTTP {e.code} {e.reason}") from None
    except urllib.error.URLError as e:
        raise TransportError(f"HL URLError {e.reason}") from None
    except json.JSONDecodeError as e:
        raise TransportError(f"HL non-JSON: {e}") from None


def _hl_candles(coin: str, start_ms: int, end_ms: int, interval: str = "1m"):
    cs = _hl_post({"type": "candleSnapshot",
                   "req": {"coin": coin, "interval": interval,
                           "startTime": int(start_ms), "endTime": int(end_ms)}})
    if not isinstance(cs, list) or not cs:
        raise TransportError(f"HL empty candles for {coin} [{start_ms},{end_ms}]")
    return cs


def _hl_price_feedts(coin: str, ts_ms: int):
    """(close_price Decimal, feed_ts_ms int) for the latest candle at/just before ts_ms.

    Picking a candle with t <= ts_ms guarantees a non-negative reference age (no lookahead).
    """
    cs = _hl_candles(coin, ts_ms - 120_000, ts_ms + 120_000)
    past = [c for c in cs if int(c["t"]) <= ts_ms]
    chosen = max(past, key=lambda c: int(c["t"])) if past else \
        min(cs, key=lambda c: abs(int(c["t"]) - ts_ms))
    return Decimal(str(chosen["c"])), int(chosen["t"])


def _realized_vol_annual(candles) -> float:
    """Annualized realized vol from 1m candles; mirrors hl_candles.calculate_realized_volatility
    (clamp [0.30, 3.00]; fallback 0.80). Inlined to avoid an aiohttp import in this sync runner."""
    if not candles or len(candles) < 2:
        return SIGMA_FALLBACK
    rets = []
    for i in range(1, len(candles)):
        prev, curr = float(candles[i - 1]["c"]), float(candles[i]["c"])
        if prev > 0 and curr > 0:
            rets.append(math.log(curr / prev))
    if len(rets) < 2:
        return SIGMA_FALLBACK
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
    raw = math.sqrt(var) * math.sqrt(525_600)
    return max(SIGMA_CLAMP[0], min(raw, SIGMA_CLAMP[1]))


def _hl_sigma_annual(coin: str, now_ms: int) -> float:
    return _realized_vol_annual(_hl_candles(coin, now_ms - 60 * 60 * 1000, now_ms))


def _model_context(asset: str, market: dict, book: dict, now_ms: int) -> dict:
    """Real read-only HL-basis diagnostic model context (Decimal-safe via gateg5_model).

    Reference/strike are a Hyperliquid DIAGNOSTIC BASIS (REFERENCE_SOURCE), NOT the
    Chainlink settlement oracle; edge here is HL-basis diagnostic, not alpha.
    Observation-only: feeds signal_log/diagnostics; no trade routing.
    """
    market_end_ts = int(market["market_end_ts"])
    window_start_ms = (market_end_ts - TARGET_INTERVAL_S) * 1000

    p_now, feed_ts = _hl_price_feedts(asset, now_ms)            # current underlying + feed ts
    strike, _ = _hl_price_feedts(asset, window_start_ms)        # window-open price = strike
    sigma_annual = _hl_sigma_annual(asset, now_ms)

    tte_s = market_end_ts - (now_ms // 1000)
    if tte_s <= 0:
        raise gm.ModelInputError("nonpositive tte for market window")
    tte_years = Decimal(tte_s) / gm.SECONDS_PER_YEAR

    fair_yes = gm.fair_yes_gbm(p_now, strike, sigma_annual, tte_years)  # P(up), Decimal

    # exec_ask_vwap computed exactly as plumbing.normalize_signal will (deterministic),
    # so the NO-leg edge is consistent with the stored exec_ask_vwap.
    asks_json = plumbing.ladder_to_decimal_json(book["asks"])
    fill = plumbing.walk_ask_ladder_for_stake(
        plumbing.parse_ask_ladder(asks_json), Decimal(INTENDED_STAKE))
    # zero-cost convention preserved explicitly (fee/slippage/margin = 0)
    entry_edge = gm.no_side_entry_edge(fair_yes, fill.exec_ask_vwap)

    return {
        "reference_feed_ts": feed_ts,           # real HL candle ts -> nonzero reference_age_ms
        "intended_stake": INTENDED_STAKE,
        "decision_cost_buffer": "0",
        "realized_entry_cost": "0", "realized_fee_cost": "0",   # zero-cost convention
        "fair_yes": str(fair_yes),
        "fair_yes_sigma": str(Decimal(str(sigma_annual))),
        "fair_model_version": f"hl-basis-gbm-digital-v0/{REFERENCE_SOURCE}",
        "strike": str(strike),
        "reference_price": str(p_now),
        "underlying_spot_price": str(p_now),
        "entry_edge": str(entry_edge),
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
