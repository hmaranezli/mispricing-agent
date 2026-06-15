"""tests/test_e10c_session_trade_count_source.py — E10c real in-memory session trade count (TDD).

E10b `_scan_and_execute`'i `max_trades_first_session_halt(_session_trade_count())` ile bağladı ama
`_session_trade_count()` ŞİMDİLİK sabit 0 → gate test'li ama RUNTIME'da fiilen tetiklenmez. E10c:
gerçek PROCESS-RUNTIME, IN-MEMORY seans açılan-işlem sayacı. Başarılı açılış (hem legacy `elif position:`
hem atomic OPENED yolu) sayacı +1 artırır; başarısız/no-open (FAK kill, DUPLICATE, RECOVERY_REQUIRED)
ARTIRMAZ; limit'e ulaşınca E10b gate execute'tan ÖNCE yeni girişi engeller.

Politika (bu slice): restart-safe DEĞİL (process-memory), DB COUNT YOK, canlı DB YOK, RiskStateSnapshot
şeması DEĞİŞMEZ. Sayaç YALNIZ kabul edilen/açılan girişleri sayar (başarısız denemeleri değil).

Bu testler GERÇEK `_session_trade_count`'u kullanır (enjekte ETMEZ); diğer her şey (scan/council/execute/
log_position_open/ws_prices) mock'lanır. Canlı API/DB/order/Telegram YOK.

İlk RED: `_session_trade_count()` sabit 0 → başarılı açılıştan sonra da 0 kalır (artış yok) → AssertionError;
ayrıca `_reset_session_trade_count` seam'i eksik → AttributeError. Her ikisi de E10c'nin pin'lediği
eksik üretim seam'i (syntax/unrelated-import hatası DEĞİL).
"""
import os
import sys

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import main_loop


SLUG = "btc-updown-15m-t"


@pytest.fixture(autouse=True)
def _reset_session_counter():
    """Seanslar arası in-memory sayaç sızıntısını engelle. GREEN reset seam'i varsa onu kullan;
    RED-safe: yokken sessiz geç (asıl RED, artış-assertion'ı olsun, fixture setup hatası DEĞİL)."""
    reset = getattr(main_loop, "_reset_session_trade_count", None)
    if callable(reset):
        reset()
    yield
    reset = getattr(main_loop, "_reset_session_trade_count", None)
    if callable(reset):
        reset()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


def _position_legacy():
    """Legacy başarı yolu (line 289 `elif position:`): düz dict, accounting_persisted YOK.
    yes/no token YOK → _exit_tok falsy → enrich_entry_depth/create_task atlanır."""
    return {"slug": SLUG, "action": "YES", "pm_entry_price": 0.45,
            "shares": 10, "position_id": "p1"}


def _position_atomic_opened():
    """Atomic accounting envelope (Faz 2c gerçek üretim açılış): _acct=OPENED + persisted=True."""
    return {"accounting_persisted": True, "accounting_result": "OPENED",
            "position": {"slug": SLUG, "action": "YES", "pm_entry_price": 0.45,
                         "shares": 10, "position_id": "p1"}}


def _envelope_duplicate():
    """Idempotent DUPLICATE — append YOK, gerçek yeni açılış DEĞİL → sayaç ARTMAMALI."""
    return {"accounting_result": "DUPLICATE", "order_intent_id": "oi1",
            "existing_position_id": "ep1"}


def _envelope_recovery():
    """RECOVERY_REQUIRED — phantom position YOK, append YOK → sayaç ARTMAMALI."""
    return {"accounting_result": "RECOVERY_REQUIRED", "recovery_reason": "reconcile"}


async def _run_one_scan(execute_return):
    """_scan_and_execute'i NEW_ENTRIES + Operational ile koşar; GERÇEK _session_trade_count kullanır
    (enjekte ETMEZ). execute spy döner. Her çağrı taze open_positions=[] alır (MAX_OPEN_POSITIONS=1
    bir sonraki çağrıyı bloklamasın)."""
    mock_exec = AsyncMock(return_value=execute_return)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop._effective_risk_mode", new=MagicMock(return_value="Operational")), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=({}, {})), \
         patch("main_loop.log_position_open", new_callable=AsyncMock), \
         patch("main_loop.ws_prices", new=MagicMock()), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], 1000.0)
    return mock_exec


def test_fresh_session_count_starts_at_zero():
    """Taze process/test reset → sayaç 0."""
    assert main_loop._session_trade_count() == 0


def test_reset_helper_resets_count():
    """_reset_session_trade_count() seam'i var ve sayacı 0'a çeker. RED: helper eksik → AttributeError."""
    main_loop._reset_session_trade_count()
    assert main_loop._session_trade_count() == 0


@pytest.mark.asyncio
async def test_legacy_open_increments_count_by_one():
    """Legacy başarı yolu açılışı → sayaç tam +1. RED: sabit 0 kalır."""
    assert main_loop._session_trade_count() == 0
    await _run_one_scan(_position_legacy())
    assert main_loop._session_trade_count() == 1


@pytest.mark.asyncio
async def test_atomic_opened_increments_count_by_one():
    """Atomic OPENED (gerçek üretim açılış) → sayaç tam +1. RED: sabit 0 kalır."""
    await _run_one_scan(_position_atomic_opened())
    assert main_loop._session_trade_count() == 1


@pytest.mark.asyncio
async def test_failed_open_does_not_increment():
    """execute None (FAK kill, capital riske girmedi) → sayaç ARTMAZ."""
    await _run_one_scan(None)
    assert main_loop._session_trade_count() == 0


@pytest.mark.asyncio
async def test_duplicate_does_not_increment():
    """DUPLICATE envelope (append YOK) → sayaç ARTMAZ."""
    await _run_one_scan(_envelope_duplicate())
    assert main_loop._session_trade_count() == 0


@pytest.mark.asyncio
async def test_recovery_required_does_not_increment():
    """RECOVERY_REQUIRED envelope (phantom YOK) → sayaç ARTMAZ."""
    await _run_one_scan(_envelope_recovery())
    assert main_loop._session_trade_count() == 0


@pytest.mark.asyncio
async def test_two_successful_opens_count_two():
    """İki ardışık başarılı açılış → sayaç 2 (process-runtime birikir)."""
    await _run_one_scan(_position_legacy())
    await _run_one_scan(_position_legacy())
    assert main_loop._session_trade_count() == 2


@pytest.mark.asyncio
async def test_reaching_limit_then_e10b_blocks_next_entry():
    """limit-1 başarılı açılış izinli; bir tane daha limit'e ulaşır; sonraki giriş E10b gate ile
    execute'tan ÖNCE engellenir. RED: sayaç hiç artmaz → count==limit-1 assertion'ı patlar."""
    limit = config.MAX_TRADES_FIRST_SESSION  # 6
    for _ in range(limit - 1):
        m = await _run_one_scan(_position_legacy())
        m.assert_called_once()
    assert main_loop._session_trade_count() == limit - 1

    m = await _run_one_scan(_position_legacy())
    m.assert_called_once()
    assert main_loop._session_trade_count() == limit

    # Limit'e ulaşıldı → bir sonraki entry execute'tan ÖNCE bloklanır (E10b gate).
    m = await _run_one_scan(_position_legacy())
    m.assert_not_called()
    assert main_loop._session_trade_count() == limit
