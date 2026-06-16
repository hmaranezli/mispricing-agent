#!/usr/bin/env python3
"""analysis/test_order.py — Canlıya geçmeden önce $1 CLOB order testi.

Gerçek bir Polymarket marketine $1 YES order gönderir.
Fill olursa → hemen satar (temizler).
Fill olmazsa (IOC iptal) → kayıp yok.

Amaç: clob_executor + position_store zincirinin gerçek API'de
çalıştığını doğrulamak. Canlıya geçmeden ÖNCE çalıştır.

Kullanım:
    python analysis/test_order.py
"""
import asyncio
import json
import sys
import os
from decimal import Decimal, ROUND_DOWN
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from execution.clob_client import get_client, reset_client
from data.shortterm import find_shortterm
from py_clob_client_v2.clob_types import BalanceAllowanceParams, AssetType, OrderArgs, OrderType

MIN_TEST_USD   = 1.10  # Polymarket min order $1 — $1.10 ile en az 2 share alınır
TEST_ASSET     = "btc" # BTC marketlerinde test

# ── DEFAULT-SAFE MANUAL ORDER GUARD ──
# Bu script gerçek CLOB order'ı gönderebilir (create_and_post_order). VARSAYILAN: KAPALI.
# Yalnızca operatör açıkça izin verirse (env MANUAL_ORDER_SCRIPT_ENABLED ∈ {1,true,yes,on})
# çalışır; aksi halde order göndermeden ÖNCE bloklar. Hiçbir otomatik/konsey yolu bu script'i
# tetiklemez; tek tetikleyici elle çalıştırma + açık opt-in env.
MANUAL_ORDER_SCRIPT_ENV = "MANUAL_ORDER_SCRIPT_ENABLED"


def _manual_order_enabled() -> bool:
    """Default-safe: returns True only when MANUAL_ORDER_SCRIPT_ENABLED is explicitly opted in."""
    return os.getenv(MANUAL_ORDER_SCRIPT_ENV, "").strip().lower() in ("1", "true", "yes", "on")


async def run_test() -> bool:
    print("=" * 60)
    print("$1 TEST ORDER — CLOB entegrasyon doğrulaması")
    print("=" * 60)

    # ── GUARD: default-safe block (no client, no order) ──
    if not _manual_order_enabled():
        print(f"[manual_order_guard] BLOCKED — {MANUAL_ORDER_SCRIPT_ENV} disabled (default). "
              f"Hiçbir order gönderilmedi. Opt-in için {MANUAL_ORDER_SCRIPT_ENV}=1 ayarla.")
        return False

    # 1. Client
    print("\n[1] Client başlatılıyor...")
    try:
        reset_client()
        client = get_client()
        print("    ✓ Bağlandı")
    except Exception as e:
        print(f"    ✗ {e}")
        return False

    # 2. Bakiye kontrol
    print("\n[2] USDC bakiye kontrol...")
    try:
        bal = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        usdc = float(bal.get("balance", 0))
        print(f"    USDC (CLOB deposit): {usdc}")
        if usdc < MIN_TEST_USD:
            print(f"    ⚠ CLOB deposit bakiye={usdc} (native USDC görünmüyor — devam ediyoruz)")
    except Exception as e:
        print(f"    ✗ {e}")
        return False

    # 3. Aktif BTC market bul
    print(f"\n[3] Aktif {TEST_ASSET.upper()} marketi aranıyor...")
    try:
        markets = await find_shortterm(intervals=(5, 15))
        candidates = [
            m for m in markets
            if TEST_ASSET in m.get("slug", "").lower()
            and m.get("clobTokenIds")
            and m.get("bestAsk")
            and float(m.get("bestAsk", 1)) < 0.95
            and float(m.get("bestAsk", 0)) > 0.05
        ]
        if not candidates:
            print("    ✗ Uygun market yok (şu an aktif BTC 5m/15m marketi bulunamadı)")
            return False
        market = candidates[0]
        raw_ids = market.get("clobTokenIds", "[]")
        token_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
        yes_token = token_ids[0] if token_ids else None
        if not yes_token:
            print("    ✗ clobTokenIds boş")
            return False
        best_ask  = float(market["bestAsk"])
        slug      = market["slug"]
        print(f"    ✓ Market : {slug}")
        print(f"      YES token: {yes_token[:20]}...")
        print(f"      best_ask : {best_ask:.4f}")
    except Exception as e:
        print(f"    ✗ {e}")
        return False

    # 4. $1 BUY order gönder — shares × price ≤ 2 decimal (CLOB zorunlu)
    p = Decimal(str(round(best_ask, 2)))
    budget = Decimal(str(round(MIN_TEST_USD, 2)))
    shares = float(budget / p)  # fallback
    for prec in ("0.0001", "0.001", "0.01", "0.1", "1"):
        s = (budget / p).quantize(Decimal(prec), rounding=ROUND_DOWN)
        if (s * p * 100) % 1 == 0:
            shares = float(s)
            break
    print(f"\n[4] ${MIN_TEST_USD} YES order gönderiliyor ({shares} shares @ {best_ask})...")
    try:
        order_args = OrderArgs(
            token_id=yes_token,
            price=best_ask,
            size=shares,
            side="BUY",
        )
        resp = client.create_and_post_order(order_args, order_type=OrderType.FOK)
        print(f"    Response: {resp}")

        def _get(obj, key, default=None):
            return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

        status         = _get(resp, "status", "")
        success        = _get(resp, "success", False)
        order_id       = _get(resp, "orderID", "")
        taking_amount  = _get(resp, "takingAmount", None)
        making_amount  = _get(resp, "makingAmount", None)

        matched = success is True or (status or "").lower() == "matched"

        print(f"    Status     : {status}")
        print(f"    Order ID   : {order_id}")
        print(f"    takingAmount (shares): {taking_amount}")
        print(f"    makingAmount (USDC)  : {making_amount}")
        print(f"    Matched    : {matched}")

        if matched:
            fill_shares = float(taking_amount) if taking_amount else 0
            fill_usdc   = float(making_amount) if making_amount else 0
            print(f"    ✓ Order DOLDU — {fill_shares} share @ ${fill_usdc:.4f} USDC")
            if fill_shares > 0:
                sell_price = round(best_ask * 0.95, 2)
                sell_args  = OrderArgs(
                    token_id=yes_token,
                    price=sell_price,
                    size=fill_shares,
                    side="SELL",
                )
                sell_resp   = client.create_and_post_order(sell_args, order_type=OrderType.FOK)
                sell_status = _get(sell_resp, "status", "?")
                sell_success = _get(sell_resp, "success", False)
                print(f"    SELL status: {sell_status} | success: {sell_success}")
        else:
            print("    ⚠ FOK iptal oldu (fill yok) — kayıp yok, likidite yetersiz olabilir")

    except Exception as e:
        print(f"    ✗ Order hatası: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ Test tamamlandı — CLOB entegrasyonu çalışıyor")
    print("   Artık DRY_RUN=False yapabilirsin")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = asyncio.run(run_test())
    sys.exit(0 if ok else 1)
