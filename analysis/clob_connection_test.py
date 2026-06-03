#!/usr/bin/env python3
"""analysis/clob_connection_test.py — Aşama 1: CLOB API bağlantı doğrulama.

Kullanım:
    python analysis/clob_connection_test.py

Kontroller:
  1. Credentials yükle + client başlat
  2. Wallet USDC bakiyesini oku
  3. Bilinen bir BTC marketi için clobTokenIds doğrula
  4. Order GÖNDERİLMEZ

Başarı koşulu: tüm adımlar geçer, sonunda "HAZIR" mesajı.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv yoksa .env'den değil, sistem env'inden okur

from execution.clob_client import get_client, reset_client
from data.shortterm import find_shortterm


async def run_canary() -> bool:
    print("=" * 60)
    print("CLOB API BAĞLANTI TESTİ — Order gönderilmez")
    print("=" * 60)

    # 1. Client başlat
    print("\n[1] Credentials yükleniyor...")
    try:
        reset_client()
        client = get_client()
        print("    ✓ ClobClient oluşturuldu")
    except KeyError as e:
        print(f"    ✗ Eksik env değişkeni: {e}")
        print("      .env dosyasına POLY_PRIVATE_KEY, POLY_API_KEY, POLY_API_SECRET, POLY_API_PASSPHRASE ekle")
        return False
    except Exception as e:
        print(f"    ✗ Client hatası: {e}")
        return False

    # 2. Wallet bakiyesi
    print("\n[2] Wallet bakiyesi okunuyor...")
    try:
        from py_clob_client_v2.clob_types import BalanceAllowanceParams, AssetType
        bal = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        usdc = bal.get("balance", "?")
        print(f"    ✓ USDC bakiye: {usdc} (0 = henüz yüklenmemiş)")
    except Exception as e:
        print(f"    ✗ Bakiye okunamadı: {e}")
        print("      Bu hata authentication sorunu işareti olabilir.")
        return False

    # 3. clobTokenIds doğrulama
    print("\n[3] BTC market clobTokenIds okunuyor...")
    try:
        import json as _json
        markets = await find_shortterm(intervals=(5,))
        btc_markets = [m for m in markets if "btc" in m.get("slug", "").lower()]
        if btc_markets:
            m = btc_markets[0]
            raw_ids = m.get("clobTokenIds", "[]")
            token_ids = _json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
            print(f"    ✓ Market: {m['slug']}")
            print(f"      YES token: {str(token_ids[0])[:20]}..." if token_ids else "      YES token: YOK")
            print(f"      NO token:  {str(token_ids[1])[:20]}..." if len(token_ids) > 1 else "      NO token:  YOK")
            if not token_ids:
                print("    ⚠ clobTokenIds boş — Polymarket API yanıtını kontrol et")
        else:
            print("    ⚠ Şu an aktif BTC marketi yok (normal olabilir)")
    except Exception as e:
        print(f"    ✗ Market verisi okunamadı: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ HAZIR — DRY_RUN=False öncesi BANKROLL_USD=50 ayarla (.env'de)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = asyncio.run(run_canary())
    sys.exit(0 if ok else 1)
