"""tests/test_mainloop_accounting.py — Faz 2c Task H4+H5 (consumer) RED testleri.

Amendment 1/2: execute() success ENVELOPE döner — accounting metadata position objesine SIZMAZ.
  OPENED:    {accounting_persisted:True, accounting_result:"OPENED", position:{...pure...}}
  DUPLICATE: {accounting_persisted:True, accounting_result:"DUPLICATE", order_intent_id,
              existing_position_id}   (partial 'position' objesi YOK)

main_loop._scan_and_execute consumer sözleşmesi (RED — henüz implemente DEĞİL):
  - OPENED  → open_positions.append(res["position"]) (PURE); log_position_open ÇAĞRILMAZ;
              ws.subscribe + enrich KORUNUR; open_positions'da accounting metadata OLMAZ.
  - DUPLICATE → forensic WARNING; append/ws/write YOK.
  - RECOVERY_REQUIRED → append/ws/write YOK.
  - legacy/dry (accounting_persisted YOK) → eski log_position_open KORUNUR.

Mevcut main_loop accounting_result'a BAKMADAN `if position:` ile log_position_open + append + ws
yapıyor VE yeni envelope/DUPLICATE shape'ini unpack edemediği için position["action"]'da KeyError
fırlatıyor → davranış-eksikliği. _drive() exception'ı yakalar; testler önce "RAISE etmemeli"
contract'ını (temiz assertion) doğrular.

Hiçbir test canlı DB/network kullanmaz; execute() mock'lanır, conn=None.
"""
import os
import sys
import logging
import contextlib

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def _finding(action="YES"):
    return {"slug": "btc-up-5m-acct", "asset": "BTC", "action": action,
            "fair_value": 0.55, "best_ask": 0.35, "edge": 0.20, "seconds_remaining": 900,
            "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222"}


def _gate():
    return {"pass": True, "confidence_score": 82.5}


def _risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15}


def _position_only():
    """ENVELOPE içindeki PURE position objesi — accounting metadata YOK."""
    return {"position_id": "pos-opened-1", "order_intent_id": "iid-1",
            "slug": "btc-up-5m-acct", "asset": "BTC", "action": "YES",
            "shares": 71.43, "pm_entry_price": 0.35, "position_usd": 25.0,
            "ask_at_decision": 0.35, "slippage_pct": 0.0,
            "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222", "status": "open"}


def _opened_envelope():
    return {"accounting_persisted": True, "accounting_result": "OPENED",
            "position": _position_only()}


def _duplicate_envelope():
    # Partial position objesi YASAK; existing_position_id readback'ten gelir.
    return {"accounting_persisted": True, "accounting_result": "DUPLICATE",
            "order_intent_id": "iid-1", "existing_position_id": "existing-pos"}


def _recovery_dict():
    # Recovery shape (amendment'ta değişmedi). position_id/action mevcut main_loop'un append'e
    # kadar TEMİZ ilerlemesi için var; GREEN'de main_loop bu dict'i (accounting_result ile) atlamalı.
    return {"accounting_persisted": False, "accounting_result": "RECOVERY_REQUIRED",
            "order_intent_id": "iid-1", "recovery_reason": "CONFIRM_TX_FAILED",
            "position_id": "pos-recovery-phantom",
            "slug": "btc-up-5m-acct", "asset": "BTC", "action": "YES",
            "shares": 71.43, "pm_entry_price": 0.35,
            "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222"}


def _legacy_dict():
    """Dry/legacy executor return — accounting_persisted YOK (eski yol korunmalı)."""
    return {"position_id": "pos-legacy", "slug": "btc-up-5m-acct", "asset": "BTC",
            "action": "YES", "shares": 2.0, "pm_entry_price": 0.36, "position_usd": 1.25,
            "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
            "opened_at": "2026-06-07T00:00:00+00:00", "dry_run": False}


def _consumer(exec_return):
    import main_loop
    log_spy = AsyncMock()
    ws_mock = MagicMock()
    enrich_mock = AsyncMock()
    ctx = (
        patch.object(config, "NEW_ENTRIES_ENABLED", True),
        patch("main_loop.scan_edges", new_callable=AsyncMock, return_value=[_finding()]),
        patch("main_loop._run_council", new_callable=AsyncMock,
              return_value=(_gate(), _risk())),
        patch("main_loop.execute", new_callable=AsyncMock, return_value=exec_return),
        patch("main_loop.log_position_open", log_spy),
        patch("main_loop.ws_prices", ws_mock),
        patch("main_loop.enrich_entry_depth", enrich_mock),
    )
    return main_loop, log_spy, ws_mock, enrich_mock, ctx


async def _drive(main_loop, ctx, open_positions):
    """_scan_and_execute'i sürer; exception'ı YAKALAR (raise yerine döndürür) → temiz assertion-RED."""
    with contextlib.ExitStack() as stack:
        for cm in ctx:
            stack.enter_context(cm)
        try:
            await main_loop._scan_and_execute(open_positions, [], 1000.0, conn=None)
            return None
        except Exception as e:
            return e


# H5-14) OPENED envelope → log_position_open ÇAĞRILMAZ; res["position"] (PURE) append edilir
@pytest.mark.asyncio
async def test_mainloop_skips_log_position_open_on_accounting_persisted():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_opened_envelope())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"main_loop OPENED envelope'u unpack edemeyip RAISE etti: {err!r}"
    log_spy.assert_not_called()                           # execute atomik yazdı → ikinci writer YOK
    assert len(open_positions) == 1
    assert open_positions[0].get("position_id") == "pos-opened-1", "res['position'] append edilmeli"


# H5-15) OPENED → append + ws.subscribe + enrich KORUNUR; DB write YOK; metadata leak YOK
@pytest.mark.asyncio
async def test_mainloop_appends_ws_enrich_on_opened_without_db_write():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_opened_envelope())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"main_loop OPENED envelope RAISE etti: {err!r}"
    assert len(open_positions) == 1
    assert "accounting_persisted" not in open_positions[0], "metadata open_positions'a SIZMAMALI"
    assert "accounting_result" not in open_positions[0]
    assert ws_mock.subscribe.called, "ws.subscribe korunmalı"
    assert enrich_mock.called, "enrich_entry_depth korunmalı"
    log_spy.assert_not_called()


# H5-16) OPENED sonrası ikinci writer denenmez (no-double accounting)
@pytest.mark.asyncio
async def test_mainloop_no_double_row_after_execute():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_opened_envelope())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"main_loop OPENED envelope RAISE etti: {err!r}"
    assert log_spy.call_count == 0, "ikinci yazım denemesi YOK (execute tek yazıcı)"
    assert len(open_positions) == 1


# H5-17) RECOVERY_REQUIRED → write/append/ws YOK
@pytest.mark.asyncio
async def test_mainloop_recovery_result_no_write_no_append_no_ws():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_recovery_dict())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"recovery result RAISE etmemeli: {err!r}"
    log_spy.assert_not_called()
    assert len(open_positions) == 0, "recovery dict position SANILMAMALI"
    assert not ws_mock.subscribe.called


# H5-18) DUPLICATE envelope → forensic WARNING; append/ws/write YOK; partial position OKUNMAZ
@pytest.mark.asyncio
async def test_mainloop_duplicate_warning_no_append_no_ws_no_write(caplog):
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_duplicate_envelope())
    open_positions = []
    with caplog.at_level(logging.WARNING):
        err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"main_loop DUPLICATE envelope'u position sanıp RAISE etmemeli: {err!r}"
    assert len(open_positions) == 0, "DUPLICATE append edilMEMELİ"
    assert not ws_mock.subscribe.called
    log_spy.assert_not_called()
    assert any(r.levelno >= logging.WARNING for r in caplog.records), \
        "DUPLICATE forensic WARNING üretmeli (order_intent_id + existing_position_id)"


# H5-19) legacy/dry path (accounting_persisted YOK) → eski log_position_open KORUNUR (regresyon)
@pytest.mark.asyncio
async def test_dry_run_path_still_uses_log_position_open():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_legacy_dict())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"legacy path RAISE etmemeli: {err!r}"
    log_spy.assert_called_once()                          # legacy davranış korunur
    assert len(open_positions) == 1


# H5-20) RECOVERY_REQUIRED → phantom tracked position oluşmaz (gelecek entry'yi kilitlemez)
@pytest.mark.asyncio
async def test_recovery_required_blocks_future_entry_or_no_resubmit():
    main_loop, log_spy, ws_mock, enrich_mock, ctx = _consumer(_recovery_dict())
    open_positions = []
    err = await _drive(main_loop, ctx, open_positions)
    assert err is None, f"recovery result RAISE etmemeli: {err!r}"
    assert open_positions == [], "recovery → phantom tracked position YOK (resubmit/karışıklık önle)"
    assert not ws_mock.subscribe.called
