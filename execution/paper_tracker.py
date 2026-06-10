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

from data.clob_price import get_book, sorted_asks, sorted_bids

TP_LEVELS = (15, 20, 30)   # MFE take-profit eşikleri (%) — peak-time depth-walk ölçümü

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
    """Ask tarafı depth-walk EN UCUZDAN: position_usd ile ağırlıklı ort fill.

    sorted_asks (ucuz→pahalı) kullanır — asks[0]'ı best sanmaz (book sorting bug fix).
    Returns (price, method, quality, levels). Boş kitap → (None,'none','low',0).
    """
    asks = sorted_asks(book)  # ucuzdan pahalıya
    if not asks:
        return None, "none", "low", 0
    remaining_usd = position_usd
    shares = 0.0
    levels = 0
    for px, sz in asks:
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


COLLAPSE_SECS = 180   # signal_seconds_remaining bunun altı → collapse riski, paper_late cohort
LATE_SNAPSHOT_MS = 90_000  # snapshot bu kadar eskiyse late_entry (T=0 sync bozuldu)


def _action_fair(action, yes_fair):
    """Aldığımız tarafın fair olasılığı. YES→yes_fair, NO→1-yes_fair."""
    if yes_fair is None:
        return None
    return yes_fair if action == "YES" else round(1 - yes_fair, 4)


def _slippage_baseline(finding):
    """Slippage baseline = ALDIĞIMIZ token'ın ask'ı. YES→best_ask, NO→no_ask.
    NO-fill'i YES-best_ask ile karşılaştırma artefaktını önler."""
    if finding.get("action") == "YES":
        return finding.get("best_ask")
    return finding.get("no_ask") or finding.get("best_ask")


SIZE_LADDER = (1.25, 10, 25, 50, 100)  # simüle exit notional ($) — tradable capacity ölçümü


def _depth_walk_sell(book, shares):
    """Aggressive taker SELL: bids'i pahalıdan ucuza ez, shares kadar.
    Returns (avg_sell_price, levels_used, filled_shares, unfilled_shares).
    Boş kitap → (None, 0, 0.0, shares)."""
    bids = sorted_bids(book)  # pahalı→ucuz (best satış önce)
    if not bids:
        return None, 0, 0.0, round(shares, 6)
    remaining, proceeds, levels = shares, 0.0, 0
    for px, sz in bids:
        take = min(remaining, sz)
        proceeds += take * px
        remaining -= take
        levels += 1
        if remaining <= 0:
            break
    filled = shares - remaining
    avg = round(proceeds / filled, 6) if filled > 0 else None
    return avg, levels, round(filled, 6), round(max(remaining, 0.0), 6)


def _tradable_capacity(book, ideal_tp_price):
    """avg fiyatı ideal_tp_price altına düşürmeden absorbe edilebilen max notional ($).
    bids price >= ideal_tp_price olan seviyelerin toplam (size*price)."""
    cap = 0.0
    for px, sz in sorted_bids(book):  # azalan
        if px >= ideal_tp_price:
            cap += px * sz
        else:
            break
    return round(cap, 2)


def _cadence_flag(observed_return_pct, tp_level, real_pnl, ideal_pnl):
    """Cadence overshoot: observed-target > 5pp VEYA real %20+ > ideal → True."""
    overshoot = observed_return_pct * 100 - tp_level
    if overshoot > 5:
        return True
    if real_pnl is not None and ideal_pnl and real_pnl > ideal_pnl * 1.2:
        return True
    return False


def _conservative_pnl(real_pnl, ideal_pnl, complete):
    """conservative = min(real, ideal); partial fill → None (fail)."""
    if not complete or real_pnl is None:
        return None
    return min(real_pnl, ideal_pnl)


async def _measure_tp_ladder(paper_id, exit_token, tp_level, slug, asset, action,
                             entry_price, observed_return, shares_unused=0,
                             pos_usd_unused=0, db_path=None):
    """TP eşiği geçildiğinde SIZE-LADDER ($1.25-$100) SELL depth-walk (fire-and-forget).

    TEK get_book → 5 size aynı book üzerinde simüle. Partial fill → P&L NULL (fail).
    conservative=min(real,ideal). cadence_artifact_flag. Sadece paper/shadow; live'a bağlanmaz.
    """
    from datetime import datetime, timezone
    try:
        book = await asyncio.wait_for(get_book(exit_token), timeout=GET_BOOK_TIMEOUT)
        if not book or entry_price <= 0:
            return
        timeframe = "5m" if "-5m-" in (slug or "") else "15m"
        ideal_tp_price = entry_price * (1 + tp_level / 100.0)
        capacity = _tradable_capacity(book, ideal_tp_price)
        overshoot_pp = round(observed_return * 100 - tp_level, 2)
        now_iso = datetime.now(timezone.utc).isoformat()

        for notional in SIZE_LADDER:
            shares = notional / entry_price
            avg, levels, filled, unfilled = _depth_walk_sell(book, shares)
            complete = (unfilled <= 1e-9 and avg is not None)
            ideal_pnl = round((tp_level / 100.0) * notional, 6)
            if complete:
                real_pnl = round((avg - entry_price) / entry_price * notional, 6)
                slip = round((ideal_tp_price - avg) / ideal_tp_price, 4) if ideal_tp_price > 0 else None
            else:
                real_pnl, slip = None, None  # partial → fail
            cad = 1 if _cadence_flag(observed_return, tp_level, real_pnl, ideal_pnl) else 0
            cons = _conservative_pnl(real_pnl, ideal_pnl, complete)
            await _write_tp_ladder({
                "paper_id": paper_id, "slug": slug, "asset": asset, "action": action,
                "timeframe": timeframe, "tp_level": tp_level, "entry_price": entry_price,
                "observed_return_pct": round(observed_return, 4), "overshoot_pct": overshoot_pp,
                "cadence_artifact_flag": cad,
                "simulated_exit_notional_usd": notional, "shares_to_sell": round(shares, 6),
                "avg_exit_price": avg, "exit_levels_used": levels,
                "exit_fill_complete": 1 if complete else 0, "exit_unfilled_shares": unfilled,
                "real_tradable_tp_pnl": real_pnl, "ideal_tp_pnl": ideal_pnl,
                "conservative_tp_pnl": cons, "exit_slippage_pct": slip,
                "tradable_capacity_usd": capacity, "tp_hit_ts": now_iso, "created_at": now_iso,
            }, db_path)
    except Exception as e:
        print(f"[paper_tp] {slug} tp{tp_level} ladder fail-open: {e}")


def _net_ev_after_slippage(action, fair, est_fill, fee=0.02):
    """Tahmini gerçek fill sonrası net EV (sabit slippage değil, depth-walk fill).

    YES: fair*(1-fee) - est_fill ; NO: (1-fair)*(1-fee) - est_fill
    Returns (net_ev, paper_viability).
    """
    if action == "YES":
        net_ev = fair * (1 - fee) - est_fill
    else:
        net_ev = (1 - fair) * (1 - fee) - est_fill
    net_ev = round(net_ev, 4)
    viability = "positive_after_slippage" if net_ev > 0 else "negative_after_slippage"
    return net_ev, viability


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


async def build_entry_snapshot(finding: dict, position_usd: float = 1.25) -> dict | None:
    """T=0 entry snapshot — sinyal görüldüğü anda fiyat/EV dondurur (temporal sync).

    get_book burada (T=0) çağrılır; paper_open_worker bunu kullanır, T+60s'de YENİDEN ÇEKMEZ.
    action-side fair + slippage baseline (NO artefaktı yok). Hata → None (fail-open).
    """
    try:
        action = finding.get("action", "YES")
        token = (finding.get("yes_token_id") if action == "YES"
                 else finding.get("no_token_id"))
        depth_price = depth_method = depth_quality = None
        try:
            book = await asyncio.wait_for(get_book(token), timeout=GET_BOOK_TIMEOUT)
            depth_price, depth_method, depth_quality, _ = _estimate_entry_price(book, position_usd)
        except Exception:
            pass
        if depth_price is None:
            ba = finding.get("best_ask")
            if not ba or ba <= 0:
                return None
            depth_price, depth_method, depth_quality = _ask_buffer_price(ba)

        yes_fair  = finding.get("fair_value")
        act_fair  = _action_fair(action, yes_fair)
        baseline  = _slippage_baseline(finding)
        slip      = round((depth_price - baseline) / baseline, 4) if baseline else None
        net_ev, viab = _net_ev_after_slippage(action, yes_fair, depth_price)

        return {
            "entry_price":             depth_price,
            "entry_method":            depth_method,
            "data_quality":            depth_quality,
            "signal_best_ask":         finding.get("best_ask"),
            "signal_best_bid":         finding.get("best_bid"),
            "signal_depth_walk_entry": depth_price if depth_method == "depth_walk" else None,
            "signal_fee_adj_edge":     finding.get("fee_adj_edge"),
            "signal_net_ev":           net_ev,
            "signal_slippage":         slip,
            "signal_seconds_remaining": finding.get("seconds_remaining"),
            "signal_timestamp_ms":     int(time.time() * 1000),
            "yes_fair":                yes_fair,
            "no_fair":                 round(1 - yes_fair, 4) if yes_fair is not None else None,
            "action_fair":             act_fair,
            "paper_viability":         viab,
        }
    except Exception as e:
        print(f"[paper] build_entry_snapshot fail-open: {e}")
        return None


# ── schedule: non-blocking giriş noktası ─────────────────────────────────────

def schedule_paper_open(finding, gate_result, risk_result, conn=None, db_path=None,
                        snapshot=None, paper_id=None, tracking_key=None):
    """SENKRON + non-blocking. Paper-open worker fırlatır, anında döner.

    snapshot: build_entry_snapshot(T=0) çıktısı — worker get_book çağırmaz (temporal sync).
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
            _paper_open_worker(finding, gate_result, risk_result, db_path, delay,
                               snapshot, paper_id, tracking_key)
        )
        return delay
    except Exception as e:
        print(f"[paper] schedule fail-open: {e}")
        return round((time.perf_counter() - t0) * 1000, 3)


async def _paper_open_worker(finding, gate_result, risk_result, db_path=None,
                             live_delay_ms=0.0, snapshot=None, paper_id_override=None,
                             tracking_key_override=None):
    """Background: depth-walk entry estimate + shadow_positions insert.

    Live loop'u bekletmez. Hata → fail-open (memory map temizlenir, log)."""
    key = _dedupe_key(finding)
    try:
        position_usd = float((risk_result or {}).get("position_usd", 1.25) or 1.25)
        token_id = (finding.get("yes_token_id") if finding.get("action") == "YES"
                    else finding.get("no_token_id"))

        action = finding.get("action", "YES")
        fair = finding.get("fair_value") or 0.0
        depth_levels = 0
        now_ms = int(time.time() * 1000)

        # ── TEMPORAL SYNC: snapshot varsa T=0 entry, get_book ÇAĞIRMA ─────────
        if snapshot is not None:
            entry_price  = snapshot["entry_price"]
            entry_method = snapshot.get("entry_method")
            data_quality = snapshot.get("data_quality")
            depth_price  = snapshot.get("signal_depth_walk_entry")
            est_slip     = snapshot.get("signal_slippage")
            net_ev       = snapshot.get("signal_net_ev")
            viability    = snapshot.get("paper_viability")
            yes_fair     = snapshot.get("yes_fair")
            no_fair      = snapshot.get("no_fair")
            action_fair  = snapshot.get("action_fair")
            sig_secs     = snapshot.get("signal_seconds_remaining")
            sig_ts       = snapshot.get("signal_timestamp_ms")
            entry_source = "scout_snapshot"
            snapshot_age_ms = round(now_ms - sig_ts, 1) if sig_ts else None
        else:
            depth_price = depth_method = depth_quality = None
            try:
                book = await asyncio.wait_for(get_book(token_id), timeout=GET_BOOK_TIMEOUT)
                depth_price, depth_method, depth_quality, depth_levels = \
                    _estimate_entry_price(book, position_usd)
            except Exception as be:
                print(f"[paper] {finding.get('slug')} book hatası, fallback: {be}")
            if depth_price is not None:
                entry_price, entry_method, data_quality = depth_price, depth_method, depth_quality
                entry_source = "immediate_depth_walk"
            else:
                ba = finding.get("best_ask")
                if not ba or ba <= 0:
                    print(f"[paper] {finding.get('slug')} fiyat yok — paper açılamadı")
                    _active.pop(key, None)
                    return
                entry_price, entry_method, data_quality = _ask_buffer_price(ba)
                entry_source = "fallback_late_book"
            baseline = _slippage_baseline(finding)
            est_slip = round((entry_price - baseline) / baseline, 4) if baseline else None
            net_ev, viability = _net_ev_after_slippage(action, fair, entry_price)
            yes_fair    = fair
            no_fair     = round(1 - fair, 4) if fair else None
            action_fair = _action_fair(action, fair)
            sig_secs    = finding.get("seconds_remaining")
            snapshot_age_ms = None

        shares = round(position_usd / entry_price, 6) if entry_price > 0 else 0.0
        paper_id = paper_id_override or str(uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        secs_at_open = finding.get("seconds_remaining")
        # EVENT-LEVEL UNIQUE tracking_key: main_loop'tan (snapshot_id-bazlı, signal_ts_ms).
        # Yoksa snapshot signal_timestamp_ms'den türet. slug|asset|tf|action ASLA kullanılmaz.
        _sig_ms = snapshot.get("signal_timestamp_ms") if snapshot else None
        _tracking_key = tracking_key_override or (
            f"{finding.get('slug')}|{_sig_ms}" if _sig_ms else None)

        # ── Cohort tasnifi ────────────────────────────────────────────────────
        # 5m AYRI deney evreni (paper_5m) — 15m clean cohort'una ASLA karışmaz.
        collapse_flag = 1 if (sig_secs is not None and sig_secs < COLLAPSE_SECS) else 0
        late_flag = 1 if (snapshot_age_ms is not None and snapshot_age_ms > LATE_SNAPSHOT_MS) else 0
        is_5m = "-5m-" in (finding.get("slug", "") or "")
        if is_5m:
            cohort, dq = "paper_5m", (data_quality or "estimated")  # 5m komple ayrı
        elif collapse_flag or late_flag:
            cohort, dq = "paper_late", "late_collapse_entry"
        else:
            cohort, dq = "paper", (data_quality or "estimated")

        rec = {
            "paper_id":              paper_id,
            "source_event_id":      f"{finding.get('slug')}|{now_iso}",
            "ts_open":              now_iso,
            "slug":                 finding.get("slug"),
            "asset":                finding.get("asset"),
            "action":               action,
            "entry_price_estimated": entry_price,
            "entry_method":         entry_method,
            "position_usd_paper":   position_usd,
            "shares_paper":         shares,
            "fair_value":           fair,
            "edge":                 finding.get("edge"),
            "fee_adj_edge":         finding.get("fee_adj_edge"),
            "edge_bucket":          finding.get("edge_bucket"),
            "depth_walk_estimated_fill":       depth_price,
            "estimated_slippage_pct":          est_slip,
            "net_ev_after_estimated_slippage": net_ev,
            "paper_viability":      viability,
            "yes_fair":             yes_fair,
            "no_fair":              no_fair,
            "action_fair":          action_fair,
            "entry_source":         entry_source,
            "snapshot_age_ms":      snapshot_age_ms,
            "seconds_remaining_at_signal": sig_secs,
            "seconds_remaining_at_open":   secs_at_open,
            "late_entry_flag":      late_flag,
            "collapse_timing_flag": collapse_flag,
            "signal_timestamp_ms":  (snapshot.get("signal_timestamp_ms") if snapshot else None),
            "cohort":               cohort,
            "tracking_key":         _tracking_key,
            "ref_price":            finding.get("ref_price"),
            "entry_hl_price":       finding.get("cur_price"),
            "confidence_score":     (gate_result or {}).get("confidence_score"),
            "data_quality":         dq,
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
            "_tp_hits":          set(),  # ölçülen TP eşikleri (first-hit idempotency)
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
    elapsed = time.monotonic() - state.get("_opened_monotonic", time.monotonic())
    # V3.1 Fix4: peak/trough damgalanırken zamanını da kaydet (time_to_mfe/mae)
    _stamp_mfe_mae_time(state, dd, elapsed)

    ref = state.get("ref_price")
    hl_drift = (hl_price - ref) / ref if (ref and hl_price) else 0.0
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

    # ── TP first-hit depth-walk ölçümü (peak-time tradable MFE) ──────────────
    # dd bir TP eşiğini İLK kez geçtiyse → fire-and-forget gerçek SELL depth-walk.
    # İdempotent: state["_tp_hits"] + DB UNIQUE(paper_id,tp_level). Live'a bağlanmaz.
    tp_hits = state.setdefault("_tp_hits", set())
    exit_tok = (state.get("yes_token_id") if state["action"] == "YES"
                else state.get("no_token_id"))
    for tp in TP_LEVELS:
        if dd >= tp / 100.0 and tp not in tp_hits:
            tp_hits.add(tp)
            asyncio.create_task(_measure_tp_ladder(
                state["paper_id"], exit_tok, tp, state["slug"], state["asset"],
                state["action"], entry, dd, 0, 0, state.get("db_path"),
            ))

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
        # V3.1 Fix4: resolve_ts sadece resolve/expiry'de (stop'ta NULL); time_to_* in-memory
        _resolve_ts = (datetime.now(timezone.utc).isoformat()
                       if reason in ("market_resolved", "expired", "resolved") else None)
        await _close_paper_position(
            state["paper_id"], reason, exit_price, resolve_exit,
            round(state.get("_mae_trough", 0.0), 4),
            round(state.get("_mfe_peak", 0.0), 4),
            round(state.get("_mfe_peak", 0.0), 4),
            db_path,
            time_to_mfe_s=state.get("_t_mfe"),
            time_to_mae_s=state.get("_t_mae"),
            resolve_ts=_resolve_ts,
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


def _stamp_mfe_mae_time(state, dd, elapsed):
    """V3.1 Fix4 — peak/trough YENİ rekor yapınca o anın elapsed'ini damgala.
    Sadece in-memory state (bu process). Karar mantığına dokunmaz."""
    if dd > state.get("_mfe_peak", 0.0):
        state["_mfe_peak"] = dd
        state["_t_mfe"] = elapsed
    elif "_mfe_peak" not in state:
        state["_mfe_peak"] = max(0.0, dd)
    if dd < state.get("_mae_trough", 0.0):
        state["_mae_trough"] = dd
        state["_t_mae"] = elapsed
    elif "_mae_trough" not in state:
        state["_mae_trough"] = min(0.0, dd)


async def recover_orphan_open_paper(db_path=None):
    """V3.1 Fix4.1 — Restart Recovery. Bot startup'ta DB'de status='open' kalan paper'lar
    önceki process'ten ORPHAN. in-memory _opened_monotonic kaybolduğu için MFE/MAE zaman
    sayaçları GÜVENİLMEZ → invalid işaretle (sahte timestamp üretme). Hata→log+devam."""
    path = db_path or DB_FILE
    try:
        async with aiosqlite.connect(str(path)) as conn:
            cur = await conn.execute(
                """UPDATE shadow_positions
                      SET time_to_mfe_s=NULL, time_to_mae_s=NULL,
                          mfe_mae_time_valid=0, mfe_mae_time_invalid_reason='process_restart'
                    WHERE status='open'""")
            await conn.commit()
            n = cur.rowcount
        if n:
            print(f"[paper] restart recovery: {n} orphan open paper → mfe_mae_time_valid=0 (process_restart)")
        return n
    except Exception as e:
        print(f"[paper] recover_orphan_open_paper fail-open: {e}")
        return 0


async def _insert_paper_position(rec, db_path=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO shadow_positions (
                       paper_id, source_event_id, ts_open, slug, asset, action,
                       entry_price_estimated, entry_method, position_usd_paper, shares_paper,
                       fair_value, edge, ref_price, entry_hl_price, confidence_score,
                       status, cohort, confidence_level, data_quality, is_paper,
                       edge_bucket, fee_adj_edge, depth_walk_estimated_fill,
                       estimated_slippage_pct, net_ev_after_estimated_slippage,
                       paper_viability, yes_fair, no_fair, action_fair, entry_source,
                       snapshot_age_ms, seconds_remaining_at_signal, seconds_remaining_at_open,
                       late_entry_flag, collapse_timing_flag, signal_timestamp_ms,
                       tracking_key, mfe_mae_time_valid, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open',?,'low',?,1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                (rec["paper_id"], rec["source_event_id"], rec["ts_open"], rec["slug"],
                 rec["asset"], rec["action"], rec["entry_price_estimated"], rec["entry_method"],
                 rec["position_usd_paper"], rec["shares_paper"], rec["fair_value"], rec["edge"],
                 rec["ref_price"], rec["entry_hl_price"], rec["confidence_score"],
                 rec.get("cohort", "paper"), rec["data_quality"],
                 rec.get("edge_bucket"), rec.get("fee_adj_edge"),
                 rec.get("depth_walk_estimated_fill"), rec.get("estimated_slippage_pct"),
                 rec.get("net_ev_after_estimated_slippage"), rec.get("paper_viability"),
                 rec.get("yes_fair"), rec.get("no_fair"), rec.get("action_fair"),
                 rec.get("entry_source"), rec.get("snapshot_age_ms"),
                 rec.get("seconds_remaining_at_signal"), rec.get("seconds_remaining_at_open"),
                 rec.get("late_entry_flag"), rec.get("collapse_timing_flag"),
                 rec.get("signal_timestamp_ms"), rec.get("tracking_key"), rec["created_at"]),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)


async def _write_tp_measurement(rec, db_path=None):
    """TP exit ölçümünü yazar (INSERT OR IGNORE — UNIQUE(paper_id,tp_level) idempotent)."""
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO tp_exit_measurements (
                       paper_id, slug, asset, action, tp_level, entry_price, shares,
                       real_tradable_tp_pnl, sell_avg_price, exit_slippage_pct,
                       exit_levels_used, exit_book_age_ms, tp_hit_ts,
                       exit_depth_walk_source, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["paper_id"], rec.get("slug"), rec.get("asset"), rec.get("action"),
                 rec["tp_level"], rec.get("entry_price"), rec.get("shares"),
                 rec.get("real_tradable_tp_pnl"), rec.get("sell_avg_price"),
                 rec.get("exit_slippage_pct"), rec.get("exit_levels_used"),
                 rec.get("exit_book_age_ms"), rec.get("tp_hit_ts"),
                 rec.get("exit_depth_walk_source"), rec.get("created_at")),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)


async def _write_tp_ladder(rec, db_path=None):
    """TP size-ladder ölçümü (INSERT OR IGNORE — UNIQUE(paper_id,tp_level,notional) idempotent)."""
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT OR IGNORE INTO tp_size_ladder (
                       paper_id, slug, asset, action, timeframe, tp_level, entry_price,
                       observed_return_pct, overshoot_pct, cadence_artifact_flag,
                       simulated_exit_notional_usd, shares_to_sell, avg_exit_price,
                       exit_levels_used, exit_fill_complete, exit_unfilled_shares,
                       real_tradable_tp_pnl, ideal_tp_pnl, conservative_tp_pnl,
                       exit_slippage_pct, tradable_capacity_usd, tp_hit_ts, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["paper_id"], rec.get("slug"), rec.get("asset"), rec.get("action"),
                 rec.get("timeframe"), rec["tp_level"], rec.get("entry_price"),
                 rec.get("observed_return_pct"), rec.get("overshoot_pct"),
                 rec.get("cadence_artifact_flag"), rec["simulated_exit_notional_usd"],
                 rec.get("shares_to_sell"), rec.get("avg_exit_price"), rec.get("exit_levels_used"),
                 rec.get("exit_fill_complete"), rec.get("exit_unfilled_shares"),
                 rec.get("real_tradable_tp_pnl"), rec.get("ideal_tp_pnl"),
                 rec.get("conservative_tp_pnl"), rec.get("exit_slippage_pct"),
                 rec.get("tradable_capacity_usd"), rec.get("tp_hit_ts"), rec.get("created_at")),
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
                                mae_pct, mfe_pct, mfe_peak, db_path=None,
                                time_to_mfe_s=None, time_to_mae_s=None, resolve_ts=None):
    path = db_path or DB_FILE
    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """UPDATE shadow_positions SET
                       status='closed', ts_close=?, close_reason=?,
                       pm_exit_estimated=?, resolve_exit=?,
                       mae_pct=?, mfe_pct=?, mfe_peak=?,
                       time_to_mfe_s=?, time_to_mae_s=?, resolve_ts=?
                   WHERE paper_id=?""",
                (datetime.now(timezone.utc).isoformat(), close_reason, pm_exit,
                 resolve_exit, mae_pct, mfe_pct, mfe_peak,
                 time_to_mfe_s, time_to_mae_s, resolve_ts, paper_id),
            )
            await conn.commit()
    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
