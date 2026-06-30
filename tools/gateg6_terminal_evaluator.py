#!/usr/bin/env python3
"""
Gate G.6 — Terminal Evaluator for G.5 FILLED_ACTIVE candidates.

Reads ended FILLED_ACTIVE candidates from a G.5 telemetry DB (READ-ONLY), fetches
PUBLIC resolution evidence (Gamma canonical + CLOB cross-check), and computes a
DIAGNOSTIC terminal PnL per candidate.

HARD BOUNDARIES:
  * PUBLIC read-only GET only. NO auth, NO wallet, NO signing, NO capital, NO orders.
  * DB opened READ-ONLY/immutable; NO DB writes.
  * NO S1 access. Live S1 stays CREATED_EMPTY_LOCKED_CONTAINER; append DENIED.
  * Live fetch is inert unless armed: GATEG6_EVAL_ARM=PUBLIC-READONLY-EVAL-CONFIRMED.

WARNING: results are HL-basis diagnostic edge realization, NOT tradeable alpha.
Polymarket up/down markets settle on the Chainlink BTC/USD stream; the G.5
entry_edge was computed off a Hyperliquid diagnostic basis (source-basis
confounder). This evaluator measures realization of that diagnostic edge only.

Resolution logic is split into PURE deciders (gamma_decide / clob_decide) that take
already-fetched JSON, plus thin live fetchers — so unit tests run fully offline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from itertools import zip_longest
from urllib.parse import urlencode

EVAL_ARM_ENV = "GATEG6_EVAL_ARM"
EVAL_ARM_TOKEN = "PUBLIC-READONLY-EVAL-CONFIRMED"
DEFAULT_DB = "/tmp/gateg5_edge_telemetry_1000.sqlite3"

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CLOB_MARKETS = "https://clob.polymarket.com/markets"   # GET /markets/{condition_id}
POLYMARKET_URL = "https://polymarket.com/market/{slug}"
DEFAULT_STAKE = Decimal("25")
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "application/json",
}

# status strings
ST_RESOLVED = "RESOLVED"
ST_NOT_FINAL = "UNRESOLVED_NOT_FINAL"
ST_CONFLICT = "UNRESOLVED_CONFLICT"
ST_RES_MISSING = "RESOLUTION_MISSING"
ST_CLOB_MISSING = "CLOB_FINAL_STATE_MISSING"
ST_PRICE_TOKEN_MISMATCH = "PRICE_TOKEN_MISMATCH"
ST_OUTCOME_AMBIGUOUS = "OUTCOME_INDEX_AMBIGUOUS"
ST_RES_NOT_FINAL = "RESOLUTION_NOT_FINAL"
ST_VOID_OR_REFUND = "VOID_OR_REFUND"

FAIL_CLOSED = (ST_NOT_FINAL, ST_CONFLICT, ST_RES_MISSING, ST_CLOB_MISSING,
               ST_PRICE_TOKEN_MISMATCH, ST_OUTCOME_AMBIGUOUS, ST_RES_NOT_FINAL,
               ST_VOID_OR_REFUND)

CHAINLINK_NOTE = "CHAINLINK_REFERENCE_UNAVAILABLE"
ALPHA_WARNING = "HL-basis diagnostic edge realization, not tradeable alpha."
UNKNOWN_PRICE_TOKEN = "UNKNOWN_PRICE_TOKEN_BINDING"

# Down<->No, Up<->Yes synonyms; anything else normalizes to None -> FAIL CLOSED.
_LABEL_SYNONYMS = {"down": "DOWN", "no": "DOWN", "up": "UP", "yes": "UP"}
_WINDOW_RE = re.compile(r"updown-15m-(\d+)")


class TransportError(Exception):
    """Normalized public-GET failure (never a raw traceback)."""


# =============================================================================
# small helpers
# =============================================================================
def _coerce_list(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    return v


def _d(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _norm_label(s):
    if not isinstance(s, str):
        return None
    return _LABEL_SYNONYMS.get(s.strip().lower())


def window_of(slug):
    m = _WINDOW_RE.search(slug or "")
    return m.group(1) if m else None


# =============================================================================
# PURE deciders (take already-fetched JSON; no network) — unit-tested offline
# =============================================================================
def gamma_decide(payload, slug, condition_id):
    """Canonical Gamma decision. Returns (status, winner_index, meta)."""
    markets = payload if isinstance(payload, list) else [payload]
    markets = [m for m in markets if isinstance(m, dict)
               and m.get("slug") == slug and m.get("conditionId") == condition_id]
    if not markets:
        return (ST_RES_MISSING, None, {})
    m = markets[0]
    meta = {"clobTokenIds": _coerce_list(m.get("clobTokenIds")),
            "outcomes": _coerce_list(m.get("outcomes")),
            "outcomePrices": _coerce_list(m.get("outcomePrices")),
            "closed": m.get("closed"), "umaResolutionStatus": m.get("umaResolutionStatus"),
            "resolutionSource": m.get("resolutionSource")}
    if not m.get("closed"):
        return (ST_RES_NOT_FINAL, None, meta)
    if str(m.get("umaResolutionStatus") or "").lower() != "resolved":
        return (ST_RES_NOT_FINAL, None, meta)
    prices = meta["outcomePrices"]
    if not isinstance(prices, list) or len(prices) != 2:
        return (ST_VOID_OR_REFUND, None, meta)         # non-binary -> refund/void
    dec = [_d(p) for p in prices]
    if any(p is None for p in dec):
        return (ST_RES_MISSING, None, meta)
    winners = [i for i, p in enumerate(dec) if p >= Decimal("0.99")]
    if len(winners) == 1:
        return (ST_RESOLVED, winners[0], meta)
    if all(Decimal("0.4") <= p <= Decimal("0.6") for p in dec):
        return (ST_VOID_OR_REFUND, None, meta)
    return (ST_RES_NOT_FINAL, None, meta)


def clob_decide(payload, condition_id):
    """CLOB cross-check decision from /markets/{cid}. Returns (status, winner_token, meta)."""
    m = payload
    if not isinstance(m, dict):
        return (ST_CLOB_MISSING, None, {})
    if (m.get("condition_id") or m.get("conditionId")) != condition_id:
        return (ST_CLOB_MISSING, None, {})
    if not m.get("closed"):
        return (ST_RES_NOT_FINAL, None, {"closed": m.get("closed")})
    tokens = m.get("tokens") or []
    token_ids = {str(t.get("token_id")) for t in tokens if t.get("token_id") is not None}
    wins = [t for t in tokens if t.get("winner") is True]
    meta = {"tokens": tokens, "token_ids": token_ids}
    if len(wins) != 1:
        return (ST_VOID_OR_REFUND, None, meta)
    meta["winner_outcome"] = wins[0].get("outcome")
    return (ST_RESOLVED, str(wins[0].get("token_id")), meta)


# =============================================================================
# live public read-only fetchers (thin; injected-over in tests)
# =============================================================================
def _get(url, params=None):
    if params:
        url = f"{url}?{urlencode(params)}"
    req = urllib.request.Request(url, method="GET", headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:    # noqa: S310 (public URL)
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise TransportError(f"HTTP {e.code} {e.reason} from {url}") from None
    except urllib.error.URLError as e:
        raise TransportError(f"URLError {e.reason} from {url}") from None
    except json.JSONDecodeError as e:
        raise TransportError(f"non-JSON from {url}: {e}") from None


def gamma_fetch_live(slug, condition_id):
    return _get(GAMMA_MARKETS, {"slug": slug, "closed": "true"})


def clob_fetch_live(condition_id):
    return _get(f"{CLOB_MARKETS}/{condition_id}")


# =============================================================================
# per-candidate terminal evaluation (fetchers injectable for offline tests)
# =============================================================================
def evaluate_candidate(cand, *, gamma_fetch=gamma_fetch_live, clob_fetch=clob_fetch_live):
    cid = cand["condition_id"]
    slug = cand.get("slug")
    if not slug:
        return {**_base(cand), "status": ST_RES_MISSING, "reason": "no slug"}

    # ---- Gamma canonical ----
    try:
        g_payload = gamma_fetch(slug, cid)
    except TransportError as te:
        return {**_base(cand), "status": ST_RES_MISSING, "reason": str(te)}
    g_status, g_idx, g_meta = gamma_decide(g_payload, slug, cid)
    if g_status != ST_RESOLVED:
        return {**_base(cand), "status": g_status,
                "resolution_source": g_meta.get("resolutionSource", CHAINLINK_NOTE),
                "gamma": {k: g_meta.get(k) for k in ("closed", "umaResolutionStatus",
                                                     "outcomePrices", "outcomes")}}

    outcomes = g_meta.get("outcomes") or []
    token_ids = g_meta.get("clobTokenIds") or []
    if not (isinstance(outcomes, list) and 0 <= g_idx < len(outcomes)
            and isinstance(token_ids, list) and 0 <= g_idx < len(token_ids)):
        return {**_base(cand), "status": ST_OUTCOME_AMBIGUOUS, "gamma_winner_index": g_idx,
                "gamma_outcomes": outcomes}
    gamma_winner_label = outcomes[g_idx]
    gamma_winner_token = str(token_ids[g_idx])

    # ---- LABEL-based binding (synonyms; never positional fallback) ----
    norm_local = _norm_label(cand["outcome_label"])
    norm_outcomes = [_norm_label(o) for o in outcomes]
    if norm_local is None or norm_outcomes.count(norm_local) != 1:
        return {**_base(cand), "status": ST_OUTCOME_AMBIGUOUS,
                "gamma_outcomes": outcomes, "local_label": cand["outcome_label"]}
    cand_gamma_idx = norm_outcomes.index(norm_local)
    if str(cand["token_id"]) != str(token_ids[cand_gamma_idx]):
        return {**_base(cand), "status": ST_OUTCOME_AMBIGUOUS,
                "reason": "local token_id != gamma token at local label index"}

    # ---- CLOB cross-check ----
    try:
        c_payload = clob_fetch(cid)
    except TransportError as te:
        return {**_base(cand), "status": ST_CLOB_MISSING, "reason": str(te),
                "gamma_winner_token": gamma_winner_token}
    c_status, c_winner_token, c_meta = clob_decide(c_payload, cid)
    if c_status != ST_RESOLVED:
        return {**_base(cand),
                "status": (c_status if c_status in FAIL_CLOSED else ST_CLOB_MISSING),
                "gamma_winner_token": gamma_winner_token}
    if str(cand["token_id"]) not in c_meta.get("token_ids", set()):
        return {**_base(cand), "status": ST_PRICE_TOKEN_MISMATCH,
                "reason": "candidate token_id absent from CLOB tokens"}
    if gamma_winner_token != str(c_winner_token):
        return {**_base(cand), "status": ST_CONFLICT,
                "gamma_winner_token": gamma_winner_token, "clob_winner_token": str(c_winner_token)}

    priced_token_id = str(c_winner_token)
    if not priced_token_id or priced_token_id == UNKNOWN_PRICE_TOKEN:
        return {**_base(cand), "status": ST_PRICE_TOKEN_MISMATCH,
                "reason": "priced_token_id unresolved at PnL computation"}

    # ---- diagnostic PnL with normalized $25 clamp ----
    matched = (str(cand["token_id"]) == gamma_winner_token)
    payout = Decimal("1") if matched else Decimal("0")
    exec_ask = _d(cand["exec_ask_vwap"]) or Decimal("0")
    pnl_per_share = payout - exec_ask
    qty_avail = _d(cand.get("exec_fill_qty_avail"))
    stake_qty = (DEFAULT_STAKE / exec_ask) if exec_ask > 0 else Decimal("0")
    # clamp: never credit more shares than the $25 stake could buy
    norm_qty = min(qty_avail, stake_qty) if (qty_avail is not None and qty_avail > 0) else stake_qty
    normalized_pnl_25 = pnl_per_share * norm_qty
    return {**_base(cand), "status": ST_RESOLVED, "winner_index": g_idx,
            "gamma_winner_label": gamma_winner_label, "winner_token": gamma_winner_token,
            "clob_winner_outcome": c_meta.get("winner_outcome"),
            "priced_token_id": priced_token_id,
            "resolution_source": g_meta.get("resolutionSource", CHAINLINK_NOTE),
            "matched": matched, "payout": str(payout),
            "pnl_per_share": str(pnl_per_share),                 # PRIMARY metric
            "normalized_qty_25": str(norm_qty),
            "normalized_pnl_at_25usd": str(normalized_pnl_25)}   # dollar diagnostic


def _base(cand):
    return {"signal_id": cand["signal_id"], "asset": cand["asset"], "slug": cand.get("slug"),
            "window": window_of(cand.get("slug")),
            "outcome_label": cand["outcome_label"], "outcome_index": cand["outcome_index"],
            "token_id": cand["token_id"], "exec_ask_vwap": cand["exec_ask_vwap"],
            "entry_edge": cand["entry_edge"], "condition_id": cand["condition_id"],
            "market_end_ts": cand["market_end_ts"], "ts_signal": cand.get("ts_signal"),
            "priced_token_id": UNKNOWN_PRICE_TOKEN, "chainlink_reference": CHAINLINK_NOTE,
            "market_url": POLYMARKET_URL.format(slug=cand.get("slug"))}


# =============================================================================
# read-only candidate loading + grouping / effective-N
# =============================================================================
def load_candidates(db_path, now_s):
    uri = f"file:{db_path}?mode=ro&immutable=1"
    c = sqlite3.connect(uri, uri=True)
    try:
        rows = c.execute(
            "SELECT signal_id, asset, outcome_label, outcome_index, condition_id, "
            "       token_id, exec_ask_vwap, exec_fill_qty_avail, entry_edge, "
            "       ts_signal, market_end_ts, slug "
            "FROM signal_log "
            "WHERE fill_decision='FILLED_ACTIVE' AND market_end_ts <= ? "
            "ORDER BY market_end_ts",
            (now_s,)).fetchall()
    finally:
        c.close()
    cols = ["signal_id", "asset", "outcome_label", "outcome_index", "condition_id",
            "token_id", "exec_ask_vwap", "exec_fill_qty_avail", "entry_edge",
            "ts_signal", "market_end_ts", "slug"]
    return [dict(zip(cols, r)) for r in rows]


def dedup_earliest(cands):
    """One representative per condition_id, the EARLIEST ts_signal (inference view)."""
    best = {}
    for c in cands:
        cid = c["condition_id"]
        ts = c.get("ts_signal") or ""
        if cid not in best or str(ts) < str(best[cid].get("ts_signal") or ""):
            best[cid] = c
    return list(best.values())


def effective_n_report(cands):
    cids = [c["condition_id"] for c in cands]
    windows = [window_of(c.get("slug")) for c in cands if window_of(c.get("slug"))]
    dup = {}
    for cid in cids:
        dup[cid] = dup.get(cid, 0) + 1
    win_assets = {}
    for c in cands:
        w = window_of(c.get("slug"))
        if w:
            win_assets.setdefault(w, set()).add(c["asset"])
    cross = [w for w, a in win_assets.items() if len(a) > 1]
    return {"total_rows": len(cands),
            "unique_condition_ids": len(set(cids)),
            "unique_windows": len(set(win_assets)),
            "duplicate_condition_ids": sum(1 for v in dup.values() if v > 1),
            "same_window_cross_asset_windows": len(cross),
            "correlation_warning": (len(cross) > 0)}


def select_distinct(cands, *, limit=None, distinct=False, mixed=False):
    if not distinct and not mixed and not limit:
        return cands
    rep = {}
    for c in cands:
        cid = c["condition_id"]
        if cid not in rep or (_d(c["entry_edge"]) or Decimal(0)) > (_d(rep[cid]["entry_edge"]) or Decimal(0)):
            rep[cid] = c
    reps = list(rep.values())
    if mixed:
        btc = [c for c in reps if c["asset"] == "BTC"]
        sol = [c for c in reps if c["asset"] == "SOL"]
        other = [c for c in reps if c["asset"] not in ("BTC", "SOL")]
        reps = [c for pair in zip_longest(btc, sol) for c in pair if c] + other
    if limit:
        reps = reps[:limit]
    return reps


# =============================================================================
# modes
# =============================================================================
def dry_run(db_path, now_s):
    cands = load_candidates(db_path, now_s)
    print(f"[dry-run] DB={db_path}")
    print(f"[dry-run] ended FILLED_ACTIVE candidates: {len(cands)}")
    print(f"[dry-run] effective_n: {json.dumps(effective_n_report(cands))}")
    print(f"[dry-run] {ALPHA_WARNING}")
    print(f"[dry-run] chainlink_reference: {CHAINLINK_NOTE} (no settlement fetch in dry-run)")
    for c in cands:
        print(json.dumps({"signal_id": c["signal_id"], "asset": c["asset"], "slug": c["slug"],
                          "window": window_of(c["slug"]), "outcome_label": c["outcome_label"],
                          "token_id": c["token_id"], "exec_ask_vwap": c["exec_ask_vwap"],
                          "priced_token_id": UNKNOWN_PRICE_TOKEN,
                          "condition_id": c["condition_id"], "market_end_ts": c["market_end_ts"]}))


def evaluate_all(db_path, now_s, *, limit=None, distinct=False, mixed=False):
    cands = load_candidates(db_path, now_s)
    eff = effective_n_report(cands)
    selected = select_distinct(cands, limit=limit, distinct=distinct, mixed=mixed)
    results = [evaluate_candidate(c) for c in selected]       # public GETs only; NO DB write
    resolved = [r for r in results if r["status"] == ST_RESOLVED]
    agg = {"effective_n": eff, "selected": len(results),
           "unique_condition_ids_selected": len({r["condition_id"] for r in results}),
           "asset_split": {a: sum(1 for r in results if r["asset"] == a)
                           for a in sorted({r["asset"] for r in results})},
           "resolved": len(resolved),
           "fail_closed": {s: sum(1 for r in results if r["status"] == s)
                           for s in FAIL_CLOSED if any(r["status"] == s for r in results)}}
    if resolved:
        wins = sum(1 for r in resolved if r["matched"])
        agg["win_rate"] = f"{wins}/{len(resolved)}"
        agg["avg_pnl_per_share"] = str(sum(Decimal(r["pnl_per_share"]) for r in resolved) / len(resolved))
    print(json.dumps({"warning": ALPHA_WARNING, "chainlink_reference": CHAINLINK_NOTE,
                      "aggregate": agg, "results": results}, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--distinct-condition-ids", action="store_true")
    ap.add_argument("--mixed-assets", action="store_true")
    ap.add_argument("--now", type=int, default=None)
    args = ap.parse_args(argv)
    import time
    now_s = args.now if args.now is not None else int(time.time())

    sys.stderr.write("Gate G.6 Terminal Evaluator — public read-only, no DB write, no S1.\n")
    if args.dry_run:
        dry_run(args.db, now_s)
        return 0
    if os.environ.get(EVAL_ARM_ENV, "") != EVAL_ARM_TOKEN:
        sys.stderr.write(
            f"[GUARD] {EVAL_ARM_ENV} != {EVAL_ARM_TOKEN!r}. UNARMED — refusing network "
            "resolution fetch. Use --dry-run for the read-only candidate plan.\n")
        return 2
    evaluate_all(args.db, now_s, limit=args.limit,
                 distinct=args.distinct_condition_ids, mixed=args.mixed_assets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
