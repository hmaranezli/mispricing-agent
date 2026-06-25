"""data/reference_collector.py — Tier-0 PUBLIC_REFERENCE_BASKET evidence collector (radar, NOT trading).

Concurrently + timed fetches Coinbase + Kraken USD **spot** and Hyperliquid **perp** (all via injected
clients), then writes APPEND-ONLY evidence to three isolated tables against the supplied ``db_path``:
  reference_price_ticks         — one row per source (including rejected sources; rejection is evidence)
  proxy_reference_basket_ticks  — Coinbase+Kraken midpoint + spread guard (perp NEVER merged in)
  perp_basis_ticks              — Hyperliquid perp basis vs the spot basket (separate row)

Tier-0 = collect only. NO candidate flagging, NO order/positions/shadow writes, NO trading/sizing, NO
runtime-loop wiring. All economic math uses ``Decimal`` and is stored as canonical decimal strings.
``spread_guard_max_bps`` is caller-supplied (no hardcoded final threshold). This module imports NO
trading/runtime surface (main_loop/scout/execution/position/monitor/S1/hl_candles).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite

from data.public_spot_fetchers import (
    fetch_coinbase_spot, fetch_kraken_spot, fetch_hyperliquid_perp,
)

_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_to_ms(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except (ValueError, TypeError):
        return None


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


async def _insert_reference_tick(conn, tick: dict) -> str:
    tick_id = _new_id("ref")
    await conn.execute(
        """INSERT INTO reference_price_ticks
           (tick_id, source_name, source_type, asset, pair, quote, source_event_ts_raw,
            source_event_ts_parse_status, collector_received_at, ingest_skew_ms, fetch_started_at,
            fetch_completed_at, source_age_ms, price_raw, price_decimal_text, raw_payload_json,
            reject_reason, schema_version, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tick_id, tick["source_name"], tick["source_type"], tick["asset"], tick["pair"], tick["quote"],
         tick["source_event_ts_raw"], tick["source_event_ts_parse_status"], _now_iso(), None,
         tick["fetch_started_at"], tick["fetch_completed_at"], tick["source_age_ms"], tick["price_raw"],
         tick["price_decimal_text"], tick["raw_payload_json"], tick["reject_reason"],
         _SCHEMA_VERSION, _now_iso()))
    return tick_id


def _classify_spread(cb_ok: bool, kr_ok: bool, spread_bps: Decimal | None,
                     max_bps: Decimal) -> tuple[str, str]:
    """Return (spread_guard_status, proxy_confidence)."""
    if cb_ok and kr_ok:
        if spread_bps is not None and spread_bps <= max_bps:
            return "ok", "high"
        return "fail", "unusable"
    if cb_ok or kr_ok:
        return "single_source", "low"
    return "missing", "unusable"


async def collect_tier0(asset: str, *, coinbase_client, kraken_client, hyperliquid_client,
                        db_path: str, spread_guard_max_bps, max_source_age_ms: int | None = None) -> dict:
    """Fetch the three sources concurrently and persist Tier-0 evidence. Returns a summary dict."""
    cb, kr, hl = await asyncio.gather(
        fetch_coinbase_spot(asset, client=coinbase_client),
        fetch_kraken_spot(asset, client=kraken_client),
        fetch_hyperliquid_perp(asset, client=hyperliquid_client),
    )
    max_bps = Decimal(str(spread_guard_max_bps))

    async with aiosqlite.connect(str(db_path)) as conn:
        cb_id = await _insert_reference_tick(conn, cb)
        kr_id = await _insert_reference_tick(conn, kr)
        hl_id = await _insert_reference_tick(conn, hl)

        cb_price = Decimal(cb["price_decimal_text"]) if cb["price_decimal_text"] else None
        kr_price = Decimal(kr["price_decimal_text"]) if kr["price_decimal_text"] else None
        cb_ok, kr_ok = cb_price is not None, kr_price is not None

        # --- spot basket (Coinbase+Kraken ONLY; perp never enters this median) ---
        spot_ref: Decimal | None = None
        spread_bps: Decimal | None = None
        if cb_ok and kr_ok:
            spot_ref = (cb_price + kr_price) / Decimal(2)
            if spot_ref != 0:
                spread_bps = abs(cb_price - kr_price) / spot_ref * Decimal(10000)
        elif cb_ok:
            spot_ref = cb_price
        elif kr_ok:
            spot_ref = kr_price
        spread_status, confidence = _classify_spread(cb_ok, kr_ok, spread_bps, max_bps)
        if spread_status == "fail":
            spot_ref = None  # failed guard is never silently blessed as a usable reference

        used = [s for s, ok in (("coinbase", cb_ok), ("kraken", kr_ok)) if ok]
        excluded = [t["source_name"] for t, ok in ((cb, cb_ok), (kr, kr_ok)) if not ok]

        basket_id = _new_id("basket")
        span_ms = None
        starts = [_iso_to_ms(cb["fetch_started_at"]), _iso_to_ms(kr["fetch_started_at"])]
        ends = [_iso_to_ms(cb["fetch_completed_at"]), _iso_to_ms(kr["fetch_completed_at"])]
        if all(v is not None for v in starts + ends):
            span_ms = max(ends) - min(starts)
        skew_ms = (abs(ends[0] - ends[1]) if all(v is not None for v in ends) else None)

        await conn.execute(
            """INSERT INTO proxy_reference_basket_ticks
               (basket_id, asset, anchor_ts, coinbase_tick_id, kraken_tick_id,
                coinbase_fetch_started_at, coinbase_fetch_completed_at, kraken_fetch_started_at,
                kraken_fetch_completed_at, basket_capture_span_ms, completion_skew_ms,
                coinbase_source_age_ms, kraken_source_age_ms, spot_reference_decimal_text,
                spread_bps_decimal_text, spread_guard_status, used_spot_sources_json,
                excluded_sources_json, max_source_age_ms, proxy_confidence, not_official_chainlink,
                schema_version, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (basket_id, asset, _now_iso(), cb_id, kr_id,
             cb["fetch_started_at"], cb["fetch_completed_at"], kr["fetch_started_at"],
             kr["fetch_completed_at"], span_ms, skew_ms, cb["source_age_ms"], kr["source_age_ms"],
             (str(spot_ref) if spot_ref is not None else None),
             (str(spread_bps) if spread_bps is not None else None), spread_status,
             json.dumps(used), json.dumps(excluded), max_source_age_ms, confidence, 1,
             _SCHEMA_VERSION, _now_iso()))

        # --- perp basis (separate; never merged into spot) ---
        basis_id = None
        hl_price = Decimal(hl["price_decimal_text"]) if hl["price_decimal_text"] else None
        if hl_price is not None:
            basis_id = _new_id("basis")
            if spot_ref is not None and spot_ref != 0:
                basis_bps = (hl_price - spot_ref) / spot_ref * Decimal(10000)
                direction = ("perp_premium" if basis_bps > 0
                             else "perp_discount" if basis_bps < 0 else "flat")
                quality = "ok"
            else:
                basis_bps, direction, quality = None, None, "no_spot_reference"
            await conn.execute(
                """INSERT INTO perp_basis_ticks
                   (basis_id, asset, proxy_basket_id, hyperliquid_tick_id,
                    hyperliquid_fetch_started_at, hyperliquid_fetch_completed_at,
                    hyperliquid_source_age_ms, perp_price_decimal_text, spot_reference_decimal_text,
                    basis_bps_decimal_text, basis_direction, basis_quality_status, schema_version,
                    created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (basis_id, asset, basket_id, hl_id, hl["fetch_started_at"], hl["fetch_completed_at"],
                 hl["source_age_ms"], str(hl_price),
                 (str(spot_ref) if spot_ref is not None else None),
                 (str(basis_bps) if basis_bps is not None else None), direction, quality,
                 _SCHEMA_VERSION, _now_iso()))

        await conn.commit()

    return {
        "asset": asset,
        "reference_tick_ids": {"coinbase": cb_id, "kraken": kr_id, "hyperliquid": hl_id},
        "basket_id": basket_id,
        "spread_guard_status": spread_status,
        "proxy_confidence": confidence,
        "spot_reference_decimal_text": (str(spot_ref) if spot_ref is not None else None),
        "basis_id": basis_id,
        "rejects": {t["source_name"]: t["reject_reason"] for t in (cb, kr, hl) if t["reject_reason"]},
    }
