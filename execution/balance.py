"""execution/balance.py — Etkili bankroll: DRY_RUN→config, LIVE→gerçek USDC bakiyesi."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import config
from execution.clob_client import get_client
from py_clob_client_v2.clob_types import BalanceAllowanceParams, AssetType

_MICRO = 1_000_000  # 1 USDC = 1_000_000 mikro-USDC
_TIMEOUT = 8.0      # senkron CLOB çağrısı için max bekleme


async def get_effective_bankroll(bankroll_config: float) -> float:
    """
    DRY_RUN=True  → bankroll_config (env değeri), API çağrısı yok.
    DRY_RUN=False → Polymarket gerçek USDC bakiyesi, bankroll_config üst sınır.
    Hata durumunda bankroll_config fallback — sistem durmaz.
    """
    if config.DRY_RUN:
        return bankroll_config

    try:
        client = get_client()
        loop = asyncio.get_event_loop()
        # senkron CLOB istemcisi thread'de çalıştırılır — event loop bloke olmaz
        bal = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.get_balance_allowance(
                    params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
                ),
            ),
            timeout=_TIMEOUT,
        )
        usdc = float(bal.get("balance", 0)) / _MICRO
        effective = min(usdc, bankroll_config)
        if effective < bankroll_config * 0.5:
            print(f"[bankroll] Bakiye düştü: ${effective:.2f} / config=${bankroll_config:.2f}")
        return effective
    except Exception as e:
        print(f"[bankroll] Bakiye okunamadı ({e}), fallback=${bankroll_config:.2f}")
        return bankroll_config
