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
