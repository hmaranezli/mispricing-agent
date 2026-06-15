"""tests/test_e11b_no_fill_streak_source.py — E11b in-memory no-fill burst streak source (TDD).

E11a `no_fill_burst_halt` saf predicate'i ardışık no-fill sayısını ENJEKTE bekliyor. E11b o sayacı
besler: `_scan_and_execute`'ta her entry denemesinin execute() çıktısını
{OPENED / DUPLICATE / RECOVERY_REQUIRED / no-open(None)} bucket'a çevirip **ardışık no-fill** sayacını
tutar. PROCESS-RUNTIME in-memory (E10c `_SESSION_TRADE_COUNT` simetrisi); restart-safe DEĞİL,
DB COUNT YOK, RiskStateSnapshot şeması değişmez.

Hedef eksik/placeholder seam'ler (main_loop):
    _no_fill_streak() -> int
    _reset_no_fill_streak() -> None
    _increment_no_fill_streak() -> None

Davranış (gözlemlenebilir; iç implementasyona overfit YOK):
- Taze/reset → 0.
- execute() None (no-open / FAK kill) → +1.
- RECOVERY_REQUIRED envelope → +1.
- İki ardışık no-fill/recovery → 2.
- OPENED (atomic) → 0'a reset.
- Legacy open → 0'a reset.
- DUPLICATE → ARTIRMAZ ve RESET ETMEZ (streak korunur).
- Council None (execute hiç çağrılmadı / prevalidation) → ARTIRMAZ.
- Entry/exit ayrımı: yalnız _scan_and_execute entry çıktıları besler; _monitor_positions/panic-flatten
  dokunulmaz. no_fill_burst_halt gate'i HENÜZ bağlanmaz (E11c).

İlk RED: seam'ler yok → AttributeError; ve/veya no-fill/recovery sonrası streak 0 kalır.
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
def _reset_streaks():
    """Seanslar arası in-memory sayaç sızıntısını engelle. GREEN reset seam'i varsa kullan;
    RED-safe: yokken sessiz geç (asıl RED, streak/seam assertion'ları olsun, fixture hatası DEĞİL)."""
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count", "_reset_session_submit_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()
    yield
    for name in ("_reset_no_fill_streak", "_reset_session_trade_count", "_reset_session_submit_count"):
        fn = getattr(main_loop, name, None)
        if callable(fn):
            fn()


def _finding():
    return {"slug": SLUG, "action": "YES", "fair_value": 0.6,
            "best_ask": 0.45, "edge": 0.15, "seconds_remaining": 600}


def _position_legacy():
    """Legacy başarı yolu (line 289 `elif position:`)."""
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


async def _run_one_scan(execute_return, council_result=({}, {})):
    """_scan_and_execute'i NEW_ENTRIES + Operational + E10b-bypass ile koşar; GERÇEK _no_fill_streak
    kullanır. _session_trade_count→0 patch'lenir ki E10c counter bleed E10b gate'i tetiklemesin.
    council_result=None → execute hiç çağrılmaz (council veto). Her çağrı taze open_positions=[]."""
    mock_exec = AsyncMock(return_value=execute_return)
    with patch.object(config, "NEW_ENTRIES_ENABLED", True), \
         patch("main_loop._effective_risk_mode", new=MagicMock(return_value="Operational")), \
         patch("main_loop._session_trade_count", new=MagicMock(return_value=0)), \
         patch("main_loop._session_submit_count", new=MagicMock(return_value=0)), \
         patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]), \
         patch("main_loop._run_council", new_callable=AsyncMock, return_value=council_result), \
         patch("main_loop.log_position_open", new_callable=AsyncMock), \
         patch("main_loop.ws_prices", new=MagicMock()), \
         patch("main_loop.execute", mock_exec):
        await main_loop._scan_and_execute([], [], 1000.0)
    return mock_exec


def test_fresh_streak_is_zero():
    """Taze process/test reset → no-fill streak 0."""
    assert main_loop._no_fill_streak() == 0


def test_reset_helper_resets_streak():
    """_reset_no_fill_streak() seam'i var ve streak'i 0'a çeker. RED: helper eksik → AttributeError."""
    main_loop._reset_no_fill_streak()
    assert main_loop._no_fill_streak() == 0


def test_increment_helper_increments_streak():
    """_increment_no_fill_streak() seam'i var ve +1 yapar. RED: helper eksik → AttributeError."""
    main_loop._increment_no_fill_streak()
    assert main_loop._no_fill_streak() == 1


@pytest.mark.asyncio
async def test_no_open_none_increments_streak():
    """execute() None (FAK kill / no-open) → streak +1. RED: 0 kalır."""
    assert main_loop._no_fill_streak() == 0
    await _run_one_scan(None)
    assert main_loop._no_fill_streak() == 1


@pytest.mark.asyncio
async def test_recovery_required_increments_streak():
    """RECOVERY_REQUIRED envelope → streak +1. RED: 0 kalır."""
    await _run_one_scan(_envelope_recovery())
    assert main_loop._no_fill_streak() == 1


@pytest.mark.asyncio
async def test_two_consecutive_no_fill_count_two():
    """İki ardışık no-fill/recovery → streak 2."""
    await _run_one_scan(None)
    await _run_one_scan(_envelope_recovery())
    assert main_loop._no_fill_streak() == 2


@pytest.mark.asyncio
async def test_atomic_open_resets_streak():
    """no-fill birikti, sonra atomic OPENED → streak 0'a reset."""
    await _run_one_scan(None)
    await _run_one_scan(None)
    assert main_loop._no_fill_streak() == 2
    await _run_one_scan(_position_atomic_opened())
    assert main_loop._no_fill_streak() == 0


@pytest.mark.asyncio
async def test_legacy_open_resets_streak():
    """no-fill birikti, sonra legacy open → streak 0'a reset."""
    await _run_one_scan(None)
    assert main_loop._no_fill_streak() == 1
    await _run_one_scan(_position_legacy())
    assert main_loop._no_fill_streak() == 0


@pytest.mark.asyncio
async def test_duplicate_does_not_increment_or_reset():
    """DUPLICATE → ne artar ne resetlenir (mevcut streak korunur)."""
    await _run_one_scan(None)
    assert main_loop._no_fill_streak() == 1
    await _run_one_scan(_envelope_duplicate())
    assert main_loop._no_fill_streak() == 1


@pytest.mark.asyncio
async def test_council_veto_does_not_increment():
    """Council None (execute hiç çağrılmadı / prevalidation) → streak ARTMAZ."""
    m = await _run_one_scan(_position_legacy(), council_result=None)
    m.assert_not_called()
    assert main_loop._no_fill_streak() == 0
