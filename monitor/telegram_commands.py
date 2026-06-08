"""monitor/telegram_commands.py — Telegram komut alici (polling).

Desteklenen komutlar (Turkce karakter yok):
  /durum         — acik pozisyonlar + gunluk P&L
  /istatistik    — tum zamanlar istatistik
  /istatistikN   — son N saat istatistik  (orn: /istatistik6)
  /durdur        — kill switch devreye al
  /baslat        — kill switch kaldir
"""
import asyncio
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from monitor.notifier  import send_telegram
from monitor.kill_switch import arm as ks_arm, disarm as ks_disarm
from monitor import positions_cache

TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
DB_PATH             = Path("logs/mispricing.db")
POLL_TIMEOUT        = 10   # saniye
POLL_INTERVAL       = 2    # saniye
EPOCH3_START_SEQ    = 1336  # kalibrasyon fix sonrası ilk temiz trade (2026-06-08 07:27 UTC)


# ── yardimci fonksiyonlar ──────────────────────────────────────────────────────

def is_authorized(chat_id: str) -> bool:
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def parse_hours(text: str) -> int | None:
    """'/istatistik6' → 6  |  '/istatistik' → None"""
    suffix = text.removeprefix("/istatistik")
    if suffix == "":
        return None
    return int(suffix) if suffix.isdigit() else None


def build_stats_message(total: int, wins: int, losses: int, pnl: float, hours: int | None, expired: int = 0, breakeven: int = 0) -> str:
    denominator = wins + losses
    win_rate    = wins / denominator * 100 if denominator else 0
    label       = f"son {hours} saat" if hours else "tum zamanlar"
    msg = (
        f"=== ISTATISTIK ({label}) ===\n"
        f"Trade     : {total}\n"
        f"Win/Loss  : {wins}/{losses}\n"
        f"Win rate  : {win_rate:.1f}%\n"
        f"Net P&L   : ${pnl:+.2f}"
    )
    if breakeven:
        msg += f"\nBerabere  : {breakeven}"
    if expired:
        msg += f"\nExpired   : {expired} (PnL bekleniyor)"
    return msg


def build_durum_message(open_positions: list[dict], daily_pnl: float, stale_secs: float | None = None) -> str:
    lines = [f"=== DURUM ===", f"Acik pozisyon: {len(open_positions)}/5"]
    for p in open_positions:
        seq   = f"#{p['seq_no']} " if p.get("seq_no") is not None else ""
        slug  = p.get("slug", "?")[:24]
        act   = p.get("action", "?")
        entry = p.get("pm_entry_price", 0)
        usd   = p.get("position_usd", 0)
        lines.append(f"  {seq}{act} {slug} entry={entry:.3f} ${usd:.2f}")
    lines.append(f"Gunluk P&L: ${daily_pnl:+.2f}")
    if stale_secs is not None and stale_secs > 30:
        lines.append(f"[Son scan: {int(stale_secs)}s once]")
    return "\n".join(lines)


# ── DB sorguları ───────────────────────────────────────────────────────────────

def _query_stats(hours: int | None) -> dict:
    if not DB_PATH.exists():
        return {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0}
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    where = ""
    params: tuple = ()
    if hours:
        since  = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        where  = "WHERE ts_close > ? AND status='closed' AND dry_run=0"
        params = (since,)
    else:
        where  = "WHERE status='closed' AND dry_run=0"
    c.execute(
        f"SELECT COUNT(*), SUM(realized_pnl), "
        f"COUNT(CASE WHEN realized_pnl>0 THEN 1 END), "
        f"COUNT(CASE WHEN realized_pnl<0 THEN 1 END), "
        f"COUNT(CASE WHEN pm_exit_price IS NULL THEN 1 END), "
        f"COUNT(CASE WHEN realized_pnl=0 AND pm_exit_price IS NOT NULL THEN 1 END) "
        f"FROM positions {where}", params
    )
    row = c.fetchone()
    conn.close()
    return {
        "total":     row[0] or 0,
        "pnl":       row[1] or 0.0,
        "wins":      row[2] or 0,
        "losses":    row[3] or 0,
        "expired":   row[4] or 0,
        "breakeven": row[5] or 0,
    }


def _query_stats_epoch3() -> dict:
    """Epoch 3 (seq_no >= EPOCH3_START_SEQ) istatistik — kalibrasyon sonrası temiz trade'ler."""
    if not DB_PATH.exists():
        return {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "expired": 0, "breakeven": 0}
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute(
        "SELECT COUNT(*), SUM(realized_pnl), "
        "COUNT(CASE WHEN realized_pnl>0 THEN 1 END), "
        "COUNT(CASE WHEN realized_pnl<0 THEN 1 END), "
        "COUNT(CASE WHEN pm_exit_price IS NULL THEN 1 END), "
        "COUNT(CASE WHEN realized_pnl=0 AND pm_exit_price IS NOT NULL THEN 1 END) "
        "FROM positions WHERE status='closed' AND dry_run=0 AND seq_no >= ?",
        (EPOCH3_START_SEQ,)
    )
    row = c.fetchone()
    conn.close()
    return {
        "total":     row[0] or 0,
        "pnl":       row[1] or 0.0,
        "wins":      row[2] or 0,
        "losses":    row[3] or 0,
        "expired":   row[4] or 0,
        "breakeven": row[5] or 0,
    }


def _query_open_positions() -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute(
        "SELECT slug, action, pm_entry_price, position_usd "
        "FROM positions WHERE status='open' AND dry_run=0 ORDER BY ts_open DESC LIMIT 5"
    )
    rows = c.fetchall()
    conn.close()
    return [
        {"slug": r[0], "action": r[1], "pm_entry_price": r[2], "position_usd": r[3]}
        for r in rows
    ]


def _query_daily_pnl() -> float:
    if not DB_PATH.exists():
        return 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn  = sqlite3.connect(DB_PATH)
    c     = conn.cursor()
    c.execute(
        "SELECT SUM(realized_pnl) FROM positions "
        "WHERE date(ts_close)=? AND status='closed' AND dry_run=0", (today,)
    )
    val = c.fetchone()[0]
    conn.close()
    return val or 0.0


# ── komut isleyici ─────────────────────────────────────────────────────────────

def handle_command(text: str) -> str:
    text = text.strip()

    if text in ("/help", "/yardim"):
        return (
            "Kullanilabilir komutlar:\n\n"
            "/durum         — Acik pozisyonlar + gunluk P&L\n"
            "/istatistik    — Tum zamanlar istatistik\n"
            "/istatistik6   — Son 6 saat\n"
            "/istatistik12  — Son 12 saat\n"
            "/istatistik24  — Son 24 saat\n"
            "/pause         — Yeni islem dur, monitor devam\n"
            "/devam         — Pause'u kaldir, normale don\n"
            "/flatten       — Acik pozisyonlari kapat, pause\n"
            "/hardkill      — Process oldur (son care!)\n"
            "/durdur        — /hardkill alias (eski kas hafizasi)\n"
            "/baslat        — Soft stop / kill switch kaldir\n"
            "/hardbaslat    — Hard stop (bust) kaldir\n"
            "/help          — Bu mesaj"
        )

    if text == "/durum":
        cached = positions_cache.get_open_positions()
        stale  = positions_cache.seconds_since_update()
        if cached or stale < float("inf"):
            open_pos = cached
        else:
            open_pos = _query_open_positions()
            stale = None
        daily_pnl = _query_daily_pnl()
        return build_durum_message(open_pos, daily_pnl, stale_secs=stale)

    if text == "/pause":
        from monitor.state import soft_pause
        soft_pause()
        return "PAUSE: Yeni islem acilmiyor. Acik pozisyonlar WS hizinda izlenmeye devam ediyor."

    if text == "/devam":
        from monitor.state import soft_resume
        from monitor import circuit_breaker
        soft_resume()
        circuit_breaker.reset_streak()
        ks_disarm()
        return "Devam: Bot normal moda geri dondu."

    if text == "/flatten":
        from monitor.state import request_flatten
        request_flatten()
        return "FLATTEN: Acik pozisyonlar bir sonraki iterasyonda FAK SELL ile kapatilacak. Bot PAUSE moduna giriyor."

    if text == "/hardkill":
        ks_arm()
        return "HARD KILL: Process durduruluyor. UYARI: Acik pozisyonlar kaderine birakiliyor, izlenmeyecek!"

    if text == "/durdur":
        ks_arm()
        return "HARD KILL (/durdur): Process durduruluyor. UYARI: Acik pozisyonlar kaderine birakiliyor, izlenmeyecek!"

    if text == "/baslat":
        from monitor.state import soft_resume
        from monitor import circuit_breaker
        soft_resume()
        circuit_breaker.reset_streak()
        ks_disarm()
        return "Soft stop KALDIRILDI. Streak sifirland. Bot devam ediyor."

    if text == "/hardbaslat":
        from monitor.state import hard_resume
        hard_resume()
        return "Hard stop KALDIRILDI. Bot devam ediyor."

    if text.startswith("/istatistik"):
        hours = parse_hours(text)
        s     = _query_stats(hours)
        msg   = build_stats_message(s["total"], s["wins"], s["losses"], s["pnl"], hours,
                                    s.get("expired", 0), s.get("breakeven", 0))
        if hours is None:
            e3 = _query_stats_epoch3()
            e3_wr = e3["wins"] / (e3["wins"] + e3["losses"]) * 100 if (e3["wins"] + e3["losses"]) else 0
            epoch3_block = (
                f"\n\n=== Epoch 3 (ana KPI) ===\n"
                f"Trade     : {e3['total']}\n"
                f"Win/Loss  : {e3['wins']}/{e3['losses']}\n"
                f"Win rate  : {e3_wr:.1f}%\n"
                f"Net P&L   : ${e3['pnl']:+.2f}"
            )
            msg = epoch3_block + "\n\n--- tum zamanlar ---\n" + msg
        return msg

    return f"Bilinmeyen komut: {text}\nKomutlar: /durum /istatistik /istatistik6 /durdur /baslat /hardbaslat"


# ── polling loop ───────────────────────────────────────────────────────────────

async def poll_commands() -> None:
    """Ana bot ile birlikte asyncio.create_task() ile calisir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    offset = 0
    base   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    loop = asyncio.get_event_loop()
    while True:
        try:
            resp = await loop.run_in_executor(
                None,
                lambda off=offset: requests.get(
                    f"{base}/getUpdates",
                    params={"offset": off, "timeout": POLL_TIMEOUT},
                    timeout=POLL_TIMEOUT + 5,
                ),
            )
            data = resp.json()
            if not data.get("ok"):
                await asyncio.sleep(POLL_INTERVAL)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg    = update.get("message", {})
                chat   = str(msg.get("chat", {}).get("id", ""))
                text   = msg.get("text", "").strip()

                if not is_authorized(chat) or not text.startswith("/"):
                    continue

                reply = handle_command(text)
                send_telegram(reply)

        except Exception:
            pass

        await asyncio.sleep(POLL_INTERVAL)
