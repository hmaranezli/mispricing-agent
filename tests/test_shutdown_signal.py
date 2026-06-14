"""tests/test_shutdown_signal.py — D#8 SIGTERM graceful shutdown flag (TDD).

KÖK SORUN (D readiness sweep): SIGTERM (restart.sh `kill $PIDS`) süreci anında sonlandırıyor →
main()'in `finally: await conn.close()`'ı ÇALIŞMIYOR, graceful değil. Çözüm `monitor/state.py`'nin
mevcut loop-kontrol flag pattern'ini (FLATTEN_REQUESTED/SOFT_PAUSED) aynalayan bir shutdown bayrağı:
sinyal handler flag set eder (raise değil), main() loop'u flag'i `kill_switch_check` yanında kontrol
edip break eder → mevcut finally temizliği çalışır.

Bu ilk RED yalnız SAF flag API'sini sürer (sinyal/loop entegrasyonu sonraki adım). Gerçek sinyal
GÖNDERİLMEZ; I/O yok.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_shutdown_flag_request_and_clear():
    """Saf flag API: başlangıçta False → request_shutdown() True → clear_shutdown() False.

    İlk RED: monitor.state içinde request_shutdown/is_shutdown_requested/clear_shutdown YOK →
    AttributeError (feature missing). Gerçek sinyal/restart yok."""
    from monitor import state

    state.clear_shutdown()
    assert state.is_shutdown_requested() is False      # başlangıç: shutdown istenmiş değil
    state.request_shutdown()
    assert state.is_shutdown_requested() is True        # request → flag set
    state.clear_shutdown()
    assert state.is_shutdown_requested() is False       # clear → tekrar temiz (test izolasyonu)


# ── SIGTERM handler installer (gerçek sinyal göndermeden test) ─────────────────

class _FakeLoop:
    """asyncio event loop yerine geçer: add_signal_handler çağrılarını handlers dict'ine kaydeder
    (gerçek sinyal kaydı YOK)."""
    def __init__(self):
        self.handlers = {}

    def add_signal_handler(self, sig, callback, *args):
        self.handlers[sig] = (callback, args)


def test_install_shutdown_signal_handlers_binds_sigterm_to_request_shutdown():
    """install_shutdown_signal_handlers(loop) SIGTERM'i loop'a bağlamalı; callback çağrılınca
    monitor.state.request_shutdown() flag'i set olmalı. Gerçek sinyal GÖNDERİLMEZ — fake loop +
    callback doğrudan çağrılır.

    İlk RED: monitor.shutdown / install_shutdown_signal_handlers YOK → ImportError (feature missing)."""
    import signal
    from monitor.shutdown import install_shutdown_signal_handlers
    from monitor import state

    state.clear_shutdown()
    fake_loop = _FakeLoop()
    install_shutdown_signal_handlers(loop=fake_loop)

    assert signal.SIGTERM in fake_loop.handlers, "SIGTERM loop'a bağlanmalı"
    callback, _args = fake_loop.handlers[signal.SIGTERM]
    assert state.is_shutdown_requested() is False       # henüz tetiklenmedi
    callback()                                          # SIGTERM geldi (simülasyon)
    assert state.is_shutdown_requested() is True, "SIGTERM callback → request_shutdown flag set"
    state.clear_shutdown()                              # test izolasyonu
