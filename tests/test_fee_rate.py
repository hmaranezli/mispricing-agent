# tests/test_fee_rate.py
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, AsyncMock
import data.fee_rate as fee_mod


@pytest.mark.asyncio
async def test_fetch_returns_parsed_fee():
    """CLOB API base_fee:1000 → 0.02 döner."""
    with patch.object(fee_mod, "_fetch_from_api", return_value=0.02):
        result = await fee_mod.fetch_fee_rate("some-token-id-123")
    assert result == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_cache_avoids_second_api_call():
    """Aynı token ikinci çağrıda cache'den gelir, API çağrısı yapılmaz."""
    fee_mod._cache.clear()
    fee_mod._cache["tok-abc"] = (0.02, time.monotonic() + 300)
    call_count = 0

    async def fake_fetch(token_id):
        nonlocal call_count
        call_count += 1
        return 0.02

    with patch.object(fee_mod, "_fetch_from_api", side_effect=fake_fetch):
        result = await fee_mod.fetch_fee_rate("tok-abc")

    assert result == 0.02
    assert call_count == 0  # cache hit, API çağrılmadı


@pytest.mark.asyncio
async def test_expired_cache_refetches():
    """Süresi geçmiş cache → API tekrar çağrılır."""
    fee_mod._cache.clear()
    fee_mod._cache["tok-xyz"] = (0.02, time.monotonic() - 1)  # süresi geçmiş

    with patch.object(fee_mod, "_fetch_from_api", return_value=0.02) as mock_fetch:
        result = await fee_mod.fetch_fee_rate("tok-xyz")

    mock_fetch.assert_called_once_with("tok-xyz")
    assert result == 0.02


@pytest.mark.asyncio
async def test_api_error_returns_default():
    """API hatası → 0.02 fallback, sistem durmuyor."""
    fee_mod._cache.clear()
    with patch.object(fee_mod, "_fetch_from_api", side_effect=Exception("timeout")):
        result = await fee_mod.fetch_fee_rate("tok-err")
    assert result == 0.02
