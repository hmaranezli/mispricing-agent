"""tests/test_clob_reconcile.py — Faz 2c-4 Araf-Intent Resolution Driver (dual-oracle reconcile).

Fixture'lar GERÇEK Polymarket OpenAPI DEĞİL — docs/plan VARSAYIMI (canlı sample henüz yok =
live-blocker). Alan adları/tipleri canlı örnekle doğrulanana kadar "milimetrik gerçek" iddia
EDİLMEZ. Çekirdek invariant: CONFIRMED trade kanıtı olmadan FILLED/PARTIAL_FILLED/CANCELLED YAZILMAZ
(dual-oracle: get_order=lifecycle, get_trades=settlement/accounting).
"""
import pytest


# ── 1) RED: pending/unconfirmed match → terminal muhasebe YOK (fail-closed) ──

def test_pending_unconfirmed_match_does_not_terminal_account():
    """get_order MATCHED + size_matched>0, ama get_trades'te eşleşen trade YALNIZ
    MATCHED/MINED/RETRYING (CONFIRMED YOK) → sistem FILLED/PARTIAL_FILLED/CANCELLED üretmemeli;
    fail-closed/non-terminal (RECOVERY_REQUIRED/NO_EVIDENCE/WAIT/SUBMITTED_UNKNOWN) kalmalı.

    İlk RED structural: `data.clob_reconcile.decide_araf_resolution` henüz yok → ImportError.
    """
    # Import test GÖVDESİNDE → modül yoksa temiz "1 failed" (collection error DEĞİL).
    from data.clob_reconcile import decide_araf_resolution

    order_id = "ord-araf-1"

    # intent (minimal v0; docs/plan varsayımı)
    intent = {
        "order_intent_id": "iid-araf-1",
        "market_token_id": "tok-araf",
        "side": "BUY",
        "intended_size": "10",
        "exchange_order_id": order_id,     # bizim borsa order_id'miz (taker/maker slot'ta eşleşmeli)
    }

    # get_order fixture: MATCHED + tam size_matched AMA CONFIRMED settlement DEĞİL (lifecycle kanıtı)
    order = {
        "status": "ORDER_STATUS_MATCHED",
        "original_size": "10",
        "size_matched": "10",
        "associate_trades": ["trade_unconfirmed_1"],
    }

    # get_trades fixture: tek sayfa, tarama TAM (next_cursor=LTE=), eşleşen trade VAR ama CONFIRMED YOK
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_unconfirmed_1",
                "status": "TRADE_STATUS_MATCHED",     # ∈ {MATCHED, MINED, RETRYING} — CONFIRMED DEĞİL
                "taker_order_id": order_id,            # order_id eşleşmesi (taker-side; bizim FAK taker)
                "maker_orders": [
                    {"order_id": "maker-counterparty",
                     "matched_amount": "10",
                     "price": "0.36",
                     "fee_rate_bps": "0",              # tip canlı sample gelene kadar KİLİTLENMEDİ
                     "side": "SELL"},
                ],
                "size": "10",
                "price": "0.36",
                "side": "BUY",
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Result shape esnek: dict veya `.state` taşıyan obje (mevcut reconcile_intent dict döndürüyor)
    state = result["state"] if isinstance(result, dict) else getattr(result, "state")

    # CONFIRMED trade yokken terminal muhasebe YASAK (anti-hallucination)
    assert state not in {"FILLED", "PARTIAL_FILLED", "CANCELLED"}, \
        f"CONFIRMED trade yokken terminal muhasebe YASAK: {state}"
    # Beklenen: fail-closed / non-terminal
    assert state in {"RECOVERY_REQUIRED", "NO_EVIDENCE", "WAIT", "SUBMITTED_UNKNOWN"}, \
        f"fail-closed/non-terminal beklenir: {state}"


# ── 2) RED: maker-side CONFIRMED fill → maker_orders[] slot'tan tanı (top-level side KÖR değil) ──

def test_maker_order_confirmed_fill_uses_maker_slot_side():
    """Bizim order_id top-level `taker_order_id`'de DEĞİL, `maker_orders[].order_id` içinde
    eşleşiyor ve trade `TRADE_STATUS_CONFIRMED` ise → maker-side fill tanınmalı, terminal
    (FILLED/PARTIAL_FILLED, tam fill → FILLED) dönmeli. Top-level trade side KÖR kullanılmamalı;
    yön `maker_orders[].side` / intent side ile doğrulanmalı (burada top-level SELL, maker slot BUY).

    RED (şimdilik): CONFIRMED yolu `decide_araf_resolution`'da NotImplementedError ile placeholder.
    """
    from data.clob_reconcile import decide_araf_resolution

    our_id = "our_maker_order_1"

    intent = {
        "order_intent_id": "iid-maker-1",
        "market_token_id": "tok-maker",
        "side": "BUY",
        "intended_size": "10",
        "exchange_order_id": our_id,
    }

    order = {
        "status": "ORDER_STATUS_MATCHED",
        "original_size": "10",
        "size_matched": "10",
        "associate_trades": ["trade_confirmed_maker_1"],
    }

    # CONFIRMED trade; bizim order_id YALNIZ maker_orders[] içinde; top-level side TERS (SELL)
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_confirmed_maker_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": "someone_else_taker_order",   # bizim DEĞİL
                "side": "SELL",                                  # top-level — KÖR kullanılmamalı
                "size": "10",
                "price": "0.48",                                 # top-level — kullanılmamalı
                "maker_orders": [
                    {"order_id": our_id,
                     "side": "BUY",                              # bizim yön — bununla doğrula
                     "matched_amount": "10",
                     "price": "0.52"},                           # fee_rate_bps yok → tip kilitlenmedi
                ],
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)
    state = result["state"] if isinstance(result, dict) else getattr(result, "state")

    assert state in {"FILLED", "PARTIAL_FILLED"}, \
        f"maker-side CONFIRMED fill terminal olmalı: {state}"
    assert state == "FILLED", f"tam maker fill (10/10) FILLED beklenir: {state}"


# ── 3) PIN: zero-fill cancel → tek gözlemde CANCELLED yazma (eventual-consistency guard) ──

def test_zero_fill_cancel_requires_stable_second_observation():
    """get_order CANCELED + size_matched==0 + flawless scan (next_cursor=LTE=, data=[]) + CONFIRMED
    trade YOK olsa bile, bu İLK/TEK gözlemse sistem hemen CANCELLED terminal YAZMAMALI. get_order ile
    get_trades atomik değil → eventual consistency: CANCELLED için ikinci stabil gözlem gerekir.
    Mevcut kod CONFIRMED kanıtı olmadan terminal yazmıyor → bu invariant PIN ile kilitlenir.
    (Saf imza korunur: decide_araf_resolution(intent, order, trades); time/retry mock YOK.)
    """
    from data.clob_reconcile import decide_araf_resolution

    intent = {
        "order_intent_id": "iid-zero-1",
        "market_token_id": "tok-zero",
        "side": "BUY",
        "intended_size": "10",
        "exchange_order_id": "zero_fill_order_1",
    }

    order = {
        "status": "ORDER_STATUS_CANCELED",
        "original_size": "10",
        "size_matched": "0",
        "associate_trades": [],
    }

    trades = {
        "next_cursor": "LTE=",     # tarama TAM
        "data": [],                # CONFIRMED trade KESİNLİKLE yok
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)
    state = result["state"] if isinstance(result, dict) else getattr(result, "state")

    # Tek gözlemde terminal (özellikle CANCELLED) YAZILMAMALI
    assert state not in {"CANCELLED", "FILLED", "PARTIAL_FILLED"}, \
        f"tek gözlemde terminal yazılmamalı (eventual-consistency): {state}"
    # Beklenen: non-terminal / fail-closed
    assert state in {"RECOVERY_REQUIRED", "NO_EVIDENCE", "WAIT", "SUBMITTED_UNKNOWN"}, \
        f"non-terminal/fail-closed beklenir: {state}"
