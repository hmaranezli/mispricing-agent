"""tests/test_entry_air_pocket.py — Entry FAK_NO_MATCH air pocket telemetri testleri.

DB schema, shadow quote hesabı, log fonksiyonları ve executor entegrasyonu.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import pytest
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock


# ── Yardımcılar ──────────────────────────────────────────────────────────────

async def _mem_conn():
    """In-memory SQLite bağlantısı + şema init."""
    from db.schema import init_schema
    conn = await aiosqlite.connect(":memory:")
    await init_schema(conn)
    return conn


def _sample_event(**overrides):
    base = {
        "slug":                  "btc-updown-15m-test",
        "asset":                 "BTC",
        "action":                "YES",
        "market_id":             None,
        "token_id":              "yes-tok-123",
        "event_ts":              "2026-06-08T03:00:00+00:00",
        "council_pass_ts":       "2026-06-08T02:59:59+00:00",
        "order_submit_ts":       "2026-06-08T03:00:00+00:00",
        "error_ts":              "2026-06-08T03:00:00.300+00:00",
        "council_to_submit_ms":  1200.0,
        "submit_to_error_ms":    300.0,
        "fair":                  0.665,
        "expected_ask":          0.580,
        "original_worst_price":  0.590,
        "original_fee_adj":      0.0617,
        "min_edge":              0.04,
        "reported_liquidity":    8195.84,
        "top_of_book_size":      25.0,
        "book_levels_used":      3,
        "book_source":           "rest",
        "book_age_ms":           0.0,
        "order_id":              "0xabc123",
        "error_type":            "fak_no_match",
        "position_created":      0,
        "fresh_ask_after_fail":          0.600,
        "fresh_no_ask_after_fail":       None,
        "fresh_book_age_ms":             0.0,
        "fresh_fee_adj_after_fail":      0.041,
        "fresh_price_delta_cents":       2.0,
        "fresh_edge_still_passes_min_edge": 1,
        "would_retry_passed_shadow":     1,
        "delayed_ask_after_fail":        None,
        "delayed_no_ask_after_fail":     None,
        "delayed_book_age_ms":           None,
        "delayed_fee_adj_after_fail":    None,
        "delayed_price_delta_cents":     None,
        "delayed_edge_still_passes_min_edge": None,
        "delayed_would_retry_passed_shadow":  None,
    }
    base.update(overrides)
    return base


# ── DB Şema testleri ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_entry_air_pocket_table_created():
    """DB init sonrası entry_air_pocket_events tablosu oluşmalı."""
    conn = await _mem_conn()
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_air_pocket_events'"
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None, "entry_air_pocket_events tablosu bulunamadı"


@pytest.mark.asyncio
async def test_entry_air_pocket_table_has_required_columns():
    """Tablo kritik sütunları içermeli."""
    conn = await _mem_conn()
    async with conn.execute("PRAGMA table_info(entry_air_pocket_events)") as cur:
        cols = {row[1] async for row in cur}
    await conn.close()
    required = {
        "id", "slug", "asset", "action", "token_id",
        "event_ts", "council_pass_ts", "order_submit_ts", "error_ts",
        "council_to_submit_ms", "submit_to_error_ms",
        "fair", "expected_ask", "original_worst_price", "original_fee_adj", "min_edge",
        "reported_liquidity", "top_of_book_size", "book_levels_used", "book_source", "book_age_ms",
        "order_id", "error_type", "position_created",
        "fresh_ask_after_fail", "fresh_no_ask_after_fail", "fresh_book_age_ms",
        "fresh_fee_adj_after_fail", "fresh_price_delta_cents",
        "fresh_edge_still_passes_min_edge", "would_retry_passed_shadow",
        "delayed_ask_after_fail", "delayed_no_ask_after_fail", "delayed_book_age_ms",
        "delayed_fee_adj_after_fail", "delayed_price_delta_cents",
        "delayed_edge_still_passes_min_edge", "delayed_would_retry_passed_shadow",
    }
    missing = required - cols
    assert not missing, f"Eksik sütunlar: {missing}"


# ── log_entry_air_pocket testleri ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_entry_air_pocket_returns_int_id():
    """log_entry_air_pocket → int event_id döner."""
    from db.logger import log_entry_air_pocket
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    await conn.close()
    assert isinstance(event_id, int)
    assert event_id > 0


@pytest.mark.asyncio
async def test_log_entry_air_pocket_stores_core_fields():
    """Kaydedilen satır slug, asset, action, error_type alanlarını doğru içermeli."""
    from db.logger import log_entry_air_pocket
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    async with conn.execute(
        "SELECT slug, asset, action, error_type, position_created FROM entry_air_pocket_events WHERE id=?",
        (event_id,)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert row is not None
    assert row[0] == "btc-updown-15m-test"
    assert row[1] == "BTC"
    assert row[2] == "YES"
    assert row[3] == "fak_no_match"
    assert row[4] == 0  # position_created=False


@pytest.mark.asyncio
async def test_log_entry_air_pocket_stores_timing_fields():
    """council_to_submit_ms ve submit_to_error_ms kaydedilmeli."""
    from db.logger import log_entry_air_pocket
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    async with conn.execute(
        "SELECT council_to_submit_ms, submit_to_error_ms FROM entry_air_pocket_events WHERE id=?",
        (event_id,)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert abs(row[0] - 1200.0) < 0.01
    assert abs(row[1] - 300.0) < 0.01


@pytest.mark.asyncio
async def test_log_entry_air_pocket_stores_fresh_shadow_fields():
    """fresh_ask_after_fail ve would_retry_passed_shadow kaydedilmeli."""
    from db.logger import log_entry_air_pocket
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    async with conn.execute(
        "SELECT fresh_ask_after_fail, would_retry_passed_shadow, fresh_fee_adj_after_fail "
        "FROM entry_air_pocket_events WHERE id=?",
        (event_id,)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert abs(row[0] - 0.600) < 1e-4
    assert row[1] == 1
    assert abs(row[2] - 0.041) < 1e-4


@pytest.mark.asyncio
async def test_log_multiple_events_sequential_ids():
    """Birden fazla event art arda farklı ID alır."""
    from db.logger import log_entry_air_pocket
    conn = await _mem_conn()
    id1 = await log_entry_air_pocket(conn, _sample_event())
    id2 = await log_entry_air_pocket(conn, _sample_event(slug="eth-test"))
    await conn.close()
    assert id2 > id1


# ── update_entry_air_pocket_delayed testleri ─────────────────────────────────

@pytest.mark.asyncio
async def test_update_delayed_snapshot_writes_fields():
    """update_entry_air_pocket_delayed → delayed_* alanlarını doldurur."""
    from db.logger import log_entry_air_pocket, update_entry_air_pocket_delayed
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    await update_entry_air_pocket_delayed(conn, event_id, {
        "delayed_ask_after_fail":             0.610,
        "delayed_no_ask_after_fail":          None,
        "delayed_book_age_ms":                401.5,
        "delayed_fee_adj_after_fail":         0.025,
        "delayed_price_delta_cents":          3.0,
        "delayed_edge_still_passes_min_edge": 0,
        "delayed_would_retry_passed_shadow":  0,
    })
    async with conn.execute(
        "SELECT delayed_ask_after_fail, delayed_book_age_ms, delayed_would_retry_passed_shadow "
        "FROM entry_air_pocket_events WHERE id=?",
        (event_id,)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert abs(row[0] - 0.610) < 1e-4
    assert abs(row[1] - 401.5) < 0.1
    assert row[2] == 0


@pytest.mark.asyncio
async def test_update_delayed_snapshot_does_not_touch_fresh_fields():
    """Delayed update, fresh_* alanlarını değiştirmemeli."""
    from db.logger import log_entry_air_pocket, update_entry_air_pocket_delayed
    conn = await _mem_conn()
    event_id = await log_entry_air_pocket(conn, _sample_event())
    await update_entry_air_pocket_delayed(conn, event_id, {
        "delayed_ask_after_fail":             0.610,
        "delayed_no_ask_after_fail":          None,
        "delayed_book_age_ms":                400.0,
        "delayed_fee_adj_after_fail":         0.025,
        "delayed_price_delta_cents":          3.0,
        "delayed_edge_still_passes_min_edge": 0,
        "delayed_would_retry_passed_shadow":  0,
    })
    async with conn.execute(
        "SELECT fresh_ask_after_fail, would_retry_passed_shadow FROM entry_air_pocket_events WHERE id=?",
        (event_id,)
    ) as cur:
        row = await cur.fetchone()
    await conn.close()
    assert abs(row[0] - 0.600) < 1e-4  # değişmemeli
    assert row[1] == 1                  # değişmemeli


# ── Shadow quote hesap testleri ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shadow_quote_fee_adj_yes_action():
    """YES action fee_adj: fair×(1−fee) − (ask+slippage)."""
    from data.shadow_quote import _fee_adj, ENTRY_SLIPPAGE
    fee = 0.02
    result = _fee_adj("YES", fair=0.665, ask=0.580, fee=fee)
    expected = 0.665 * 0.98 - (0.580 + ENTRY_SLIPPAGE)
    assert abs(result - expected) < 1e-6


@pytest.mark.asyncio
async def test_shadow_quote_fee_adj_no_action():
    """NO action fee_adj: (1−fair)×(1−fee) − (no_ask+slippage)."""
    from data.shadow_quote import _fee_adj, ENTRY_SLIPPAGE
    fee = 0.02
    result = _fee_adj("NO", fair=0.665, ask=0.420, fee=fee)
    expected = (1 - 0.665) * 0.98 - (0.420 + ENTRY_SLIPPAGE)
    assert abs(result - expected) < 1e-6


@pytest.mark.asyncio
async def test_shadow_quote_would_retry_true_when_edge_passes():
    """fresh_fee_adj >= min_edge → would_retry_passed=True."""
    from data.shadow_quote import get_shadow_quote
    book_resp = {"asks": [{"price": "0.580", "size": "50"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    assert q["would_retry_passed"] is True
    assert q["edge_still_passes"] is True


@pytest.mark.asyncio
async def test_shadow_quote_would_retry_false_when_edge_fails():
    """fresh_fee_adj < min_edge → would_retry_passed=False."""
    from data.shadow_quote import get_shadow_quote
    # ask çok yüksek → edge negatif
    book_resp = {"asks": [{"price": "0.650", "size": "10"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    assert q["would_retry_passed"] is False


@pytest.mark.asyncio
async def test_shadow_quote_uses_ws_cache_first():
    """WS cache'de taze veri varsa REST çağrısı yapılmamalı."""
    from data.shadow_quote import get_shadow_quote
    mock_book = AsyncMock(return_value=None)  # REST çağrılırsa fail etsin
    fake_cache = {"yes-tok": {"best_ask": 0.585, "best_bid": 0.575, "ts": time.time(), "spread": 0.01}}
    with patch("data.shadow_quote.get_book", mock_book), \
         patch("data.shadow_quote.ws_prices._cache", fake_cache), \
         patch("data.shadow_quote.ws_prices.STALE_SECS", 15):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    mock_book.assert_not_called()
    assert q["source"] == "ws_cache"
    assert abs(q["ask"] - 0.585) < 1e-4


@pytest.mark.asyncio
async def test_shadow_quote_rest_fallback_when_ws_miss():
    """WS cache boşsa REST get_book() çağrılmalı."""
    from data.shadow_quote import get_shadow_quote
    book_resp = {"asks": [{"price": "0.590", "size": "30"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    assert q["source"] == "rest"
    assert abs(q["ask"] - 0.590) < 1e-4


@pytest.mark.asyncio
async def test_shadow_quote_returns_nulls_on_api_failure():
    """REST API başarısız → tüm sayısal alanlar None, crash yok."""
    from data.shadow_quote import get_shadow_quote
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, side_effect=Exception("timeout")), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    assert q["ask"] is None
    assert q["fee_adj"] is None
    assert q["would_retry_passed"] is None
    assert q["source"] == "none"


@pytest.mark.asyncio
async def test_shadow_quote_price_delta_cents_correct():
    """price_delta_cents = (fresh_ask − original_ask) × 100."""
    from data.shadow_quote import get_shadow_quote
    book_resp = {"asks": [{"price": "0.600", "size": "20"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.580, min_edge=0.04)
    assert abs(q["price_delta_cents"] - 2.0) < 0.01  # (0.600 - 0.580) * 100


@pytest.mark.asyncio
async def test_shadow_quote_extracts_top_size_from_rest():
    """REST book'tan top_of_book_size hesaplanmalı (USD = size × price)."""
    from data.shadow_quote import get_shadow_quote
    book_resp = {"asks": [{"price": "0.590", "size": "100"}, {"price": "0.600", "size": "50"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("yes-tok", "YES", fair=0.665, original_ask=0.575, min_edge=0.04)
    # top_size = 100 shares × 0.590 = 59 USD
    assert q["top_size"] is not None
    assert abs(q["top_size"] - 59.0) < 0.1
    assert q["levels"] == 2


@pytest.mark.asyncio
async def test_shadow_quote_no_action_fields():
    """NO action → no_ask dolu, fee_adj (1-fair) formülü."""
    from data.shadow_quote import get_shadow_quote, _fee_adj, ENTRY_SLIPPAGE
    book_resp = {"asks": [{"price": "0.420", "size": "80"}], "bids": []}
    with patch("data.shadow_quote.get_book", new_callable=AsyncMock, return_value=book_resp), \
         patch("data.shadow_quote.ws_prices._cache", {}):
        q = await get_shadow_quote("no-tok", "NO", fair=0.665, original_ask=0.415, min_edge=0.04)
    assert q["no_ask"] is not None
    expected_fa = (1 - 0.665) * 0.98 - (0.420 + ENTRY_SLIPPAGE)
    assert abs(q["fee_adj"] - expected_fa) < 1e-4


# ── Executor entegrasyon testleri (FAK_NO_MATCH) ─────────────────────────────

def _finding(action="YES"):
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": action,
        "fair_value": 0.665, "ref_price": 95000.0, "cur_price": 96000.0,
        "best_ask": 0.580, "best_bid": 0.570, "seconds_remaining": 900,
        "edge": 0.085, "slug": "btc-updown-15m-test", "neg_risk": False,
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
    }

def _gate():
    return {"pass": True, "confidence_score": 100.0, "action_taken": "open",
            "fee_adj_edge": 0.0617, "liquidity_usd": 8195.84}

def _risk():
    return {"pass": True, "position_usd": 1.25, "kelly_f": 0.05,
            "kelly_fraction_applied": 0.25, "reason": ""}

FAK_NO_MATCH_MSG = (
    "PolyApiException[status_code=400, error_message={'error': "
    "'no orders found to match with FAK order. FAK orders are partially "
    "filled or killed if no match is found.', 'orderID': '0x64ebfe8abc123'}]"
)


@pytest.mark.asyncio
async def test_fak_no_match_detected_and_logged():
    """FAK 400 hatası → log_entry_air_pocket çağrılır, event error_type=fak_no_match."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    mock_log = AsyncMock(return_value=42)
    mock_shadow = AsyncMock(return_value={
        "ask": 0.600, "no_ask": None, "book_age_ms": 0.0,
        "fee_adj": 0.041, "price_delta_cents": 2.0,
        "edge_still_passes": True, "would_retry_passed": True,
        "source": "rest", "top_size": 25.0, "levels": 2,
    })
    mock_conn = MagicMock()

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("execution.clob_executor.get_shadow_quote", mock_shadow), \
         patch("asyncio.create_task", return_value=MagicMock()):
        result = await execute(_finding("YES"), _gate(), _risk(), [],
                               conn=mock_conn, council_pass_ts="2026-06-08T02:59:59+00:00")

    assert result is None
    mock_log.assert_called_once()
    _, logged_event = mock_log.call_args[0]
    assert logged_event["error_type"] == "fak_no_match"
    assert logged_event["slug"] == "btc-updown-15m-test"
    assert logged_event["position_created"] == 0
    assert logged_event["asset"] == "BTC"
    assert logged_event["order_id"] == "0x64ebfe8abc123"


@pytest.mark.asyncio
async def test_fak_no_match_fires_delayed_task():
    """FAK_NO_MATCH → asyncio.create_task delayed snapshot için çağrılır."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    mock_log = AsyncMock(return_value=99)
    mock_shadow = AsyncMock(return_value={
        "ask": 0.600, "no_ask": None, "book_age_ms": 0.0,
        "fee_adj": 0.041, "price_delta_cents": 2.0,
        "edge_still_passes": True, "would_retry_passed": True,
        "source": "rest", "top_size": None, "levels": None,
    })
    mock_conn = MagicMock()

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("execution.clob_executor.get_shadow_quote", mock_shadow), \
         patch("asyncio.create_task", return_value=MagicMock()) as mock_create_task:
        await execute(_finding("YES"), _gate(), _risk(), [],
                      conn=mock_conn, council_pass_ts=None)

    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_fak_no_match_returns_none():
    """FAK_NO_MATCH → execute() her durumda None döner."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", AsyncMock(return_value=1)), \
         patch("execution.clob_executor.get_shadow_quote", AsyncMock(return_value={
             "ask": None, "no_ask": None, "book_age_ms": None,
             "fee_adj": None, "price_delta_cents": None,
             "edge_still_passes": None, "would_retry_passed": None,
             "source": "none", "top_size": None, "levels": None,
         })), \
         patch("asyncio.create_task", return_value=MagicMock()):
        result = await execute(_finding("YES"), _gate(), _risk(), [])
    assert result is None


@pytest.mark.asyncio
async def test_fak_no_match_no_crash_when_shadow_fails():
    """Shadow quote exception → execute() yine de None döner, crash yok."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", AsyncMock(return_value=1)), \
         patch("execution.clob_executor.get_shadow_quote", AsyncMock(side_effect=Exception("net fail"))), \
         patch("asyncio.create_task", return_value=MagicMock()):
        result = await execute(_finding("YES"), _gate(), _risk(), [])
    assert result is None  # crash yok


@pytest.mark.asyncio
async def test_fak_no_match_no_log_when_conn_none():
    """conn=None → log_entry_air_pocket çağrılmaz ama execute() yine None döner."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    mock_log = AsyncMock(return_value=1)

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("execution.clob_executor.get_shadow_quote", AsyncMock(return_value={
             "ask": None, "no_ask": None, "book_age_ms": None,
             "fee_adj": None, "price_delta_cents": None,
             "edge_still_passes": None, "would_retry_passed": None,
             "source": "none", "top_size": None, "levels": None,
         })), \
         patch("asyncio.create_task", return_value=MagicMock()):
        result = await execute(_finding("YES"), _gate(), _risk(), [], conn=None)

    assert result is None
    mock_log.assert_not_called()


@pytest.mark.asyncio
async def test_non_fak_exception_does_not_log_air_pocket():
    """Farklı exception (timeout, auth) → log_entry_air_pocket çağrılmamalı."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception("Connection timeout after 5s")

    mock_log = AsyncMock(return_value=1)

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("asyncio.create_task", return_value=MagicMock()):
        result = await execute(_finding("YES"), _gate(), _risk(), [], conn=MagicMock())

    assert result is None
    mock_log.assert_not_called()


@pytest.mark.asyncio
async def test_fak_no_match_stores_council_pass_ts():
    """council_pass_ts execute()'a geçilince event'e yazılmalı."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    mock_log = AsyncMock(return_value=1)
    mock_shadow = AsyncMock(return_value={
        "ask": None, "no_ask": None, "book_age_ms": None,
        "fee_adj": None, "price_delta_cents": None,
        "edge_still_passes": None, "would_retry_passed": None,
        "source": "none", "top_size": None, "levels": None,
    })

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("execution.clob_executor.get_shadow_quote", mock_shadow), \
         patch("asyncio.create_task", return_value=MagicMock()):
        await execute(_finding(), _gate(), _risk(), [], conn=MagicMock(),
                      council_pass_ts="2026-06-08T02:59:59.123+00:00")

    _, event = mock_log.call_args[0]
    assert event["council_pass_ts"] == "2026-06-08T02:59:59.123+00:00"
    assert event["council_to_submit_ms"] is not None
    assert event["council_to_submit_ms"] >= 0


@pytest.mark.asyncio
async def test_fak_no_match_gate_fee_adj_in_event():
    """gate_result'daki fee_adj_edge event'e original_fee_adj olarak yazılmalı."""
    from execution.clob_executor import execute
    fake_client = MagicMock()
    fake_client.create_market_order.return_value = MagicMock()
    fake_client.post_order.side_effect = Exception(FAK_NO_MATCH_MSG)

    mock_log = AsyncMock(return_value=1)

    with patch("execution.clob_executor.get_client", return_value=fake_client), \
         patch("execution.clob_executor._get_clob_price", new_callable=AsyncMock, return_value=0.580), \
         patch("execution.clob_executor.log_entry_air_pocket", mock_log), \
         patch("execution.clob_executor.get_shadow_quote", AsyncMock(return_value={
             "ask": None, "no_ask": None, "book_age_ms": None,
             "fee_adj": None, "price_delta_cents": None,
             "edge_still_passes": None, "would_retry_passed": None,
             "source": "none", "top_size": None, "levels": None,
         })), \
         patch("asyncio.create_task", return_value=MagicMock()):
        await execute(_finding(), _gate(), _risk(), [], conn=MagicMock())

    _, event = mock_log.call_args[0]
    assert abs(event["original_fee_adj"] - 0.0617) < 1e-4
    assert abs(event["reported_liquidity"] - 8195.84) < 0.01


# ── Gate fee_adj_edge propagation ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate_result_includes_fee_adj_edge():
    """gate() dönüşü fee_adj_edge ve liquidity_usd içermeli."""
    from council.gate import gate

    finding      = {"slug": "test", "asset": "BTC", "action": "YES",
                    "fair_value": 0.65, "best_ask": 0.58, "edge": 0.07}
    verification = {"fresh_seconds": 400, "pass": True,
                    "fresh_best_ask": 0.58, "fresh_best_bid": 0.57}
    redteam      = {"pass": True, "fee_adj_edge": 0.055, "liquidity_usd": 5000.0,
                    "spread": 0.01, "vetoes": [], "warnings": [], "taker_fee": 0.02}
    risk_result  = {"pass": True, "position_usd": 1.25, "requires_human_approval": False,
                    "kelly_f": 0.04}

    with patch("config.DRY_RUN", True), \
         patch("config.CONFIDENCE_THRESHOLD", 0):
        result = await gate(finding, verification, redteam, risk_result)

    assert "fee_adj_edge" in result
    assert abs(result["fee_adj_edge"] - 0.055) < 1e-4
    assert "liquidity_usd" in result
    assert abs(result["liquidity_usd"] - 5000.0) < 0.1
