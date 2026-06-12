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


# ── 4) RED: stable second observation zero-fill → CANCELLED (ayrı saf stability helper) ──

def test_stable_second_zero_fill_cancel_returns_cancelled():
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {
        "order_id": "zero_fill_order_1",
        "side": "BUY",
        "original_size": "10",
    }

    first_obs = {
        "order": {
            "order_id": "zero_fill_order_1",
            "status": "ORDER_STATUS_CANCELED",
            "original_size": "10",
            "size_matched": "0",
            "associate_trades": [],
        },
        "trades": {
            "next_cursor": "LTE=",
            "data": [],
        },
    }

    second_obs = {
        "order": {
            "order_id": "zero_fill_order_1",
            "status": "ORDER_STATUS_CANCELED",
            "original_size": "10",
            "size_matched": "0",
            "associate_trades": [],
        },
        "trades": {
            "next_cursor": "LTE=",
            "data": [],
        },
    }

    # Deep identity check to prevent object alias leakage
    assert second_obs is not first_obs
    assert second_obs["order"] is not first_obs["order"]
    assert second_obs["trades"] is not first_obs["trades"]

    result = decide_zero_fill_cancel_with_stability(
        intent=intent,
        first_obs=first_obs,
        second_obs=second_obs,
    )

    assert result.state == "CANCELLED"


# ── 5) Fail-closed safety matrix: stability helper tehlikeli durumda CANCELLED DÖNMEZ ──

def _zfc_obs(order_id="zero_fill_order_1", status="ORDER_STATUS_CANCELED",
             size_matched="0", next_cursor="LTE=", data=None):
    """Her çağrıda YENİ canonical zero-fill-cancel observation literal'i döner (alias yok).
    data verilmezse boş yeni liste; verilirse aynen kullanılır (çağıran fresh liste geçmeli)."""
    return {
        "order": {
            "order_id": order_id,
            "status": status,
            "original_size": "10",
            "size_matched": size_matched,
            "associate_trades": [],
        },
        "trades": {
            "next_cursor": next_cursor,
            "data": [] if data is None else data,
        },
    }


def test_stable_zero_fill_cancel_blocks_unconfirmed_trade_trace():
    """İki gözlem zero-fill cancel gibi görünse de, bizim order_id'mize ait UNCONFIRMED
    (MATCHED/MINED) trade izi varsa CANCELLED yazılamaz — iz fill'e dönüşebilir (fail-closed)."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}

    # İki obs ayrı literal (inner trade dict'leri de ayrı) — alias yok
    first_obs = {
        "order": {"order_id": "zero_fill_order_1", "status": "ORDER_STATUS_CANCELED",
                  "original_size": "10", "size_matched": "0", "associate_trades": []},
        "trades": {"next_cursor": "LTE=", "data": [
            {"id": "trade_pending_a", "status": "TRADE_STATUS_MATCHED",
             "taker_order_id": "zero_fill_order_1", "maker_orders": [],
             "size": "10", "price": "0.36", "side": "BUY"},
        ]},
    }
    second_obs = {
        "order": {"order_id": "zero_fill_order_1", "status": "ORDER_STATUS_CANCELED",
                  "original_size": "10", "size_matched": "0", "associate_trades": []},
        "trades": {"next_cursor": "LTE=", "data": [
            {"id": "trade_pending_a", "status": "TRADE_STATUS_MINED",
             "taker_order_id": "zero_fill_order_1", "maker_orders": [],
             "size": "10", "price": "0.36", "side": "BUY"},
        ]},
    }
    assert second_obs is not first_obs and second_obs["trades"] is not first_obs["trades"]

    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"unconfirmed trade izi varken CANCELLED yazılmamalı: {result.state}"
    assert result.state == "RECOVERY_REQUIRED", f"fail-closed beklenir: {result.state}"


def test_stable_zero_fill_cancel_requires_complete_scan():
    """Herhangi gözlemde next_cursor != 'LTE=' (scan eksik) → CANCELLED yazılamaz."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}
    first_obs = _zfc_obs()                              # tam scan (LTE=)
    second_obs = _zfc_obs(next_cursor="MORE_PAGES")     # scan eksik
    assert second_obs is not first_obs

    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"eksik scan'de CANCELLED yazılmamalı: {result.state}"


def test_stable_zero_fill_cancel_blocks_size_matched_positive():
    """Herhangi gözlemde size_matched > 0 → zero-fill değil → CANCELLED yazılamaz."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}
    first_obs = _zfc_obs(size_matched="0")
    second_obs = _zfc_obs(size_matched="1")            # pozitif fill → zero-fill değil
    assert second_obs is not first_obs

    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"size_matched>0 iken CANCELLED yazılmamalı: {result.state}"


def test_stable_zero_fill_cancel_blocks_observation_mismatch():
    """İki gözlem canonical alanlarda uyuşmuyorsa (second LIVE) → instabilite → CANCELLED yok."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}
    first_obs = _zfc_obs(status="ORDER_STATUS_CANCELED")
    second_obs = _zfc_obs(status="ORDER_STATUS_LIVE")  # canonical cancel değil → instabil
    assert second_obs is not first_obs

    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"gözlem uyuşmazlığında CANCELLED yazılmamalı: {result.state}"


def test_stable_zero_fill_cancel_blocks_order_id_mismatch():
    """second_obs order_id farklı (bizim order'ımıza ait değil) → CANCELLED yazılamaz."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}
    first_obs = _zfc_obs(order_id="zero_fill_order_1")
    second_obs = _zfc_obs(order_id="some_other_order")
    assert second_obs is not first_obs

    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"order_id mismatch'te CANCELLED yazılmamalı: {result.state}"


def test_stable_zero_fill_cancel_invalid_numeric_fails_closed():
    """size_matched parse edilemezse exception FIRLAMAMALI; fail-closed non-terminal dönmeli."""
    from data.clob_reconcile import decide_zero_fill_cancel_with_stability

    intent = {"order_id": "zero_fill_order_1", "side": "BUY", "original_size": "10"}
    first_obs = _zfc_obs(size_matched="not-a-number")
    second_obs = _zfc_obs(size_matched="0")
    assert second_obs is not first_obs

    # Exception yakalanıp success sayılmaz; fırlarsa pytest doğal olarak fail eder (doğru RED)
    result = decide_zero_fill_cancel_with_stability(
        intent=intent, first_obs=first_obs, second_obs=second_obs)
    assert result.state != "CANCELLED", \
        f"parse edilemeyen numeric'te CANCELLED yazılmamalı: {result.state}"
    assert result.state == "RECOVERY_REQUIRED", f"fail-closed beklenir: {result.state}"
