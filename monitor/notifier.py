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
    send_telegram(
        f"KAPANDI {pos['asset']} {pos['action']}\n"
        f"Sebep: {pos.get('exit_reason', '?')}"
    )


def notify_halt(reason: str) -> None:
    send_telegram(f"HALT — Sistem durdu. Sebep: {reason}")
