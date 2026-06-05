"""data/clob_price.py testleri."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.clob_price import get_clob_price


@pytest.mark.asyncio
async def test_get_clob_price_returns_float_on_success():
    """Başarılı API yanıtında float döner."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"price": "0.7500"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result == 0.75


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_when_price_zero():
    """API price=0 → None döner (liquidity yok)."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"price": "0"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_on_http_error():
    """HTTP 400/500 → None döner."""
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_on_exception():
    """Network exception → None döner (crash yok)."""
    with patch("data.clob_price.aiohttp.ClientSession", side_effect=Exception("timeout")):
        result = await get_clob_price("tok-abc")
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_for_empty_token():
    """Boş token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_clob_price("")
    mock_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_get_clob_price_returns_none_for_none_token():
    """None token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_clob_price(None)
    mock_cls.assert_not_called()
    assert result is None
