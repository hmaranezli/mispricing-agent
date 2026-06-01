#!/usr/bin/env python3
"""analysis/approve_usdc.py — TEK SEFERLİK USDC harcama izni.

Polymarket CLOB'un cüzdandaki USDC'yi kullanabilmesi için Polygon'da
on-chain onay işlemi gerekir. Bu script bunu yapar.

Gereksinimler:
  - .env'de POLY_* credentials dolu
  - Cüzdanda USDC yüklü
  - Cüzdanda az miktarda MATIC (gas için ~$0.01)

Kullanım:
    python analysis/approve_usdc.py

Bu işlem BİR KEZ yapılır. Sonrasında gerekmez.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from py_clob_client.clob_types import (
    BalanceAllowanceParams, AssetType, RequestArgs
)
from execution.clob_client import get_client, reset_client


def run_approval() -> bool:
    print("=" * 60)
    print("USDC HARCAMA İZNİ — Tek seferlik on-chain işlem")
    print("=" * 60)

    print("\n[1] Client başlatılıyor...")
    try:
        reset_client()
        client = get_client()
        print("    ✓ Bağlandı")
    except Exception as e:
        print(f"    ✗ Hata: {e}")
        return False

    print("\n[2] Mevcut allowance kontrol ediliyor...")
    try:
        bal = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        balance   = bal.get("balance", "0")
        allowance = list(bal.get("allowances", {}).values())
        print(f"    USDC bakiye  : {balance}")
        print(f"    Allowances   : {allowance}")
        if any(float(a) > 0 for a in allowance if a):
            print("    ✓ Zaten onaylı — tekrar çalıştırmaya gerek yok")
            return True
    except Exception as e:
        print(f"    ⚠ Kontrol hatası: {e}")

    print("\n[3] USDC approval gönderiliyor (Polygon'da on-chain)...")
    print("    Metamask popup gelmez — doğrudan private key ile imzalanır")
    try:
        resp = client.update_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        print(f"    ✓ Onay gönderildi: {resp}")
    except Exception as e:
        print(f"    ✗ Onay hatası: {e}")
        print("      Cüzdanda MATIC var mı? Gas için küçük miktarda gerekli.")
        return False

    print("\n[4] Onay doğrulanıyor...")
    try:
        bal2 = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        allowance2 = list(bal2.get("allowances", {}).values())
        print(f"    Yeni allowances: {allowance2}")
        if any(float(a) > 0 for a in allowance2 if a):
            print("    ✓ Onay başarılı — artık order gönderilebilir")
        else:
            print("    ⚠ Onay henüz yansımamış (blockchain gecikmesi normal)")
    except Exception as e:
        print(f"    ⚠ Doğrulama hatası: {e}")

    print("\n" + "=" * 60)
    print("✅ USDC approval tamamlandı")
    print("   Sıradaki adım: config.py'de DRY_RUN=False yap, botu yeniden başlat")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = run_approval()
    sys.exit(0 if ok else 1)
