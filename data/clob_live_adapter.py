"""data/clob_live_adapter.py — v0→v1 Live Schema Adapter / ACL (thin, leaf modül).

Canlı `get_trades_paginated` page'ini resolver v0 trades-dict'ine çevirir. Karar kaynağı:
docs/ARAF_PHASE_CLOSEOUT.md §8.4 (kalibrasyon, DÜZELTİLDİ).

Tek zorunlu yapısal dönüşüm: page["trades"] → trades_dict["data"]. next_cursor taşınır (resolver
zero-fill scan-complete kanıtı `next_cursor == "LTE="` için okur). limit/count resolver dict'ine
SIZMAZ (driver/crawler telemetry'si). Trade-level alanlar PASS-THROUGH (rename/status-normalize/
dedupe/sort/collapse YOK; bunlar resolver-owned). maker_orders[] dokunulmadan iletilir.

ACL Decimal/math/fee_amount ÜRETMEZ; numerikler string kalır (Decimal parse resolver-owned).
Yapısal ihlalde `LiveSchemaError` (driver bunu RECOVERY'ye çevirir; resolver'a bozuk dict beslenmez).
Bu modül resolver'ı (data/clob_reconcile.py) IMPORT ETMEZ — leaf, döngüsel bağımlılık yok.
"""


class LiveSchemaError(Exception):
    """Canlı page/trade yapısal kontrat ihlali (dict değil / trades yok / list değil /
    next_cursor yok / trade dict değil). Fail-closed sentineli — çağıran RECOVERY'ye çevirir."""


def adapt_live_trades_page(page: dict) -> dict:
    """Canlı get_trades_paginated page'ini resolver v0 trades-dict'ine çevirir.

    Dönüş: {"data": <page["trades"] pass-through>, "next_cursor": <page["next_cursor"]>}.
    limit/count düşürülür. Yapısal ihlalde LiveSchemaError. Decimal/muhasebe/normalize YOK.
    """
    if not isinstance(page, dict):
        raise LiveSchemaError("page is not a dict")
    if "trades" not in page:
        raise LiveSchemaError("page missing 'trades'")
    if "next_cursor" not in page:
        raise LiveSchemaError("page missing 'next_cursor'")
    trades = page["trades"]
    if not isinstance(trades, list):
        raise LiveSchemaError("page['trades'] is not a list")
    for tr in trades:
        if not isinstance(tr, dict):
            raise LiveSchemaError("trade element is not a dict")
    return {"data": trades, "next_cursor": page["next_cursor"]}
