"""monitor/restart_guard.py — D#8 restart preflight / tmux self-kill footgun guard.

restart.sh `tmux kill-session -t mispricing` yapıyor; ama operatör/Claude oturumu DA "mispricing"
session'ında olabilir → restart o oturumu öldürür (footgun). Bu modül saf karar verir: hedef tmux
session İÇİNDE BULUNULAN session ile aynıysa restart REDDEDİLİR.

`check_restart_safe` saf karar (I/O yok, adlar enjekte). `detect_current_tmux_session` ince I/O
sarmalayıcı (`$TMUX` env + `tmux display-message`), enjekte edilebilir → testte gerçek tmux yok.
`main` CLI giriş: restart.sh `python -m monitor.restart_guard --target "$SESSION"` ile çağırır;
footgun'da non-zero exit → `set -e` kill-session'a ulaşmaz.
"""
import os
import sys
import argparse
import subprocess


class RestartFootgunError(RuntimeError):
    """Restart, içinde çalışılan tmux session'ını öldürecek → reddedildi (self-kill footgun)."""


def check_restart_safe(target_session: str, current_session) -> None:
    """Restart preflight: hedef session İÇİNDE BULUNULAN session ise `RestartFootgunError` raise et.

    - current_session truthy ve target_session == current_session → footgun → RAISE.
    - farklı session → güvenli (no-op).
    - current_session None/boş (tmux dışı / tespit edilemedi) → güvenli no-op: bilinmeyen/eşleşmeyen
      oturum hedefle çakışmaz, footgun kanıtlanamaz. (Tespit güvenilirliği AYRI I/O katmanının işi.)
    """
    if current_session and target_session == current_session:
        raise RestartFootgunError(
            f"Restart REDDEDİLDİ: hedef tmux session '{target_session}' içinde bulunulan session ile "
            f"aynı → restart bu oturumu öldürür. Botu farklı bir session'dan/dışarıdan yeniden başlat.")


def _tmux_session_runner() -> str:
    """Gerçek tmux çağrısı: `tmux display-message -p '#S'` (mevcut session adı). Sadece $TMUX set
    iken çağrılır. Hata → "" (tespit edilemedi = güvenli no-op tarafı; karar check_restart_safe'de)."""
    try:
        out = subprocess.run(["tmux", "display-message", "-p", "#S"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout
    except Exception:
        return ""


def detect_current_tmux_session(env=None, runner=None) -> str:
    """İçinde bulunulan tmux session adını döner; tmux dışındaysa "".

    `$TMUX` env YOKSA "" döner ve runner çağrılmaz (gereksiz subprocess yok). Set ise `runner`
    (default gerçek `tmux display-message`) çıktısını strip'leyip döner. env+runner enjekte
    edilebilir → unit testte gerçek tmux/subprocess YOK.
    """
    env = os.environ if env is None else env
    if not env.get("TMUX"):
        return ""
    runner = _tmux_session_runner if runner is None else runner
    return (runner() or "").strip()


def main(argv=None, detector=None, stderr=None) -> int:
    """Restart preflight CLI. `--target` hedef session; mevcut session `detector` (default
    detect_current_tmux_session) ile tespit edilir, `check_restart_safe` ile kıyaslanır.

    Footgun → stderr'a mesaj + return 1 (restart.sh `set -e` ile kill-session'a ulaşmaz). Güvenli → 0.
    detector+stderr enjekte edilebilir → testte gerçek tmux yok.
    """
    stderr = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(prog="restart_guard",
                                     description="Restart preflight: tmux self-kill footgun guard")
    parser.add_argument("--target", required=True, help="restart.sh'in öldüreceği hedef tmux session")
    args = parser.parse_args(argv)
    detector = detect_current_tmux_session if detector is None else detector
    current = detector()
    try:
        check_restart_safe(args.target, current)
    except RestartFootgunError as e:
        print(str(e), file=stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
