#!/bin/bash
# restart.sh — Botu temiz yeniden başlatır.
# Mevcut tüm main_loop.py process'lerini öldürür, sonra tmux'ta tek instance başlatır.

set -e

SESSION="mispricing"

echo "[restart] Mevcut process'ler kontrol ediliyor..."
PIDS=$(pgrep -f "python.*main_loop.py" || true)
if [ -n "$PIDS" ]; then
    echo "[restart] Öldürülüyor: $PIDS"
    kill $PIDS
    sleep 2
else
    echo "[restart] Çalışan process yok."
fi

echo "[restart] Tmux session kontrol ediliyor..."
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[restart] Eski session kapatılıyor: $SESSION"
    tmux kill-session -t "$SESSION"
fi

echo "[restart] Yeni session başlatılıyor..."
tmux new-session -d -s "$SESSION" \
    "source venv/bin/activate && PYTHONUNBUFFERED=1 python -u main_loop.py 2>&1 | tee -a logs/main_loop.log"

sleep 1
RUNNING=$(pgrep -f "python.*main_loop.py" | wc -l)
echo "[restart] Tamamlandı — $RUNNING process çalışıyor (tmux: $SESSION)"
