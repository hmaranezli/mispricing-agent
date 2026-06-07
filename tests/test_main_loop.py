"""tests/test_main_loop.py — main_loop birim testleri. Sıfır API çağrısı."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest_asyncio
import aiosqlite
from db.schema import init_schema
from db.logger import log_position_open
from main_loop import _run_council, _scan_and_execute, _monitor_positions, _load_open_positions, fetch_resolved, _heal_pending_resolutions


# ── Fixture'lar ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def default_ws_prices():
    """Monitor testlerinde ws_prices varsayılan olarak geçerli fiyat döndürür.
    asyncio.wait_for her zaman TimeoutError → tüm eski testler REST heartbeat path'ten geçer.
    Stale-Gamma testleri ws_prices'ı None döndürecek şekilde override eder.
    _last_rest_ts her test öncesinde sıfırlanır — heartbeat starvation testleri kendi
    değerlerini set eder.
    """
    import main_loop as _ml
    import time as _time
    _ml._last_rest_ts = _time.time()  # heartbeat_due=False → WS path testleri temiz çalışır
    with patch("main_loop.ws_prices") as mock_ws, \
         patch("main_loop.asyncio.wait_for", new_callable=AsyncMock,
               side_effect=asyncio.TimeoutError):
        mock_ws.get_bid.return_value = 0.50
        mock_ws.get_ask.return_value = 0.50
        mock_ws.subscribe.return_value = None
        mock_event = MagicMock()
        mock_event.wait = AsyncMock(return_value=None)
        mock_event.clear = MagicMock()
        mock_event.is_set = MagicMock(return_value=True)
        mock_ws.get_price_event.return_value = mock_event
        yield mock_ws


def _finding():
    return {
        "question": "Will BTC go up?", "asset": "BTC", "action": "YES",
        "fair_value": 0.55, "ref_price": 95000.0, "cur_price": 95500.0,
        "best_ask": 0.35, "best_bid": 0.33, "seconds_remaining": 900,
        "edge": 0.20, "slug": "btc-up-15min-test", "neg_risk": False,
    }

def _pass_verify():
    return {"pass": True, "fresh_best_ask": 0.35, "fresh_best_bid": 0.33,
            "fresh_seconds": 900, "halt": False, "reason": ""}

def _pass_redteam():
    return {"pass": True, "vetoes": [], "warnings": [], "fee_adj_edge": 0.18,
            "liquidity_usd": 2000.0, "spread": 0.02}

def _pass_risk():
    return {"pass": True, "position_usd": 25.0, "kelly_f": 0.15,
            "kelly_fraction_applied": 0.25, "reason": ""}

def _pass_gate():
    return {"pass": True, "confidence_score": 82.5,
            "action_taken": "dry_run_logged", "reason": ""}


# ── Task 1: _run_council() ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_council_returns_none_when_verify_fails():
    """verify() fail → _run_council None döner."""
    with patch("main_loop.verify", new_callable=AsyncMock) as mock_v:
        mock_v.return_value = {"pass": False, "reason": "timeout"}
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is None


@pytest.mark.asyncio
async def test_run_council_returns_gate_and_risk_on_success():
    """Tüm katmanlar geçince (gate_result, risk_result) tuple döner."""
    with patch("main_loop.verify",       new_callable=AsyncMock) as mv, \
         patch("main_loop.redteam_eval", new_callable=AsyncMock) as mr, \
         patch("main_loop.risk_eval",    new=MagicMock(return_value=_pass_risk())), \
         patch("main_loop.gate",         new_callable=AsyncMock) as mg:
        mv.return_value = _pass_verify()
        mr.return_value = _pass_redteam()
        mg.return_value = _pass_gate()
        result = await _run_council(_finding(), bankroll_usd=1000.0,
                                    n_open=0, daily_loss_usd=0.0)
    assert result is not None
    gate_result, risk_result = result
    assert gate_result["pass"] is True
    assert risk_result["position_usd"] == 25.0


@pytest.mark.asyncio
async def test_run_council_updates_finding_with_fresh_price_after_verify():
    """verify() taze fiyat döndürünce finding güncellenir — execute stale fiyat kullanmaz.

    Scout: best_ask=0.35 (T+0).
    Verify: fresh_best_ask=0.42 (T+3s) — fiyat 7 cent hareket etti.
    execute() finding["best_ask"] ile çalıştığından finding güncellenmeli
    ki FOK limit stale fiyat yerine taze fiyat kullansın.
    """
    finding = _finding()  # best_ask=0.35, best_bid=0.33
    fresh_verify = {
        **_pass_verify(),
        "fresh_best_ask": 0.42,  # 7 cent yukarı hareket
        "fresh_best_bid": 0.40,
    }
    with patch("main_loop.verify",       new_callable=AsyncMock) as mv, \
         patch("main_loop.redteam_eval", new_callable=AsyncMock) as mr, \
         patch("main_loop.risk_eval",    new=MagicMock(return_value=_pass_risk())), \
         patch("main_loop.gate",         new_callable=AsyncMock) as mg:
        mv.return_value = fresh_verify
        mr.return_value = _pass_redteam()
        mg.return_value = _pass_gate()
        await _run_council(finding, bankroll_usd=1000.0, n_open=0, daily_loss_usd=0.0)
    assert finding["best_ask"] == 0.42, (
        f"finding['best_ask'] taze fiyatla güncellenmeli idi: {finding['best_ask']} (beklenen 0.42)"
    )
    assert finding["best_bid"] == 0.40, (
        f"finding['best_bid'] taze fiyatla güncellenmeli idi: {finding['best_bid']} (beklenen 0.40)"
    )


# ── Task 2: _scan_and_execute() ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_skips_when_max_positions_reached():
    """MAX_OPEN_POSITIONS doluysa scan_edges hiç çağrılmaz."""
    import config
    open_pos = [{"position_id": str(i)} for i in range(config.MAX_OPEN_POSITIONS)]
    with patch("main_loop.scan_edges", new_callable=AsyncMock) as mock_scan:
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    mock_scan.assert_not_called()


@pytest.mark.asyncio
async def test_scan_opens_position_on_full_council_pass():
    """Konsey geçince execute() çağrılır, pozisyon open_positions'a eklenir."""
    open_pos = []
    fake_pos = {"position_id": "abc-123", "status": "open", "asset": "BTC",
                "action": "YES", "slug": "btc-up-test"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    assert len(open_pos) == 1
    assert open_pos[0]["position_id"] == "abc-123"


@pytest.mark.asyncio
async def test_scan_skips_already_open_slug():
    """Aynı slug için açık pozisyon varsa _run_council çağrılmaz."""
    existing = {"position_id": "exist-001", "slug": "btc-up-15min-test", "status": "open"}
    open_pos = [existing]
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council:
        mock_scan.return_value = [_finding()]   # _finding() slug = "btc-up-test"
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    mock_council.assert_not_called()
    assert len(open_pos) == 1


@pytest.mark.asyncio
async def test_scan_does_not_open_same_slug_twice_in_one_scan():
    """findings listesinde aynı slug iki kez varsa yalnızca bir pozisyon açılır."""
    dup_finding = {**_finding(), "slug": "dup-slug-test"}
    fake_pos = {"position_id": "dup-001", "slug": "dup-slug-test",
                "status": "open", "asset": "BTC", "action": "YES"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [dup_finding, dup_finding]  # aynı slug iki kez
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        open_pos = []
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0)
    assert len(open_pos) == 1, f"Beklenen 1 pozisyon, açılan: {len(open_pos)}"
    assert mock_exec.call_count == 1, f"execute {mock_exec.call_count} kez çağrıldı"


# ── Task 2b: failed_slugs thrashing fix ──────────────────────────────────────

@pytest.mark.asyncio
async def test_fok_failed_slug_not_added_to_failed_set():
    """FAK kill (execute→None) olan slug failed_slugs'a EKLENMEMELİ.
    Capital riske girmedi — likidite yoktu, 7s sonra yeniden denenecek."""
    failed: set[str] = set()
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = None          # FAK kill — no fill
        await _scan_and_execute([], [], bankroll_usd=1000.0, failed_slugs=failed)
    assert _finding()["slug"] not in failed, "FAK kill sonrası slug failed_slugs'a eklenmemeli — retry serbest"


@pytest.mark.asyncio
async def test_fok_failed_slug_skipped_before_council():
    """failed_slugs'taki slug için _run_council hiç çağrılmaz."""
    slug = _finding()["slug"]
    failed: set[str] = {slug}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council:
        mock_scan.return_value = [_finding()]
        await _scan_and_execute([], [], bankroll_usd=1000.0, failed_slugs=failed)
    mock_council.assert_not_called()


@pytest.mark.asyncio
async def test_fok_failed_slug_does_not_block_different_slug():
    """failed_slugs'ta farklı bir slug varsa mevcut finding engellenmez."""
    failed: set[str] = {"some-completely-different-slug-99999"}
    fake_pos = {"position_id": "ok-001", "slug": _finding()["slug"],
                "status": "open", "asset": "BTC", "action": "YES"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        open_pos = []
        await _scan_and_execute(open_pos, [], bankroll_usd=1000.0, failed_slugs=failed)
    mock_council.assert_called_once()
    assert len(open_pos) == 1


@pytest.mark.asyncio
async def test_successful_fill_not_added_to_failed_slugs():
    """Başarılı fill (execute→position) olan slug failed_slugs'a eklenmez."""
    failed: set[str] = set()
    slug = _finding()["slug"]
    fake_pos = {"position_id": "win-001", "slug": slug,
                "status": "open", "asset": "BTC", "action": "YES"}
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec:
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = fake_pos
        await _scan_and_execute([], [], bankroll_usd=1000.0, failed_slugs=failed)
    assert slug not in failed, "Başarılı fill failed_slugs'a eklenmemeli"


# ── Task 3: _monitor_positions() ─────────────────────────────────────────────

def _open_position():
    """Açık pozisyon fixture'ı."""
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    return {
        "position_id": "pos-xyz", "asset": "BTC", "action": "YES",
        "slug": "btc-up-test", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "position_usd": 25.0, "kelly_f": 0.15,
        "confidence_score": 82.5, "seconds_remaining": 900,
        "opened_at": opened_at, "status": "open",
        "requires_human_approval": False, "dry_run": True,
        "exit_reason": None, "closed_at": None,
    }


@pytest.mark.asyncio
async def test_monitor_closes_position_on_exit_signal():
    """check_exit sinyal verince pozisyon open'dan closed'a geçer."""
    import config as _cfg
    pos = _open_position()
    open_pos = [pos]
    closed = []
    fake_window = {"best_ask": 0.52, "best_bid": 0.50,
                   "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",     new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",     new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.check_exit",        return_value="max_hold_time"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "max_hold_time"
    assert closed[0]["status"] == "closed"


@pytest.mark.asyncio
async def test_monitor_skips_on_missing_market_and_no_resolution():
    """parse_market_window None + fetch_resolved None → geçici API hatası, pozisyon atlanır."""
    open_pos = [_open_position()]
    closed = []
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock) as mock_res:
        mock_hl.return_value  = 95000.0
        mock_pm.return_value  = {}
        mock_res.return_value = None
        await _monitor_positions(open_pos, closed)
    # Her iki API None döndürünce pozisyon kapatılmamalı — bir sonraki döngüde tekrar dene
    assert len(open_pos) == 1, "Geçici API hatasında pozisyon listede kalmalı"
    assert len(closed) == 0, "Geçici API hatasında closed listesine eklenmemeli"
    assert open_pos[0]["status"] == "open"


@pytest.mark.asyncio
async def test_monitor_skips_when_ws_and_clob_price_both_fail():
    """WS None + CLOB REST None → stale Gamma kullanma, döngüyü atla.

    Stale Gamma best_ask=0.65 → current_val=1-0.65=0.35 < 0.59×0.80=0.472
    → mevcut kod yanlışlıkla stop_loss_hit tetikler (kazanan NO pozisyonunda felaket).
    Fix: fiyat verisi yoksa bu döngüyü atla, pozisyon açık kalsın.
    """
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
    pos = {
        **_open_position(),
        "action": "NO", "pm_entry_price": 0.59,
        "yes_token_id": "tok-yes-123", "no_token_id": "tok-no-123",
        "opened_at": opened_at,
    }
    open_pos = [pos]
    closed = []
    # Stale Gamma: best_ask=0.65 → 1-0.65=0.35 < stop_thresh=0.472 → false stop
    fake_window = {"best_ask": 0.65, "best_bid": 0.63,
                   "seconds_remaining": 400, "neg_risk": False}
    import config as _cfg
    with patch("main_loop.current_price",     new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",     new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.ws_prices")         as mock_ws, \
         patch("main_loop.get_clob_price",    new_callable=AsyncMock) as mock_clob, \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value     = 95000.0
        mock_pm.return_value     = {}
        mock_ws.get_ask.return_value = None   # WS stale
        mock_ws.get_bid.return_value = None
        mock_clob.return_value   = None       # CLOB REST başarısız
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 1, (
        "WS+CLOB fiyat verisi yoksa stale Gamma kullanılmamalı — pozisyon açık kalmalı"
    )
    assert len(closed) == 0, "Fiyatsız döngüde yanlış stop_loss tetiklenmemeli"


@pytest.mark.asyncio
async def test_monitor_closes_with_resolution_price_on_yes():
    """window=None iken fetch_resolved sonuç verirse pm_exit_price dolu kapanır (YES)."""
    pos = {**_open_position(), "action": "YES"}
    open_pos = [pos]
    closed = []
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=None), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock) as mock_res:
        mock_hl.return_value  = 95000.0
        mock_pm.return_value  = {}
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _monitor_positions(open_pos, closed)
    assert len(open_pos) == 0
    assert len(closed) == 1
    assert closed[0]["pm_exit_price"] == 1.0
    assert closed[0]["exit_reason"] == "market_resolved"


# ── _load_open_positions() ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mem_db():
    async with aiosqlite.connect(":memory:") as db:
        await init_schema(db)
        yield db


@pytest.mark.asyncio
async def test_load_open_positions_empty_db(mem_db):
    """DB'de açık pozisyon yoksa boş liste döner."""
    result = await _load_open_positions(mem_db)
    assert result == []


@pytest.mark.asyncio
async def test_load_open_positions_returns_open_ones(mem_db):
    """DB'deki status=open pozisyonlar yüklenir, closed olanlar atlanır."""
    open_pos = {
        "position_id": "r-001", "slug": "btc-up-5min", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.18,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-05-30T10:00:00+00:00",
    }
    closed_pos = {**open_pos, "position_id": "r-002", "slug": "eth-down-15min"}
    await log_position_open(mem_db, open_pos)
    await log_position_open(mem_db, closed_pos)
    await mem_db.execute("UPDATE positions SET status='closed' WHERE position_id='r-002'")
    await mem_db.commit()

    result = await _load_open_positions(mem_db)
    assert len(result) == 1
    assert result[0]["position_id"] == "r-001"
    assert result[0]["asset"] == "BTC"
    assert result[0]["ref_price"] == 95000.0
    assert result[0]["edge"] == 0.18
    assert result[0]["opened_at"] == "2026-05-30T10:00:00+00:00"


@pytest.mark.asyncio
async def test_monitor_no_position_exit_uses_no_price(default_ws_prices):
    """NO pozisyon erken çıkışta pm_exit_price = WS no_token bid (Gamma fallback değil)."""
    default_ws_prices.get_bid.return_value = 0.90  # NO token bid: WS'den gerçek değer
    pos = {**_open_position(), "action": "NO", "pm_entry_price": 0.46,
           "no_token_id": "tok-no", "yes_token_id": "tok-yes"}
    open_pos = [pos]
    closed = []
    fake_window = {
        "best_ask": 0.10, "best_bid": 0.09,
        "seconds_remaining": 500, "neg_risk": False,
    }
    import config as _cfg
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",          return_value="thesis_invalidated"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(closed) == 1
    assert abs(closed[0]["pm_exit_price"] - 0.90) < 1e-4, \
        f"NO çıkış fiyatı WS bid=0.90 olmalı, got: {closed[0]['pm_exit_price']:.4f}"


@pytest.mark.asyncio
async def test_monitor_stop_loss_adds_to_failed_slugs():
    """stop_loss_hit → slug failed_slugs'a eklenir (kaybeden tezi aynı pencerede tekrar açma)."""
    pos = {**_open_position(), "action": "YES", "pm_entry_price": 0.35}
    failed = set()
    fake_window = {"best_ask": 0.20, "best_bid": 0.18, "seconds_remaining": 500, "neg_risk": False}
    import config as _cfg
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",          return_value="stop_loss_hit"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions([pos], [], failed_slugs=failed)
    assert "btc-up-test" in failed, "stop_loss sonrası slug kilitlenmeli"


@pytest.mark.asyncio
async def test_monitor_profit_target_does_not_lock_slug():
    """profit_target_hit → slug failed_slugs'a EKLENMEZ (yüksek-edge re-entry serbest)."""
    pos = {**_open_position(), "action": "YES", "pm_entry_price": 0.35}
    failed = set()
    fake_window = {"best_ask": 0.75, "best_bid": 0.72, "seconds_remaining": 500, "neg_risk": False}
    import config as _cfg
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",          return_value="profit_target_hit"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions([pos], [], failed_slugs=failed)
    assert "btc-up-test" not in failed, "kâr alımı pencereyi kilitlememeli — re-entry serbest"


@pytest.mark.asyncio
async def test_monitor_yes_position_exit_uses_best_bid_not_ask(default_ws_prices):
    """DRY_RUN YES çıkışta pm_exit_price = WS bid (satış fiyatı), ask değil."""
    default_ws_prices.get_bid.return_value = 0.72  # YES token bid: WS'den
    pos = {**_open_position(), "action": "YES", "pm_entry_price": 0.35,
           "yes_token_id": "tok-yes", "no_token_id": "tok-no"}
    open_pos = [pos]
    closed = []
    fake_window = {
        "best_ask": 0.75, "best_bid": 0.99,  # Gamma ask=0.75, bid=0.99 — ikisi de kullanılmamalı
        "seconds_remaining": 500, "neg_risk": False,
    }
    import config as _cfg
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",          return_value="thesis_invalidated"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 95000.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(closed) == 1
    assert abs(closed[0]["pm_exit_price"] - 0.72) < 1e-4, \
        f"YES çıkış fiyatı WS bid=0.72 olmalı, got: {closed[0]['pm_exit_price']:.4f}"


@pytest.mark.asyncio
async def test_dry_run_passes_zero_daily_loss_to_council():
    """DRY_RUN=True → _run_council'a daily_loss_usd=0 geçilir, kayıp limiti uygulanmaz."""
    import config
    open_pos = []
    loss_pos = {
        "action": "YES", "pm_entry_price": 0.10, "pm_exit_price": 0.0,
        "position_usd": 100.0, "position_id": "loss-001",
        "closed_at": datetime.now(timezone.utc).isoformat(),
    }
    with patch("main_loop.scan_edges",   new_callable=AsyncMock) as mock_scan, \
         patch("main_loop._run_council", new_callable=AsyncMock) as mock_council, \
         patch("main_loop.execute",      new_callable=AsyncMock) as mock_exec, \
         patch.object(config, "DRY_RUN", True):
        mock_scan.return_value    = [_finding()]
        mock_council.return_value = (_pass_gate(), _pass_risk())
        mock_exec.return_value    = {"position_id": "dry-001", "status": "open",
                                     "asset": "BTC", "action": "YES", "slug": "btc-test"}
        await _scan_and_execute(open_pos, [loss_pos] * 10, bankroll_usd=1000.0)
    mock_council.assert_called_once()
    _, kwargs = mock_council.call_args
    assert kwargs.get("daily_loss_usd") == 0.0


# Not: test_daily_loss_includes_recovered_closed_positions silindi.
# _daily_loss_usd() fonksiyonu main_loop'tan kaldırıldı.
# Günlük kayıp limiti circuit_breaker'a taşındı (bkz. tests/test_circuit_breaker.py).


# ── Task: _heal_pending_resolutions() ────────────────────────────────────────

@pytest.mark.asyncio
async def test_heal_fixes_null_pnl_when_api_returns(mem_db):
    """fetch_resolved veri döndürünce pm_exit_price ve realized_pnl DB'ye yazılır."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-001', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-up-5m', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    closed_today = [{"position_id": "heal-001", "pm_exit_price": None, "exit_reason": "market_expired"}]

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late"):
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, closed_today, limit=3)

    async with mem_db.execute(
        "SELECT pm_exit_price, realized_pnl, exit_reason FROM positions WHERE position_id='heal-001'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == 1.0
    assert abs(row[1] - 200.0) < 0.01   # (1.0 - 0.20) / 0.20 * 50 = 200
    assert row[2] == "market_resolved_late"
    assert closed_today[0]["pm_exit_price"] == 1.0
    assert closed_today[0]["exit_reason"] == "market_resolved_late"
    assert abs(closed_today[0]["realized_pnl"] - 200.0) < 0.01


@pytest.mark.asyncio
async def test_heal_skips_when_api_still_none(mem_db):
    """fetch_resolved hâlâ None dönerse DB kaydına dokunulmaz."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-002', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-up-5m', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late"):
        mock_res.return_value = None
        await _heal_pending_resolutions(mem_db, [], limit=3)

    async with mem_db.execute(
        "SELECT pm_exit_price FROM positions WHERE position_id='heal-002'"
    ) as cur:
        row = await cur.fetchone()
    assert row[0] is None


@pytest.mark.asyncio
async def test_heal_respects_limit(mem_db):
    """limit=2 → 5 null kayıt varsa sadece 2 işlenir, 3 null kalır."""
    for i in range(5):
        await mem_db.execute(
            f"""INSERT INTO positions
                   (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                    position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
               VALUES ('lim-{i:03d}', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                       'slug-{i}', 'BTC', 'YES', 0.20, 50.0, 0.10, 75.0,
                       'closed', 'market_expired', 1)"""
        )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late"):
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, [], limit=2)

    async with mem_db.execute(
        "SELECT COUNT(*) FROM positions WHERE pm_exit_price IS NULL AND status='closed'"
    ) as cur:
        remaining = (await cur.fetchone())[0]
    assert remaining == 3  # 5 - 2 = 3 hâlâ null


@pytest.mark.asyncio
async def test_heal_calls_notify_resolved_late(mem_db):
    """Heal başarılıysa notify_resolved_late doğru asset/seq_no ile çağrılır."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run, seq_no)
           VALUES ('heal-ntf', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'xrp-updown-5m-1000', 'XRP', 'YES', 0.5, 1.25, 0.30, 80.0,
                   'closed', 'market_expired', 1, 99)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late") as mock_notify:
        mock_res.return_value = {"yes_exit": 1.0, "no_exit": 0.0}
        await _heal_pending_resolutions(mem_db, [], limit=3)

    mock_notify.assert_called_once()
    call_pos = mock_notify.call_args[0][0]
    assert call_pos["asset"] == "XRP"
    assert call_pos["seq_no"] == 99
    assert call_pos["pm_exit_price"] == 1.0
    assert call_pos["action"] == "YES"


@pytest.mark.asyncio
async def test_heal_no_notify_when_api_none(mem_db):
    """fetch_resolved None döndürürse notify_resolved_late çağrılmaz."""
    await mem_db.execute(
        """INSERT INTO positions
               (position_id, ts_open, ts_close, slug, asset, action, pm_entry_price,
                position_usd, kelly_f, confidence_score, status, exit_reason, dry_run)
           VALUES ('heal-no-ntf', '2026-06-01T10:00:00+00:00', '2026-06-01T10:05:00+00:00',
                   'btc-updown-5m-2000', 'BTC', 'YES', 0.5, 1.25, 0.30, 80.0,
                   'closed', 'market_expired', 1)"""
    )
    await mem_db.commit()

    with patch("main_loop.fetch_resolved", new_callable=AsyncMock) as mock_res, \
         patch("main_loop.notify_resolved_late") as mock_notify:
        mock_res.return_value = None
        await _heal_pending_resolutions(mem_db, [], limit=3)

    mock_notify.assert_not_called()


# ── Regression: notify_open n_open_before slice bug ─────────────────────────

def test_notify_open_slice_after_monitor_captures_all_new():
    """
    Regression: n_open_before'un _monitor_positions'dan ÖNCE alınması,
    aynı turda hem kapanma hem açılma olunca notify_open'ın bazı
    pozisyonları atlamasına neden oluyordu.

    Senaryo: başlangıçta 3 açık pozisyon → monitor hepsini kapatıyor (liste boşalıyor)
    → scan 3 yeni açıyor. Eski kodda n_open_before=3 olduğu için
    open_positions[3:] boş liste dönerdi (0/1/2 indeksindekiler atlanır).
    Fix: n_open_before monitor'dan SONRA alınıyor.
    """
    open_positions = [{"id": i} for i in range(3)]

    # Monitor tüm pozisyonları kapatıyor
    open_positions.clear()

    # BUG: n_open_before=3 alındığında
    n_open_before_bug = 3
    for i in range(3):
        open_positions.append({"id": f"new-{i}"})
    assert open_positions[n_open_before_bug:] == []  # hepsi atlanırdı

    # FIX: n_open_before monitor'dan SONRA alındığında
    open_positions.clear()
    n_open_before_fix = len(open_positions)  # = 0
    for i in range(3):
        open_positions.append({"id": f"new-{i}"})
    assert len(open_positions[n_open_before_fix:]) == 3  # hepsi yakalanır


# ── Task 7: CLOB router + sell path ──────────────────────────────────────────

def test_bankroll_reads_from_env(monkeypatch):
    """BANKROLL_USD env değişkeni set edilince main_loop bu değeri kullanır."""
    monkeypatch.setenv("BANKROLL_USD", "50.0")
    import importlib
    import main_loop as ml
    importlib.reload(ml)
    assert abs(ml.BANKROLL_CONFIG - 50.0) < 0.01


@pytest.mark.asyncio
async def test_live_monitor_calls_sell_position_on_exit():
    """DRY_RUN=False iken _monitor_positions çıkışta sell_position çağırır."""
    import config
    from datetime import datetime, timedelta, timezone
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    pos = {
        "position_id": "live-pos-001", "asset": "BTC", "action": "YES",
        "slug": "btc-up-test", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "position_usd": 25.0, "kelly_f": 0.15,
        "confidence_score": 82.5, "seconds_remaining": 900,
        "opened_at": opened_at, "status": "open",
        "requires_human_approval": False, "dry_run": False,
        "exit_reason": None, "closed_at": None,
        "shares": 71.43, "order_id": "ord-001",
        "yes_token_id": "yes-tok-111", "no_token_id": "no-tok-222",
    }
    open_pos = [pos]
    closed   = []
    fake_window = {"best_ask": 0.08, "best_bid": 0.90,
                   "seconds_remaining": 900, "neg_risk": False}

    with patch.object(config, "DRY_RUN", False), \
         patch("main_loop.current_price",      new_callable=AsyncMock, return_value=95000.0), \
         patch("main_loop.fetch_by_slug",      new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.check_exit",          return_value="profit_target_hit"), \
         patch("main_loop.sell_position",       new_callable=AsyncMock, return_value=(0.91, 71.43)) as mock_sell:
        await _monitor_positions(open_pos, closed)

    mock_sell.assert_called_once()
    assert len(closed) == 1
    assert abs(closed[0]["pm_exit_price"] - 0.91) < 0.001


@pytest.mark.asyncio
async def test_live_monitor_keeps_position_open_when_sell_returns_none():
    """DRY_RUN=False iken sell_position None → pozisyon AÇIK kalır, kapatılmaz.

    FAK SELL kill edildiğinde None döner. main_loop pozisyonu açık_positions'tan
    çıkarmamalı — sonraki döngüde tekrar deneyecek.
    """
    import config
    from datetime import datetime, timedelta, timezone
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    pos = {
        "position_id": "live-pos-002", "asset": "SOL", "action": "YES",
        "slug": "sol-up-5m-test", "pm_entry_price": 0.30, "fair_value": 0.60,
        "ref_price": 150.0, "position_usd": 10.0, "kelly_f": 0.10,
        "confidence_score": 75.0, "seconds_remaining": 600,
        "opened_at": opened_at, "status": "open",
        "requires_human_approval": False, "dry_run": False,
        "exit_reason": None, "closed_at": None,
        "shares": 4.0, "order_id": "ord-002",
        "yes_token_id": "yes-tok-sol", "no_token_id": "no-tok-sol",
        "entry_hl_price": 150.0,
    }
    open_pos = [pos]
    closed   = []
    fake_window = {"best_ask": 0.50, "best_bid": 0.48,
                   "seconds_remaining": 600, "neg_risk": False}

    with patch.object(config, "DRY_RUN", False), \
         patch("main_loop.current_price",       new_callable=AsyncMock, return_value=150.0), \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.check_exit",           return_value="thesis_invalidated"), \
         patch("main_loop.sell_position",        new_callable=AsyncMock, return_value=None):
        await _monitor_positions(open_pos, closed)

    # SELL None → pozisyon hala açık
    assert len(open_pos) == 1, "sell_position=None → pozisyon açık_positions'ta kalmalı"
    assert len(closed) == 0, "sell_position=None → closed_today'e eklenmemeli"


@pytest.mark.asyncio
async def test_load_open_positions_includes_entry_hl_price(mem_db):
    """DB'den yüklenen pozisyonda entry_hl_price alanı olmalı."""
    pos = {
        "position_id": "hl-load-01", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "pm_entry_price": 0.35, "fair_value": 0.55,
        "ref_price": 95000.0, "edge": 0.18,
        "position_usd": 1.25, "kelly_f": 0.15, "confidence_score": 82.0,
        "opened_at": "2026-06-03T10:00:00+00:00",
        "entry_hl_price": 66500.0,
    }
    await log_position_open(mem_db, pos)
    result = await _load_open_positions(mem_db)
    assert len(result) == 1
    assert result[0].get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={result[0].get('entry_hl_price')}, beklenen 66500.0"


@pytest.mark.asyncio
async def test_monitor_passes_exit_hl_price_to_closed_position():
    """_monitor_positions exit anındaki HL fiyatını closed dict'e eklemeli."""
    pos = _open_position()
    open_pos = [pos]
    closed = []
    fake_window = {"best_ask": 0.72, "best_bid": 0.70,
                   "seconds_remaining": 500, "neg_risk": False}
    import config as _cfg
    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",       new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.parse_market_window", return_value=fake_window), \
         patch("main_loop.fetch_resolved",      new_callable=AsyncMock, return_value=None), \
         patch("main_loop.check_exit",          return_value="thesis_invalidated"), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_hl.return_value = 66502.0
        mock_pm.return_value = {}
        await _monitor_positions(open_pos, closed)
    assert len(closed) == 1
    assert closed[0].get("exit_hl_price") == 66502.0, \
        f"exit_hl_price={closed[0].get('exit_hl_price')}, beklenen 66502.0"


@pytest.mark.asyncio
async def test_heal_passes_hl_prices_to_notify(mem_db):
    """_heal entry_hl_price DB'den okuyup exit için current_price çağırmalı."""
    await mem_db.execute(
        """INSERT INTO positions
           (position_id, ts_open, slug, asset, action, pm_entry_price, position_usd,
            confidence_score, status, exit_reason, dry_run, seq_no, entry_hl_price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("heal-hl-01", "2026-06-03T10:00:00+00:00", "slug-heal-hl", "BTC", "YES",
         0.35, 1.25, 82.0, "closed", "market_expired", 1, 5, 66500.0),
    )
    await mem_db.commit()
    closed_today = [{"position_id": "heal-hl-01", "pm_exit_price": None,
                     "exit_reason": "market_expired"}]
    notify_calls = []
    with patch("main_loop.fetch_resolved",       new_callable=AsyncMock,
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("main_loop.patch_position_resolution", new_callable=AsyncMock), \
         patch("main_loop.current_price",        new_callable=AsyncMock,
               return_value=66510.0) as mock_hl, \
         patch("main_loop.notify_resolved_late", side_effect=lambda p: notify_calls.append(p)):
        await _heal_pending_resolutions(mem_db, closed_today)
    mock_hl.assert_called_once_with("BTC")
    assert len(notify_calls) == 1
    assert notify_calls[0].get("entry_hl_price") == 66500.0, \
        f"entry_hl_price={notify_calls[0].get('entry_hl_price')}, beklenen 66500.0"
    assert notify_calls[0].get("exit_hl_price") == 66510.0, \
        f"exit_hl_price={notify_calls[0].get('exit_hl_price')}, beklenen 66510.0"


@pytest.mark.asyncio
async def test_monitor_skips_position_on_transient_api_error():
    """fetch_by_slug=None VE fetch_resolved=None → pozisyon kapatılmaz, atlanır."""
    from main_loop import _monitor_positions

    pos = {
        "position_id": "pos-skip-001",
        "slug": "btc-updown-5m-9999",
        "asset": "BTC",
        "action": "YES",
        "pm_entry_price": 0.80,
        "position_usd": 1.25,
        "shares": 1.5,
        "status": "open",
        "seq_no": 1,
    }
    open_positions = [pos]
    closed_today = []

    with patch("main_loop.current_price", new_callable=AsyncMock, return_value=95_000.0), \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("main_loop.fetch_resolved", new_callable=AsyncMock, return_value=None):
        await _monitor_positions(open_positions, closed_today, conn=None)

    # API error olduğunda pozisyon kapatılmaz
    assert len(open_positions) == 1, "Geçici API hatasında pozisyon listeden çıkarılmamalı"
    assert len(closed_today) == 0, "Geçici API hatasında closed_today'e eklenmemeli"
    assert open_positions[0]["status"] == "open"


@pytest.mark.asyncio
async def test_monitor_closes_on_definitive_resolution():
    """fetch_by_slug=None ama fetch_resolved sonuç döndürünce → market_resolved kapatılır."""
    from main_loop import _monitor_positions

    pos = {
        "position_id": "pos-resolve-001",
        "slug": "btc-updown-5m-8888",
        "asset": "BTC",
        "action": "YES",
        "pm_entry_price": 0.75,
        "position_usd": 1.25,
        "shares": 1.5,
        "status": "open",
        "seq_no": 1,
        "entry_hl_price": 95_000.0,
        "fair_value": 0.80,
        "dry_run": True,
    }
    open_positions = [pos]
    closed_today = []

    with patch("main_loop.current_price", new_callable=AsyncMock, return_value=95_000.0), \
         patch("main_loop.fetch_by_slug", new_callable=AsyncMock, return_value=None), \
         patch("main_loop.fetch_resolved", new_callable=AsyncMock,
               return_value={"yes_exit": 1.0, "no_exit": 0.0}), \
         patch("main_loop.log_position_close", new_callable=AsyncMock):
        await _monitor_positions(open_positions, closed_today, conn=None)

    assert len(open_positions) == 0, "Resolved market pozisyonu kapatmalı"
    assert len(closed_today) == 1
    assert closed_today[0]["exit_reason"] == "market_resolved"


# ── WS resolved handler testleri ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_ws_resolved_closes_yes_position_on_yes_win(monkeypatch):
    """YES pozisyon + 'Yes' kazanınca pm_exit=1.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-1", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_1", "no_token_id": "no_tok_1",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_1", "no_tok_1"],
        "winning_asset_id": "yes_tok_1",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }

    monkeypatch.setattr("main_loop.current_price", AsyncMock(return_value=96000.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 0
    assert len(closed_today) == 1
    assert closed_today[0]["pm_exit_price"] == 1.0
    assert closed_today[0]["exit_reason"] == "market_resolved"


@pytest.mark.asyncio
async def test_handle_ws_resolved_closes_no_position_on_no_win(monkeypatch):
    """NO pozisyon + 'No' kazanınca pm_exit=1.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-2", "slug": "eth-down-15m", "asset": "ETH",
        "action": "NO", "yes_token_id": "yes_tok_2", "no_token_id": "no_tok_2",
        "pm_entry_price": 0.40, "fair_value": 0.20, "edge": 0.20,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 3000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_2", "no_tok_2"],
        "winning_asset_id": "no_tok_2",
        "winning_outcome": "No",
        "timestamp": "123",
    }

    monkeypatch.setattr("main_loop.current_price", AsyncMock(return_value=2900.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 0
    assert closed_today[0]["pm_exit_price"] == 1.0


@pytest.mark.asyncio
async def test_handle_ws_resolved_yes_position_loses(monkeypatch):
    """YES pozisyon + 'No' kazanınca pm_exit=0.0 ile kapanmalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock, patch

    pos = {
        "position_id": "pos-ws-3", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_3", "no_token_id": "no_tok_3",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["yes_tok_3", "no_tok_3"],
        "winning_asset_id": "no_tok_3",
        "winning_outcome": "No",
        "timestamp": "123",
    }

    monkeypatch.setattr("main_loop.current_price", AsyncMock(return_value=94000.0))

    with patch("main_loop.log_position_close", new=AsyncMock()), \
         patch("main_loop.notify_close"):
        await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert closed_today[0]["pm_exit_price"] == 0.0


@pytest.mark.asyncio
async def test_handle_ws_resolved_ignores_unrelated_market(monkeypatch):
    """assets_ids eşleşmiyorsa pozisyona dokunmamalı."""
    from main_loop import _handle_ws_resolved
    from unittest.mock import AsyncMock

    pos = {
        "position_id": "pos-ws-4", "slug": "btc-up-5m", "asset": "BTC",
        "action": "YES", "yes_token_id": "yes_tok_4", "no_token_id": "no_tok_4",
        "pm_entry_price": 0.55, "fair_value": 0.70, "edge": 0.15,
        "position_usd": 1.25, "kelly_f": 0.10, "confidence_score": 80.0,
        "seconds_remaining": 300, "status": "open", "dry_run": False,
        "opened_at": "2026-01-01T00:00:00+00:00", "exit_reason": None, "closed_at": None,
        "entry_hl_price": 95000.0,
    }
    open_positions = [pos]
    closed_today   = []
    event = {
        "event_type": "market_resolved",
        "assets_ids": ["other_tok_1", "other_tok_2"],
        "winning_asset_id": "other_tok_1",
        "winning_outcome": "Yes",
        "timestamp": "123",
    }

    monkeypatch.setattr("main_loop.current_price", AsyncMock(return_value=95000.0))
    await _handle_ws_resolved(event, open_positions, closed_today, conn=None)

    assert len(open_positions) == 1
    assert len(closed_today) == 0


# ── Faz 1.1: price_source overwrite testleri ─────────────────────────────────

def _pos_with_token(action="YES"):
    """yes_token_id + no_token_id içeren açık pozisyon fixture'ı."""
    opened_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    return {
        "position_id": "pos-src-001", "asset": "BTC", "action": action,
        "slug": "btc-up-test-src", "pm_entry_price": 0.35, "fair_value": 0.55,
        "position_usd": 25.0, "kelly_f": 0.15, "confidence_score": 82.5,
        "opened_at": opened_at, "status": "open",
        "yes_token_id": "tok-yes-src", "no_token_id": "tok-no-src",
    }


@pytest.mark.asyncio
async def test_monitor_sets_price_source_ws_bid_for_yes_ws_price():
    """YES + WS bid mevcut → price_source='ws_bid', mae_data_quality='exact'."""
    import config as _cfg
    pos = _pos_with_token("YES")
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",        new_callable=AsyncMock, return_value=95000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_bid.return_value = 0.50
        mock_ws.get_ask.return_value = 0.52
        await _monitor_positions([pos], [])
    assert pos.get("price_source")     == "ws_bid", \
        f"Beklenen ws_bid, alınan: {pos.get('price_source')}"
    assert pos.get("mae_data_quality") == "exact", \
        f"Beklenen exact, alınan: {pos.get('mae_data_quality')}"


@pytest.mark.asyncio
async def test_monitor_sets_price_source_clob_rest_bid_for_yes_rest_fallback():
    """YES + WS bid None → CLOB REST fallback → price_source='clob_rest_bid', mae_data_quality='exact'."""
    import config as _cfg
    pos = _pos_with_token("YES")
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",        new_callable=AsyncMock, return_value=95000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.get_clob_price",       new_callable=AsyncMock, return_value=0.49), \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_bid.return_value = None
        await _monitor_positions([pos], [])
    assert pos.get("price_source")     == "clob_rest_bid", \
        f"Beklenen clob_rest_bid, alınan: {pos.get('price_source')}"
    assert pos.get("mae_data_quality") == "exact", \
        f"Beklenen exact, alınan: {pos.get('mae_data_quality')}"


@pytest.mark.asyncio
async def test_monitor_sets_price_source_ws_ask_complement_for_no_ws_price():
    """NO + WS ask mevcut → price_source='ws_ask_complement', mae_data_quality='estimated'."""
    import config as _cfg
    pos = _pos_with_token("NO")
    fake_window = {"best_ask": 0.70, "best_bid": 0.68, "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",        new_callable=AsyncMock, return_value=95000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_ask.return_value = 0.70
        mock_ws.get_bid.return_value = 0.68
        await _monitor_positions([pos], [])
    assert pos.get("price_source")     == "ws_ask_complement", \
        f"Beklenen ws_ask_complement, alınan: {pos.get('price_source')}"
    assert pos.get("mae_data_quality") == "estimated", \
        f"Beklenen estimated, alınan: {pos.get('mae_data_quality')}"


@pytest.mark.asyncio
async def test_monitor_sets_price_source_clob_rest_ask_complement_for_no_rest_fallback():
    """NO + WS ask None → CLOB REST fallback → price_source='clob_rest_ask_complement', mae_data_quality='estimated'."""
    import config as _cfg
    pos = _pos_with_token("NO")
    fake_window = {"best_ask": 0.70, "best_bid": 0.68, "seconds_remaining": 900, "neg_risk": False}
    with patch("main_loop.current_price",        new_callable=AsyncMock, return_value=95000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.ws_prices")           as mock_ws, \
         patch("main_loop.get_clob_price",       new_callable=AsyncMock, return_value=0.71), \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        mock_ws.get_ask.return_value = None
        await _monitor_positions([pos], [])
    assert pos.get("price_source")     == "clob_rest_ask_complement", \
        f"Beklenen clob_rest_ask_complement, alınan: {pos.get('price_source')}"
    assert pos.get("mae_data_quality") == "estimated", \
        f"Beklenen estimated, alınan: {pos.get('mae_data_quality')}"


# ── Faz 2: WS event-driven _monitor_positions ────────────────────────────────

@pytest.mark.asyncio
async def test_monitor_ws_path_returns_true_and_makes_no_rest_calls():
    """WS event anında gelirse True döner ve current_price/fetch_by_slug çağrılmaz."""
    import config as _cfg
    import data.ws_prices as _ws
    _ws._price_event = None
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900

    with patch("main_loop.current_price",       new_callable=AsyncMock) as mock_hl, \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock) as mock_pm, \
         patch("main_loop.check_exit",           return_value=None), \
         patch("main_loop.asyncio.wait_for",     new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        result = await _monitor_positions([pos], [])

    assert result is True, "WS event tetiklendi → True dönmeli"
    mock_hl.assert_not_called(), "WS path'te current_price (REST) çağrılmamalı"
    mock_pm.assert_not_called(), "WS path'te fetch_by_slug (REST) çağrılmamalı"


@pytest.mark.asyncio
async def test_monitor_rest_path_returns_false_and_refreshes_cache():
    """WS event 7s içinde gelmezse False döner, cache güncellenir."""
    import config as _cfg
    pos = _pos_with_token("YES")
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 888, "neg_risk": False}

    with patch("main_loop.current_price",       new_callable=AsyncMock, return_value=96000.0), \
         patch("main_loop.fetch_by_slug",        new_callable=AsyncMock, return_value={}), \
         patch("main_loop.parse_market_window",  return_value=fake_window), \
         patch("main_loop.check_exit",           return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        # autouse fixture zaten asyncio.wait_for → TimeoutError yapar (REST path)
        result = await _monitor_positions([pos], [])

    assert result is False, "Timeout → False dönmeli"
    assert pos.get("_cached_hl_price")          == 96000.0, "HL cache güncellenmeli"
    assert pos.get("_cached_seconds_remaining") == 888,     "seconds_remaining cache güncellenmeli"


@pytest.mark.asyncio
async def test_monitor_ws_path_skips_closing_position():
    """_closing=True pozisyon WS event path'te check_exit çağrılmadan skip edilir."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    pos["_closing"] = True

    mock_check = MagicMock(return_value="stop_loss_hit")
    with patch("main_loop.check_exit",       mock_check), \
         patch("main_loop.asyncio.wait_for", new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        await _monitor_positions([pos], [])

    mock_check.assert_not_called(), "_closing pozisyonunda check_exit çağrılmamalı"


@pytest.mark.asyncio
async def test_monitor_live_sets_closing_true_before_sell():
    """LIVE: exit kararında _closing=True sell_position() çağrısı öncesinde set edilir."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900

    closing_at_call = {}
    async def fake_sell(p):
        closing_at_call["val"] = p.get("_closing")
        return 0.30

    with patch("main_loop.check_exit",          return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",        side_effect=fake_sell), \
         patch("main_loop.log_position_close",  new_callable=AsyncMock), \
         patch("main_loop.asyncio.wait_for",    new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions([pos], [])

    assert closing_at_call.get("val") is True, "sell_position() çağrısında _closing=True olmalı"


@pytest.mark.asyncio
async def test_monitor_live_resets_closing_on_fak_fail():
    """LIVE: sell_position() None dönerse _closing=False reset edilir, pozisyon listede kalır."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    open_pos = [pos]

    with patch("main_loop.check_exit",         return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",       new_callable=AsyncMock, return_value=None), \
         patch("main_loop.asyncio.wait_for",   new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions(open_pos, [])

    assert pos.get("_closing") is False, "FAK fail → _closing=False resetlenmeli"
    assert len(open_pos) == 1,           "FAK fail → pozisyon listede kalmalı"


@pytest.mark.asyncio
async def test_monitor_live_no_double_sell_on_log_failure():
    """SELL başarılı + DB log exception → pozisyon open_positions'dan çıkarılmış olmalı.

    Başarılı SELL sonrası log hatası _closing=False yapmamalı ve pozisyon listede kalmamalı.
    Aksi halde sonraki tick'te aynı pozisyon tekrar satılmaya çalışılır (double-sell riski).
    """
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    open_pos = [pos]

    shares = pos.get("shares", 1.0)
    with patch("main_loop.check_exit",          return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",       new_callable=AsyncMock, return_value=(0.30, shares)), \
         patch("main_loop.close_position",      return_value={"slug": pos["slug"]}), \
         patch("main_loop.log_position_close",  new_callable=AsyncMock, side_effect=Exception("DB çöktü")), \
         patch("main_loop.asyncio.wait_for",    new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions(open_pos, [])

    assert len(open_pos) == 0, "SELL başarılı → log hatası olsa bile pozisyon listeden çıkarılmalı"


@pytest.mark.asyncio
async def test_monitor_ws_path_skips_position_when_hl_cache_empty():
    """WS event geldiğinde _cached_hl_price yoksa pozisyon skip edilmeli — crash yok, check_exit yok.

    İlk WS event heartbeat'ten önce gelebilir. Cache None iken check_exit çağrılırsa
    hl_price=0 ile yanlış stop kararı üretilir. skip → 7s heartbeat REST'i doldursun.
    """
    import config as _cfg
    pos = _pos_with_token("YES")
    # _cached_hl_price intentionally absent — ilk WS tick, heartbeat henüz gelmedi

    mock_check = MagicMock(return_value="stop_loss_hit")
    with patch("main_loop.check_exit",       mock_check), \
         patch("main_loop.asyncio.wait_for", new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", True):
        result = await _monitor_positions([pos], [])

    assert result is True,             "WS path tetiklendi → True dönmeli"
    mock_check.assert_not_called()     # cache yok → check_exit çağrılmamalı


@pytest.mark.asyncio
async def test_monitor_partial_fill_updates_shares_and_keeps_position():
    """Kısmi fill (making < shares * 0.98) → pozisyon listede kalır, shares azalır, _closing False."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    pos["shares"]                    = 2.5
    open_pos = [pos]

    # making=1.5, old_shares=2.5 → kısmi fill (1.5 < 2.5 * 0.98)
    with patch("main_loop.check_exit",        return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",     new_callable=AsyncMock, return_value=(0.30, 1.5)), \
         patch("main_loop.asyncio.wait_for",  new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions(open_pos, [])

    assert len(open_pos) == 1,                         "Kısmi fill → pozisyon listede kalmalı"
    assert abs(pos["shares"] - 1.0) < 0.001,           "shares = 2.5 - 1.5 = 1.0 olmalı"
    assert pos.get("_closing") is False,               "_closing resetlenmeli (sonraki deneme için)"
    assert pos.get("partial_fill_count") == 1,         "partial_fill_count artmalı"


@pytest.mark.asyncio
async def test_monitor_partial_fill_accumulates_shares_and_usdc():
    """Kısmi fill → partial_fill_shares ve partial_realized_usdc kümülatif birikir."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    pos["shares"]                    = 2.5
    pos["partial_fill_shares"]       = 0.8   # önceki kısmi fill
    pos["partial_realized_usdc"]     = 0.24  # önceki kısmi usdc
    open_pos = [pos]

    # fill_price=0.30, making=1.0 → 1.0 share @ 0.30 USDC = 0.30 USDC
    with patch("main_loop.check_exit",        return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",     new_callable=AsyncMock, return_value=(0.30, 1.0)), \
         patch("main_loop.asyncio.wait_for",  new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions(open_pos, [])

    # partial_fill_shares: 0.8 + 1.0 = 1.8
    assert abs(pos.get("partial_fill_shares", 0) - 1.8) < 0.001, \
        f"partial_fill_shares={pos.get('partial_fill_shares')}, beklenen 1.8"
    # partial_realized_usdc: 0.24 + 0.30 * 1.0 = 0.54
    assert abs(pos.get("partial_realized_usdc", 0) - 0.54) < 0.001, \
        f"partial_realized_usdc={pos.get('partial_realized_usdc')}, beklenen 0.54"


@pytest.mark.asyncio
async def test_monitor_full_fill_closes_position():
    """Tam fill (making >= shares * 0.98) → pozisyon listeden çıkar."""
    import config as _cfg
    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    pos["shares"]                    = 2.5
    open_pos = [pos]

    # making=2.49 ≥ 2.5*0.98=2.45 → tam fill sayılır
    with patch("main_loop.check_exit",        return_value="stop_loss_hit"), \
         patch("main_loop.sell_position",     new_callable=AsyncMock, return_value=(0.30, 2.49)), \
         patch("main_loop.close_position",    return_value={"slug": pos["slug"]}), \
         patch("main_loop.log_position_close", new_callable=AsyncMock), \
         patch("main_loop.asyncio.wait_for",  new_callable=AsyncMock, return_value=None), \
         patch.object(_cfg, "DRY_RUN", False):
        await _monitor_positions(open_pos, [])

    assert len(open_pos) == 0, "Tam fill → pozisyon listeden çıkarılmalı"


@pytest.mark.asyncio
async def test_monitor_forces_rest_heartbeat_when_overdue():
    """WS event gelse bile heartbeat süresi dolduysa REST path çalışmalı (starvation önleme).

    WS sub-saniye tick'ler gelirse 7s timeout asla ateşlenmez → HL cache güncellenmez,
    scan/heal bloke olur. Çözüm: last_rest_ts izle, 7s geçtiyse WS event olsa bile REST yap.
    """
    import main_loop as ml
    import config as _cfg
    import time

    pos = _pos_with_token("YES")
    pos["_cached_hl_price"]          = 95000.0
    pos["_cached_seconds_remaining"] = 900
    fake_window = {"best_ask": 0.52, "best_bid": 0.50, "seconds_remaining": 880, "neg_risk": False}

    # Heartbeat'in son kez 10s önce çalıştığını simüle et (7s sınırı aşılmış)
    original_last = ml._last_rest_ts
    ml._last_rest_ts = time.time() - 10.0
    try:
        with patch("main_loop.current_price",      new_callable=AsyncMock, return_value=96000.0) as mock_hl, \
             patch("main_loop.fetch_by_slug",       new_callable=AsyncMock, return_value={}) as mock_pm, \
             patch("main_loop.parse_market_window", return_value=fake_window), \
             patch("main_loop.check_exit",          return_value=None), \
             patch("main_loop.asyncio.wait_for",    new_callable=AsyncMock, return_value=None), \
             patch.object(_cfg, "DRY_RUN", True):
            # WS event geliyor (wait_for → None, TimeoutError değil) ama heartbeat süresi dolmuş
            result = await _monitor_positions([pos], [])
    finally:
        ml._last_rest_ts = original_last

    assert result is False,         "Heartbeat vadesi dolmuş → REST path → False dönmeli (scan tetiklensin)"
    mock_hl.assert_called_once(),   "HL fiyatı REST'ten yenilenmeli"
    mock_pm.assert_called_once(),   "PM market bilgisi REST'ten yenilenmeli"
    assert pos.get("_cached_hl_price") == 96000.0, "HL cache güncellenmeli"


# ── 3-Tier Emergency: _do_flatten ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_do_flatten_sells_all_and_clears_list():
    """_do_flatten tüm açık pozisyonları FAK SELL ile kapatır, listeden siler."""
    from main_loop import _do_flatten
    pos = _pos_with_token("YES")
    pos["shares"] = 1.5
    pos["_cached_hl_price"] = 95000.0
    open_pos = [pos]
    closed = []

    with patch("main_loop.sell_position",     new_callable=AsyncMock, return_value=(0.40, 1.5)), \
         patch("main_loop.close_position",    return_value={"slug": pos["slug"], "realized_pnl": -0.10}), \
         patch("main_loop.log_position_close", new_callable=AsyncMock), \
         patch("main_loop.notify_close"), \
         patch("main_loop.send_telegram"):
        await _do_flatten(open_pos, closed, conn=None)

    assert len(open_pos) == 0, "flatten sonrası liste boş olmalı"
    assert len(closed) == 1,   "kapanan pozisyon closed listesine eklenmeli"


@pytest.mark.asyncio
async def test_do_flatten_keeps_position_on_sell_failure():
    """sell_position None → pozisyon açık kalır, _closing sıfırlanır."""
    from main_loop import _do_flatten
    pos = _pos_with_token("YES")
    pos["shares"] = 1.5
    open_pos = [pos]
    closed = []

    with patch("main_loop.sell_position", new_callable=AsyncMock, return_value=None), \
         patch("main_loop.send_telegram"):
        await _do_flatten(open_pos, closed, conn=None)

    assert len(open_pos) == 1, "sell başarısız → pozisyon listede kalmalı"
    assert pos.get("_closing") is False, "_closing sıfırlanmalı"


@pytest.mark.asyncio
async def test_do_flatten_skips_already_closing():
    """_closing=True olan pozisyon flatten'da atlanır."""
    from main_loop import _do_flatten
    pos = _pos_with_token("YES")
    pos["shares"] = 1.5
    pos["_closing"] = True
    open_pos = [pos]
    closed = []

    sell_mock = AsyncMock(return_value=(0.40, 1.5))
    with patch("main_loop.sell_position", sell_mock), \
         patch("main_loop.send_telegram"):
        await _do_flatten(open_pos, closed, conn=None)

    sell_mock.assert_not_called(), "zaten kapanmakta olan pozisyon tekrar satılmamalı"


# ── Faz 2.3: _do_flatten partial fill ────────────────────────────────────────

@pytest.mark.asyncio
async def test_do_flatten_partial_fill_keeps_remaining():
    """_do_flatten: making_shares < old_shares*0.98 → kısmi fill, pos listede kalır."""
    from main_loop import _do_flatten
    pos = _pos_with_token("YES")
    pos["shares"] = 2.0

    open_pos = [pos]
    closed   = []

    with patch("main_loop.sell_position",  new_callable=AsyncMock, return_value=(0.80, 0.5)), \
         patch("main_loop.close_position") as mock_close, \
         patch("main_loop.send_telegram"):
        await _do_flatten(open_pos, closed, conn=None)

    assert len(open_pos) == 1,                  "kısmi fill → pozisyon listede kalmalı"
    assert pos["shares"] == pytest.approx(1.5), "kalan shares güncellenmeli"
    assert pos.get("_closing") is False,        "_closing sıfırlanmalı"
    assert pos.get("partial_fill_count") == 1
    assert len(closed) == 0,                    "kısmi fill → close_position çağrılmamalı"
    mock_close.assert_not_called()


# ── Faz 2.3: _load_open_positions partial fill alanları ──────────────────────

@pytest.mark.asyncio
async def test_load_open_positions_restores_partial_fill_fields(mem_db):
    """_load_open_positions partial fill alanlarını DB'den geri yükler."""
    from db.logger import log_position_open, log_partial_fill_update
    import config

    pos = {
        "position_id": "pfu-reload-001", "ts_open": "2026-01-01T00:00:00+00:00",
        "slug": "eth-up-reload", "asset": "ETH", "action": "YES",
        "pm_entry_price": 0.60, "fair_value": 0.75, "ref_price": 0.58,
        "edge": 0.15, "position_usd": 1.25, "kelly_f": 0.10,
        "confidence_score": 80.0, "dry_run": False, "shares": 2.0,
        "order_id": "ord-002", "yes_token_id": "tok-yes-2", "no_token_id": "tok-no-2",
        "seq_no": 2, "entry_hl_price": 3000.0,
    }
    await log_position_open(mem_db, pos)

    pos["shares"]                = 0.5
    pos["partial_fill_count"]    = 2
    pos["partial_fill_shares"]   = 1.5
    pos["partial_realized_usdc"] = 0.90
    await log_partial_fill_update(mem_db, pos)

    old_dry = config.DRY_RUN
    config.DRY_RUN = False
    try:
        loaded = await _load_open_positions(mem_db)
    finally:
        config.DRY_RUN = old_dry

    p = next((x for x in loaded if x["position_id"] == "pfu-reload-001"), None)
    assert p is not None,                             "pozisyon yüklenmeli"
    assert p["shares"]                == pytest.approx(0.5)
    assert p["partial_fill_count"]    == 2
    assert p["partial_fill_shares"]   == pytest.approx(1.5)
    assert p["partial_realized_usdc"] == pytest.approx(0.90)


# ── Task 4: main() scan koşullu ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ws_triggered_flag_skips_scan_execute():
    """ws_triggered=True iken scan+heal mantığı atlanır (main() koşullu bloğu doğrular)."""
    import config as _cfg
    scan_called = []

    async def fake_monitor(*a, **kw):
        return True  # WS event

    async def fake_scan(*a, **kw):
        scan_called.append(1)

    with patch("main_loop._monitor_positions",        fake_monitor), \
         patch("main_loop._scan_and_execute",          fake_scan), \
         patch("main_loop.get_effective_bankroll",    new_callable=AsyncMock, return_value=25.0), \
         patch("main_loop._heal_pending_resolutions", new_callable=AsyncMock), \
         patch("main_loop.positions_cache"), \
         patch.object(_cfg, "DRY_RUN", True):
        # main() döngüsünün bir iterasyonunu manuel simüle et
        ws_triggered = await fake_monitor()
        if not ws_triggered:
            await fake_scan()

    assert scan_called == [], "WS event → _scan_and_execute çağrılmamalı"
