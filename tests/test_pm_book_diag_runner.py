"""tests/test_pm_book_diag_runner.py — TDD for PM book diagnostic runner.

run_pm_book_diag connects fetch_clob_book -> Decimal sanitizer -> collect_polymarket_book_tick.
Serial interval evidence only. Dedicated lab DB only. No live API. No reference/pairing/math.

First RED: module tools.pm_book_diag_runner does not exist -> ImportError.
"""
import asyncio
import json
import os
import sys

import aiosqlite
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import init_schema
from tools.pm_book_diag_runner import run_pm_book_diag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_YES_TOK = "YES-TOKEN-001"
_NO_TOK  = "NO-TOKEN-002"
_SLUG    = "btc-up-down-5m-1"
_ASSET   = "BTC"
_TF      = "5m"
_BASE    = "https://clob.example.com"
_SLEEP   = 1.0  # minimum allowed

_BOOK_JSON = json.dumps({
    "asks": [{"price": "0.60", "size": "10"}],
    "bids": [{"price": "0.58", "size": "5"}],
})

# ---------------------------------------------------------------------------
# Fake HTTP client infrastructure (aiohttp-like protocol)
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status: int, body: str):
        self.status = status
        self._body = body

    async def text(self):
        return self._body


class _FakeClient:
    """Returns the same response for every token request; tracks calls."""
    def __init__(self, response: _FakeResponse | None = None):
        self._resp = response or _FakeResponse(200, _BOOK_JSON)
        self.calls: list[str] = []

    async def get(self, url, *, params=None, timeout=None):
        self.calls.append((params or {}).get("token_id", ""))
        return self._resp


class _MappedClient:
    """Per-token different response or exception."""
    def __init__(self, mapping: dict):
        self._mapping = mapping
        self.calls: list[str] = []

    async def get(self, url, *, params=None, timeout=None):
        token_id = (params or {}).get("token_id", "")
        self.calls.append(token_id)
        val = self._mapping[token_id]
        if isinstance(val, BaseException):
            raise val
        return val


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

async def _noop_sleep(_):
    pass


def _base_args(db_path, http_client=None, max_captures=1, **extra):
    defaults = dict(
        yes_token_id=_YES_TOK,
        no_token_id=_NO_TOK,
        market_slug=_SLUG,
        asset=_ASSET,
        timeframe=_TF,
        db_path=db_path,
        base_url=_BASE,
        http_client=http_client or _FakeClient(),
        cycle_sleep_seconds=_SLEEP,
        max_captures=max_captures,
        _sleep_fn=_noop_sleep,
    )
    defaults.update(extra)  # extra overrides defaults (e.g. _sleep_fn, _monotonic_fn)
    return defaults


async def _row_count(db_path: str) -> int:
    conn = await aiosqlite.connect(db_path)
    async with conn.execute("SELECT COUNT(*) FROM polymarket_book_ticks") as cur:
        n = (await cur.fetchone())[0]
    await conn.close()
    return n


async def _all_rows(db_path: str) -> list[dict]:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    async with conn.execute("SELECT * FROM polymarket_book_ticks") as cur:
        rows = [dict(r) for r in await cur.fetchall()]
    await conn.close()
    return rows


# ---------------------------------------------------------------------------
# 1. Programmer errors fail fast
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_programmer_errors_fail_fast(tmp_path):
    """All contract violations raise ValueError before the loop starts."""
    db = str(tmp_path / "lab.db")
    client = _FakeClient()
    good = dict(yes_token_id=_YES_TOK, no_token_id=_NO_TOK, market_slug=_SLUG,
                asset=_ASSET, timeframe=_TF, db_path=db, base_url=_BASE,
                http_client=client, cycle_sleep_seconds=_SLEEP, max_captures=1,
                _sleep_fn=_noop_sleep)

    bad_cases = [
        {**good, "yes_token_id": ""},
        {**good, "no_token_id": ""},
        {**good, "yes_token_id": _YES_TOK, "no_token_id": _YES_TOK},  # same token
        {**good, "market_slug": ""},
        {**good, "asset": ""},
        {**good, "timeframe": ""},
        {**good, "db_path": ""},
        {**good, "base_url": ""},
        {**good, "http_client": None},
        {**good, "cycle_sleep_seconds": 0.5},   # < 1.0
        {**good, "cycle_sleep_seconds": 0.0},   # zero
        {**good, "max_captures": None},          # no stop condition (duration_seconds absent)
        {**good, "max_captures": 0},             # max_captures < 1
        {**good, "max_captures": None, "duration_seconds": -1.0},  # negative duration
        {**good, "max_captures": None, "duration_seconds": 0.0},   # zero duration
    ]
    for args in bad_cases:
        with pytest.raises(ValueError):
            await run_pm_book_diag(**args)


# ---------------------------------------------------------------------------
# 2. Explicit token IDs used exactly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explicit_token_ids_used_exactly(tmp_path):
    """Fetcher is called with caller-supplied YES and NO token IDs, in that order."""
    db = str(tmp_path / "lab.db")
    client = _FakeClient()
    await run_pm_book_diag(**_base_args(db, http_client=client, max_captures=1))
    assert client.calls == [_YES_TOK, _NO_TOK]


# ---------------------------------------------------------------------------
# 3. Explicit market_slug / asset / timeframe persisted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explicit_market_slug_asset_timeframe_persisted(tmp_path):
    """Persisted row carries the exact market_slug, asset, and timeframe supplied."""
    db = str(tmp_path / "lab.db")
    await run_pm_book_diag(**_base_args(db, max_captures=1))
    rows = await _all_rows(db)
    assert len(rows) == 1
    assert rows[0]["market_slug"] == _SLUG
    assert rows[0]["asset"] == _ASSET
    assert rows[0]["timeframe"] == _TF
    assert rows[0]["yes_token_id"] == _YES_TOK
    assert rows[0]["no_token_id"] == _NO_TOK


# ---------------------------------------------------------------------------
# 4. Dedicated db_path used; no default DB touched
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dedicated_db_path_used(tmp_path):
    """Row appears in the supplied lab DB. Runner never falls back to a default path."""
    db = str(tmp_path / "my_lab.db")
    await run_pm_book_diag(**_base_args(db, max_captures=1))
    # Row must exist in the exact supplied path
    assert await _row_count(db) == 1


# ---------------------------------------------------------------------------
# 5. max_captures bounds loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_max_captures_bounds_loop(tmp_path):
    """Exactly max_captures rows are written, then loop exits."""
    db = str(tmp_path / "lab.db")
    await run_pm_book_diag(**_base_args(db, max_captures=3))
    assert await _row_count(db) == 3


# ---------------------------------------------------------------------------
# 6. duration_seconds bounds loop with mocked clock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duration_seconds_bounds_loop(tmp_path):
    """Loop exits when _monotonic_fn() >= deadline; captures stop at the right count."""
    db = str(tmp_path / "lab.db")

    # _monotonic_fn call sequence:
    #   call 0 (setup):        0.0  -> deadline = 0.0 + 1.0 = 1.0
    #   call 1 (after cap 1):  0.5  -> 0.5 < 1.0 -> sleep, continue
    #   call 2 (after cap 2):  1.5  -> 1.5 >= 1.0 -> break
    # Result: 2 captures
    _values = [0.0, 0.5, 1.5, 99.0, 99.0]
    _idx = [0]
    def fake_mono():
        v = _values[_idx[0] % len(_values)]
        _idx[0] += 1
        return v

    await run_pm_book_diag(
        yes_token_id=_YES_TOK, no_token_id=_NO_TOK, market_slug=_SLUG,
        asset=_ASSET, timeframe=_TF, db_path=db, base_url=_BASE,
        http_client=_FakeClient(), cycle_sleep_seconds=_SLEEP,
        duration_seconds=1.0,
        _sleep_fn=_noop_sleep, _monotonic_fn=fake_mono,
    )
    assert await _row_count(db) == 2


# ---------------------------------------------------------------------------
# 7. cycle_sleep_seconds enforced between captures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_sleep_enforced(tmp_path):
    """sleep_fn is called with cycle_sleep_seconds after every capture except the last."""
    db = str(tmp_path / "lab.db")
    sleep_calls: list[float] = []

    async def recording_sleep(s: float):
        sleep_calls.append(s)

    await run_pm_book_diag(**_base_args(
        db, max_captures=3, _sleep_fn=recording_sleep,
    ))
    # 3 captures -> sleep between cap1-2 and cap2-3, not after cap3
    assert len(sleep_calls) == 2
    assert all(s == _SLEEP for s in sleep_calls)


# ---------------------------------------------------------------------------
# 8. Partial failure persisted, not dropped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_partial_failure_persisted_not_dropped(tmp_path):
    """YES succeeds but NO times out; row still written with reject_reason noting NO failure."""
    db = str(tmp_path / "lab.db")
    client = _MappedClient({
        _YES_TOK: _FakeResponse(200, _BOOK_JSON),
        _NO_TOK:  asyncio.TimeoutError(),
    })
    await run_pm_book_diag(**_base_args(db, http_client=client, max_captures=1))
    rows = await _all_rows(db)
    assert len(rows) == 1
    assert rows[0]["yes_asks_json"] is not None
    assert rows[0]["no_asks_json"] is None
    assert "missing" in (rows[0]["reject_reason"] or "").lower()


# ---------------------------------------------------------------------------
# 9. Both sides fail — row persisted, loop does not crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_both_fail_persisted_loop_does_not_crash(tmp_path):
    """Both YES and NO fail; row still persisted; loop exits cleanly."""
    db = str(tmp_path / "lab.db")
    client = _MappedClient({
        _YES_TOK: asyncio.TimeoutError(),
        _NO_TOK:  asyncio.TimeoutError(),
    })
    await run_pm_book_diag(**_base_args(db, http_client=client, max_captures=1))
    rows = await _all_rows(db)
    assert len(rows) == 1
    assert rows[0]["reject_reason"] is not None


# ---------------------------------------------------------------------------
# 10. No live API — injected fake client only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_live_api_fake_client_only(tmp_path):
    """Runner succeeds using only the injected fake client; no real network needed."""
    db = str(tmp_path / "lab.db")
    client = _FakeClient(_FakeResponse(200, _BOOK_JSON))
    result = await run_pm_book_diag(**_base_args(db, http_client=client, max_captures=2))
    assert result["captures"] == 2
    assert await _row_count(db) == 2


# ---------------------------------------------------------------------------
# 11. Serial interval timing fields present in row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serial_interval_timing_fields_present(tmp_path):
    """capture_span_ms, yes_no_completion_skew_ms, yes_fetch_span_ms, no_fetch_span_ms all >= 0."""
    db = str(tmp_path / "lab.db")
    await run_pm_book_diag(**_base_args(db, max_captures=1))
    rows = await _all_rows(db)
    row = rows[0]
    for field in ("capture_span_ms", "yes_no_completion_skew_ms",
                  "yes_fetch_span_ms", "no_fetch_span_ms", "fetch_span_ms"):
        assert row[field] is not None and row[field] >= 0, f"{field} must be non-negative"


# ---------------------------------------------------------------------------
# 12. venue_book_ts always missing in row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_venue_ts_always_missing_in_row(tmp_path):
    """venue_book_ts_raw is NULL and venue_book_ts_parse_status is 'missing' in every row."""
    db = str(tmp_path / "lab.db")
    await run_pm_book_diag(**_base_args(db, max_captures=2))
    rows = await _all_rows(db)
    assert len(rows) == 2
    for row in rows:
        assert row["venue_book_ts_raw"] is None
        assert row["venue_book_ts_parse_status"] == "missing"


# ---------------------------------------------------------------------------
# 13. Decimal sanitization: prevents json.dumps crash, emits fixed-point strings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decimal_sanitization_prevents_crash_and_emits_fixed_point(tmp_path):
    """Body with numeric integer literal (parse_int=Decimal) must be sanitized before writer.

    json.dumps in the writer raises TypeError on Decimal objects. The runner's adapter must
    convert Decimal -> fixed-point string via format(d, 'f') so no scientific notation bleeds
    through, and the writer's _dec() can re-parse the string cleanly.
    """
    db = str(tmp_path / "lab.db")
    # Integer size (3) becomes Decimal("3") via parse_int=Decimal.
    # Scientific price (1e-7) becomes Decimal("1E-7") via parse_float=Decimal.
    body = '{"asks": [{"price": 1e-7, "size": 3}], "bids": [{"price": 5e-8, "size": 7}]}'
    client = _FakeClient(_FakeResponse(200, body))

    # Must not raise TypeError from json.dumps inside writer
    await run_pm_book_diag(**_base_args(db, http_client=client, max_captures=1))

    rows = await _all_rows(db)
    assert len(rows) == 1
    row = rows[0]
    # Row must be persisted (not missing due to crash)
    assert row["yes_ask_levels"] is not None
    # Canonical ladder must use fixed-point strings, no 'E'/'e' in the persisted JSON
    for field in ("yes_asks_json", "yes_bids_json"):
        val = row[field] or ""
        assert "E" not in val and "e" not in val, \
            f"{field} must not contain scientific notation, got {val!r}"


# ---------------------------------------------------------------------------
# 14. Module has no forbidden scope
# ---------------------------------------------------------------------------

def test_module_has_no_forbidden_scope():
    """Source-text scan: runner must not touch any forbidden surface."""
    import tools.pm_book_diag_runner as m
    src = open(m.__file__, "r", encoding="utf-8").read().lower()
    for banned in ("gamma", "metadata", "token_map", "proxy_reference_basket_ticks",
                   "reference_book_pairs", "stale_lag", "math.log", "implied",
                   "candidate", "actionability", "response.json"):
        assert banned not in src, f"forbidden term {banned!r} found in pm_book_diag_runner.py"
