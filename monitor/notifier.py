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


def _seq(pos: dict) -> str:
    n = pos.get("seq_no")
    return f"#{n} " if n is not None else ""


def notify_open(pos: dict) -> None:
    entry_hl = pos.get("entry_hl_price")
    hl_line  = f"\nHL: ${entry_hl:,.0f}" if entry_hl else ""
    send_telegram(
        f"AÇILDI {_seq(pos)}{pos['asset']} {pos['action']}\n"
        f"Edge: {pos.get('edge', 0):.0%} | Pozisyon: ${pos.get('position_usd', 0):.2f}"
        f"{hl_line}"
    )


def notify_close(pos: dict) -> None:
    msg = (
        f"KAPANDI {_seq(pos)}{pos['asset']} {pos['action']}\n"
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
    entry_hl = pos.get("entry_hl_price")
    exit_hl  = pos.get("exit_hl_price")
    if entry_hl and exit_hl:
        msg += f"\nHL: ${entry_hl:,.0f} → ${exit_hl:,.0f}"
    elif entry_hl:
        msg += f"\nHL: ${entry_hl:,.0f}"
    send_telegram(msg)


def notify_resolved_late(pos: dict) -> None:
    """Heal edilmiş pozisyon için gecikmiş Telegram bildirimi."""
    msg = (
        f"GÜNCELLENDİ {_seq(pos)}{pos['asset']} {pos['action']}\n"
        f"market_resolved_late"
    )
    entry   = pos.get("pm_entry_price")
    exit_p  = pos.get("pm_exit_price")
    pos_usd = pos.get("position_usd", 0)
    if entry and exit_p is not None:
        pnl   = (exit_p - entry) / entry * pos_usd
        cikis = pos_usd + pnl
        pct   = pnl / pos_usd * 100 if pos_usd else 0
        sign  = "+" if pnl >= 0 else ""
        icon  = "✅" if pnl >= 0 else "❌"
        msg += (
            f"\nGiriş: ${pos_usd:.2f} → Çıkış: ${cikis:.2f}"
            f"\nP&L: {sign}${pnl:.2f} ({sign}{pct:.1f}%) {icon}"
        )
    entry_hl = pos.get("entry_hl_price")
    exit_hl  = pos.get("exit_hl_price")
    if entry_hl and exit_hl:
        msg += f"\nHL: ${entry_hl:,.0f} → ${exit_hl:,.0f}"
    elif entry_hl:
        msg += f"\nHL: ${entry_hl:,.0f}"
    send_telegram(msg)


def notify_halt(reason: str) -> None:
    send_telegram(f"HALT — Sistem durdu. Sebep: {reason}")


def notify_restart(dry_run: bool, bankroll: float) -> None:
    mod = "DRY_RUN" if dry_run else "LIVE"
    send_telegram(f"Bot baslatildi — {mod} | Bankroll: ${bankroll:.2f}")


def notify_soft_stop(streak: int, current_bankroll: float) -> None:
    send_telegram(
        f"SOFT STOP: {streak} arka arkaya kayip\n"
        f"Bankroll: ${current_bankroll:.2f}\n"
        f"/baslat ile devam"
    )


def notify_hard_stop(current_bankroll: float, starting_bankroll: float) -> None:
    pct = current_bankroll / starting_bankroll * 100
    send_telegram(
        f"HARD STOP: Bakiye %{pct:.0f} seviyesinde (${current_bankroll:.2f})\n"
        f"Bust korumasi devreye girdi!\n"
        f"/hardbaslat ile devam"
    )
