"""execution/paper_tracker.py — Paper/Shadow Position Tracker + MFE Breakeven.

NEW_ENTRIES_ENABLED=False iken live entry açılmaz → gerçek stop event üretilemez.
Bu modül council_pass + entry_disabled adaylarından GERÇEK PARA KULLANMADAN
paper position üretir; PM price path, MFE/MAE, stop event ve 4-model P&L verisi
toplar. Tüm veri ayrı shadow tablolarında, cohort='paper', confidence='low'.

GARANTİLER:
  - Live execute/sell_position/stop/target/MIN_EDGE'e DOKUNMAZ.
  - schedule_paper_open() SENKRON + non-blocking (create_task, anında döner).
  - Bounded (MAX_PAPER_POSITIONS); queue dolu → fail-open drop+log.
  - Tüm I/O timeout'lu; tüm exception yakalanır (sessiz crash yok).
  - Entry price ASLA mid değil: depth-walk estimate → ask+taker_buffer fallback.
  - Lifecycle: expiry/resolve/TTL/stale → CLOSED, memory map temizlenir.
  - Dedupe: aynı (slug,asset,action) açıkken duplicate açılmaz.
"""
import asyncio
import time
import aiosqlite
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

from data.clob_price import get_book

DB_FILE = Path("logs/mispricing.db")

# ── Limitler / eşikler ───────────────────────────────────────────────────────
MAX_PAPER_POSITIONS = 50
TAKER_BUFFER        = 0.01
MFE_ARM             = 0.15
BREAKEVEN_BUFFER    = -0.03
CATASTROPHE_MAE     = -0.45
GAMMA_HOLD_SECS     = 90
MIN_HOLD_SECS       = 15
WIDE_FLOOR          = -0.35
STOP_MAX            = 0.25   # current model: manager.STOP_LOSS_MAX aynası
STOP_MIN            = 0.12   # manager.STOP_LOSS_MIN aynası
DRIFT_INVALIDATE    = 0.003  # scout.ENTRY_DRIFT_MAX — sinyal bozulma eşiği
MAX_TTL_SECS        = 1800   # paper pozisyon max yaşam (30dk)
STALE_LIMIT         = 5      # ardışık fiyat-yok cycle → kapat
GET_BOOK_TIMEOUT    = 2.0
DB_TIMEOUT          = 3.0

# ── In-memory aktif paper map: (slug,asset,action) → paper dict ──────────────
_active: dict = {}


# ── Entry price estimate (mid ASLA) ──────────────────────────────────────────

def _estimate_entry_price(book, position_usd):
    """Ask tarafı depth-walk: position_usd ile alınabilecek ağırlıklı ort fiyat.

    Returns (price, method, quality, levels). Boş kitap → (None,'none','low',0).
    """
    asks = (book or {}).get("asks", []) if book else []
    if not asks:
        return None, "none", "low", 0
    remaining_usd = position_usd
    shares = 0.0
    levels = 0
    for a in asks:
        try:
            px = float(a.get("price", 0) or 0)
            sz = float(a.get("size", 0) or 0)
        except (TypeError, ValueError):
            continue
        if px <= 0 or sz <= 0:
            continue
        cost = px * sz
        take_usd = min(remaining_usd, cost)
        shares += take_usd / px
        remaining_usd -= take_usd
        levels += 1
        if remaining_usd <= 0:
            break
    filled_usd = position_usd - remaining_usd
    if shares <= 0 or filled_usd <= 0:
        return None, "none", "low", 0
    est = round(filled_usd / shares, 4)
    quality = "high" if remaining_usd <= 1e-9 else "low"
    return est, "depth_walk", quality, levels


def _ask_buffer_price(best_ask):
    """Fallback: best_ask + taker_buffer (execute() worst_price ile simetrik)."""
    return round(best_ask + TAKER_BUFFER, 4), "ask_buffer", "low"


# ── Model karar fonksiyonları (saf) ──────────────────────────────────────────

def _wrong_direction(hl_drift, action):
    """HL trade yönüne karşı mı? NO→drift>0 yanlış, YES→drift<0 yanlış."""
    if action == "NO":
        return hl_drift > DRIFT_INVALIDATE
    return hl_drift < -DRIFT_INVALIDATE


def _model_current(dd, frac):
    """Mevcut canlı stop_curve aynası (manager.stop_curve)."""
    stop = STOP_MAX - frac * (STOP_MAX - STOP_MIN)
    return ("EXIT", "current_stop") if dd <= -stop else ("HOLD", "watch")


def _model_conservative(dd, hl_drift, action, elapsed):
    if elapsed < 30:
        return "HOLD", "early_grace"
    if _wrong_direction(hl_drift, action):
        return "EXIT", "signal_invalidated"
    return ("EXIT", "wide_floor") if dd <= WIDE_FLOOR else ("HOLD", "noise_tolerance")


def _model_balanced(dd, hl_drift, action, frac):
    if _wrong_direction(hl_drift, action):
        return "EXIT", "signal_invalidated"
    stop = -0.40 + frac * (0.40 - 0.20)  # uzakta -0.40, yakında -0.20
    return ("EXIT", "balanced_stop") if dd <= stop else ("HOLD", "watch")


def _mfe_breakeven_decide(dd, mfe_peak, mae, secs, elapsed, state):
    """MFE breakeven shadow model. state['_breakeven_armed'] kalıcı."""
    if mfe_peak >= MFE_ARM:
        state["_breakeven_armed"] = True

    if mae is not None and mae < CATASTROPHE_MAE:
        return "CATASTROPHE_EXIT", "catastrophe"
    if elapsed < MIN_HOLD_SECS:
        return "HOLD", "min_hold"
    if secs is not None and secs < GAMMA_HOLD_SECS:
        return "HOLD", "gamma_proximity"
    if state.get("_breakeven_armed"):
        if dd <= BREAKEVEN_BUFFER:
            return "EXIT", "mfe_breakeven_stop"
        return "HOLD", "breakeven_watch"
    if dd <= WIDE_FLOOR:
        return "EXIT", "wide_floor"
    return "HOLD", "noise_tolerance"


def _all_model_decisions(dd, hl_drift, mfe_peak, mae, secs, elapsed, frac, state):
    """4 modelin (action, reason) çıktısı."""
    action = state.get("action", "YES")
    return {
        "current":       _model_current(dd, frac),
        "conservative":  _model_conservative(dd, hl_drift, action, elapsed),
        "balanced":      _model_balanced(dd, hl_drift, action, frac),
        "mfe_breakeven": _mfe_breakeven_decide(dd, mfe_peak, mae, secs, elapsed, state),
    }


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def _should_close(pos, now_monotonic):
    """Paper pozisyon kapanmalı mı? Returns reason | None."""
    if pos.get("_last_secs") is not None and pos["_last_secs"] <= 0:
        return "expired"
    if now_monotonic - pos.get("_opened_monotonic", now_monotonic) > MAX_TTL_SECS:
        return "ttl_exceeded"
    if pos.get("_stale_count", 0) >= STALE_LIMIT:
        return "stale_price"
    return None


def _dedupe_key(finding):
    return (finding.get("slug"), finding.get("asset"), finding.get("action"))


# ── schedule: non-blocking giriş noktası ─────────────────────────────────────

def schedule_paper_open(finding, gate_result, risk_result, conn=None, db_path=None):
    """SENKRON + non-blocking. Paper-open worker fırlatır, anında döner.

    Live loop'u ASLA bloklamaz (içinde await/get_book/DB yok).
    Returns: live_loop_delay_ms (kanıt için ölçülür).
    """
    t0 = time.perf_counter()
    try:
        key = _dedupe_key(finding)
        if key in _active:
            print(f"[paper] dedupe — {key} zaten açık, yeni paper açılmadı")
            return round((time.perf_counter() - t0) * 1000, 3)
        if len(_active) >= MAX_PAPER_POSITIONS:
            print(f"[paper] queue dolu ({len(_active)}) — fail-open drop {finding.get('slug')}")
            return round((time.perf_counter() - t0) * 1000, 3)

        # rezerve et (race'i önle) — worker doldurur
        _active[key] = {"status": "reserving"}
        delay = round((time.perf_counter() - t0) * 1000, 3)
        asyncio.create_task(
            _paper_open_worker(finding, gate_result, risk_result, db_path, delay)
        )
        return delay
    except Exception as e:
        print(f"[paper] schedule fail-open: {e}")
        return round((time.perf_counter() - t0) * 1000, 3)


async def _paper_open_worker(finding, gate_result, risk_result, db_path=None,
                             live_delay_ms=0.0):
    """Background: depth-walk entry estimate + shadow_positions insert.

    Live loop'u bekletmez. Hata → fail-open (memory map temizlenir, log)."""
    key = _dedupe_key(finding)
    try:
        position_usd = float((risk_result or {}).get("position_usd", 1.25) or 1.25)
        token_id = (finding.get("yes_token_id") if finding.get("action") == "YES"
                    else finding.get("no_token_id"))

        # ── Entry estimate: depth-walk → ask+buffer fallback ─────────────────
        depth_price = depth_method = depth_quality = None
        depth_levels = 0
        try:
            book = await asyncio.wait_for(get_book(token_id), timeout=GET_BOOK_TIMEOUT)
            depth_price, depth_method, depth_quality, depth_levels = \
                _estimate_entry_price(book, position_usd)
        except Exception as be:
            print(f"[paper] {finding.get('slug')} book hatası, fallback: {be}")

        if depth_price is not None:
            entry_price, entry_method, data_quality = depth_price, depth_method, depth_quality
        else:
            best_ask = finding.get("best_ask")
            if not best_ask or best_ask <= 0:
                print(f"[paper] {finding.get('slug')} fiyat yok — paper açılamadı")
                _active.pop(key, None)
                return
            entry_price, entry_method, data_quality = _ask_buffer_price(best_ask)

        shares = round(position_usd / entry_price, 6) if entry_price > 0 else 0.0
        paper_id = str(uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        rec = {
            "paper_id":              paper_id,
            "source_event_id":      f"{finding.get('slug')}|{now_iso}",
            "ts_open":              now_iso,
            "slug":                 finding.get("slug"),
            "asset":                finding.get("asset"),
            "action":               finding.get("action"),
            "entry_price_estimated": entry_price,
            "entry_method":         entry_method,
            "position_usd_paper":   position_usd,
            "shares_paper":         shares,
            "fair_value":           finding.get("fair_value"),
            "edge":                 finding.get("edge"),
            "ref_price":            finding.get("ref_price"),
            "entry_hl_price":       finding.get("cur_price"),
            "confidence_score":     (gate_result or {}).get("confidence_score"),
            "data_quality":         data_quality,
            "created_at":           now_iso,
        }
        await _insert_paper_position(rec, db_path)

        # paper_entry_events: entry estimate denetimi
        await _insert_entry_event({
            "paper_id":         paper_id,
            "ts":               now_iso,
            "slug":             finding.get("slug"),
            "asset":            finding.get("asset"),
            "action":           finding.get("action"),
            "best_ask":         finding.get("best_ask"),
            "depth_walk_price": depth_price,
            "ask_buffer_price": (round(finding.get("best_ask", 0) + TAKER_BUFFER, 4)
                                 if finding.get("best_ask") else None),
            "chosen_price":     entry_price,
            "chosen_method":    entry_method,
            "book_levels":      depth_levels,
            "created_at":       now_iso,
        }, db_path)

        # in-memory state (monitor için)
        _active[key] = {
            "paper_id":          paper_id,
            "slug":              finding.get("slug"),
            "asset":             finding.get("asset"),
            "action":            finding.get("action"),
            "yes_token_id":      finding.get("yes_token_id"),
            "no_token_id":       finding.get("no_token_id"),
            "entry_price":       entry_price,
            "shares":            shares,
            "position_usd":      position_usd,
            "ref_price":         finding.get("ref_price"),
            "status":            "open",
            "_opened_monotonic": time.monotonic(),
            "_mfe_peak":         0.0,
            "_mae_trough":       0.0,
            "_breakeven_armed":  False,
            "_stale_count":      0,
            "_last_secs":        finding.get("seconds_remaining"),
            "_model_exits":      {},  # model → (price, reason, ts)
            "db_path":           db_path,
        }
        print(f"[paper] AÇILDI {finding.get('slug')} {finding.get('action')} "
              f"entry={entry_price} ({entry_method}) shares={shares} delay={live_delay_ms}ms")
    except Exception as e:
        _active.pop(key, None)  # fail-open: rezervasyonu temizle
        print(f"[paper] open_worker fail-open: {e}")


# ── DB yardımcıları (async + timeout) ────────────────────────────────────────

PAPER_MONITOR_SECS = 15   # paper price-path cadence (live 7s loop'tan bağımsız)


async def update_paper_position(state, pm_price, hl_price, secs, db_path=None):
    """Bir paper pozisyonu güncelle: MFE/MAE + 4-model karar + stop event.

    pm_price: tuttuğumuz token'ın anlık bid'i (paper exit estimate).
    EXIT eden model ilk anında kilitlenir (_model_exits). Returns decisions dict.
    """
    t0 = time.perf_counter()
    entry = state.get("entry_price") or 0.0
    dd = (pm_price - entry) / entry if entry > 0 else 0.0
    state["_mfe_peak"]   = max(state.get("_mfe_peak", 0.0), dd)
    state["_mae_trough"] = min(state.get("_mae_trough", 0.0), dd)

    ref = state.get("ref_price")
    hl_drift = (hl_price - ref) / ref if (ref and hl_price) else 0.0
    elapsed = time.monotonic() - state.get("_opened_monotonic", time.monotonic())
    total = elapsed + max(secs or 1, 1)
    frac = elapsed / total

    decisions = _all_model_decisions(
        dd, hl_drift, state["_mfe_peak"], state["_mae_trough"],
        secs, elapsed, frac, state,
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    # Her model ilk EXIT'ini kilitle (would_exit_price = o anki bid)
    for model, (action, reason) in decisions.items():
        if action in ("EXIT", "CATASTROPHE_EXIT") and model not in state["_model_exits"]:
            state["_model_exits"][model] = (pm_price, reason, now_iso)

    state["_last_secs"] = secs
    compute_ms = round((time.perf_counter() - t0) * 1000, 2)

    try:
        await _record_stop_event({
            "paper_id":            state["paper_id"],
            "ts":                  now_iso,
            "slug":                state["slug"],
            "asset":               state["asset"],
            "action":              state["action"],
            "seconds_remaining":   secs,
            "pm_price":            pm_price,
            "drawdown_pct":        round(dd, 4),
            "hl_drift_pct":        round(hl_drift, 5),
            "mae_pct":             round(state["_mae_trough"], 4),
            "mfe_pct":             round(dd, 4),
            "mfe_peak":            round(state["_mfe_peak"], 4),
            "current_action":      decisions["current"][0],
            "conservative_action": decisions["conservative"][0],
            "balanced_action":     decisions["balanced"][0],
            "mfe_breakeven_action": decisions["mfe_breakeven"][0],
            "decision_reason":     decisions["mfe_breakeven"][1],
            "paper_compute_ms":    compute_ms,
            "created_at":          now_iso,
        }, db_path)
    except Exception as e:
        print(f"[paper] stop_event write fail-open: {e}")

    return decisions


async def _finalize_models(state, exit_price, exit_reason, db_path=None):
    """Paper kapanırken her model için would_pnl yaz.
    EXIT etmiş model → kilitli fiyat; etmemiş → kapanış (resolve/expiry) fiyatı.
    """
    entry = state.get("entry_price") or 0.0
    pos_usd = state.get("position_usd") or 0.0
    now_iso = datetime.now(timezone.utc).isoformat()
    for model in ("current", "conservative", "balanced", "mfe_breakeven"):
        locked = state["_model_exits"].get(model)
        if locked:
            px, reason, ts = locked
        else:
            px, reason, ts = exit_price, exit_reason, now_iso
        would_pnl = (px - entry) / entry * pos_usd if entry > 0 else None
        try:
            await _record_model_pnl({
                "paper_id":          state["paper_id"],
                "model":             model,
                "would_exit_price":  px,
                "would_exit_reason": reason,
                "would_exit_ts":     ts,
                "would_pnl":         round(would_pnl, 6) if would_pnl is not None else None,
                "resolve_exit":      exit_price,
                "created_at":        now_iso,
            }, db_path)
        except Exception as e:
            print(f"[paper] model_pnl write fail-open ({model}): {e}")


async def _paper_monitor_cycle(db_path=None):
    """Tüm açık paper pozisyonları bir kez güncelle + lifecycle close.

    Live monitor'dan TAMAMEN ayrı. Her pozisyon hatası izole (fail-open)."""
    from data.shortterm import fetch_by_slug, fetch_resolved, parse_market_window
    from data.hl_candles import current_price
    from data.clob_price import get_clob_price

    now_m = time.monotonic()
    for key, state in list(_active.items()):
        if state.get("status") != "open":
            continue
        try:
            token = (state.get("yes_token_id") if state["action"] == "YES"
                     else state.get("no_token_id"))
            # token state'te yok → finding'den gelmedi; slug'tan resolve kontrolü yine çalışır
            market = await fetch_by_slug(state["slug"])
            window = parse_market_window(market) if market else None

            if window is None:
                res = await fetch_resolved(state["slug"])
                if res:
                    rx = res["yes_exit"] if state["action"] == "YES" else res["no_exit"]
                    await _close_and_finalize(key, state, "market_resolved", rx, rx, db_path)
                else:
                    state["_stale_count"] = state.get("_stale_count", 0) + 1
                    reason = _should_close(state, now_m)
                    if reason:
                        await _close_and_finalize(key, state, reason, None, None, db_path)
                continue

            secs = window["seconds_remaining"]
            # NO artefaktından kaçın: tuttuğumuz token'ın GERÇEK bid'i (1-best_ask değil)
            bid = await get_clob_price(token, "SELL") if token else None
            if bid is None:
                # fallback: YES için window.best_bid, NO için 1-best_ask
                bid = (window.get("best_bid") if state["action"] == "YES"
                       else round(1 - window.get("best_ask", 1.0), 4))
            hl = await current_price(state["asset"])
            if bid is None or bid <= 0:
                state["_stale_count"] = state.get("_stale_count", 0) + 1
            else:
                state["_stale_count"] = 0
                await update_paper_position(state, bid, hl, secs, db_path)

            reason = _should_close(state, now_m)
            if reason:
                # expiry → resolve fiyatı dene
                rx = None
                if reason == "expired":
                    res = await fetch_resolved(state["slug"])
                    if res:
                        rx = res["yes_exit"] if state["action"] == "YES" else res["no_exit"]
                await _close_and_finalize(key, state, reason, rx if rx is not None else bid,
                                          rx, db_path)
        except Exception as e:
            print(f"[paper_monitor] {state.get('slug')} hata (fail-open): {e}")


async def _close_and_finalize(key, state, reason, exit_price, resolve_exit, db_path=None):
    """Paper kapat: DB güncelle + model_pnl yaz + memory map'ten çıkar (leak önleme)."""
    state["status"] = "closed"
    try:
        await _close_paper_position(
            state["paper_id"], reason, exit_price, resolve_exit,
            round(state.get("_mae_trough", 0.0), 4),
            round(state.get("_mfe_peak", 0.0), 4),
            round(state.get("_mfe_peak", 0.0), 4),
            db_path,
        )
        await _finalize_models(state, exit_price if exit_price is not None else 0.0,
                               reason, db_path)
    except Exception as e:
        print(f"[paper] close fail-open: {e}")
    finally:
        _active.pop(key, None)  # MEMORY LEAK ÖNLEME — her durumda çıkar
        print(f"[paper] KAPANDI {state.get('slug')} reason={reason} aktif={len(_active)}")


async def _paper_monitor_loop(db_path=None):
    """Background paper monitor — live loop'u ASLA yavaşlatmaz (ayrı task+cadence)."""
    await asyncio.sleep(30)  # startup offset
    while True:
        try:
            await _paper_monitor_cycle(db_path)
        except Exception as e:
            print(f"[paper_monitor_loop] cycle hatası (fail-open): {e}")
        await asyncio.sleep(PAPER_MONITOR_SECS)


async def _insert_paper_position(rec, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO shadow_positions (
                       paper_id, source_event_id, ts_open, slug, asset, action,
                       entry_price_estimated, entry_method, position_usd_paper, shares_paper,
                       fair_value, edge, ref_price, entry_hl_price, confidence_score,
                       status, cohort, confidence_level, data_quality, is_paper, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open','paper','low',?,1,?)""",
                (rec["paper_id"], rec["source_event_id"], rec["ts_open"], rec["slug"],
                 rec["asset"], rec["action"], rec["entry_price_estimated"], rec["entry_method"],
                 rec["position_usd_paper"], rec["shares_paper"], rec["fair_value"], rec["edge"],
                 rec["ref_price"], rec["entry_hl_price"], rec["confidence_score"],
                 rec["data_quality"], rec["created_at"]),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)


async def _insert_entry_event(rec, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO paper_entry_events (
                       paper_id, ts, slug, asset, action, best_ask,
                       depth_walk_price, ask_buffer_price, chosen_price,
                       chosen_method, book_levels, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["paper_id"], rec["ts"], rec["slug"], rec["asset"], rec["action"],
                 rec["best_ask"], rec["depth_walk_price"], rec["ask_buffer_price"],
                 rec["chosen_price"], rec["chosen_method"], rec["book_levels"], rec["created_at"]),
            )
            await conn.commit()
    try:
        await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
    except Exception as e:
        print(f"[paper] entry_event write fail (fail-open): {e}")


async def _record_stop_event(rec, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO shadow_stop_events (
                       paper_id, ts, slug, asset, action, seconds_remaining, pm_price,
                       drawdown_pct, hl_drift_pct, mae_pct, mfe_pct, mfe_peak,
                       current_action, conservative_action, balanced_action,
                       mfe_breakeven_action, decision_reason, paper_compute_ms, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["paper_id"], rec["ts"], rec["slug"], rec["asset"], rec["action"],
                 rec["seconds_remaining"], rec["pm_price"], rec["drawdown_pct"],
                 rec["hl_drift_pct"], rec["mae_pct"], rec["mfe_pct"], rec["mfe_peak"],
                 rec["current_action"], rec["conservative_action"], rec["balanced_action"],
                 rec["mfe_breakeven_action"], rec["decision_reason"], rec["paper_compute_ms"],
                 rec["created_at"]),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)


async def _record_model_pnl(rec, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO shadow_model_pnl (
                       paper_id, model, would_exit_price, would_exit_reason,
                       would_exit_ts, would_pnl, resolve_exit, cohort, created_at
                   ) VALUES (?,?,?,?,?,?,?,'paper',?)""",
                (rec["paper_id"], rec["model"], rec["would_exit_price"],
                 rec["would_exit_reason"], rec["would_exit_ts"], rec["would_pnl"],
                 rec["resolve_exit"], rec["created_at"]),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)


async def _close_paper_position(paper_id, close_reason, pm_exit, resolve_exit,
                                mae_pct, mfe_pct, mfe_peak, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """UPDATE shadow_positions SET
                       status='closed', ts_close=?, close_reason=?,
                       pm_exit_estimated=?, resolve_exit=?,
                       mae_pct=?, mfe_pct=?, mfe_peak=?
                   WHERE paper_id=?""",
                (datetime.now(timezone.utc).isoformat(), close_reason, pm_exit,
                 resolve_exit, mae_pct, mfe_pct, mfe_peak, paper_id),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
