"""monitor/notifier.py — Telegram bildirim gönderici."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import config

_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(msg: str) -> None:
    """Token/chat_id yoksa sessizce atla; hata olsa da botu durdurmaz."""
    token   = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    prefix = "[DRY RUN] " if config.DRY_RUN else ""
    try:
        requests.post(
            _API.format(token=token),
            json={"chat_id": chat_id, "text": prefix + msg},
            timeout=5,
        )
    except Exception:
        pass


def notify_open(pos: dict) -> None:
    send_telegram(
        f"AÇILDI {pos['asset']} {pos['action']}\n"
        f"Edge: {pos.get('edge', 0):.0%} | Pozisyon: ${pos.get('position_usd', 0):.2f}"
    )


def notify_close(pos: dict) -> None:
    msg = (
        f"KAPANDI {pos['asset']} {pos['action']}\n"
        f"Sebep: {pos.get('exit_reason', '?')}"
    )
    entry   = pos.get("pm_entry_price")
    exit_p  = pos.get("pm_exit_price")
    pos_usd = pos.get("position_usd", 0)
    if entry and exit_p is not None:
        pnl    = (exit_p - entry) / entry * pos_usd
        cikis  = pos_usd + pnl
        pct    = pnl / pos_usd * 100 if pos_usd else 0
        sign   = "+" if pnl >= 0 else ""
        icon   = "✅" if pnl >= 0 else "❌"
        msg += (
            f"\nGiriş: ${pos_usd:.2f} → Çıkış: ${cikis:.2f}"
            f"\nP&L: {sign}${pnl:.2f} ({sign}{pct:.1f}%) {icon}"
        )
    send_telegram(msg)


def notify_halt(reason: str) -> None:
    send_telegram(f"HALT — Sistem durdu. Sebep: {reason}")
