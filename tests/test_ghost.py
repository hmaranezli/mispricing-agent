"""tests/test_ghost.py — hayalet pozisyon tespiti birim testleri. Ağ çağrısı yok."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from execution.ghost import detect_ghosts, _known_token_ids, fetch_portfolio_positions


def _portfolio_entry(asset: str, slug: str, outcome: str = "Down", size: float = 2.0,
                     redeemable: bool = False, current_value: float = 1.0) -> dict:
    return {
        "asset": asset, "slug": slug, "outcome": outcome, "size": size,
        "redeemable": redeemable, "currentValue": current_value,
    }


def _open_pos(yes_tid: str, no_tid: str, slug: str = "btc-updown-5m-1") -> dict:
    return {"slug": slug, "yes_token_id": yes_tid, "no_token_id": no_tid, "action": "YES"}


def test_known_token_ids_includes_both_sides():
    """DB açık pozisyondan hem YES hem NO token id'leri toplanır (str olarak)."""
    pos = [_open_pos("111", "222")]
    ids = _known_token_ids(pos)
    assert ids == {"111", "222"}


def test_known_token_ids_casts_to_str():
    """token id int gelse bile str karşılaştırma için normalize edilir."""
    pos = [{"slug": "s", "yes_token_id": 111, "no_token_id": 222}]
    assert _known_token_ids(pos) == {"111", "222"}


@pytest.mark.asyncio
async def test_detect_ghosts_finds_untracked_token():
    """Portföyde olup DB'de OLMAYAN token = hayalet."""
    portfolio = [
        _portfolio_entry("111", "btc-updown-5m-tracked"),   # DB'de var
        _portfolio_entry("999", "xrp-updown-5m-ghost"),     # DB'de YOK → hayalet
    ]
    async def fake_fetch():
        return portfolio
    open_positions = [_open_pos("111", "222")]
    ghosts = await detect_ghosts(open_positions, fetch_fn=fake_fetch)
    assert len(ghosts) == 1
    assert ghosts[0]["slug"] == "xrp-updown-5m-ghost"


@pytest.mark.asyncio
async def test_detect_ghosts_empty_when_all_tracked():
    """Tüm portföy tokenları DB'de varsa hayalet yok."""
    portfolio = [_portfolio_entry("111", "s1"), _portfolio_entry("222", "s2")]
    async def fake_fetch():
        return portfolio
    open_positions = [_open_pos("111", "222")]
    ghosts = await detect_ghosts(open_positions, fetch_fn=fake_fetch)
    assert ghosts == []


@pytest.mark.asyncio
async def test_detect_ghosts_matches_no_side_token():
    """Hayalet kontrolü NO token tarafını da kapsar (sadece YES değil)."""
    portfolio = [_portfolio_entry("222", "s-no-side")]  # bu pozisyonun NO token'ı
    async def fake_fetch():
        return portfolio
    open_positions = [_open_pos("111", "222")]
    ghosts = await detect_ghosts(open_positions, fetch_fn=fake_fetch)
    assert ghosts == [], "NO token DB'de izleniyorsa hayalet sayılmaz"


@pytest.mark.asyncio
async def test_fetch_portfolio_empty_without_funder():
    """Funder adresi yoksa ağ çağrısı yapmadan boş liste döner."""
    result = await fetch_portfolio_positions(funder="")
    assert result == []
