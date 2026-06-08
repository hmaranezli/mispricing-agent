"""scripts/watch_20trades.py — Epoch 3 ≥ N trade olunca raporu Telegram'a gönderir.

Kullanım:
  python scripts/watch_20trades.py          # 20 tradede tetikle
  python scripts/watch_20trades.py 30       # 30 tradede tetikle
"""
import sys
import sqlite3
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.notifier import send_telegram

DB_PATH          = Path("logs/mispricing.db")
EPOCH3_START_SEQ = 1336
TARGET           = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
POLL_SECS        = 30


def epoch3_count() -> int:
    if not DB_PATH.exists():
        return 0
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM positions "
        "WHERE seq_no >= ? AND dry_run=0 AND status='closed'",
        (EPOCH3_START_SEQ,),
    )
    n = c.fetchone()[0]
    conn.close()
    return n


def send_chunked(text: str, chunk: int = 3800) -> None:
    """Telegram 4096 char limiti için böl gönder."""
    lines = text.splitlines(keepends=True)
    buf   = ""
    for line in lines:
        if len(buf) + len(line) > chunk:
            send_telegram(buf)
            buf = ""
        buf += line
    if buf.strip():
        send_telegram(buf)


print(f"[watch] Epoch 3'te {TARGET} trade bekleniyor (şu an: {epoch3_count()})")

while True:
    n = epoch3_count()
    if n >= TARGET:
        print(f"[watch] {n} trade ulaşıldı → rapor oluşturuluyor...")
        result = subprocess.run(
            [sys.executable, "scripts/report_20trades.py", str(TARGET)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        header = f"📊 Epoch 3 — {TARGET} Trade Raporu\n{'='*40}\n"
        body   = result.stdout or result.stderr or "(rapor boş)"
        send_chunked(header + body)
        print(f"[watch] Telegram'a gönderildi. Çıkılıyor.")
        break

    time.sleep(POLL_SECS)
