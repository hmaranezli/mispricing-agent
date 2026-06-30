"""
Gate G7-lite — default-OFF, diagnostic-only, POST-SIGNAL Coinbase+Kraken proxy capture tests.

  * ZERO NETWORK: the public spot fetchers are driven by an INJECTED fake async client only.
    urllib is hard-patched to raise, proving no live call escapes (test 14).
  * Proxy is NEVER an at-entry reference: it is persisted only as POST_SIGNAL_CAPTURE_DIAGNOSTIC
    with capture-start/complete timestamps and signed skew vs the IMMUTABLE ts_signal_ms.
  * Proxy NEVER influences the core decision projection (candidate side/token, fair value,
    entry_edge, FILLED_ACTIVE/UNFILLED_*); ON vs OFF must be bit-identical for that projection.
  * TRUE_CHAINLINK / Chainlink-aligned fields stay NOT_COMPUTED/null.
  * Temporary SQLite files only; no operational DB, no S1.

Run with:  pytest -q tests/test_gateg7_proxy_telemetry.py
"""

import asyncio
import importlib.util
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg5_plumbing as plumb
from analysis.forensic import gateg7_source_basis as sb

engine = plumb.engine
FillDecision = engine.FillDecision

# load runner (tools/ is not a package)
_SPEC = importlib.util.spec_from_file_location(
    "gateg5_telemetry_runner", "/root/mispricing_agent/tools/gateg5_telemetry_runner.py")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)

# --- explicit fixture constants (declared, never tuned from observed outcomes) ---
SPREAD_BPS = Decimal("50")          # spread-guard threshold for fixtures
TS_SIGNAL = 1_000_000_000_000       # immutable signal timestamp (ms)
CAPTURE_START = TS_SIGNAL + 120      # proxy capture begins 120ms AFTER signal
CAPTURE_DONE = TS_SIGNAL + 540       # proxy capture completes 540ms AFTER signal
HL_PRICE = "60010"


# ---------------------------------------------------------------------------
# injected fake async http client (zero network)
# ---------------------------------------------------------------------------
class FakeClient:
    """async def client(url) -> dict. Maps host substring -> payload; counts calls."""

    def __init__(self, coinbase=None, kraken=None):
        self._cb = coinbase
        self._kr = kraken
        self.calls = []

    async def __call__(self, url):
        self.calls.append(url)
        if "coinbase.com" in url:
            if isinstance(self._cb, Exception):
                raise self._cb
            return self._cb
        if "kraken.com" in url:
            if isinstance(self._kr, Exception):
                raise self._kr
            return self._kr
        raise AssertionError(f"unexpected url {url}")


def _cb_ok(amount="60020"):
    return {"data": {"amount": amount, "base": "BTC", "currency": "USD"}}


def _kr_ok(last="60040"):
    return {"error": [], "result": {"XXBTZUSD": {"c": [last, "0.1"]}}}


def _clock(seq):
    it = iter(seq)
    return lambda: next(it)


def _diag(*, coinbase, kraken, started=CAPTURE_START, completed=CAPTURE_DONE,
          enabled=True, client=None, spread=SPREAD_BPS):
    client = client or FakeClient(coinbase=coinbase, kraken=kraken)
    return runner.proxy_context(
        "BTC", HL_PRICE, TS_SIGNAL,
        enabled=enabled, client=client, clock=_clock([started, completed]),
        spread_bps_threshold=spread), client


# ---------------------------------------------------------------------------
# 1. flag OFF -> zero proxy calls
# ---------------------------------------------------------------------------
def test_flag_off_makes_zero_proxy_calls():
    client = FakeClient(coinbase=_cb_ok(), kraken=_kr_ok())
    out = runner.proxy_context("BTC", HL_PRICE, TS_SIGNAL, enabled=False,
                               client=client, clock=_clock([1, 2]),
                               spread_bps_threshold=SPREAD_BPS)
    assert out is None
    assert client.calls == []


# ---------------------------------------------------------------------------
# 2. valid legs -> POST_SIGNAL_CAPTURE_DIAGNOSTIC
# ---------------------------------------------------------------------------
def test_valid_legs_post_signal_diagnostic():
    diag, client = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    assert diag["proxy_capture_status"] == sb.PROXY_POST_SIGNAL_DIAGNOSTIC
    assert diag["source_basis_mode"] == sb.CHAINLINK_PROXY_ONLY
    assert diag["proxy_ts_provenance"] == sb.PROXY_TS_PROVENANCE_CAPTURE_ONLY
    assert sb.CHAINLINK_PROXY_ONLY in diag["proxy_labels"]
    assert sb.CHAINLINK_PROXY_NOT_CANONICAL in diag["proxy_labels"]
    # midpoint 60020/60040 = 60030; HL 60010 -> basis -20
    assert Decimal(diag["proxy_reference_price"]) == Decimal("60030")
    assert Decimal(diag["proxy_basis_hl_minus_proxy"]) == Decimal("-20")
    assert len(client.calls) == 2


# ---------------------------------------------------------------------------
# 3. ts_signal_ms immutable
# ---------------------------------------------------------------------------
def test_ts_signal_immutable():
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    assert diag["ts_signal_ms"] == TS_SIGNAL  # echoed, never shifted


# ---------------------------------------------------------------------------
# 4. skew fields exact (two separate metrics, not collapsed)
# ---------------------------------------------------------------------------
def test_skew_fields_exact_and_separate():
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    assert diag["proxy_capture_started_ts_ms"] == CAPTURE_START
    assert diag["proxy_capture_completed_ts_ms"] == CAPTURE_DONE
    assert diag["proxy_capture_started_vs_signal_ms"] == CAPTURE_START - TS_SIGNAL   # 120
    assert diag["proxy_lag_after_signal_ms"] == CAPTURE_DONE - TS_SIGNAL             # 540
    # the two metrics are distinct, never merged
    assert diag["proxy_capture_started_vs_signal_ms"] != diag["proxy_lag_after_signal_ms"]


# ---------------------------------------------------------------------------
# 5. ON vs OFF -> bit-identical core decision projection
# ---------------------------------------------------------------------------
NOW_MS = TS_SIGNAL


def _market(**over):
    base = dict(asset="BTC", side="NO", condition_id="cond-1", token_id="tokDown",
                outcome_index=1, outcome_label="Down", slug="btc-updown-15m-1000000000",
                market_end_ts=NOW_MS // 1000 + 600, clobTokenIds=["tokUp", "tokDown"],
                outcomes=["Up", "Down"])
    base.update(over)
    return base


def _book():
    return {"asks": [["0.10", "1000"]], "bids": [["0.05", "1000"]], "quote_ts_ms": NOW_MS - 100}


def _patch_hl(monkeypatch):
    def fake_pf(coin, ts_ms):
        return (Decimal("59000"), NOW_MS - 30_000) if ts_ms == NOW_MS else (Decimal("60000"), ts_ms)
    monkeypatch.setattr(runner, "_hl_price_feedts", fake_pf)
    monkeypatch.setattr(runner, "_hl_sigma_annual", lambda c, n: 0.8)


def _core_projection(monkeypatch):
    ctx = runner._model_context("BTC", _market(), _book(), NOW_MS)
    ns = plumb.normalize_signal(_market(), _book(), ctx, capture_ts_ms=NOW_MS)
    return runner.core_decision_projection(ns)


def test_on_off_core_decision_projection_bit_identical(monkeypatch):
    _patch_hl(monkeypatch)
    proj_off = _core_projection(monkeypatch)  # no proxy computed
    # compute a proxy diagnostic alongside; it must not perturb the decision
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    proj_on = _core_projection(monkeypatch)
    assert proj_on == proj_off
    assert proj_off["fill_decision"] == FillDecision.FILLED_ACTIVE
    # the proxy diagnostic exposes NONE of the decision fields
    for k in ("fill_decision", "entry_edge", "fair_yes", "token_id", "side", "exec_ask_vwap"):
        assert k not in diag


# ---------------------------------------------------------------------------
# 6. proxy never populates chainlink-aligned fields
# ---------------------------------------------------------------------------
def test_proxy_never_populates_chainlink():
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    assert diag["chainlink_capture_status"] == sb.CHAINLINK_REFERENCE_UNAVAILABLE
    assert diag["chainlink_reference_price"] is None
    assert diag["basis_hl_minus_chainlink"] is None
    assert diag["chainlink_aligned_edge_status"] == sb.NOT_COMPUTED


# ---------------------------------------------------------------------------
# 7-10. fail-closed -> NOT_COMPUTED
# ---------------------------------------------------------------------------
def test_missing_coinbase_leg_not_computed():
    diag, _ = _diag(coinbase={"data": {"currency": "USD"}}, kraken=_kr_ok())  # no amount
    assert diag["source_basis_mode"] == sb.NOT_COMPUTED
    assert diag["proxy_capture_status"] == sb.PROXY_REFERENCE_UNAVAILABLE
    assert diag["proxy_basis_hl_minus_proxy"] is None


def test_missing_kraken_leg_not_computed():
    diag, _ = _diag(coinbase=_cb_ok(), kraken={"error": ["EQuery:Unknown"], "result": {}})
    assert diag["source_basis_mode"] == sb.NOT_COMPUTED
    assert diag["proxy_capture_status"] == sb.PROXY_REFERENCE_UNAVAILABLE


def test_non_usd_payload_not_computed():
    diag, _ = _diag(coinbase={"data": {"amount": "60020", "currency": "USDT"}}, kraken=_kr_ok())
    assert diag["source_basis_mode"] == sb.NOT_COMPUTED
    assert diag["proxy_capture_status"] == sb.PROXY_REFERENCE_UNAVAILABLE


def test_spread_guard_fail_not_computed():
    # 60000 vs 61000 -> ~165 bps >> 50 bps guard
    diag, _ = _diag(coinbase=_cb_ok("60000"), kraken=_kr_ok("61000"))
    assert diag["source_basis_mode"] == sb.NOT_COMPUTED
    assert diag["proxy_capture_status"] == sb.PROXY_SPREAD_GUARD_FAIL
    assert diag["proxy_basis_hl_minus_proxy"] is None
    # skew/timestamps still recorded even on fail-closed
    assert diag["proxy_capture_started_vs_signal_ms"] == CAPTURE_START - TS_SIGNAL


# ---------------------------------------------------------------------------
# 11. Decimal/string safety
# ---------------------------------------------------------------------------
def test_decimal_string_safety_no_float():
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    for f in ("proxy_reference_price", "proxy_basis_hl_minus_proxy", "hl_reference_price"):
        v = diag[f]
        if v is not None:
            assert isinstance(v, str) and not isinstance(v, float)
            Decimal(v)


# ---------------------------------------------------------------------------
# 12. additive schema insertion + backward-compatible reads
# ---------------------------------------------------------------------------
def test_additive_schema_and_backward_compatible_reads(tmp_path, monkeypatch):
    db = str(tmp_path / "g7lite.sqlite3")
    conn = sqlite3.connect(db)
    plumb.init_mock_db(conn)            # existing G5 signal_log / mark_path schema
    runner._init_proxy_table(conn)      # additive G7-lite side table
    # write a normalized signal the normal way (no proxy involvement)
    _patch_hl(monkeypatch)
    ctx = runner._model_context("BTC", _market(), _book(), NOW_MS)
    ns = plumb.normalize_signal(_market(), _book(), ctx, capture_ts_ms=NOW_MS)
    plumb.write_signal(conn, ns, prev_hash="GENESIS")
    # write the proxy diagnostic into the side table
    diag, _ = _diag(coinbase=_cb_ok(), kraken=_kr_ok())
    runner._write_proxy_basis(conn, ns.signal.signal_id, "BTC", diag)
    conn.commit()
    # backward-compatible: a reader that only knows signal_log is unaffected
    n_sig = conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0]
    assert n_sig == 1
    # the additive table round-trips the two separate skew metrics + immutable ts_signal
    row = conn.execute(
        "SELECT ts_signal_ms, proxy_capture_started_vs_signal_ms, proxy_lag_after_signal_ms, "
        "source_basis_mode, proxy_capture_status FROM gateg7_proxy_basis "
        "WHERE signal_id=?", (ns.signal.signal_id,)).fetchone()
    assert row[0] == TS_SIGNAL
    assert row[1] == CAPTURE_START - TS_SIGNAL
    assert row[2] == CAPTURE_DONE - TS_SIGNAL
    assert row[3] == sb.CHAINLINK_PROXY_ONLY
    assert row[4] == sb.PROXY_POST_SIGNAL_DIAGNOSTIC
    conn.close()


# ---------------------------------------------------------------------------
# 14. zero live network calls (urllib hard-blocked)
# ---------------------------------------------------------------------------
def test_zero_live_network_calls(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("live network call attempted")
    monkeypatch.setattr(runner.urllib.request, "urlopen", _boom)
    diag, client = _diag(coinbase=_cb_ok(), kraken=_kr_ok())   # injected client only
    assert diag["proxy_capture_status"] == sb.PROXY_POST_SIGNAL_DIAGNOSTIC
    assert all("coinbase.com" in u or "kraken.com" in u for u in client.calls)
