"""monitor/shutdown.py — D#8 SIGTERM/SIGINT graceful shutdown handler installer.

SIGTERM (restart.sh `kill $PIDS`) default'ta süreci anında öldürür → main()'in `finally:
conn.close()` temizliği çalışmaz. Bu modül asyncio loop'a SIGTERM/SIGINT handler bağlar: sinyal
gelince RAISE etmez, yalnız `monitor.state.request_shutdown()` flag'ini set eder. main() loop'u
flag'i kill_switch_check yanında kontrol edip break eder → mevcut finally temizliği çalışır (graceful).

Fail-soft: `add_signal_handler` desteklenmeyen platform/loop (örn. Windows ProactorEventLoop) →
NotImplementedError yutulur (handler kurulamasa da bot çalışmaya devam eder); callback exception
yutulur (sinyal yolunda çökme yok).
"""
import signal
import asyncio
import logging

from monitor import state

logger = logging.getLogger("monitor.shutdown")

# SIGTERM = restart.sh/systemd; SIGINT = Ctrl-C. İkisi de graceful shutdown'a yönlendirilir.
_SHUTDOWN_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def _on_shutdown_signal() -> None:
    """Sinyal callback'i: RAISE ETMEZ, yalnız flag set eder (fail-soft)."""
    try:
        state.request_shutdown()
        logger.critical("[shutdown] graceful shutdown sinyali alındı — loop temiz kapanacak.")
    except Exception as e:
        logger.critical("[shutdown] shutdown sinyal callback FAIL (yutuldu): %s", e)


def install_shutdown_signal_handlers(loop=None) -> None:
    """SIGTERM/SIGINT'i graceful shutdown flag'ine bağla. loop None → çalışan asyncio loop.

    Fail-soft: add_signal_handler desteklenmiyorsa (NotImplementedError) ilgili sinyal atlanır."""
    if loop is None:
        loop = asyncio.get_running_loop()
    for sig in _SHUTDOWN_SIGNALS:
        try:
            loop.add_signal_handler(sig, _on_shutdown_signal)
        except NotImplementedError:
            logger.warning("[shutdown] add_signal_handler(%s) bu platformda desteklenmiyor — atlandı.", sig)
