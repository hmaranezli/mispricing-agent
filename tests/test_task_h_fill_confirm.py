"""tests/test_task_h_fill_confirm.py — Faz 2c Task H2: classify_fak_fill (saf fonksiyon).

classify_fak_fill = FAK BUY response → karar nesnesi. USD-denominated (D1), cost yoksa
position yok (D3), resting/open = FAK invariant breach (D2/D6). SAF fonksiyon — DB read/write
YOK, execute() wiring YOK, recovery/emergency_pause çağrısı YOK.

RED turu: fonksiyon stub (`raise NotImplementedError`); GREEN davranışı henüz yazılmadı.
"""
from decimal import Decimal

import pytest

from execution.order_intent import classify_fak_fill as C


# 1) FULL_FILL — USD bazında: making (harcanan) requested'i karşılıyor → FILLED
def test_full_fill_usd_denominated():
    d = C(status="matched", taking_amount="71.43", making_amount="25.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_FILLED" and d["state"] == "FILLED"
    assert d["shares"] == Decimal("71.43")          # shares AYRI korunur (takingAmount'tan)
    assert d["spent_usd"] == Decimal("25.00")
    assert d["fill_price"] == (Decimal("25.00") / Decimal("71.43")).quantize(Decimal("0.000001"))


# 2) PARTIAL_FILL — 0 < making < requested → PARTIAL; taking USD gibi yorumlanmaz
def test_partial_fill_usd_denominated():
    d = C(status="matched", taking_amount="40.00", making_amount="14.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED"
    assert d["shares"] == Decimal("40.00") and d["spent_usd"] == Decimal("14.00")


# 3a) NO_FILL — taking=0, order_id YOK → terminal CANCELLED (FAK_ZERO_FILL), position yok
def test_zero_fill_no_order_id_is_terminal_cancelled():
    d = C(status="unmatched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id=None)
    assert d["kind"] == "TERMINAL_ZERO" and d["state"] == "CANCELLED"
    assert d["reason"] == "FAK_ZERO_FILL"


# 3b) NO_FILL_PROOF — order_id/accepted var ama fill kanıtı yok → bloklayıcı, position SİNYALİ YOK
def test_zero_fill_with_order_id_blocks_submitted_unknown():
    d = C(status="matched", taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id="ord-x")
    assert d["kind"] == "BLOCK_UNKNOWN" and d["state"] == "SUBMITTED_UNKNOWN"
    assert d["kind"] not in ("OPEN_FILLED", "OPEN_PARTIAL")   # position açma sinyali DEĞİL


# 4) COST_MISSING — shares var ama making/cost yok → RECOVERY (FILL_COST_MISSING); cost UYDURULMAZ
def test_shares_present_but_cost_missing_is_recovery():
    d = C(status="matched", taking_amount="40.00", making_amount=None,
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
    assert d["reason"] == "FILL_COST_MISSING"
    assert d["shares"] == Decimal("40.00")
    assert d["spent_usd"] is None                            # cost UYDURULMAZ


# 5) BREACH/INVARIANT — live/delayed/open/resting → recovery/blocking; recovery ÇAĞRILMAZ (saf)
@pytest.mark.parametrize("st", ["live", "delayed", "open", "resting"])
def test_resting_status_is_invariant_breach_recovery(st):
    d = C(status=st, taking_amount="0", making_amount="0",
          requested_usd="25.00", order_id="ord-x")
    assert d["kind"] == "RECOVERY" and d["state"] == "RECOVERY_REQUIRED"
    assert "INVARIANT_BREACH" in d["reason"]
    assert d["kind"] not in ("OPEN_FILLED", "OPEN_PARTIAL")  # filled SAYILMAZ


# 6) SHARES_VS_USD CONFUSION — büyük taking full fill yapmaz; karar making(USD) ile verilir
def test_large_shares_small_cost_is_partial_not_full():
    # 1000 shares dolu ama yalnız 10 USD harcandı, requested 25 USD → USD bazında PARTIAL
    d = C(status="matched", taking_amount="1000.0", making_amount="10.00",
          requested_usd="25.00", order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED", (
        "büyük takingAmount FILLED yapmamalı — karar makingAmount(USD) ile verilmeli")
    assert d["shares"] == Decimal("1000.0")     # shares korunur
    assert d["spent_usd"] == Decimal("10.00")   # ama tamlık USD bazında PARTIAL


# 7) TYPE SAFETY — parasal alanlar Decimal döner (float DEĞİL)
def test_monetary_fields_are_decimal_not_float():
    d = C(status="matched", taking_amount="40.00", making_amount="14.00",
          requested_usd="25.00", order_id="ord")
    for k in ("shares", "spent_usd", "fill_price"):
        assert isinstance(d[k], Decimal), f"{k} Decimal olmalı, float DEĞİL: {type(d[k])}"
        assert not isinstance(d[k], float)
    # Exact Decimal aritmetiği: 14.00/40.00 = 0.35 → quantize 0.350000
    assert d["fill_price"] == Decimal("0.350000")


# ── Ek RED turu: rounding/tolerance (epsilon) davranışı ──────────────────────

# 8) Near-full fill tolerance: making requested'e çok yakın (tolerans içinde) → FULL_FILL
def test_near_full_fill_within_tolerance_is_full():
    d = C(status="filled", taking_amount="28.57", making_amount=Decimal("9.99999999"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_FILLED" and d["state"] == "FILLED", (
        "tolerans içindeki near-full (9.99999999/10.00) FULL_FILL sayılmalı")
    assert d["spent_usd"] == Decimal("9.99999999")


# 9) Real partial must remain partial: making tolerans ALTINDA → PARTIAL_FILL
def test_real_partial_below_tolerance_stays_partial():
    d = C(status="filled", taking_amount="28.28", making_amount=Decimal("9.90"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_PARTIAL" and d["state"] == "PARTIAL_FILLED", (
        "tolerans altındaki gerçek partial (9.90/10.00) PARTIAL kalmalı")
    assert d["spent_usd"] == Decimal("9.90")


# 10) Tolerance Decimal olmalı (float epsilon DEĞİL); parasal alanlar Decimal kalmalı
def test_tolerance_is_decimal_not_float_epsilon():
    d = C(status="filled", taking_amount="28.57", making_amount=Decimal("9.99999999"),
          requested_usd=Decimal("10.00"), order_id="ord")
    assert d["kind"] == "OPEN_FILLED"
    for k in ("shares", "spent_usd", "fill_price"):
        assert isinstance(d[k], Decimal) and not isinstance(d[k], float), (
            f"{k} Decimal olmalı (float epsilon yasak): {type(d[k])}")


# 11) Status normalization: "FILLED" == "filled" → aynı sınıflandırma (case-insensitive)
def test_status_normalization_uppercase_equals_lowercase():
    args = dict(taking_amount="28.57", making_amount=Decimal("10.00"),
                requested_usd=Decimal("10.00"), order_id="ord")
    up = C(status="FILLED", **args)
    lo = C(status="filled", **args)
    assert up["kind"] == lo["kind"] == "OPEN_FILLED"
    assert up["state"] == lo["state"] == "FILLED"
    assert up == lo, f"case farkı aynı sonucu vermeli: {up} != {lo}"
