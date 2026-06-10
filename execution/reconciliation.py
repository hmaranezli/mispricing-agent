"""execution/reconciliation.py — Faz 2c-1: get_trades → intent akıbeti (saf karar fonksiyonu).

Statik ±tick tolerance YASAK → DIRECTIONAL:
  TAKER_BUY  : executed_price <= intended_limit  (daha kötüsünü ödemeyiz → fazlası bizim değil)
  TAKER_SELL : executed_price >= intended_limit  (daha azına satmayız → azı bizim değil)
AGGREGATE: aynı token+side+window içindeki directional-pass trade'leri grupla (toplam size,
weighted-avg). DEDUP: matched_trade_ids → double-count YOK (periyodik reconcile güvenli).
AMBIGUOUS (çoklu-grup / FAZLA-fill > intended) → RECOVERY_REQUIRED + emergency_pause.
get_trades şeması ham dict (canlı sample = live-blocker; burada fixture-contract).
Float YASAK → Decimal.
"""
from decimal import Decimal


def _side_match(intent_side: str, trade_side: str) -> bool:
    ts = (trade_side or "").upper()
    return (intent_side == "TAKER_BUY" and ts == "BUY") or \
           (intent_side == "TAKER_SELL" and ts == "SELL")


def _directional_ok(intent_side: str, exec_price: Decimal, limit: Decimal) -> bool:
    if intent_side == "TAKER_BUY":
        return exec_price <= limit       # alış: limit'ten pahalıya fill bizim değil
    if intent_side == "TAKER_SELL":
        return exec_price >= limit       # satış: limit'ten ucuza fill bizim değil
    return False


def reconcile_intent(intent, candidate_trades, now_ts, window_s=60):
    """intent + get_trades adayları → karar dict.
    Returns: {state, executed_size(Decimal), avg_price(Decimal|None), matched_trade_ids,
              reason, emergency_pause(bool)}.
    """
    side = intent["side"]
    limit = Decimal(str(intent["intended_price"]))
    intended = Decimal(str(intent["intended_size"]))
    token = intent["market_token_id"]
    intent_ts = intent["intent_timestamp"]
    already = set(intent.get("matched_trade_ids") or [])

    matched_ids = []
    total_size = Decimal("0")
    weighted_notional = Decimal("0")
    for tr in candidate_trades:
        tid = tr.get("trade_id")
        if tid in already:
            continue                                   # DEDUP → double-count YOK
        if tr.get("asset_id") != token:
            continue
        if not _side_match(side, tr.get("side")):
            continue
        t = tr.get("match_time")
        if t is None or t < intent_ts or (t - intent_ts) > window_s:
            continue                                   # time window (dar)
        price = Decimal(str(tr.get("price")))
        size = Decimal(str(tr.get("size")))
        if size <= 0:
            continue
        if not _directional_ok(side, price, limit):
            continue                                   # directional-fail → bizim değil, elenir
        matched_ids.append(tid)
        total_size += size
        weighted_notional += price * size

    avg_price = (weighted_notional / total_size).quantize(Decimal("0.0001")) \
        if total_size > 0 else None

    # AMBIGUOUS: FAZLA fill (toplam > intended) → bizim olmayan trade karışmış → RECOVERY
    if total_size > intended:
        return {"state": "RECOVERY_REQUIRED", "executed_size": total_size,
                "avg_price": avg_price, "matched_trade_ids": matched_ids,
                "reason": "ambiguous_overfill", "emergency_pause": True}

    if total_size >= intended:                         # == intended (üstü yukarıda yakalandı)
        return {"state": "FILLED", "executed_size": total_size, "avg_price": avg_price,
                "matched_trade_ids": matched_ids, "reason": None, "emergency_pause": False}

    if total_size > 0:                                 # 0 < toplam < intended
        return {"state": "PARTIAL_FILLED", "executed_size": total_size, "avg_price": avg_price,
                "matched_trade_ids": matched_ids, "reason": None, "emergency_pause": False}

    # aday yok: window doldu → CANCELLED (FAK ölü); devam → bekle (SUBMITTED_UNKNOWN)
    if (now_ts - intent_ts) > window_s:
        return {"state": "CANCELLED", "executed_size": Decimal("0"), "avg_price": None,
                "matched_trade_ids": [], "reason": "no_fill_window_expired", "emergency_pause": False}
    return {"state": "SUBMITTED_UNKNOWN", "executed_size": Decimal("0"), "avg_price": None,
            "matched_trade_ids": [], "reason": "awaiting_fill", "emergency_pause": False}
