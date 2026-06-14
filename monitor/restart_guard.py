"""monitor/restart_guard.py — D#8 restart preflight / tmux self-kill footgun guard.

restart.sh `tmux kill-session -t mispricing` yapıyor; ama operatör/Claude oturumu DA "mispricing"
session'ında olabilir → restart o oturumu öldürür (footgun). Bu modül saf karar verir: hedef tmux
session İÇİNDE BULUNULAN session ile aynıysa restart REDDEDİLİR.

Saf fonksiyon (I/O yok): session adları enjekte edilir. Gerçek `$TMUX`/`tmux display-message`
tespiti ince I/O sarmalayıcının sorumluluğu (ayrı adım) — burada deterministik karar.
"""


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
