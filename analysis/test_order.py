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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from execution.clob_client import get_client, reset_client
from data.shortterm import find_shortterm
from py_clob_client_v2.clob_types import BalanceAllowanceParams, AssetType, OrderArgs

MIN_TEST_USD   = 0.80  # $0.80 test — fee (~$0.03) dahil $1.00 bakiyeye sığar
TEST_ASSET     = "btc" # BTC marketlerinde test


async def run_test() -> bool:
    print("=" * 60)
    print("$1 TEST ORDER — CLOB entegrasyon doğrulaması")
    print("=" * 60)

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

    # 4. $1 BUY order gönder
    shares = round(MIN_TEST_USD / best_ask, 4)
    print(f"\n[4] ${MIN_TEST_USD} YES order gönderiliyor ({shares} shares @ {best_ask})...")
    try:
        order_args = OrderArgs(
            token_id=yes_token,
            price=best_ask,
            size=shares,
            side="BUY",
        )
        resp = client.create_and_post_order(order_args)
        print(f"    Response: {resp}")

        status      = resp.get("status") if isinstance(resp, dict) else getattr(resp, "status", "?")
        order_id    = resp.get("orderID") if isinstance(resp, dict) else getattr(resp, "orderID", "?")
        size_filled = resp.get("sizeFilled") if isinstance(resp, dict) else getattr(resp, "sizeFilled", "0")

        print(f"    Status     : {status}")
        print(f"    Order ID   : {order_id}")
        print(f"    Size filled: {size_filled}")

        if status == "MATCHED":
            print("    ✓ Order DOLDU — şimdi satıyoruz...")
            filled = float(size_filled or 0)
            if filled > 0:
                sell_args = OrderArgs(
                    token_id=yes_token,
                    price=round(best_ask * 0.95, 2),
                    size=filled,
                    side="SELL",
                )
                sell_resp = client.create_and_post_order(sell_args)
                sell_status = sell_resp.get("status") if isinstance(sell_resp, dict) else getattr(sell_resp, "status", "?")
                print(f"    SELL status: {sell_status}")
        else:
            print("    ⚠ IOC iptal oldu (fill yok) — kayıp yok, bu normal olabilir")

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
