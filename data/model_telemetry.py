"""data/model_telemetry.py — Legacy fair-value modeli karar telemetrisi.

Model davranışını DEĞİŞTİRMEZ — sadece iç değişkenleri (raw vs clamped vol,
sigma_t, z_score, overconfidence flag) loglar. VOL CLAMP hipotezini ölçer:
clamp_hit_rate + vol_clamp_and_high_z = overconfidence imzası.

Async/non-blocking: schedule_telemetry create_task fırlatır, anında döner.
Hata → log error + devam (bot loop ASLA crash etmez). Idempotent (UNIQUE event_id).
"""
import asyncio
import math
import time
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path("logs/mispricing.db")

LEGACY_VERSION    = "LEGACY_GBM_V1"
VOL_CLAMP_MIN     = 0.30
VOL_CLAMP_MAX     = 3.00
Z_OVERCONF_THRESHOLD = 1.0   # |z| >= bu → overconfident (fair ekstreme); veriyle ayarlanacak
_SECONDS_PER_YEAR = 31_557_600.0

DB_TIMEOUT     = 3.0
MAX_CONCURRENT = 16
_active = 0


_raw_vol_cache: dict = {}
RAW_VOL_TTL = 300.0  # raw realized vol 5dk cache (scout _get_all_vols ile simetrik)


async def get_raw_vol(asset):
    """Clamp ÖNCESİ realized vol (telemetri için), 5dk cache. Hata → None."""
    c = _raw_vol_cache.get(asset)
    now = time.time()
    if c and (now - c[1]) < RAW_VOL_TTL:
        return c[0]
    try:
        from data.hl_candles import fetch_candles, realized_vol_raw
        candles = await fetch_candles(asset, "1m", 60)
        raw = realized_vol_raw(candles)
        _raw_vol_cache[asset] = (raw, now)
        return raw
    except Exception:
        return None


def compute_legacy_telemetry(asset, action, p_now, p_ref, secs, best_bid, best_ask,
                             raw_vol, fair_yes_val, net_ev, fair_gap, edge_bin,
                             would_enter, snapshot_id, slug=None, timeframe=None,
                             snapshot_age_ms=None, fee_adjustment=None,
                             decision_threshold=None, skip_reason=None,
                             vol_source="realized_1m_60m", vol_window="60m"):
    """Legacy GBM iç değişkenlerini hesaplar (SAF — model kararını değiştirmez).

    raw_vol: clamp ÖNCESİ realized vol (None → fallback 0.80 raw kabul edilir).
    """
    raw = raw_vol if raw_vol is not None else 0.80
    clamped = max(VOL_CLAMP_MIN, min(raw, VOL_CLAMP_MAX))
    vol_was_clamped = abs(clamped - raw) > 1e-12

    sigma_t = z = z_abs = None
    if p_now and p_ref and p_now > 0 and p_ref > 0 and secs and secs > 0:
        years = secs / _SECONDS_PER_YEAR
        sigma_t = clamped * math.sqrt(years)
        if sigma_t > 1e-12:
            z = math.log(p_now / p_ref) / sigma_t
            z_abs = abs(z)

    z_overconf = (z_abs is not None and z_abs >= Z_OVERCONF_THRESHOLD)
    spread = (best_ask - best_bid) if (best_ask is not None and best_bid is not None) else None
    fair_no = (1.0 - fair_yes_val) if fair_yes_val is not None else None
    action_fair = fair_yes_val if action == "YES" else fair_no

    return {
        "event_id":             f"{snapshot_id}|{LEGACY_VERSION}",
        "snapshot_id":          snapshot_id,
        "timestamp":            datetime.now(timezone.utc).isoformat(),
        "slug":                 slug,
        "asset":                asset,
        "timeframe":            timeframe,
        "action":               action,
        "model_version":        LEGACY_VERSION,
        "ref_price":            p_ref,
        "p_now":                p_now,
        "best_bid":             best_bid,
        "best_ask":             best_ask,
        "spread":               spread,
        "snapshot_age_ms":      snapshot_age_ms,
        "raw_realized_vol":     round(raw, 6),
        "clamped_model_vol":    round(clamped, 6),
        "vol_was_clamped":      vol_was_clamped,
        "vol_clamp_min":        VOL_CLAMP_MIN,
        "vol_clamp_max":        VOL_CLAMP_MAX,
        "vol_source":           vol_source,
        "vol_window":           vol_window,
        "sigma_t":              round(sigma_t, 8) if sigma_t is not None else None,
        "z_score":              round(z, 6) if z is not None else None,
        "z_abs":                round(z_abs, 6) if z_abs is not None else None,
        "z_overconfidence_flag": z_overconf,
        "z_overconfidence_threshold": Z_OVERCONF_THRESHOLD,
        "vol_clamp_and_high_z": bool(vol_was_clamped and z_overconf),
        "drift_term":           0,
        "momentum_term":        0,
        "fair_yes":             fair_yes_val,
        "fair_no":              fair_no,
        "action_fair":          action_fair,
        "fee_adjustment":       fee_adjustment,
        "net_ev":               net_ev,
        "fair_gap":             fair_gap,
        "edge_bin":             edge_bin,
        "decision_threshold":   decision_threshold,
        "would_enter":          1 if would_enter else 0,
        "skip_reason":          skip_reason,
        "created_at":           datetime.now(timezone.utc).isoformat(),
    }


def schedule_telemetry(rec, db_path=None):
    """SENKRON + non-blocking. Telemetri yazımını background'a fırlatır, anında döner.
    Live/scout loop'u ASLA bloklamaz (içinde await/DB yok). Returns delay_ms."""
    global _active
    t0 = time.perf_counter()
    try:
        if _active >= MAX_CONCURRENT:
            print(f"[model_telemetry] queue dolu ({_active}) — drop {rec.get('event_id')}")
            return round((time.perf_counter() - t0) * 1000, 3)
        _active += 1
        asyncio.create_task(_telemetry_worker(rec, db_path))
    except Exception as e:
        print(f"[model_telemetry] schedule error (devam): {e}")
    return round((time.perf_counter() - t0) * 1000, 3)


async def _telemetry_worker(rec, db_path=None):
    """Background: telemetri DB yazımı. Hata → log error + devam (crash YOK)."""
    global _active
    try:
        await _write_telemetry(rec, db_path)
    except Exception as e:
        print(f"[model_telemetry] write error (devam): {e}")
    finally:
        _active = max(0, _active - 1)


async def _write_telemetry(rec, db_path=None):
    """model_decision_events INSERT OR IGNORE (UNIQUE event_id → idempotent), timeout'lu."""
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO model_decision_events (
                       event_id, snapshot_id, timestamp, slug, asset, timeframe, action,
                       model_version, ref_price, p_now, best_bid, best_ask, spread,
                       snapshot_age_ms, raw_realized_vol, clamped_model_vol, vol_was_clamped,
                       vol_clamp_min, vol_clamp_max, vol_source, vol_window, sigma_t,
                       z_score, z_abs, z_overconfidence_flag, z_overconfidence_threshold,
                       vol_clamp_and_high_z, drift_term, momentum_term, fair_yes, fair_no,
                       action_fair, fee_adjustment, net_ev, fair_gap, edge_bin,
                       decision_threshold, would_enter, skip_reason, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["event_id"], rec["snapshot_id"], rec["timestamp"], rec.get("slug"),
                 rec.get("asset"), rec.get("timeframe"), rec.get("action"), rec["model_version"],
                 rec.get("ref_price"), rec.get("p_now"), rec.get("best_bid"), rec.get("best_ask"),
                 rec.get("spread"), rec.get("snapshot_age_ms"), rec.get("raw_realized_vol"),
                 rec.get("clamped_model_vol"), 1 if rec.get("vol_was_clamped") else 0,
                 rec.get("vol_clamp_min"), rec.get("vol_clamp_max"), rec.get("vol_source"),
                 rec.get("vol_window"), rec.get("sigma_t"), rec.get("z_score"), rec.get("z_abs"),
                 1 if rec.get("z_overconfidence_flag") else 0, rec.get("z_overconfidence_threshold"),
                 1 if rec.get("vol_clamp_and_high_z") else 0, rec.get("drift_term"),
                 rec.get("momentum_term"), rec.get("fair_yes"), rec.get("fair_no"),
                 rec.get("action_fair"), rec.get("fee_adjustment"), rec.get("net_ev"),
                 rec.get("fair_gap"), rec.get("edge_bin"), rec.get("decision_threshold"),
                 rec.get("would_enter"), rec.get("skip_reason"), rec.get("created_at")),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
