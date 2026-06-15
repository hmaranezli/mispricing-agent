"""tests/test_e11e_submit_count_source.py — E11e in-memory submit counter source (TDD).

E11d `fill_to_submit_halt` saf predicate'i `opened` + `submitted` sayıları ENJEKTE bekliyor. opened =
E10c `_SESSION_TRADE_COUNT` zaten var; E11e `submitted` sayacını besler: `_scan_and_execute`'ta
HER GERÇEK execute() çağrısında (sonuç ne olursa olsun) submit +1. PROCESS-RUNTIME in-memory
(E10c/E11b simetrisi); restart-safe DEĞİL, DB COUNT YOK, RiskStateSnapshot şeması değişmez.

Hedef eksik/placeholder seam'ler (main_loop):
    _session_submit_count() -> int
    _increment_session_submit_count() -> None
    _reset_session_submit_count() -> None

Davranış (gözlemlenebilir):
- Taze/reset → 0.
- HER execute() çağrısı → +1 (OPENED / RECOVERY_REQUIRED / no-open(None) / DUPLICATE — hepsi).
- İki execute çağrısı → 2.
- Council veto / pre-execute → ARTMAZ (execute hiç çağrılmadı).
- E5 risk-mode / NEW_ENTRIES blok → ARTMAZ.
- E10b max-trades blok → ARTMAZ.
- E11c no-fill burst blok → ARTMAZ.
- Entry-only; _monitor_positions/panic-flatten/exit dokunulmaz. fill_to_submit_halt gate'i HENÜZ
  bağlanmaz (E11f).

İlk RED: seam'ler yok → AttributeError; ve/veya execute sonrası submitted 0 kalır.
Canlı API/DB/order/Telegram YOK.
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
def _reset_counters():
    """Seanslar arası in-memory sayaç sızıntısını engelle. GREEN reset seam'leri varsa kullan;
    RED-safe: yokken sessiz geç (asıl RED, submit/seam assertion'ları olsun, fixture hatası DEĞİL)."""
    names = ("_reset_session_submit_count", "_reset_no_fill_streak", "_reset_session_trade_count")

    def _reset_all():
        for name in names:
            fn = getattr(main_loop, name, None)
            if callable(fn):
                fn()

    _reset_all()
    yield
    _reset_all()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


def _position_legacy():
    return {"slug": SLUG, "action": "YES", "pm_entry_price": 0.45,
            "shares": 10, "position_id": "p1"}


def _position_atomic_opened():
    return {"accounting_persisted": True, "accounting_result": "OPENED",
            "position": {"slug": SLUG, "action": "YES", "pm_entry_price": 0.45,
                         "shares": 10, "position_id": "p1"}}


def _envelope_duplicate():
    return {"accounting_persisted": True, "accounting_result": "DUPLICATE",
            "order_intent_id": "oi1", "existing_position_id": "ep1"}


def _envelope_recovery():
    return {"accounting_persisted": False, "accounting_result": "RECOVERY_REQUIRED",
            "order_intent_id": "oi1", "recovery_reason": "FAK_RECOVERY"}


async def _run_one_scan(execute_return, *, new_entries=True, risk_mode="Operational",
                        session_trade_count=0, no_fill_streak=0, council_result=({}, {})):
    """_scan_and_execute'i enjekte gate durumlarıyla koşar; GERÇEK _session_submit_count kullanır.
    Tüm gate'ler default'ta GEÇER (execute'a ulaşılır). Gate-blok testleri ilgili parametreyi değiştirir.
    execute spy döner. Her çağrı taze open_positions=[]."""
    mock_exec = AsyncMock(return_value=execute_return)
    with patch.object(config, "NEW_ENTRIES_ENABLED", new_entries), \
         patch("main_loop._effective_risk_mode", new=MagicMock(return_value=risk_mode)), \
         patch("main_loop._session_trade_count", new=MagicMock(return_value=session_trade_count)), \
         patch("main_loop._no_fill_streak", new=MagicMock(return_value=no_fill_streak)), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=council_result), \
         patch("main_loop.log_position_open", new_callable=AsyncMock), \
         patch("main_loop.ws_prices", new=MagicMock()), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], 1000.0)
    return mock_exec


def test_fresh_submit_count_is_zero():
    """Taze process/test reset → submit sayacı 0."""
    assert main_loop._session_submit_count() == 0


def test_reset_helper_resets_submit_count():
    """_reset_session_submit_count() seam'i var ve 0'a çeker. RED: helper eksik → AttributeError."""
    main_loop._reset_session_submit_count()
    assert main_loop._session_submit_count() == 0


def test_increment_helper_increments_submit_count():
    """_increment_session_submit_count() seam'i var ve +1 yapar. RED: helper eksik → AttributeError."""
    main_loop._increment_session_submit_count()
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_opened_increments_submit():
    """OPENED → execute çağrıldı → submit +1."""
    assert main_loop._session_submit_count() == 0
    m = await _run_one_scan(_position_atomic_opened())
    m.assert_called_once()
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_legacy_open_increments_submit():
    """Legacy open → execute çağrıldı → submit +1."""
    await _run_one_scan(_position_legacy())
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_recovery_required_increments_submit():
    """RECOVERY_REQUIRED → execute çağrıldı → submit +1."""
    await _run_one_scan(_envelope_recovery())
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_no_open_none_increments_submit():
    """execute() None (FAK kill) → execute çağrıldı → submit +1."""
    await _run_one_scan(None)
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_duplicate_increments_submit():
    """DUPLICATE → execute çağrıldı → submit +1 (sonuç önemsiz; submit gerçekleşti)."""
    await _run_one_scan(_envelope_duplicate())
    assert main_loop._session_submit_count() == 1


@pytest.mark.asyncio
async def test_two_execute_calls_count_two():
    """İki execute çağrısı → submit 2 (process-runtime birikir)."""
    await _run_one_scan(None)
    await _run_one_scan(_position_atomic_opened())
    assert main_loop._session_submit_count() == 2


@pytest.mark.asyncio
async def test_council_veto_does_not_increment():
    """Council None (execute hiç çağrılmadı) → submit ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), council_result=None)
    m.assert_not_called()
    assert main_loop._session_submit_count() == 0


@pytest.mark.asyncio
async def test_new_entries_disabled_does_not_increment():
    """NEW_ENTRIES_ENABLED=False → execute öncesi blok → submit ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), new_entries=False)
    m.assert_not_called()
    assert main_loop._session_submit_count() == 0


@pytest.mark.asyncio
async def test_risk_mode_block_does_not_increment():
    """E5 risk-mode ≠ Operational → execute öncesi blok → submit ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), risk_mode="Halted")
    m.assert_not_called()
    assert main_loop._session_submit_count() == 0


@pytest.mark.asyncio
async def test_max_trades_block_does_not_increment():
    """E10b max-trades blok (session_trade_count >= 6) → execute öncesi blok → submit ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), session_trade_count=6)
    m.assert_not_called()
    assert main_loop._session_submit_count() == 0


@pytest.mark.asyncio
async def test_no_fill_burst_block_does_not_increment():
    """E11c no-fill burst blok (no_fill_streak >= 3) → execute öncesi blok → submit ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), no_fill_streak=3)
    m.assert_not_called()
    assert main_loop._session_submit_count() == 0
