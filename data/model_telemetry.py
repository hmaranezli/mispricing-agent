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
_collision_count = 0  # tracking_key UNIQUE collision sayacı (sessiz veri kaybı ÖLÇÜLÜR)


def get_collision_count():
    return _collision_count


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


TAKER_FEE = 0.02
ENTRY_SLIPPAGE = 0.01


def make_tracking_key_v2(slug, signal_timestamp_ms, action, event_uid):
    """EVENT-LEVEL UNIQUE tracking_key = slug|signal_ts_ms|action|event_uid.
    action AYRIŞTIRICI (aynı slug+ms+farklı action → farklı key). event_uid (uuid) %100 unique.
    slug|asset|tf|action ve slug|signal_ts_ms (action'sız) YASAK."""
    return f"{slug}|{signal_timestamp_ms}|{action}|{event_uid}"


def resolve_join_method(event_paper_id, paper_paper_id, event_tk, paper_tk):
    """Calibration join standardı. Öncelik: paper_id > tracking_key > slug_action_fallback.
    slug_action_fallback → PROVISIONAL/LOW_CONFIDENCE (final hükümde kullanılmaz)."""
    if event_paper_id and paper_paper_id and event_paper_id == paper_paper_id:
        return "paper_id"
    if event_tk and paper_tk and event_tk == paper_tk:
        return "tracking_key"
    return "slug_action_fallback"


def is_final_join(join_method):
    """FINAL rapor: paper_id veya tracking_key. slug_action_fallback DIŞLANIR."""
    return join_method in ("paper_id", "tracking_key")


def compute_legacy_telemetry_v2(asset, action, slug, timeframe, p_now, p_ref,
                                tte_seconds, raw_vol, yes_bid, yes_ask, no_ask_observed,
                                fair_yes_val, net_ev, fair_gap, edge_bin, would_enter,
                                snapshot_id, fee_adjustment, decision_threshold,
                                window_open_ts=None, window_close_ts=None,
                                snapshot_age_ms=None, skip_reason=None, paper_id=None,
                                tracking_key=None, hl_drift_at_entry=None,
                                vol_source="realized_1m_60m", vol_window="60m"):
    """V2 telemetri: NO türetim + TTE izolasyonu + counterfactual_supported + tracking_key.

    Model davranışını DEĞİŞTİRMEZ — sadece input/output loglar.
    """
    # base (V1) hesap — clamp/sigma_t/z
    base = compute_legacy_telemetry(
        asset=asset, action=action, p_now=p_now, p_ref=p_ref, secs=tte_seconds,
        best_bid=yes_bid, best_ask=yes_ask, raw_vol=raw_vol, fair_yes_val=fair_yes_val,
        net_ev=net_ev, fair_gap=fair_gap, edge_bin=edge_bin, would_enter=would_enter,
        snapshot_id=snapshot_id, slug=slug, timeframe=timeframe,
        snapshot_age_ms=snapshot_age_ms, fee_adjustment=fee_adjustment,
        decision_threshold=decision_threshold, skip_reason=skip_reason,
        vol_source=vol_source, vol_window=vol_window)

    # NO bid/ask türetimi
    if no_ask_observed is not None:
        no_ask, src = round(no_ask_observed, 4), "observed_no_ask"
    elif yes_bid is not None:
        no_ask, src = round(1 - yes_bid, 4), "derived_from_yes_book"
    else:
        no_ask, src = None, "unavailable"
    no_bid = round(1 - yes_ask, 4) if yes_ask is not None else None

    if action == "YES":
        action_bid, action_ask = yes_bid, yes_ask
    else:
        action_bid, action_ask = no_bid, no_ask
    action_spread = (action_ask - action_bid) if (action_ask is not None and action_bid is not None) else None
    # V3.1 Fix2: crossed (ask<bid karışık kaynak) tespiti + tutarlı spread (her iki taraf YES book).
    # net_ev/edge ETKİLENMEZ (finding'den gelir) — sadece telemetri kalite işareti.
    spread_crossed_flag = 1 if (action_spread is not None and action_spread < 0) else 0
    bid_ask_consistent_spread = (round(yes_ask - yes_bid, 4)
                                 if (yes_ask is not None and yes_bid is not None) else None)

    # TTE izolasyonu
    tte_years = (tte_seconds / _SECONDS_PER_YEAR) if (tte_seconds and tte_seconds > 0) else None

    # counterfactual_supported: action_ask + tte + threshold + raw_vol gerekli
    cf_reason = None
    if action_ask is None:
        cf_reason = "missing_action_ask"
    elif tte_years is None or tte_years <= 0:
        cf_reason = "missing_or_zero_tte"
    elif decision_threshold is None:
        cf_reason = "missing_threshold"
    elif raw_vol is None:
        cf_reason = "missing_raw_vol"
    cf_supported = cf_reason is None

    # EVENT-LEVEL UNIQUE tracking_key: dışarıdan (main_loop, slug|ts|action|uuid).
    # Yoksa event_id'ye düş (unique). slug|signal_ts_ms (action'sız) ASLA kullanılmaz.
    if tracking_key is None:
        tracking_key = base["event_id"]

    base.update({
        "telemetry_schema_version": 2,
        "yes_bid": yes_bid, "yes_ask": yes_ask, "no_bid": no_bid, "no_ask": no_ask,
        "bid_ask_source": src, "action_bid": action_bid, "action_ask": action_ask,
        "action_spread": round(action_spread, 4) if action_spread is not None else None,
        "time_to_expiry_seconds": tte_seconds,
        "time_to_expiry_ms": tte_seconds * 1000 if tte_seconds is not None else None,
        "pricing_tte_years": tte_years,
        "pricing_model_tte_input": tte_years,
        "window_open_ts": window_open_ts, "window_close_ts": window_close_ts,
        "counterfactual_supported": cf_supported,
        "counterfactual_missing_reason": cf_reason,
        "outcome_link_supported": True,
        "tracking_key": tracking_key,
        "paper_id": paper_id, "shadow_candidate_id": None,
        # V3.1 Data Integrity
        "spread_crossed_flag": spread_crossed_flag,
        "bid_ask_consistent_spread": bid_ask_consistent_spread,
        "hl_drift_at_entry": hl_drift_at_entry,
    })
    return base


def compute_counterfactual(ev):
    """OFFLINE counterfactual: clamped yerine raw_vol ile fair/net_ev. SADECE aynı event verisi.
    Math-safe (div0/NaN/Inf/TTE→0 → supported=False). Başka parametre değişmez."""
    out = {"counterfactual_supported": False, "counterfactual_missing_reason": None}
    try:
        raw = ev.get("raw_realized_vol")
        years = ev.get("pricing_tte_years")
        p_now = ev.get("p_now"); p_ref = ev.get("ref_price")
        action = ev.get("action"); action_ask = ev.get("action_ask")
        fee = ev.get("fee_adjustment"); thr = ev.get("decision_threshold")
        if raw is None: out["counterfactual_missing_reason"] = "missing_raw_vol"; return out
        if action_ask is None: out["counterfactual_missing_reason"] = "missing_action_ask"; return out
        if not years or years <= 0: out["counterfactual_missing_reason"] = "math_error_near_expiry_tte_zero"; return out
        if not p_now or not p_ref or p_now <= 0 or p_ref <= 0:
            out["counterfactual_missing_reason"] = "math_error_invalid_price"; return out
        fee = 0.02 if fee is None else fee
        thr = 0.05 if thr is None else thr

        sigma_t_raw = raw * math.sqrt(years)
        if sigma_t_raw < 1e-12:
            out["counterfactual_missing_reason"] = "math_error_sigma_zero"; return out
        z_raw = math.log(p_now / p_ref) / sigma_t_raw
        if not math.isfinite(z_raw):
            out["counterfactual_missing_reason"] = "math_error_z_nonfinite"; return out
        fair_yes_raw = 0.5 * (1 + math.erf(z_raw / math.sqrt(2)))
        action_fair_raw = fair_yes_raw if action == "YES" else (1 - fair_yes_raw)
        net_ev_raw = action_fair_raw * (1 - fee) - (action_ask + ENTRY_SLIPPAGE)
        would_enter_unclamped = net_ev_raw >= thr

        out.update({
            "counterfactual_supported": True,
            "raw_vol_counterfactual_fair_yes": round(fair_yes_raw, 6),
            "raw_vol_counterfactual_fair_no": round(1 - fair_yes_raw, 6),
            "raw_vol_counterfactual_action_fair": round(action_fair_raw, 6),
            "raw_vol_counterfactual_net_ev": round(net_ev_raw, 6),
            "would_enter_unclamped": bool(would_enter_unclamped),
            "lower_clamp_suppressed_entry": bool(
                would_enter_unclamped and not ev.get("would_enter", 0)),
            "sigma_t_raw": round(sigma_t_raw, 8), "z_raw": round(z_raw, 6),
        })
        return out
    except Exception as e:
        out["counterfactual_missing_reason"] = f"math_error_{type(e).__name__}"
        return out


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
        if rec.get("telemetry_schema_version") == 2:
            await _write_telemetry_v2(rec, db_path)
        else:
            await _write_telemetry(rec, db_path)
    except Exception as e:
        print(f"[model_telemetry] write error (devam): {e}")
    finally:
        _active = max(0, _active - 1)


async def _write_telemetry_v2(rec, db_path=None):
    """V2 INSERT (OR IGNORE KALDIRILDI) — tracking_key UNIQUE collision IntegrityError ile
    YAKALANIR + _collision_count++ + log. Sessiz veri kaybı YOK. timeout'lu."""
    global _collision_count
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO model_decision_events (
                       event_id, snapshot_id, timestamp, slug, asset, timeframe, action,
                       model_version, ref_price, p_now, best_bid, best_ask, spread,
                       snapshot_age_ms, raw_realized_vol, clamped_model_vol, vol_was_clamped,
                       vol_clamp_min, vol_clamp_max, vol_source, vol_window, sigma_t,
                       z_score, z_abs, z_overconfidence_flag, z_overconfidence_threshold,
                       vol_clamp_and_high_z, drift_term, momentum_term, fair_yes, fair_no,
                       action_fair, fee_adjustment, net_ev, fair_gap, edge_bin,
                       decision_threshold, would_enter, skip_reason, created_at,
                       telemetry_schema_version, yes_bid, yes_ask, no_bid, no_ask,
                       bid_ask_source, action_bid, action_ask, action_spread,
                       time_to_expiry_seconds, time_to_expiry_ms, pricing_tte_years,
                       pricing_model_tte_input, window_open_ts, window_close_ts,
                       counterfactual_supported, counterfactual_missing_reason,
                       outcome_link_supported, tracking_key, paper_id, shadow_candidate_id,
                       spread_crossed_flag, bid_ask_consistent_spread, hl_drift_at_entry
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["event_id"], rec.get("snapshot_id"), rec.get("timestamp"), rec.get("slug"),
                 rec.get("asset"), rec.get("timeframe"), rec.get("action"), rec.get("model_version"),
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
                 rec.get("would_enter"), rec.get("skip_reason"), rec.get("created_at"),
                 rec.get("telemetry_schema_version"), rec.get("yes_bid"), rec.get("yes_ask"),
                 rec.get("no_bid"), rec.get("no_ask"), rec.get("bid_ask_source"),
                 rec.get("action_bid"), rec.get("action_ask"), rec.get("action_spread"),
                 rec.get("time_to_expiry_seconds"), rec.get("time_to_expiry_ms"),
                 rec.get("pricing_tte_years"), rec.get("pricing_model_tte_input"),
                 rec.get("window_open_ts"), rec.get("window_close_ts"),
                 1 if rec.get("counterfactual_supported") else 0,
                 rec.get("counterfactual_missing_reason"),
                 1 if rec.get("outcome_link_supported") else 0, rec.get("tracking_key"),
                 rec.get("paper_id"), rec.get("shadow_candidate_id"),
                 rec.get("spread_crossed_flag"), rec.get("bid_ask_consistent_spread"),
                 rec.get("hl_drift_at_entry")),
            )
            await conn.commit()
    import sqlite3
    try:
        await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
    except sqlite3.IntegrityError as ie:
        _collision_count += 1
        print(f"[model_telemetry] COLLISION tracking_key={rec.get('tracking_key')} "
              f"event_id={rec.get('event_id')} count={_collision_count} ({ie})")


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
                (rec["event_id"], rec.get("snapshot_id"), rec.get("timestamp"), rec.get("slug"),
                 rec.get("asset"), rec.get("timeframe"), rec.get("action"), rec.get("model_version"),
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
