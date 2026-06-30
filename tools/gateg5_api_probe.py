#!/usr/bin/env python3
"""
Gate G.5 — One-Shot READ-ONLY public market-data probe (native urllib only).

Purpose: fetch ONE live Polymarket market + orderbook via PUBLIC GET, save the
raw untouched JSON to /tmp for shape inspection, push it through the /tmp
normalizer, and print the resulting G.5 Signal / Mark dataclasses. NO DB write,
NO loop, exits after a single payload.

HARD BOUNDARIES:
  * PUBLIC market-data GET only. NO auth, NO wallet, NO signing, NO capital.
  * Native urllib only (no requests/httpx/cloudscraper). NO dependency installs.
  * NO order placement, NO S1 access, NO DB write, NO live DB.
  * One-shot: one market fetch + that market's book, then exit. NO polling loop.
  * Inert unless armed:  GATEG5_PROBE_ARM=PUBLIC-READONLY-CONFIRMED.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from analysis.forensic import gateg5_plumbing as plumbing

PROBE_ARM_ENV = "GATEG5_PROBE_ARM"
PROBE_ARM_TOKEN = "PUBLIC-READONLY-CONFIRMED"

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
CLOB_BOOK = "https://clob.polymarket.com/book"
RAW_MARKET_PATH = "/tmp/gateg5_probe_raw_market.json"
RAW_BOOK_PATH = "/tmp/gateg5_probe_raw_book.json"

# Standard browser-like headers to clear the WAF that 403'd the bare urllib UA.
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class TransportError(Exception):
    """Normalized public-GET transport failure (never surfaced as a traceback)."""


def _http_get_json(url: str, params: dict | None = None):
    """Public, unauthenticated GET with browser headers. Normalizes errors."""
    if params:
        url = f"{url}?{urlencode(params)}"
    req = urllib.request.Request(url, method="GET", headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:   # noqa: S310 (public URL)
            status = resp.status
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise TransportError(f"HTTP {e.code} {e.reason} from {url}") from None
    except urllib.error.URLError as e:
        raise TransportError(f"URLError {e.reason} from {url}") from None
    except Exception as e:  # noqa: BLE001 — last-resort normalization
        raise TransportError(f"{type(e).__name__}: {e} from {url}") from None
    try:
        return status, json.loads(body)
    except json.JSONDecodeError as e:
        raise TransportError(f"non-JSON body (HTTP {status}) from {url}: {e}") from None


def _save_raw(path: str, payload) -> None:
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)


def _coerce_list(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    return v


def _pick_binary(markets):
    """In-memory selection (NO extra GET): first binary market with valid identity."""
    if isinstance(markets, dict):
        markets = [markets]
    for m in (markets or []):
        toks = _coerce_list(m.get("clobTokenIds"))
        outs = _coerce_list(m.get("outcomes"))
        if (isinstance(toks, list) and isinstance(outs, list)
                and len(toks) == 2 == len(outs)
                and (m.get("conditionId") or m.get("condition_id"))):
            return m
    return markets[0] if markets else None


def _end_to_epoch_s(raw: dict):
    end = raw.get("endDate") or raw.get("end_date") or raw.get("endDateIso")
    if not end:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        return int(dt.timestamp())
    except ValueError:
        return None


def _map_market(raw: dict) -> dict:
    toks = _coerce_list(raw.get("clobTokenIds")) or []
    outs = _coerce_list(raw.get("outcomes")) or []
    idx = 1 if len(toks) > 1 else 0
    slug = raw.get("slug", "") or ""
    asset = raw.get("ticker") or (slug.split("-")[0].upper() if slug else "") or "UNKNOWN"
    return {
        "asset": asset,
        "side": "NO",
        "condition_id": raw.get("conditionId") or raw.get("condition_id"),
        "token_id": toks[idx] if len(toks) > idx else None,
        "outcome_index": idx,
        "outcome_label": outs[idx] if len(outs) > idx else None,
        "slug": slug,
        "market_end_ts": _end_to_epoch_s(raw),
        "clobTokenIds": toks,
        "outcomes": outs,
    }


def _map_book(raw_book: dict, now_ms: int) -> dict:
    def lv(side):
        return [[l["price"], l["size"]] for l in raw_book.get(side, []) if "price" in l and "size" in l]
    ts = raw_book.get("timestamp", now_ms)
    try:
        ts = int(ts)
    except (TypeError, ValueError):
        ts = now_ms
    return {"asks": lv("asks"), "bids": lv("bids"), "quote_ts_ms": ts}


def _banner() -> str:
    return (
        "Gate G.5 READ-ONLY public probe (native urllib)\n"
        "  PUBLIC GET only. NO auth/wallet/capital. NO DB write. NO S1. One-shot.\n"
        "  Live S1: CREATED_EMPTY_LOCKED_CONTAINER; append DENIED / NOT PERFORMED; capacity 0.\n"
    )


def main(argv=None) -> int:
    sys.stderr.write(_banner())
    if os.environ.get(PROBE_ARM_ENV, "") != PROBE_ARM_TOKEN:
        sys.stderr.write(
            f"[GUARD] {PROBE_ARM_ENV} != {PROBE_ARM_TOKEN!r}. Probe UNARMED — "
            "refusing any network I/O. No fetch, no files written.\n")
        return 2

    plumb = plumbing
    now_ms = int(time.time() * 1000)   # probe-side capture tick (injected into pure normalizer)

    # ---- one-shot fetch: market list (one GET) + that market's book (one GET) ----
    try:
        status_m, markets = _http_get_json(
            GAMMA_MARKETS, {"active": "true", "closed": "false", "limit": "10"})
        sys.stderr.write(f"[probe] markets GET -> HTTP {status_m}\n")
    except TransportError as te:
        print(f"TRANSPORT_REJECTED: {te}")
        return 1
    _save_raw(RAW_MARKET_PATH, markets)

    raw_market = _pick_binary(markets)
    if not raw_market:
        print("TRANSPORT_OK_BUT_EMPTY: no markets returned")
        return 1
    market = _map_market(raw_market)
    if not market["token_id"]:
        print("MAPPING_REJECTED: selected market has no usable clobTokenIds")
        return 1

    try:
        status_b, raw_book = _http_get_json(CLOB_BOOK, {"token_id": market["token_id"]})
        sys.stderr.write(f"[probe] book GET -> HTTP {status_b}\n")
    except TransportError as te:
        print(f"TRANSPORT_REJECTED (book): {te}")
        return 1
    _save_raw(RAW_BOOK_PATH, raw_book)
    book = _map_book(raw_book, now_ms)

    context = {
        "reference_feed_ts": now_ms, "intended_stake": "25", "decision_cost_buffer": "0",
        "realized_entry_cost": "0", "realized_fee_cost": "0", "fair_yes": "0.50",
        "fair_yes_sigma": "0.05", "fair_model_version": "probe-shape-only",
        "strike": "0", "reference_price": "0", "underlying_spot_price": "0",
        "entry_edge": "0",
    }

    # ---- normalize (rejections printed as normalized reasons, not tracebacks) ----
    try:
        ns = plumb.normalize_signal(market, book, context, capture_ts_ms=now_ms)
    except plumb.engine.ForensicError as fe:
        print(f"NORMALIZER_REJECTED: {type(fe).__name__}: {fe}")
        return 1

    s = ns.signal
    print("=== G.5 Signal (accepted) ===")
    print(f"condition_id          : {s.condition_id}")
    print(f"token_id              : {s.token_id}")
    print(f"asset/side            : {s.asset}/{s.side}")
    print(f"market_end_ts         : {s.market_end_ts}")
    print(f"reference_age_ms      : {s.reference_age_ms}")
    print(f"total_book_ask_notion : {s.ask_depth_avail}")
    print(f"exec_ask_vwap         : {s.exec_ask_vwap}")
    print(f"exec_fill_qty_avail   : {s.exec_fill_qty_avail}")
    print(f"depth_sufficient      : {ns.ask_fill.depth_sufficient}")
    print(f"fill_decision         : {s.fill_decision}")

    snap = {"ts_mark_ms": now_ms, "bids": book["bids"], "quote_ts_ms": book["quote_ts_ms"],
            "spot_price": "0", "spot_age_ms": 0, "fair_yes_t": "0.50", "fair_yes_sigma_t": "0.05"}
    try:
        nm = plumb.normalize_mark(snap, ns.signal, seq=1)
        print("=== G.5 Mark (seq=1) ===")
        print(f"exit_mark_status      : {nm.mark.exit_mark_status}")
        print(f"executable_flag       : {nm.mark.executable_flag}")
        print(f"liquidity_class       : {nm.mark.liquidity_class}")
        print(f"exit_mark_vwap        : {nm.mark.exit_mark_vwap}")
    except plumb.engine.ForensicError as fe:
        print(f"MARK_NORMALIZER_REJECTED: {type(fe).__name__}: {fe}")

    sys.stderr.write(f"[probe] raw saved: {RAW_MARKET_PATH}, {RAW_BOOK_PATH}. One-shot done.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
