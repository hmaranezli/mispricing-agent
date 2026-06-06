"""execution/ghost.py — Hayalet pozisyon tespiti.

Bot execution ortasında öldürülürse FAK fill CLOB'da gerçekleşir ama
log_position_open çağrılmadan DB'ye yazılmaz → portföyde kaydı olmayan
"hayalet" shareler kalır. Bazıları resolved + redeemable = claim edilmemiş para.

Bu modül Polymarket data-api'den GERÇEK portföyü çeker (anti-hallucination:
hafızadan değil, taze API), DB'deki açık pozisyonlarla karşılaştırır,
eşleşmeyen (DB'de izlenmeyen) token holding'lerini döndürür.

Endpoint: https://data-api.polymarket.com/positions?user=<funder>
  Dönen her kayıt: asset (token_id), slug, outcome, size, redeemable,
  currentValue, cashPnl ...
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp

DATA_API = "https://data-api.polymarket.com/positions"


async def fetch_portfolio_positions(
    funder: str | None = None,
    size_threshold: float = 0.1,
) -> list[dict]:
    """Polymarket data-api'den proxy cüzdanın açık token holding'lerini çeker.

    funder None ise POLY_FUNDER_ADDRESS env'inden okunur.
    Adres yoksa veya API hatasında boş liste döner (sistem durmaz).
    """
    addr = (funder if funder is not None else os.environ.get("POLY_FUNDER_ADDRESS", "")).strip()
    if not addr:
        return []
    timeout = aiohttp.ClientTimeout(total=15)
    params = {"user": addr, "sizeThreshold": str(size_threshold)}
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(DATA_API, params=params,
                             headers={"User-Agent": "mispricing-bot"}) as r:
                if r.status != 200:
                    return []
                data = await r.json()
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _known_token_ids(open_positions: list[dict]) -> set[str]:
    """DB açık pozisyonlardan izlenen tüm token id'lerini (YES+NO) str set olarak döndürür."""
    ids: set[str] = set()
    for p in open_positions:
        for k in ("yes_token_id", "no_token_id"):
            v = p.get(k)
            if v:
                ids.add(str(v))
    return ids


async def detect_ghosts(
    open_positions: list[dict],
    fetch_fn=fetch_portfolio_positions,
) -> list[dict]:
    """Portföyde olup DB açık pozisyonlarında OLMAYAN token holding'lerini döndürür.

    Bunlar bot tarafından kaydı tutulmayan ("hayalet") shareler — kill-mid-execution
    veya kısmi fill artıkları. Bazıları redeemable olabilir (claim edilmemiş kazanç).
    """
    portfolio = await fetch_fn()
    known = _known_token_ids(open_positions)
    return [p for p in portfolio if str(p.get("asset", "")) not in known]
