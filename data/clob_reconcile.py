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
    terminal (FILLED/PARTIAL_FILLED) olabilir.

    Accounting evidence alanları (opsiyonel, geriye uyumlu — non-fill state'lerde None):
      - matched_size / avg_price / fee_rate_bps: Decimal (float yok). fee_rate_bps EVIDENCE'tir,
        fee AMOUNT değil (amount formülü canlı contract netleşince ayrı RED).
      - matched_trade_ids: dedupe için kanıt (driver/DB sorumluluğu); accounting_source kaynak işareti.
    """
    state: str
    matched_size: Decimal | None = None
    avg_price: Decimal | None = None
    fee_rate_bps: Decimal | None = None
    matched_trade_ids: tuple | None = None
    accounting_source: str | None = None


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


def _has_any_order_trace(trades, our_order_id) -> bool:
    """trades.data içinde bizim order_id'mize ait (STATUS'TAN BAĞIMSIZ) herhangi bir trade izi var
    mı? taker_order_id / maker_orders[].order_id / (fixture-contract v0 desteği) top-level order_id.
    Bozuk/eksik yapıda EXCEPTION fırlatmaz: None trade/maker güvenle atlanır.

    Güvenli True/False: yalnız NET eşleşmede True; eşleşme yoksa False ("olmayan iz" uydurulmaz).
    Çağıran (zero-fill cancel evidence) fail-closed kullanır → iz VARSA clean cancel SAYILMAZ.
    CONFIRMED bunun alt kümesidir; bu guard status'tan bağımsız tüm izleri bloklar.
    """
    for tr in (trades or {}).get("data", []) or []:
        tr = tr or {}
        if tr.get("taker_order_id") == our_order_id:
            return True
        if any((m or {}).get("order_id") == our_order_id
               for m in (tr.get("maker_orders") or [])):
            return True
        if tr.get("order_id") == our_order_id:     # v0 desteği — yalnız order-trace block için
            return True
    return False


def _extract_taker_accounting_evidence(trades, our_order_id):
    """Tek CONFIRMED TAKER trade için accounting evidence (top-level alanlar) → dict, yoksa None.
    KAPSAM: yalnız taker-side, tek trade. Maker-side / multi-trade / VWAP DAHİL DEĞİL (sonraki RED).
    Saf — I/O yok. size/price Decimal zorunlu (parse fail → None); fee_rate_bps opsiyonel Decimal
    (yok/parse fail → None, evidence düşmez). fee AMOUNT hesaplanmaz, yalnız rate evidence taşınır."""
    for tr in (trades or {}).get("data", []) or []:
        tr = tr or {}
        if _norm_status(tr.get("status")) != "CONFIRMED":
            continue
        if tr.get("taker_order_id") != our_order_id:
            continue
        try:
            matched_size = Decimal(str(tr.get("size")))
            avg_price = Decimal(str(tr.get("price")))
        except (InvalidOperation, TypeError, ValueError):
            return None
        fee_raw = tr.get("fee_rate_bps")
        try:
            fee_rate_bps = None if fee_raw is None else Decimal(str(fee_raw))
        except (InvalidOperation, TypeError, ValueError):
            fee_rate_bps = None
        return {
            "matched_size": matched_size,
            "avg_price": avg_price,
            "fee_rate_bps": fee_rate_bps,
            "matched_trade_ids": (str(tr.get("id")),),
            "accounting_source": "CONFIRMED_TRADE",
        }
    return None


def _extract_maker_accounting_evidence(trades, our_order_id):
    """Tek CONFIRMED trade'in bizim order_id'mizle eşleşen maker_orders[] SLOT'undan accounting
    evidence (nested maker alanları) → dict, yoksa None. KAPSAM: yalnız maker-side, tek slot.
    Multi-trade / aynı trade'de birden fazla bizim maker slot / VWAP DAHİL DEĞİL (sonraki RED).
    Saf — I/O yok. matched_amount/price Decimal zorunlu (parse fail → None); fee_rate_bps opsiyonel
    Decimal (yok/parse fail → None, evidence düşmez). Top-level trade size/price/fee/side KÖR
    KULLANILMAZ — kaynak yalnız eşleşen maker slot. fee AMOUNT hesaplanmaz, yalnız rate evidence."""
    for tr in (trades or {}).get("data", []) or []:
        tr = tr or {}
        if _norm_status(tr.get("status")) != "CONFIRMED":
            continue
        for m in (tr.get("maker_orders") or []):
            m = m or {}
            if m.get("order_id") != our_order_id:
                continue
            try:
                matched_size = Decimal(str(m.get("matched_amount")))
                avg_price = Decimal(str(m.get("price")))
            except (InvalidOperation, TypeError, ValueError):
                return None
            fee_raw = m.get("fee_rate_bps")
            try:
                fee_rate_bps = None if fee_raw is None else Decimal(str(fee_raw))
            except (InvalidOperation, TypeError, ValueError):
                fee_rate_bps = None
            return {
                "matched_size": matched_size,
                "avg_price": avg_price,
                "fee_rate_bps": fee_rate_bps,
                "matched_trade_ids": (str(tr.get("id")),),
                "accounting_source": "CONFIRMED_TRADE",
            }
    return None


def _aggregate_taker_confirmed_fills(trades, our_order_id):
    """Bizim TÜM CONFIRMED taker fill'lerimizi (taker_order_id == our_order_id) topla → aggregate
    accounting evidence dict, yoksa None. KAPSAM: yalnız taker-side; maker_orders[] OKUNMAZ.
      - matched_size = Σsize, avg_price = VWAP = Σ(size·price)/Σsize, matched_trade_ids = data-order tuple.
      - fee_rate_bps: TÜM trade'ler aynı parseable rate ise o Decimal; aksi halde None (farklı-fee
        policy SONRAKİ RED — burada blend/weight YOK).
    Herhangi size/price parse fail veya total_size ≤ 0 → fail-closed None. Saf — I/O yok; next_cursor/
    scan davranışına dokunmaz. Tek trade'de single-helper ile aynı sonucu verir (Decimal-only).

    IDENTICAL-duplicate dedup: aynı scan payload'ı içinde BİREBİR AYNI satır (id+status+taker_order_id+
    side+size+price+fee_rate_bps) tekrar görünürse (pagination overlap yankısı) BİR KEZ sayılır.
    Conflicting duplicate (aynı id, FARKLI payload) farklı identity → dedup EDİLMEZ (fail-closed policy
    SONRAKİ RED). DB run-arası idempotency burada YOK (matched_trade_ids dedup anahtarı driver/DB'ye)."""
    sizes_prices = []
    ids = []
    fee_raws = []
    seen = set()
    for tr in (trades or {}).get("data", []) or []:
        tr = tr or {}
        if _norm_status(tr.get("status")) != "CONFIRMED":
            continue
        if tr.get("taker_order_id") != our_order_id:
            continue
        # Identical-duplicate skip: birebir aynı taker satırı ikinci kez sayılmaz (ham alanlar)
        identity = (str(tr.get("id")), tr.get("status"), tr.get("taker_order_id"),
                    tr.get("side"), tr.get("size"), tr.get("price"), tr.get("fee_rate_bps"))
        if identity in seen:
            continue
        seen.add(identity)
        try:
            size = Decimal(str(tr.get("size")))
            price = Decimal(str(tr.get("price")))
        except (InvalidOperation, TypeError, ValueError):
            return None
        sizes_prices.append((size, price))
        ids.append(str(tr.get("id")))
        fee_raws.append(tr.get("fee_rate_bps"))

    if not sizes_prices:
        return None
    total_size = sum((sp[0] for sp in sizes_prices), Decimal("0"))
    if total_size <= 0:
        return None
    total_notional = sum((sp[0] * sp[1] for sp in sizes_prices), Decimal("0"))
    avg_price = total_notional / total_size     # VWAP — keyfi quantize YOK

    # fee: yalnız uniform parseable rate → o rate; herhangi eksik/parse-fail/farklı → None (policy YOK)
    fee_rate_bps = None
    parsed_fees = []
    uniform = True
    for fr in fee_raws:
        if fr is None:
            uniform = False
            break
        try:
            parsed_fees.append(Decimal(str(fr)))
        except (InvalidOperation, TypeError, ValueError):
            uniform = False
            break
    if uniform and parsed_fees and len(set(parsed_fees)) == 1:
        fee_rate_bps = parsed_fees[0]

    return {
        "matched_size": total_size,
        "avg_price": avg_price,
        "fee_rate_bps": fee_rate_bps,
        "matched_trade_ids": tuple(ids),
        "accounting_source": "CONFIRMED_TRADE",
    }


def _aggregate_maker_confirmed_fills(trades, our_order_id):
    """Bizim TÜM CONFIRMED maker slotlarımızı (maker_orders[].order_id == our_order_id) topla →
    aggregate accounting evidence dict, yoksa None. KAPSAM: yalnız maker-side; top-level trade
    size/price/fee_rate_bps / taker_order_id OKUNMAZ.
      - matched_size = Σmatched_amount, avg_price = VWAP = Σ(matched_amount·price)/Σmatched_amount,
        matched_trade_ids = data-order tuple (eşleşen maker slot başına trade id).
      - fee_rate_bps: TÜM slotlar aynı parseable rate ise o Decimal; aksi halde None (farklı-fee
        policy SONRAKİ konu — burada blend/weight YOK).
    Herhangi matched_amount/price parse fail veya total ≤ 0 → fail-closed None. Saf — I/O yok;
    next_cursor/scan davranışına dokunmaz. Tek slot'ta single-helper ile aynı sonucu verir.
    Bu RED: trade başına ≤1 eşleşen maker slot varsayımı (multi-slot-per-trade dedup KAPSAM DIŞI).

    IDENTICAL-duplicate dedup (taker simetriği): aynı scan payload'ı içinde BİREBİR AYNI maker katkısı
    (top-level id+status+taker_order_id + slot order_id+side+matched_amount+price+fee_rate_bps) tekrar
    görünürse (pagination overlap yankısı) BİR KEZ sayılır. Conflicting duplicate (aynı id, FARKLI
    payload) farklı identity → dedup EDİLMEZ (fail-closed policy SONRAKİ RED). DB run-arası idempotency
    burada YOK (matched_trade_ids dedup anahtarı driver/DB'ye)."""
    amounts_prices = []
    ids = []
    fee_raws = []
    seen = set()
    for tr in (trades or {}).get("data", []) or []:
        tr = tr or {}
        if _norm_status(tr.get("status")) != "CONFIRMED":
            continue
        for m in (tr.get("maker_orders") or []):
            m = m or {}
            if m.get("order_id") != our_order_id:
                continue
            # Identical-duplicate skip: birebir aynı maker katkısı ikinci kez sayılmaz (ham alanlar)
            identity = (str(tr.get("id")), tr.get("status"), tr.get("taker_order_id"),
                        m.get("order_id"), m.get("side"), m.get("matched_amount"),
                        m.get("price"), m.get("fee_rate_bps"))
            if identity in seen:
                continue
            seen.add(identity)
            try:
                amount = Decimal(str(m.get("matched_amount")))
                price = Decimal(str(m.get("price")))
            except (InvalidOperation, TypeError, ValueError):
                return None
            amounts_prices.append((amount, price))
            ids.append(str(tr.get("id")))
            fee_raws.append(m.get("fee_rate_bps"))

    if not amounts_prices:
        return None
    total_size = sum((ap[0] for ap in amounts_prices), Decimal("0"))
    if total_size <= 0:
        return None
    total_notional = sum((ap[0] * ap[1] for ap in amounts_prices), Decimal("0"))
    avg_price = total_notional / total_size     # maker VWAP — keyfi quantize YOK

    fee_rate_bps = None
    parsed_fees = []
    uniform = True
    for fr in fee_raws:
        if fr is None:
            uniform = False
            break
        try:
            parsed_fees.append(Decimal(str(fr)))
        except (InvalidOperation, TypeError, ValueError):
            uniform = False
            break
    if uniform and parsed_fees and len(set(parsed_fees)) == 1:
        fee_rate_bps = parsed_fees[0]

    return {
        "matched_size": total_size,
        "avg_price": avg_price,
        "fee_rate_bps": fee_rate_bps,
        "matched_trade_ids": tuple(ids),
        "accounting_source": "CONFIRMED_TRADE",
    }


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

    # Multi-trade taker full-fill (aggregate): bizim TÜM CONFIRMED taker fill'lerimizin TOPLAMI
    # target'a EŞİTSE → FILLED + VWAP aggregate accounting. State kararı tek trade ile değil toplam
    # fill ile verilir. YALNIZ taker slot + full-fill; partial/dead-residual ve maker aggregation
    # KAPSAM DIŞI (toplam ≠ target ise erken-return atlanır, eski tek-trade davranışı aynen sürer).
    # Tek trade'de aggregate = single sonuç → mevcut taker full-fill testi birebir korunur.
    if _slot == "taker" and target > 0:
        taker_agg = _aggregate_taker_confirmed_fills(trades, our_order_id)
        if taker_agg is not None and taker_agg["matched_size"] == target:
            return ResolutionResult(
                state="FILLED",
                matched_size=taker_agg["matched_size"],
                avg_price=taker_agg["avg_price"],
                fee_rate_bps=taker_agg["fee_rate_bps"],
                matched_trade_ids=taker_agg["matched_trade_ids"],
                accounting_source=taker_agg["accounting_source"],
            )

    # Multi-trade MAKER full-fill (aggregate): taker'a simetrik. Bizim TÜM CONFIRMED maker
    # slotlarımızın matched_amount TOPLAMI target'a EŞİTSE → FILLED + maker VWAP aggregate accounting
    # (kaynak maker slotlar, top-level KÖR değil). YALNIZ maker slot + full-fill; toplam ≠ target ise
    # atlanır (eski tek-slot davranışı sürer). Tek slot'ta aggregate = single → maker full-fill testi
    # birebir korunur. Partial/dead-residual ve taker aggregation KAPSAM DIŞI.
    if _slot == "maker" and target > 0:
        maker_agg = _aggregate_maker_confirmed_fills(trades, our_order_id)
        if maker_agg is not None and maker_agg["matched_size"] == target:
            return ResolutionResult(
                state="FILLED",
                matched_size=maker_agg["matched_size"],
                avg_price=maker_agg["avg_price"],
                fee_rate_bps=maker_agg["fee_rate_bps"],
                matched_trade_ids=maker_agg["matched_trade_ids"],
                accounting_source=maker_agg["accounting_source"],
            )

    if target > 0 and filled == target:
        # Full fill → Decimal accounting evidence. Önce taker (top-level alanlar) yolu KORUNUR;
        # taker evidence yoksa maker slot (nested) evidence denenir. İkisi de yoksa accounting None
        # ile FILLED (mevcut fallback davranışı bozulmaz). Top-level değerler maker için KÖR değil.
        ev = _extract_taker_accounting_evidence(trades, our_order_id)
        if ev is None:
            ev = _extract_maker_accounting_evidence(trades, our_order_id)
        if ev is not None:
            return ResolutionResult(
                state="FILLED",
                matched_size=ev["matched_size"],
                avg_price=ev["avg_price"],
                fee_rate_bps=ev["fee_rate_bps"],
                matched_trade_ids=ev["matched_trade_ids"],
                accounting_source=ev["accounting_source"],
            )
        return ResolutionResult(state="FILLED")

    # Residual-live partial: confirmed 0 < filled < target VE order borsada hâlâ açık
    # (canonical LIVE/MATCHED) → residual kitapta, daha fazla dolabilir. PARTIAL_FILLED ∈
    # TERMINAL_STATES (terminal sonrası transition strict blok) olduğundan burada terminal
    # YAZILMAZ; fail-closed non-terminal RECOVERY_REQUIRED (araf takipte kalır). FAK için
    # residual-live = invariant breach. Accounting evidence yüzeye ÇIKMAZ (None) — non-terminal
    # partial accounting + DB idempotency AYRI adım. (PARTIAL_FILLED terminal tanımı DEĞİŞMEZ.)
    if filled < target and _norm_status(order.get("status")) in ("LIVE", "MATCHED"):
        return ResolutionResult(state="RECOVERY_REQUIRED")

    # Dead-residual partial (FAK kalanı öldü: order canonical CANCELED/CANCELLED vb.) → terminal
    # PARTIAL_FILLED. Final/kesin exposure olduğundan accounting evidence yüzeye çıkar. Önce taker
    # AGGREGATE (top-level alanlar, çok trade toplamı = taker VWAP) KORUNUR; taker yoksa maker slot
    # AGGREGATE (nested, çok trade/slot toplamı = maker VWAP). İkisi de yoksa eski davranış katı
    # korunur: PARTIAL_FILLED, accounting None. Nuisance maker_orders taker yolunda OKUNMAZ; top-level
    # değerler maker yolunda KÖR değil. Tek-trade/slot'ta aggregate = single → mevcut dead-residual
    # taker/maker single testleri bozulmaz. (Full-fill early-return ve residual-live guard'a dokunulmaz.)
    ev = _aggregate_taker_confirmed_fills(trades, our_order_id)
    if ev is None:
        ev = _aggregate_maker_confirmed_fills(trades, our_order_id)
    if ev is not None:
        return ResolutionResult(
            state="PARTIAL_FILLED",
            matched_size=ev["matched_size"],
            avg_price=ev["avg_price"],
            fee_rate_bps=ev["fee_rate_bps"],
            matched_trade_ids=ev["matched_trade_ids"],
            accounting_source=ev["accounting_source"],
        )
    return ResolutionResult(state="PARTIAL_FILLED")


_CANONICAL_CANCEL_STATUSES = ("CANCELED", "CANCELLED")  # iki yazım da kabul; compare'de tek canonical


def _zero_fill_cancel_evidence(intent_order_id, obs):
    """obs = {"order": {...}, "trades": {...}} tek gözlemini "canonical zero-fill cancel" açısından
    doğrular. Geçerliyse stabilite kıyası için kanıt tuple'ı döner, değilse None.

    Geçerlilik: order_id eşleşir; status canonical cancel (CANCELED/CANCELLED); size_matched
    Decimal("0"); trades.next_cursor == "LTE=" (scan complete); order_id'mizle CONFIRMED trade YOK.
    Saf — I/O yok. associate_trades dolu olması TEK BAŞINA fail değildir (CONFIRMED yokluğu esas).
    """
    order = (obs or {}).get("order") or {}
    trades = (obs or {}).get("trades") or {}
    if order.get("order_id") != intent_order_id:
        return None
    if _norm_status(order.get("status")) not in _CANONICAL_CANCEL_STATUSES:
        return None
    try:
        size_matched = Decimal(str(order.get("size_matched")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if size_matched != Decimal("0"):
        return None
    if trades.get("next_cursor") != "LTE=":
        return None
    # Bizim order_id'mize ait HERHANGİ trade izi (status'tan bağımsız: unconfirmed dahil) varsa
    # clean zero-fill cancel SAYILMAZ — pending iz fill'e dönüşebilir (CONFIRMED bunun alt kümesi).
    if _has_any_order_trace(trades, intent_order_id):
        return None
    # CANCELED/CANCELLED tek canonical'a indirgenir → yazım farkı instabilite SAYILMAZ
    return (intent_order_id, "CANCELED", size_matched, "LTE=", True)


def decide_zero_fill_cancel_with_stability(intent, first_obs, second_obs) -> ResolutionResult:
    """Zero-fill cancel için eventual-consistency guard'lı saf karar (I/O yok). İKİ bağımsız gözlem
    (driver tarafından zaman aralığıyla çekilmiş) açık input olarak taşınır — gizli state/saat YOK.

    CANCELLED yalnız İKİ gözlem de canonical zero-fill cancel iken VE birbirleriyle stabil
    (özdeş kanıt) iken döner. Aksi halde fail-closed RECOVERY_REQUIRED. Position/fill accounting
    YAPMAZ — yalnız order_intent state kararı (zero-fill = dolan yok = muhasebe yok).
    """
    if second_obs is None:
        return ResolutionResult(state="RECOVERY_REQUIRED")     # tek gözlem → terminal yok
    intent_order_id = intent.get("order_id")
    if not intent_order_id:
        return ResolutionResult(state="RECOVERY_REQUIRED")

    ev1 = _zero_fill_cancel_evidence(intent_order_id, first_obs)
    ev2 = _zero_fill_cancel_evidence(intent_order_id, second_obs)
    if ev1 is None or ev2 is None:
        return ResolutionResult(state="RECOVERY_REQUIRED")     # biri canonical değil → fail-closed
    if ev1 != ev2:
        return ResolutionResult(state="RECOVERY_REQUIRED")     # instabilite → fail-closed

    return ResolutionResult(state="CANCELLED")
