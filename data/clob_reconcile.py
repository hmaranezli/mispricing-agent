"""data/clob_reconcile.py — Faz 2c-4 Araf-Intent Resolution (dual-oracle, saf karar fonksiyonu).

Dual-oracle: get_order = lifecycle kanıtı, get_trades = settlement/accounting kanıtı.
ÇEKİRDEK INVARIANT: CONFIRMED trade kanıtı olmadan FILLED/PARTIAL_FILLED/CANCELLED YAZILMAZ;
order MATCHED / size_matched>0 olsa bile terminal muhasebe yapılmaz (anti-hallucination).

Bu dosya YALNIZ saf karar mantığıdır — gerçek CLOB client, pagination, rate-limit ve DB write
path BURADA YOK (sonraki TDD adımları). Fixture-contract v0 (canlı Polymarket sample henüz yok =
live-blocker); alan adları/tipleri/status enum'ları gerçek örnekle doğrulanana kadar varsayımdır.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class ResolutionResult:
    """Araf-intent reconcile kararı. `state` non-terminal (fail-closed) veya CONFIRMED kanıtıyla
    terminal (FILLED/PARTIAL_FILLED) olabilir. Price/fee tam muhasebesi sonraki TDD adımlarında."""
    state: str


def _norm_status(raw) -> str:
    """ORDER_STATUS_* / TRADE_STATUS_* prefix'lerini sıyır → canonical UPPER (örn. MATCHED,
    MINED, RETRYING, CONFIRMED, LIVE, CANCELED). Bilinmeyen değer olduğu gibi UPPER döner →
    çağıran fail-closed davranır (tanımadığımızı terminal saymayız)."""
    s = str(raw or "").strip().upper()
    for prefix in ("ORDER_STATUS_", "TRADE_STATUS_"):
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def _norm_side(raw) -> str:
    """Side normalize: strip + UPPER + TAKER_/MAKER_ prefix toleransı → BUY/SELL."""
    s = str(raw or "").strip().upper()
    for prefix in ("TAKER_", "MAKER_"):
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def _find_confirmed_fill(trades, our_order_id):
    """get_trades sayfasında, bizim order_id'mizle eşleşen ilk CONFIRMED trade için fill bilgisi
    döner: (slot, fill_side, matched_amount). Önce `taker_order_id` (bizim FAK taker), sonra
    `maker_orders[].order_id`. Maker eşleşmesinde top-level side/size KÖR kullanılmaz — maker
    slot'un kendi side/matched_amount'u alınır. Eşleşme yoksa None."""
    for tr in (trades or {}).get("data", []) or []:
        if _norm_status(tr.get("status")) != "CONFIRMED":
            continue
        if tr.get("taker_order_id") == our_order_id:
            return ("taker", tr.get("side"), tr.get("size"))
        for m in (tr.get("maker_orders") or []):
            if (m or {}).get("order_id") == our_order_id:
                return ("maker", (m or {}).get("side"), (m or {}).get("matched_amount"))
    return None


def decide_araf_resolution(intent, order, trades) -> ResolutionResult:
    """Araf intent için dual-oracle kararı (saf, I/O yok). `intent`/`order`/`trades` önceden
    çekilmiş ham dict'ler (client/pagination ayrı katman = sonraki adım).

    Davranış (v0):
      - CONFIRMED trade kanıtı YOKSA → terminal DÖNME → fail-closed `RECOVERY_REQUIRED`.
      - CONFIRMED + order_id eşleşme VARSA → fill side (taker→top-level, maker→maker slot) intent
        side ile doğrulanır; uyuşmazsa fail-closed. Decimal full/partial: matched == original_size
        → FILLED, 0 < matched < original → PARTIAL_FILLED. Parse edilemeyen amount → fail-closed.
      - Price/fee tam muhasebesi, zero-fill cancel, pagination, dedupe, DB write: SONRAKİ adımlar.
    """
    our_order_id = intent.get("exchange_order_id")
    match = _find_confirmed_fill(trades, our_order_id)
    if match is None:
        # CONFIRMED settlement kanıtı yok → muhasebe yapılamaz → araf devam (fail-closed)
        return ResolutionResult(state="RECOVERY_REQUIRED")

    _slot, fill_side, matched_amount = match

    # Yön doğrulama: top-level side KÖR değil; eşleşen slot'un side'ı intent side ile tutmalı
    if _norm_side(fill_side) != _norm_side(intent.get("side")):
        return ResolutionResult(state="RECOVERY_REQUIRED")

    # Decimal full/partial — string varyantlarına ("10" / "10.0" / "10.000000") karşı korumalı
    target_raw = order.get("original_size")
    if target_raw is None:
        target_raw = intent.get("intended_size", intent.get("original_size"))
    try:
        filled = Decimal(str(matched_amount))
        target = Decimal(str(target_raw))
    except (InvalidOperation, TypeError, ValueError):
        # Sayı parse edilemedi → terminal yazma, güvenli non-terminal
        return ResolutionResult(state="RECOVERY_REQUIRED")

    if filled <= 0:
        return ResolutionResult(state="RECOVERY_REQUIRED")
    if target > 0 and filled == target:
        return ResolutionResult(state="FILLED")
    return ResolutionResult(state="PARTIAL_FILLED")
