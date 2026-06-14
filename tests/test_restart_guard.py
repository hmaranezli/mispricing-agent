"""tests/test_restart_guard.py — D#8 restart preflight / tmux footgun guard (TDD).

KÖK SORUN (D readiness sweep, 2026-06-14): `restart.sh` `tmux kill-session -t mispricing` yapıyor;
ama çalışan Claude/operatör oturumu DA "mispricing" tmux session'ında olabilir → restart.sh o oturumu
ÖLDÜRÜR (footgun). Guard: restart preflight, hedef session == ŞU ANKİ session ise REDDETMELİ
(fail-closed; "içinde bulunduğun session'ı öldürme").

En dar testable seam = SAF karar fonksiyonu `check_restart_safe(target_session, current_session)`:
gerçek tmux ÇAĞRILMAZ — session adları ENJEKTE edilir (unit test deterministik, I/O yok). Gerçek
`$TMUX`/`tmux display-message` tespiti ince I/O sarmalayıcıda AYRI ele alınır (sonraki adım).

İlk RED: `monitor/restart_guard.py` modülü/fonksiyonu henüz YOK → ImportError (feature missing;
projede ilk-RED stiliyle tutarlı). Network/tmux/restart YOK.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_check_restart_safe_refuses_when_target_is_current_session():
    """Footgun: hedef tmux session == içinde çalışılan session → preflight REDDETMELİ.

    `check_restart_safe(target, current)` `current` truthy ve `target == current` iken
    `RestartFootgunError` raise etmeli (restart.sh'in kendi oturumunu öldürmesini engeller).
    Gerçek tmux yok — adlar enjekte. İlk RED: modül yok → ImportError."""
    from monitor.restart_guard import check_restart_safe, RestartFootgunError

    with pytest.raises(RestartFootgunError):
        check_restart_safe(target_session="mispricing", current_session="mispricing")


def test_check_restart_safe_passes_when_different_session():
    """Hedef session ≠ içinde çalışılan session → güvenli, raise YOK (restart başka session'ı öldürür,
    bu oturumu değil). Saf karar; gerçek tmux yok."""
    from monitor.restart_guard import check_restart_safe

    # raise etmemeli → exception sızarsa test fail eder.
    check_restart_safe(target_session="mispricing", current_session="some-other-session")


def test_check_restart_safe_passes_when_current_session_unknown():
    """`current_session` None/boş (tmux dışı veya tespit edilemedi) → bu SAF karar fonksiyonu için
    GÜVENLİ no-op (raise YOK): adı bilinmeyen/eşleşmeyen bir oturum hedef session'la çakışmaz, footgun
    KANITLANAMAZ. Gerçek `$TMUX`/`tmux display-message` güvenilirliği AYRI I/O sarmalayıcının sorumluluğu
    (sonraki adım). None ve boş string'in ikisi de pass."""
    from monitor.restart_guard import check_restart_safe

    check_restart_safe(target_session="mispricing", current_session=None)
    check_restart_safe(target_session="mispricing", current_session="")


# ── D#8 preflight CLI: tespit (detect_current_tmux_session) + giriş (main) ──────
# Tespit + karar İKİSİ DE Python'da → gerçek tmux/subprocess çağrılmadan enjeksiyonla test edilir.

def test_detect_current_tmux_session_returns_empty_when_no_tmux_env():
    """`$TMUX` env YOK (tmux dışı / cron / ssh) → "" döner ve runner HİÇ çağrılmaz (gereksiz subprocess
    yok). Boş = footgun kanıtlanamaz → check_restart_safe güvenli no-op verir."""
    from monitor.restart_guard import detect_current_tmux_session

    calls = []
    def fake_runner():
        calls.append(1)
        return "should-not-be-called"

    result = detect_current_tmux_session(env={}, runner=fake_runner)
    assert result == "", f'TMUX yokken "" beklenir: {result!r}'
    assert calls == [], "TMUX yokken runner (tmux display-message) çağrılMAMALI"


def test_detect_current_tmux_session_uses_runner_and_strips_when_in_tmux():
    """`$TMUX` set → enjekte runner (gerçekte `tmux display-message -p '#S'`) çıktısını döner, strip'li
    (trailing newline temizlenir). Gerçek tmux çağrılmaz — runner fake."""
    from monitor.restart_guard import detect_current_tmux_session

    result = detect_current_tmux_session(
        env={"TMUX": "/tmp/tmux-0/default,123,0"}, runner=lambda: "mispricing\n")
    assert result == "mispricing", f"runner çıktısı strip'li dönmeli: {result!r}"


def test_main_returns_1_and_writes_footgun_to_stderr_when_target_is_current():
    """main(["--target","mispricing"], detector=lambda:"mispricing") → footgun → return 1 + stderr mesaj.
    Gerçek tmux yok (detector enjekte). restart.sh `set -e` ile non-zero'da kill-session'a ULAŞMAZ."""
    import io
    from monitor.restart_guard import main

    buf = io.StringIO()
    rc = main(["--target", "mispricing"], detector=lambda: "mispricing", stderr=buf)
    assert rc == 1, f"footgun → exit 1 beklenir: {rc}"
    msg = buf.getvalue().lower()
    assert "mispricing" in msg and ("footgun" in msg or "reddedildi" in msg or "session" in msg), \
        f"stderr footgun mesajı içermeli: {buf.getvalue()!r}"


def test_main_returns_0_when_target_differs_from_current():
    """main(["--target","bot"], detector=lambda:"claude") → farklı session → güvenli → return 0.
    Gerçek tmux yok (detector enjekte)."""
    import io
    from monitor.restart_guard import main

    buf = io.StringIO()
    rc = main(["--target", "bot"], detector=lambda: "claude", stderr=buf)
    assert rc == 0, f"farklı session → exit 0 beklenir: {rc}"
