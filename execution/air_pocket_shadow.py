"""execution/air_pocket_shadow.py — Air-Pocket Exit Guard Shadow (Faz A).

SAF SHADOW — canlı exit davranışını ASLA değiştirmez/geciktirmez.

Akış:
  Stop tetiklendi → sell_position() (gerçek FAK, mevcut davranış)
                  → pm_exit (gerçek fill) belli
                  → schedule(...) çağrılır: SENKRON, create_task fırlatır, anında döner
                  → background _worker: sleep(400ms) → get_book → karar + post-wait
                    karşılaştırma → async DB write

Kurallar:
  - schedule() içinde await/get_book/DB YOK → canlı exit geciktirilmez
  - actual_trigger_fill_gap GERÇEK veriden (sl_trigger_px vs gerçek fill)
  - would_have_improved_fill GERÇEK post-wait book'tan (uydurma değil)
  - tüm I/O timeout'lu; tüm exception'lar yakalanır; fail-open
  - bounded: _active >= MAX_CONCURRENT → yeni task yaratılmaz (fail-open + log)
"""
import asyncio
import time
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

from data.clob_price import get_book

DB_FILE = Path("logs/mispricing.db")

# ── Guard eşikleri (13-trade örneğinden; shadow ile doğrulanacak) ────────────
WAIT_MS          = 400      # delayed-shadow ile simetrik stabilization bekleme
GAP_THRESHOLD    = 0.12     # trigger-fill gap > %12 → air-pocket (#1339 gap=%28)
DEPTH_MIN        = 1.5      # position_size'ın bu katı derinlik sağlıklı sayılır
CATASTROPHE_MAE  = -0.45    # mae bunun altı → token çöküyor, beklemeden çık
EXPIRY_HARD_SECS = 45       # kalan süre bunun altı → vade riski > fill riski

# ── I/O timeout'ları ─────────────────────────────────────────────────────────
GET_BOOK_TIMEOUT = 2.0
DB_TIMEOUT       = 3.0

# ── Bounded concurrency (fail-open) ──────────────────────────────────────────
MAX_CONCURRENT = 8
_active = 0


def _decide(gap, mae, secs):
    """Air-pocket exit guard karar ağacı (saf, yan etkisiz).

    Returns: (decision, override_reason, decision_reason)
      decision: "EXIT_NOW" | "WAIT_STABILIZE"
    Öncelik: expiry > catastrophe > air_pocket_gap > healthy_book
    """
    if secs is not None and secs < EXPIRY_HARD_SECS:
        return "EXIT_NOW", "expiry", None
    if mae is not None and mae < CATASTROPHE_MAE:
        return "EXIT_NOW", "catastrophe", None
    if gap is not None and gap > GAP_THRESHOLD:
        return "WAIT_STABILIZE", None, "air_pocket_gap"
    return "EXIT_NOW", None, "healthy_book"


def schedule(pos: dict, current_exit_price: float, exit_token: str,
             db_path=None) -> float:
    """SENKRON + non-blocking. Background shadow task fırlatır, anında döner.

    Canlı exit path'i ASLA bloklamaz: içinde await/get_book/DB YOK.
    Returns: live_exit_delay_ms (bu fonksiyonun süresi — kanıt için ölçülür).
    """
    global _active
    t0 = time.perf_counter()
    try:
        if _active >= MAX_CONCURRENT:
            print(f"[air_pocket_shadow] queue dolu ({_active}) — fail-open skip seq={pos.get('seq_no')}")
            return round((time.perf_counter() - t0) * 1000, 3)

        snap = dict(
            seq_no=pos.get("seq_no"),
            position_id=pos.get("position_id"),
            slug=pos.get("slug"),
            asset=pos.get("asset"),
            action=pos.get("action"),
            sl_trigger_px=pos.get("sl_trigger_px"),
            mae_pct=pos.get("mae_pct"),
            seconds_remaining=pos.get("_cached_seconds_remaining"),
            shares=pos.get("shares"),
        )
        live_delay = round((time.perf_counter() - t0) * 1000, 3)
        _active += 1
        asyncio.create_task(
            _worker(snap, current_exit_price, exit_token, db_path, live_delay)
        )
        return live_delay
    except Exception as e:
        # fail-open: shadow schedule patlasa bile canlı exit etkilenmez
        print(f"[air_pocket_shadow] schedule fail-open: {e}")
        return round((time.perf_counter() - t0) * 1000, 3)


async def _worker(snap: dict, current_exit_price: float, exit_token: str,
                  db_path=None, live_delay_ms: float = 0.0) -> None:
    """Background: stabilization bekle → karar + post-wait book → DB.

    Ana döngüyü ASLA bekletmez (create_task ile bağımsız). Tüm hatalar yakalanır.
    """
    global _active
    t0 = time.perf_counter()
    rec = {
        "seq_no":                   snap.get("seq_no"),
        "position_id":              snap.get("position_id"),
        "slug":                     snap.get("slug"),
        "asset":                    snap.get("asset"),
        "action":                   snap.get("action"),
        "current_exit_price":       current_exit_price,
        "current_exit_result":      "filled",
        "guarded_exit_decision":    None,
        "decision_reason":          None,
        "override_reason":          None,
        "depth_ratio":              None,
        "pred_gap":                 None,
        "actual_trigger_fill_gap":  None,
        "post_wait_bid":            None,
        "post_wait_depth":          None,
        "post_wait_error":          None,
        "would_have_improved_fill": None,
        "false_positive_guard":     None,
        "shadow_compute_ms":        None,
        "live_exit_delay_ms":       live_delay_ms,
        "error":                    None,
        "created_at":               datetime.now(timezone.utc).isoformat(),
    }
    try:
        await asyncio.sleep(WAIT_MS / 1000)

        # ── GERÇEK trigger-fill gap (current fill biliniyor) ─────────────────
        trig = snap.get("sl_trigger_px")
        gap = None
        if trig and current_exit_price and trig > 0:
            gap = round((trig - current_exit_price) / trig, 4)
        rec["actual_trigger_fill_gap"] = gap

        # ── Karar ağacı ──────────────────────────────────────────────────────
        decision, override, reason = _decide(
            gap, snap.get("mae_pct"), snap.get("seconds_remaining")
        )
        rec["guarded_exit_decision"] = decision
        rec["override_reason"]       = override
        rec["decision_reason"]       = reason

        # ── Post-wait book snapshot (GERÇEK veri, timeout'lu) ────────────────
        try:
            book = await asyncio.wait_for(get_book(exit_token), timeout=GET_BOOK_TIMEOUT)
            bids = (book or {}).get("bids", []) if book else []
            if bids:
                post_bid = float(bids[0].get("price", 0) or 0)
                rec["post_wait_bid"] = post_bid if post_bid > 0 else None

                # depth-walk: position kadar fill için derinlik
                shares = snap.get("shares") or 0.0
                remaining, filled = shares, 0.0
                for b in bids:
                    sz = float(b.get("size", 0) or 0)
                    take = min(remaining, sz)
                    filled += take
                    remaining -= take
                    if remaining <= 0:
                        break
                rec["post_wait_depth"] = round(filled, 4)
                rec["depth_ratio"] = round(filled / shares, 3) if shares > 0 else None
                rec["pred_gap"] = (round((trig - post_bid) / trig, 4)
                                   if trig and post_bid and trig > 0 else None)

                # would_have_improved_fill: post-wait bid gerçekten daha mı iyi?
                if post_bid > 0 and current_exit_price:
                    improved = post_bid > current_exit_price
                    rec["would_have_improved_fill"] = 1 if improved else 0
                    # false_positive_guard: guard WAIT dedi ama beklemek iyileştirmedi
                    if decision == "WAIT_STABILIZE":
                        rec["false_positive_guard"] = 0 if improved else 1
            else:
                rec["post_wait_error"] = "empty_book"
        except Exception as be:
            rec["post_wait_error"] = str(be)[:200]

        rec["shadow_compute_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        await _write(rec, db_path)

    except Exception as e:
        rec["error"] = str(e)[:200]
        rec["shadow_compute_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        try:
            await _write(rec, db_path)
        except Exception as we:
            print(f"[air_pocket_shadow] worker+write fail: {we}")
        print(f"[air_pocket_shadow] worker exception (fail-open): {e}")
    finally:
        _active -= 1


async def _write(rec: dict, db_path=None) -> None:
    """air_pocket_shadow tablosuna async INSERT (timeout'lu)."""
    path = db_path or DB_FILE

    async def _do():
        async with aiosqlite.connect(str(path)) as conn:
            await conn.execute(
                """INSERT INTO air_pocket_shadow (
                       seq_no, position_id, slug, asset, action,
                       current_exit_price, current_exit_result,
                       guarded_exit_decision, decision_reason, override_reason,
                       depth_ratio, pred_gap, actual_trigger_fill_gap,
                       post_wait_bid, post_wait_depth, post_wait_error,
                       would_have_improved_fill, false_positive_guard,
                       shadow_compute_ms, live_exit_delay_ms, error, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec.get("seq_no"), rec.get("position_id"), rec.get("slug"),
                    rec.get("asset"), rec.get("action"),
                    rec.get("current_exit_price"), rec.get("current_exit_result"),
                    rec.get("guarded_exit_decision"), rec.get("decision_reason"),
                    rec.get("override_reason"),
                    rec.get("depth_ratio"), rec.get("pred_gap"),
                    rec.get("actual_trigger_fill_gap"),
                    rec.get("post_wait_bid"), rec.get("post_wait_depth"),
                    rec.get("post_wait_error"),
                    rec.get("would_have_improved_fill"), rec.get("false_positive_guard"),
                    rec.get("shadow_compute_ms"), rec.get("live_exit_delay_ms"),
                    rec.get("error"), rec.get("created_at"),
                ),
            )
            await conn.commit()

    await asyncio.wait_for(_do(), timeout=DB_TIMEOUT)
