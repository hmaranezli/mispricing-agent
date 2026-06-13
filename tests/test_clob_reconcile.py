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


# ── 6) RED: taker-side CONFIRMED full fill → Decimal accounting evidence (state'ten fazlası) ──

def test_taker_confirmed_full_fill_returns_decimal_accounting_evidence():
    """Taker-side CONFIRMED full fill: result yalnız state='FILLED' değil, Decimal accounting
    evidence de taşımalı (matched_size/avg_price/fee_rate_bps/matched_trade_ids/accounting_source).
    Kanıt order.status'tan DEĞİL, CONFIRMED trade evidence'tan gelir. Tek trade; VWAP/multi-trade,
    maker-side accounting, partial/residual-live, idempotent DB accounting bu testin DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    # NOT: exchange_order_id, mevcut decide_araf_resolution contract bridge'idir (fonksiyon
    # intent["exchange_order_id"] okuyor). order_id↔exchange_order_id standardizasyonu AYRI
    # RED/refactor konusu; bu testte production contract'a dokunmadan köprü kuruyoruz.
    intent = {
        "order_id": "full_fill_order_1",
        "exchange_order_id": "full_fill_order_1",
        "side": "BUY",
        "original_size": "10",
    }

    order = {
        "order_id": "full_fill_order_1",
        "status": "ORDER_STATUS_MATCHED",
        "original_size": "10",
        "size_matched": "10",
    }

    # NOT: trade.side, mevcut decide_araf_resolution taker-side direction validation contract'ıdır
    # (taker fill'de yön top-level side ile doğrulanır). Gerçek API alan adları canlı sample ile
    # ayrıca doğrulanacak (fixture-contract v0 varsayımı).
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_full_1",
                "taker_order_id": "full_fill_order_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "side": "BUY",
                "size": "10",
                "price": "0.52",
                "fee_rate_bps": "10",
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    assert result.state == "FILLED", f"taker CONFIRMED full fill FILLED olmalı: {result.state}"
    assert result.matched_size == Decimal("10"), f"matched_size Decimal: {result.matched_size!r}"
    assert result.avg_price == Decimal("0.52"), f"avg_price Decimal: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), f"fee_rate_bps Decimal (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_full_1",), \
        f"matched_trade_ids tuple: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"


# ── 7) RED: maker-side CONFIRMED full fill → Decimal accounting evidence maker SLOT'tan ──

def test_maker_confirmed_full_fill_returns_decimal_accounting_evidence():
    """Maker-side CONFIRMED full fill: state='FILLED' KALIR (mevcut davranış), ama accounting
    evidence top-level trade alanlarından DEĞİL, bizim order_id ile eşleşen `maker_orders[]`
    slot'undan gelmeli. Top-level side/size/price/fee_rate_bps bilerek POISON (yanıltıcı) —
    test, sonucun maker slot'tan geldiğini ve top-level'ı KÖR kullanmadığını ispatlar.
    Tek maker trade; VWAP/multi-trade, partial/residual-live, idempotent DB accounting DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "our_maker_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    order = {
        "status": "ORDER_STATUS_MATCHED",
        "original_size": "10",
        "size_matched": "10",
    }

    # Tek CONFIRMED trade: top-level alanlar POISON (bizim emrimize ait değil), bizim slot
    # YALNIZ maker_orders[] içinde ve doğru değerlerle. taker_order_id bilerek bizim DEĞİL
    # → taker extractor'a sızmaz; tek doğru kaynak maker slot.
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_confirmed_maker_1",
                "status": "TRADE_STATUS_CONFIRMED",
                # ── top-level POISON (kör kullanılmamalı) ──
                "taker_order_id": "someone_else_taker_order",
                "side": "SELL",
                "size": "99",
                "price": "0.99",
                "fee_rate_bps": "999",
                # ── bizim slot (tek doğru accounting kaynağı) ──
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "10",
                        "price": "0.52",
                        "fee_rate_bps": "10",
                    },
                ],
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    assert result.state == "FILLED", f"maker CONFIRMED full fill FILLED olmalı: {result.state}"
    assert result.matched_size == Decimal("10"), \
        f"matched_size maker slot matched_amount: {result.matched_size!r}"
    assert result.avg_price == Decimal("0.52"), \
        f"avg_price maker slot price: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), \
        f"fee_rate_bps maker slot (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_confirmed_maker_1",), \
        f"matched_trade_ids trade-level id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"

    # ── poison-pill regression guard: kaynak top-level DEĞİL, maker slot ──
    assert result.matched_size != Decimal("99"), "top-level size POISON sızdı"
    assert result.avg_price != Decimal("0.99"), "top-level price POISON sızdı"
    assert result.fee_rate_bps != Decimal("999"), "top-level fee_rate_bps POISON sızdı"


# ── 8) RED: confirmed partial + residual-LIVE → terminal DÜŞÜRME (state-machine koruması) ──

def test_confirmed_partial_with_residual_live_order_is_not_terminal():
    """CONFIRMED partial fill VAR (size_matched=4) ama order hâlâ ORDER_STATUS_LIVE ve
    size_matched < original_size → residual kitapta açık. Bu durumda decide_araf_resolution
    TERMINAL state DÖNDÜRMEMELİ. Özellikle PARTIAL_FILLED YASAK: order_intent state-machine'de
    PARTIAL_FILLED ∈ TERMINAL_STATES (terminal sonrası transition strict blok) → residual sonradan
    dolarsa ek fill kaybolur / pozisyon boyutu yanlış donar. Live-residual = FAK invariant breach →
    fail-closed non-terminal RECOVERY_REQUIRED (araf takipte kalır, token yeni emre BLOK).

    Bu state-machine RED'inde accounting evidence yüzeye ÇIKMAZ (None) — non-terminal partial
    exposure accounting + DB idempotency AYRI/sonraki RED (bu turda çift-sayım riski açılmaz).
    """
    from data.clob_reconcile import decide_araf_resolution

    our_id = "our_residual_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    # Residual canlılığı: status LIVE + size_matched("4") < original_size("10")
    order = {
        "status": "ORDER_STATUS_LIVE",
        "original_size": "10",
        "size_matched": "4",
    }

    # Tek CONFIRMED partial trade (taker-side, intent BUY ile uyumlu)
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_partial_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "4",
                "price": "0.50",
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Terminal YASAK (özellikle PARTIAL_FILLED, çünkü o terminal = takipten düşme)
    assert result.state != "FILLED", f"residual-live partial FILLED olamaz: {result.state}"
    assert result.state != "CANCELLED", f"residual-live partial CANCELLED olamaz: {result.state}"
    assert result.state != "PARTIAL_FILLED", \
        f"PARTIAL_FILLED terminal → residual-live takipten düşmemeli: {result.state}"
    assert result.state == "RECOVERY_REQUIRED", \
        f"fail-closed non-terminal RECOVERY_REQUIRED beklenir: {result.state}"

    # State-machine RED'i: accounting evidence yüzeye çıkmaz (None)
    assert result.matched_size is None, f"matched_size None olmalı: {result.matched_size!r}"
    assert result.avg_price is None, f"avg_price None olmalı: {result.avg_price!r}"
    assert result.fee_rate_bps is None, f"fee_rate_bps None olmalı: {result.fee_rate_bps!r}"
    assert result.matched_trade_ids is None, \
        f"matched_trade_ids None olmalı: {result.matched_trade_ids!r}"
    assert result.accounting_source is None, \
        f"accounting_source None olmalı: {result.accounting_source!r}"


# ── 9) RED: dead-residual taker partial → terminal PARTIAL_FILLED + accounting evidence ──

def test_dead_residual_taker_partial_returns_terminal_with_accounting_evidence():
    """CONFIRMED taker partial fill (size=4) VAR ve order canonical CANCELED (residual ÖLÜ, FAK
    kalanı öldürülmüş, daha fazla fill imkânsız) → terminal PARTIAL_FILLED DOĞRU (residual-live'ın
    aksine; o RECOVERY_REQUIRED). Final/kesin exposure olduğundan accounting evidence YÜZEYE ÇIKAR:
    matched_size/avg_price/fee_rate_bps/matched_trade_ids/accounting_source (top-level taker trade).
    Discriminator = order.status: LIVE/MATCHED → residual-live; CANCELED → dead-residual.

    Yalnız taker-side, tek trade. Maker-side partial accounting, multi-trade/VWAP, fee amount,
    DB idempotency DIŞINDA (sonraki RED'ler).
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "dead_residual_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    # Dead-residual: status CANCELED (LIVE/MATCHED DEĞİL) + size_matched("4") < original_size("10")
    order = {
        "status": "ORDER_STATUS_CANCELED",
        "original_size": "10",
        "size_matched": "4",
    }

    # Tek CONFIRMED taker partial trade (intent BUY ile uyumlu); evidence kaynağı top-level
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_dead_partial_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "4",
                "price": "0.50",
                "fee_rate_bps": "10",
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Dead-residual → terminal PARTIAL_FILLED (residual-live RECOVERY_REQUIRED dalına DÜŞMEMELİ)
    assert result.state == "PARTIAL_FILLED", \
        f"dead-residual partial terminal PARTIAL_FILLED olmalı: {result.state}"
    assert result.state != "RECOVERY_REQUIRED", \
        f"dead-residual residual-live dalına düşmemeli: {result.state}"

    # Terminal partial accounting evidence (final exposure → güvenle yüzeye çıkar)
    assert result.matched_size == Decimal("4"), \
        f"matched_size confirmed taker partial: {result.matched_size!r}"
    assert result.avg_price == Decimal("0.50"), f"avg_price: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), f"fee_rate_bps (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_dead_partial_1",), \
        f"matched_trade_ids: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"


# ── 10) RED: dead-residual MAKER partial → terminal PARTIAL_FILLED + maker-slot accounting ──

def test_dead_residual_maker_partial_returns_terminal_with_accounting_evidence():
    """CONFIRMED maker-side partial fill (maker slot matched_amount=4) VAR ve order canonical
    CANCELED (residual ÖLÜ) → terminal PARTIAL_FILLED. Accounting evidence top-level POISON
    alanlardan DEĞİL, bizim order_id ile eşleşen maker_orders[] slot'undan gelmeli. Discriminator
    = order.status (LIVE/MATCHED → residual-live RECOVERY_REQUIRED; CANCELED → dead-residual).

    Yalnız maker-side dead-residual partial, tek trade. Taker dead-residual (d36d8f0), residual-live,
    multi-trade/VWAP, fee amount, DB idempotency DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "dead_residual_maker_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    # Dead-residual: status CANCELED (LIVE/MATCHED DEĞİL) + size_matched("4") < original_size("10")
    order = {
        "status": "ORDER_STATUS_CANCELED",
        "original_size": "10",
        "size_matched": "4",
    }

    # Tek CONFIRMED trade: top-level POISON (bizim değil), bizim slot YALNIZ maker_orders[] içinde.
    # taker_order_id bizim değil → taker extractor'a sızmaz; tek doğru kaynak maker slot.
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_dead_maker_partial_1",
                "status": "TRADE_STATUS_CONFIRMED",
                # ── top-level POISON (kör kullanılmamalı) ──
                "taker_order_id": "someone_else_taker_order",
                "side": "SELL",
                "size": "99",
                "price": "0.99",
                "fee_rate_bps": "999",
                # ── bizim slot (tek doğru accounting kaynağı) ──
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "4",
                        "price": "0.50",
                        "fee_rate_bps": "10",
                    },
                ],
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Dead-residual → terminal PARTIAL_FILLED (residual-live RECOVERY_REQUIRED dalına DÜŞMEMELİ)
    assert result.state == "PARTIAL_FILLED", \
        f"dead-residual maker partial terminal PARTIAL_FILLED olmalı: {result.state}"
    assert result.state != "RECOVERY_REQUIRED", \
        f"dead-residual residual-live dalına düşmemeli: {result.state}"

    # Terminal maker partial accounting evidence (maker slot kaynağı)
    assert result.matched_size == Decimal("4"), \
        f"matched_size maker slot matched_amount: {result.matched_size!r}"
    assert result.avg_price == Decimal("0.50"), f"avg_price maker slot price: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), \
        f"fee_rate_bps maker slot (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_dead_maker_partial_1",), \
        f"matched_trade_ids trade-level id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"

    # ── poison-pill regression guard: kaynak top-level DEĞİL, maker slot ──
    assert result.matched_size != Decimal("99"), "top-level size POISON sızdı"
    assert result.avg_price != Decimal("0.99"), "top-level price POISON sızdı"
    assert result.fee_rate_bps != Decimal("999"), "top-level fee_rate_bps POISON sızdı"


# ── 11) RED: multi-trade taker full-fill → VWAP accounting aggregation (tek trade ile yetinme) ──

def test_multi_trade_taker_full_fill_aggregates_vwap_accounting():
    """Aynı taker order için İKİ CONFIRMED trade (size 4 + 6). decide_araf_resolution tek trade
    ile yetinmemeli: toplam size (10) == target → state FILLED; accounting evidence AGGREGATE:
    matched_size = Σsize = 10, avg_price = VWAP = Σ(size·price)/Σsize = (4·0.50+6·0.60)/10 = 0.56,
    matched_trade_ids = data-order'da iki id, accounting_source = CONFIRMED_TRADE.

    fee_rate_bps iki trade'de de "10" (uniform) → fee aggregation bu RED'in DIŞINDA (sonraki RED).
    Yalnız taker-side; maker-side aggregation, dead-residual partial aggregation, farklı-fee/fee
    amount, DB idempotency DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "multi_taker_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    order = {
        "status": "ORDER_STATUS_FILLED",
        "original_size": "10",
        "size_matched": "10",
    }

    # İki CONFIRMED taker trade, aynı order_id; tek trade short-circuit YETMEMELİ
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_multi_taker_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "4",
                "price": "0.50",
                "fee_rate_bps": "10",
            },
            {
                "id": "trade_multi_taker_2",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "6",
                "price": "0.60",
                "fee_rate_bps": "10",
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Birincil: aggregate toplam (10) == target → FILLED (tek-trade short-circuit PARTIAL_FILLED YASAK)
    assert result.state == "FILLED", \
        f"multi-trade toplam fill target → FILLED olmalı (tek trade ile yetinme): {result.state}"

    # Aggregate accounting evidence
    assert result.matched_size == Decimal("10"), \
        f"matched_size = Σsize (4+6): {result.matched_size!r}"
    assert result.avg_price == Decimal("0.56"), \
        f"avg_price = VWAP (4·0.50+6·0.60)/10: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), \
        f"fee_rate_bps uniform (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_multi_taker_1", "trade_multi_taker_2"), \
        f"matched_trade_ids data-order iki id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"


# ── 12) PIN (RED DEĞİL): mixed fee_rate_bps → fee_rate_bps None; size/VWAP/ids/source korunur ──

def test_multi_trade_taker_mixed_fee_rate_yields_none_fee_evidence():
    """PIN / characterization — RED DEĞİLDİR; ilk koşuda PASS beklenir. Mixed-fee→None politikası
    `_aggregate_taker_confirmed_fills` içinde (ef030a0) ZATEN implement edilmiştir. Bu test o kontratı
    KİLİTLER: aynı taker order'ın iki CONFIRMED trade'i FARKLI fee_rate_bps ("10"/"20") taşırsa, tek
    bir fee_rate_bps evidence değeri finansal olarak belirsizdir → fail-safe None. Ancak boyut/fiyat
    muhasebesi fee'den bağımsız: matched_size aggregation + VWAP + trade_ids + source DEVAM eder.

    Bu PIN, maker-side aggregation (aynı fee mantığını çoğaltacak) öncesi sessiz regresyona karşı
    sigorta. Weighted/blended fee, fee_amount, maker-side aggregation, dead-residual partial DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "multi_taker_fee_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    order = {
        "status": "ORDER_STATUS_FILLED",
        "original_size": "10",
        "size_matched": "10",
    }

    # İki CONFIRMED taker trade — size/price multi-trade VWAP fixture'ıyla aynı, YALNIZ fee farklı
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_multi_taker_fee_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "4",
                "price": "0.50",
                "fee_rate_bps": "10",
            },
            {
                "id": "trade_multi_taker_fee_2",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": our_id,
                "side": "BUY",
                "size": "6",
                "price": "0.60",
                "fee_rate_bps": "20",     # ← farklı fee → tek rate belirsiz → None
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # size/fiyat muhasebesi fee'den bağımsız → aggregation DEVAM eder
    assert result.state == "FILLED", f"multi-trade full fill FILLED: {result.state}"
    assert result.matched_size == Decimal("10"), \
        f"matched_size = Σsize (4+6): {result.matched_size!r}"
    assert result.avg_price == Decimal("0.56"), \
        f"avg_price = VWAP (4·0.50+6·0.60)/10: {result.avg_price!r}"
    assert result.matched_trade_ids == ("trade_multi_taker_fee_1", "trade_multi_taker_fee_2"), \
        f"matched_trade_ids data-order iki id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"

    # mixed fee → fail-safe None (blend/first-rate YOK); fee policy kontratı kilitli
    assert result.fee_rate_bps is None, \
        f"mixed fee_rate_bps → None olmalı (belirsiz tek rate iddia edilmez): {result.fee_rate_bps!r}"


# ── 13) RED: multi-trade MAKER full-fill → VWAP accounting aggregation (tek slot ile yetinme) ──

def test_multi_trade_maker_full_fill_aggregates_vwap_accounting():
    """Aynı maker order için İKİ CONFIRMED trade, her birinde bizim maker_orders[] slotumuz
    (matched_amount 4 + 6). decide_araf_resolution tek slot/trade ile yetinmemeli: toplam (10) ==
    target → state FILLED; maker-side accounting AGGREGATE:
    matched_size = Σmatched_amount = 10, avg_price = VWAP = Σ(amount·price)/Σamount = 0.56,
    matched_trade_ids = data-order iki id, accounting_source = CONFIRMED_TRADE. Kaynak top-level
    POISON alanlar DEĞİL, maker slotlar. fee_rate_bps iki slot da "10" (uniform) → Decimal("10").

    fee aggregation policy (mixed→None) taker'da kilitli; bu RED uniform tutar. Yalnız maker-side
    full-fill; taker aggregation (ef030a0), dead-residual partial aggregation, farklı-fee/fee amount,
    trade başına çok slot, DB idempotency DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "multi_maker_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    order = {
        "status": "ORDER_STATUS_FILLED",
        "original_size": "10",
        "size_matched": "10",
    }

    # İki CONFIRMED trade; bizim slot YALNIZ maker_orders[] içinde. top-level POISON (bizim değil).
    # taker_order_id bizim değil → taker aggregate/extractor'a sızmaz; tek doğru kaynak maker slotlar.
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_multi_maker_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": "someone_else_taker_order_1",
                "side": "SELL",
                "size": "99",
                "price": "0.99",
                "fee_rate_bps": "999",
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "4",
                        "price": "0.50",
                        "fee_rate_bps": "10",
                    },
                ],
            },
            {
                "id": "trade_multi_maker_2",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": "someone_else_taker_order_2",
                "side": "SELL",
                "size": "88",
                "price": "0.88",
                "fee_rate_bps": "888",
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "6",
                        "price": "0.60",
                        "fee_rate_bps": "10",
                    },
                ],
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # Birincil: aggregate toplam (10) == target → FILLED (tek-slot short-circuit PARTIAL_FILLED YASAK)
    assert result.state == "FILLED", \
        f"multi-trade maker toplam fill target → FILLED olmalı (tek slot ile yetinme): {result.state}"

    # Aggregate maker accounting evidence (kaynak maker slotlar)
    assert result.matched_size == Decimal("10"), \
        f"matched_size = Σmatched_amount (4+6): {result.matched_size!r}"
    assert result.avg_price == Decimal("0.56"), \
        f"avg_price = maker VWAP (4·0.50+6·0.60)/10: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), \
        f"fee_rate_bps uniform maker slot (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_multi_maker_1", "trade_multi_maker_2"), \
        f"matched_trade_ids data-order iki id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"

    # ── poison-pill regression guard: kaynak top-level DEĞİL, maker slotlar ──
    assert result.matched_size != Decimal("99"), "top-level size POISON sızdı (trade 1)"
    assert result.avg_price != Decimal("0.99"), "top-level price POISON sızdı (trade 1)"
    assert result.fee_rate_bps != Decimal("999"), "top-level fee_rate_bps POISON sızdı (trade 1)"
    assert result.avg_price != Decimal("0.88"), "top-level price POISON sızdı (trade 2)"
    assert result.fee_rate_bps != Decimal("888"), "top-level fee_rate_bps POISON sızdı (trade 2)"


# ── 14) RED: dead-residual MAKER multi-trade partial → terminal PARTIAL_FILLED + VWAP aggregation ──

def test_dead_residual_maker_multi_trade_partial_aggregates_vwap_accounting():
    """CANCELED/dead-residual maker partial: İKİ CONFIRMED trade'de bizim maker slotlarımız
    (matched_amount 2 + 3), toplam 5 < target 10, order ÖLÜ (CANCELED). state PARTIAL_FILLED
    (terminal, residual-live RECOVERY_REQUIRED dalına düşmez) KALIR; ama accounting tek slot ile
    yetinmemeli → AGGREGATE: matched_size = Σmatched_amount = 5, avg_price = maker VWAP =
    Σ(amount·price)/Σamount = (2·0.50+3·0.60)/5 = 0.56, matched_trade_ids = data-order iki id,
    accounting_source = CONFIRMED_TRADE. Kaynak top-level POISON DEĞİL, maker slotlar. fee uniform "10".

    Yalnız maker dead-residual partial aggregation. Taker partial aggregation, residual-live, full-fill
    (b035fab), farklı-fee/fee amount, trade başına çok slot, DB idempotency DIŞINDA.
    """
    from decimal import Decimal
    from data.clob_reconcile import decide_araf_resolution

    our_id = "dead_multi_maker_order_1"

    intent = {
        "order_id": our_id,
        "exchange_order_id": our_id,     # decide_araf_resolution contract bridge
        "side": "BUY",
        "intended_size": "10",
    }

    # Dead-residual: status CANCELED (LIVE/MATCHED DEĞİL) + size_matched("5") < original_size("10")
    order = {
        "status": "ORDER_STATUS_CANCELED",
        "original_size": "10",
        "size_matched": "5",
    }

    # İki CONFIRMED trade; bizim slot YALNIZ maker_orders[] içinde (side="BUY"). top-level POISON.
    # taker_order_id bizim değil → taker aggregate/extractor'a sızmaz; tek doğru kaynak maker slotlar.
    trades = {
        "next_cursor": "LTE=",
        "data": [
            {
                "id": "trade_dead_multi_maker_1",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": "someone_else_dead_taker_1",
                "side": "SELL",
                "size": "99",
                "price": "0.99",
                "fee_rate_bps": "999",
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "2",
                        "price": "0.50",
                        "fee_rate_bps": "10",
                    },
                ],
            },
            {
                "id": "trade_dead_multi_maker_2",
                "status": "TRADE_STATUS_CONFIRMED",
                "taker_order_id": "someone_else_dead_taker_2",
                "side": "SELL",
                "size": "88",
                "price": "0.88",
                "fee_rate_bps": "888",
                "maker_orders": [
                    {
                        "order_id": our_id,
                        "side": "BUY",
                        "matched_amount": "3",
                        "price": "0.60",
                        "fee_rate_bps": "10",
                    },
                ],
            },
        ],
    }

    result = decide_araf_resolution(intent=intent, order=order, trades=trades)

    # State doğru olmalı (residual-live'a düşmez); birincil RED accounting aggregation'da
    assert result.state == "PARTIAL_FILLED", \
        f"dead-residual maker partial terminal PARTIAL_FILLED: {result.state}"
    assert result.state != "RECOVERY_REQUIRED", \
        f"dead-residual residual-live dalına düşmemeli: {result.state}"

    # Aggregate maker partial accounting (tek slot ile yetinme)
    assert result.matched_size == Decimal("5"), \
        f"matched_size = Σmatched_amount (2+3): {result.matched_size!r}"
    assert result.avg_price == Decimal("0.56"), \
        f"avg_price = maker VWAP (2·0.50+3·0.60)/5: {result.avg_price!r}"
    assert result.fee_rate_bps == Decimal("10"), \
        f"fee_rate_bps uniform maker slot (evidence): {result.fee_rate_bps!r}"
    assert result.matched_trade_ids == ("trade_dead_multi_maker_1", "trade_dead_multi_maker_2"), \
        f"matched_trade_ids data-order iki id: {result.matched_trade_ids!r}"
    assert result.accounting_source == "CONFIRMED_TRADE", \
        f"accounting_source: {result.accounting_source!r}"

    # ── poison-pill regression guard: kaynak top-level DEĞİL, maker slotlar ──
    assert result.matched_size != Decimal("99"), "top-level size POISON sızdı (trade 1)"
    assert result.avg_price != Decimal("0.99"), "top-level price POISON sızdı (trade 1)"
    assert result.fee_rate_bps != Decimal("999"), "top-level fee_rate_bps POISON sızdı (trade 1)"
    assert result.avg_price != Decimal("0.88"), "top-level price POISON sızdı (trade 2)"
    assert result.fee_rate_bps != Decimal("888"), "top-level fee_rate_bps POISON sızdı (trade 2)"
