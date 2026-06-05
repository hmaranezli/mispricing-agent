"""data/clob_price.py testleri."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.clob_price import get_clob_price, get_book


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


@pytest.mark.asyncio
async def test_get_book_returns_dict_with_bids_and_asks():
    """Başarılı yanıtta bids/asks içeren dict döner."""
    book_data = {
        "market": "0xabc",
        "asset_id": "tok-yes",
        "timestamp": "1234567890",
        "hash": "abc",
        "bids": [{"price": "0.44", "size": "200"}, {"price": "0.43", "size": "100"}],
        "asks": [{"price": "0.46", "size": "150"}, {"price": "0.47", "size": "250"}],
        "min_order_size": "1",
        "tick_size": "0.01",
        "neg_risk": False,
        "last_trade_price": "0.45",
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=book_data)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_book("tok-yes")
    assert result is not None
    assert result["asks"][0]["price"] == "0.46"
    assert result["bids"][0]["price"] == "0.44"
    assert result["last_trade_price"] == "0.45"


@pytest.mark.asyncio
async def test_get_book_returns_none_for_empty_token():
    """Boş token_id → API çağrısı yapılmaz, None döner."""
    with patch("data.clob_price.aiohttp.ClientSession") as mock_cls:
        result = await get_book("")
    mock_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_get_book_returns_none_on_http_404():
    """HTTP 404 (token yok / sona ermiş market) → None döner."""
    mock_resp = MagicMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    with patch("data.clob_price.aiohttp.ClientSession", return_value=mock_session):
        result = await get_book("tok-expired")
    assert result is None


@pytest.mark.asyncio
async def test_get_book_returns_none_on_exception():
    """Network exception → None döner (crash yok)."""
    with patch("data.clob_price.aiohttp.ClientSession", side_effect=Exception("timeout")):
        result = await get_book("tok-abc")
    assert result is None
