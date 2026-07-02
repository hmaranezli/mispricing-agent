"""
Gate G8 — BTC15m single-window containment lock (OFFLINE, RED-first).

Optional locked mode via GATEG8_TARGET_WINDOW_START_MS freezes the target slug set to exactly
W1 and adds a wall-clock top-of-loop expiry guard, so a boundary-launched run can never open or
persist the following window (W2). When the variable is absent, the committed rolling behavior
(runner._target_slugs) is unchanged. Injected clocks/clients only; zero live network. No orders,
wallet, G9, Slice-1/Slice-2 economic changes.
"""
import datetime as dt
import os
import sqlite3
from decimal import Decimal

import pytest

from analysis.forensic import gateg8_proxy_basis as pbmod
from tools import gateg8_paper_forward_capture as fwd

START_MS = 1_900_800_000_000          # divisible by 900_000 -> canonical 15m boundary
START_S = START_MS // 1000            # 1_900_800_000
END_MS = START_MS + 900_000
W1_SLUG = f"btc-updown-15m-{START_S}"
W2_SLUG = f"btc-updown-15m-{START_S + 900}"


# ---------------------------------------------------------------------------
# injected clocks
# ---------------------------------------------------------------------------
class _Script:
    """Returns scripted wall-clock values in order; holds the last value after exhaustion."""
    def __init__(self, values):
        self.values = list(values)
        self.i = 0
        self.calls = 0

    def read(self):
        self.calls += 1
        v = self.values[min(self.i, len(self.values) - 1)]
        self.i += 1
        return v


class _Const:
    def __init__(self, v):
        self.v = v
        self.calls = 0

    def read(self):
        self.calls += 1
        return self.v


class _Crossing:
    """`before` for the first `flip_after` reads, then `after` (models an in-flight boundary cross)."""
    def __init__(self, before, after, flip_after):
        self.before, self.after, self.flip_after = before, after, flip_after
        self.calls = 0

    def read(self):
        self.calls += 1
        return self.before if self.calls <= self.flip_after else self.after


def _mono_seq(values):
    state = {"i": 0, "v": list(values)}

    def m():
        v = state["v"][min(state["i"], len(state["v"]) - 1)]
        state["i"] += 1
        return v
    return m


# ---------------------------------------------------------------------------
# injected network fakes
# ---------------------------------------------------------------------------
def _gamma(slug):
    ep = int(slug.rsplit("-", 1)[1])
    end = dt.datetime.fromtimestamp(ep + 900, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"conditionId": f"0xcid-{ep}", "slug": slug, "outcomes": ["Up", "Down"],
            "clobTokenIds": ["tokUp", "tokDown"], "endDate": end, "feesEnabled": True,
            "feeSchedule": {"exponent": 1, "rate": 0.07, "takerOnly": True}}


def _pg_empty_recording():
    """Gamma returns no markets (no capture); records every requested slug/token."""
    rec = {"gamma": [], "book": []}

    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            rec["gamma"].append(params["slug"])
            return []
        rec["book"].append(params.get("token_id"))
        return {"asks": [], "bids": [], "timestamp": 0}
    pg.rec = rec
    return pg


def _pg_capture(book_ts):
    """Full capture path: cheap YES -> PAPER_OPEN; records requested slugs."""
    rec = {"gamma": []}

    def pg(url, params=None):
        if url == fwd.runner.GAMMA_MARKETS:
            rec["gamma"].append(params["slug"])
            return [_gamma(params["slug"])]
        tid = params["token_id"]
        ask = "0.30" if tid == "tokUp" else "0.65"
        return {"asks": [{"price": ask, "size": "1000"}],
                "bids": [{"price": "0.20", "size": "1000"}], "timestamp": book_ts}
    pg.rec = rec
    return pg


class _SpotClient:
    def __init__(self, fail_kraken=False):
        self.calls = []
        self.fail_kraken = fail_kraken

    async def __call__(self, url):
        self.calls.append(url)
        if "coinbase.com" in url:
            return {"data": {"amount": "60050.5", "currency": "USD"}}
        if "kraken.com" in url:
            if self.fail_kraken:
                raise RuntimeError("kraken down")
            return {"error": [], "result": {"XXBTZUSD": {"c": ["60010.1", "0.1"]}}}
        raise AssertionError(f"unexpected url {url}")


def _hl():
    def pf(coin, ts):
        if ts <= START_MS:                             # window-open strike query (past)
            return Decimal("59000"), ts
        return Decimal("60000"), ts - 30_000
    return pf, (lambda c, n: 0.8)


def _forbid_target_slugs(*a, **k):
    raise AssertionError("runner._target_slugs called in locked mode")


def _base_env(monkeypatch, *, max_obs=100, proxy=False, target=None):
    monkeypatch.setenv(fwd.PAPER_ARM_ENV, fwd.PAPER_ARM_TOKEN)
    monkeypatch.setenv("GATEG8_MAX_OBSERVATIONS", str(max_obs))
    monkeypatch.setenv("GATEG8_MAX_ELAPSED_S", "900")
    monkeypatch.setenv("GATEG8_MAX_SKEW_MS", "1500")
    monkeypatch.setattr(fwd.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(fwd.runner, "TARGET_ASSETS", ["BTC"])     # BTC-only config
    if proxy:
        monkeypatch.setenv(pbmod.PROXY_ARM_ENV, pbmod.PROXY_ARM_TOKEN)
    if target is not None:
        monkeypatch.setenv("GATEG8_TARGET_WINDOW_START_MS", target)
    else:
        monkeypatch.delenv("GATEG8_TARGET_WINDOW_START_MS", raising=False)


def _run(db, *, clock, monotonic=lambda: 0.0, pg, sc, pf=None, sig=None):
    hpf, hsig = _hl()
    return fwd.run(db, now_ms_provider=clock.read, monotonic_provider=monotonic,
                   public_get=pg, hl_price_feedts=pf or hpf, hl_sigma_annual=sig or hsig,
                   spot_http_client=sc, abort_check=lambda: False)


# ===========================================================================
# B. invalid values fail closed before DB + network
# ===========================================================================
@pytest.mark.parametrize("bad", ["abc", "-900000", "+900000", " 900000", "900000.0",
                                 "9e5", "0", "900001"])
def test_invalid_lock_value_fails_closed_before_db_and_network(monkeypatch, tmp_path, bad):
    _base_env(monkeypatch, target=bad)
    pg = _pg_empty_recording(); sc = _SpotClient()
    db = str(tmp_path / "b.sqlite3")
    with pytest.raises(PermissionError):
        _run(db, clock=_Const(START_MS), pg=pg, sc=sc)
    assert not os.path.exists(db)
    assert pg.rec["gamma"] == [] and sc.calls == []


# ===========================================================================
# C. already-expired target: refuse before DB + network
# ===========================================================================
def test_already_expired_target_refuses_before_db_and_network(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS))
    pg = _pg_empty_recording(); sc = _SpotClient()
    db = str(tmp_path / "c.sqlite3")
    with pytest.raises(PermissionError):
        _run(db, clock=_Const(END_MS), pg=pg, sc=sc)
    assert not os.path.exists(db)
    assert pg.rec["gamma"] == [] and sc.calls == []


# ===========================================================================
# D. frozen identity: only W1 requested; rolling generator never called
# ===========================================================================
def test_locked_mode_freezes_w1_and_never_calls_rolling(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS))
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    pg = _pg_empty_recording(); sc = _SpotClient()
    clock = _Script([START_MS + 1000, START_MS + 1000, START_MS + 800_000, END_MS])
    db = str(tmp_path / "d.sqlite3")
    res = _run(db, clock=clock, pg=pg, sc=sc)
    assert isinstance(res, dict)
    assert res["stop_reason"] == "TARGET_WINDOW_EXPIRED"
    assert set(pg.rec["gamma"]) == {W1_SLUG}
    assert W2_SLUG not in pg.rec["gamma"]


# ===========================================================================
# E. expiry guard fires before any per-cycle network
# ===========================================================================
def test_expiry_guard_fires_before_any_network(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS))
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    pg = _pg_empty_recording(); sc = _SpotClient()
    hl_calls = {"n": 0}

    def pf(coin, ts):
        hl_calls["n"] += 1
        return Decimal("59000"), ts

    clock = _Script([END_MS - 1, END_MS])              # startup ok, first cycle expired
    db = str(tmp_path / "e.sqlite3")
    res = _run(db, clock=clock, pg=pg, sc=sc, pf=pf, sig=lambda c, n: 0.8)
    assert res["stop_reason"] == "TARGET_WINDOW_EXPIRED"
    assert pg.rec["gamma"] == [] and pg.rec["book"] == []
    assert hl_calls["n"] == 0 and sc.calls == []


# ===========================================================================
# F. persistence: zero W2 rows across ledger / Slice 1 / Slice 2
# ===========================================================================
def test_no_w2_rows_persisted(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS), proxy=True)
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    pg = _pg_empty_recording(); sc = _SpotClient()
    clock = _Script([START_MS + 1000, START_MS + 1000, END_MS])
    db = str(tmp_path / "f.sqlite3")
    _run(db, clock=clock, pg=pg, sc=sc)
    conn = sqlite3.connect(db)
    led = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger WHERE slug=?", (W2_SLUG,)).fetchone()[0]
    ev = conn.execute("SELECT COUNT(*) FROM gateg8_exit_evidence WHERE slug=?", (W2_SLUG,)).fetchone()[0]
    pbc = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis WHERE slug=?", (W2_SLUG,)).fetchone()[0]
    conn.close()
    assert led == 0 and ev == 0 and pbc == 0


# ===========================================================================
# G. late launch stops at W1 end, not a fresh 900 s
# ===========================================================================
def test_late_launch_stops_at_window_end_not_fresh_900s(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS))
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    pg = _pg_empty_recording(); sc = _SpotClient()
    clock = _Script([START_MS + 850_000, START_MS + 860_000, END_MS])
    db = str(tmp_path / "g.sqlite3")
    res = _run(db, clock=clock, monotonic=lambda: 0.0, pg=pg, sc=sc)  # monotonic never hits 900
    assert res["stop_reason"] == "TARGET_WINDOW_EXPIRED"
    assert set(pg.rec["gamma"]) == {W1_SLUG}


# ===========================================================================
# H. backward wall clock: monotonic backstop authoritative; frozen identity holds
# ===========================================================================
def test_backward_wall_clock_bounded_by_monotonic_and_frozen_identity(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS))
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    pg = _pg_empty_recording(); sc = _SpotClient()
    clock = _Script([START_MS + 5000, START_MS + 5000, START_MS + 1000])   # backward, never >= end
    mono = _mono_seq([0.0, 10.0, 950.0])               # start_mono, cycle1<900, cycle2>=900
    db = str(tmp_path / "h.sqlite3")
    res = _run(db, clock=clock, monotonic=mono, pg=pg, sc=sc)
    assert res["stop_reason"] == "MAX_ELAPSED"
    assert W2_SLUG not in pg.rec["gamma"]
    assert set(pg.rec["gamma"]) <= {W1_SLUG}


# ===========================================================================
# I. in-flight model-time rule (committed semantics preserved; identity stays W1)
# ===========================================================================
def test_inflight_preclose_valid_model_read_opens_w1(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS), proxy=True, max_obs=1)
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    V = START_MS + 800_000                             # before close, admitted
    pg = _pg_capture(V); sc = _SpotClient()
    db = str(tmp_path / "ipre.sqlite3")
    _run(db, clock=_Const(V), pg=pg, sc=sc)
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT slug FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()
    grp = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0]
    conn.close()
    assert po is not None and po[0] == W1_SLUG
    assert grp == 4


def test_inflight_atclose_model_read_capture_failed_no_proxy(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=str(START_MS), proxy=True, max_obs=5)
    monkeypatch.setattr(fwd.runner, "_target_slugs", _forbid_target_slugs)
    # startup + cycle-1 guard admit (before close); capture's model read crosses to close
    pg = _pg_capture(END_MS - 1); sc = _SpotClient()
    clock = _Crossing(before=END_MS - 1, after=END_MS, flip_after=2)
    db = str(tmp_path / "iat.sqlite3")
    _run(db, clock=clock, pg=pg, sc=sc)
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()[0]
    cf = conn.execute("SELECT slug FROM gateg8_paper_ledger WHERE status='CAPTURE_FAILED'").fetchone()
    grp = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0]
    conn.close()
    assert po == 0
    assert cf is not None and cf[0] == W1_SLUG        # frozen W1 identity, never W2
    assert grp == 0                                   # no proxy group for a failed capture


# ===========================================================================
# A / J. env absent: rolling path active + functional; expiry guard inactive; no retry
# ===========================================================================
def test_env_absent_keeps_rolling_active_and_functional(monkeypatch, tmp_path):
    _base_env(monkeypatch, target=None, proxy=True, max_obs=2)
    called = {"n": 0}
    real = fwd.runner._target_slugs

    def spy(now_ms):
        called["n"] += 1
        return real(now_ms)

    monkeypatch.setattr(fwd.runner, "_target_slugs", spy)
    V = START_MS + 300_000
    pg = _pg_capture(V); sc = _SpotClient()
    db = str(tmp_path / "a.sqlite3")
    res = _run(db, clock=_Const(V), pg=pg, sc=sc)
    assert called["n"] >= 1                            # rolling generator still the target source
    assert res["stop_reason"] != "TARGET_WINDOW_EXPIRED"   # expiry guard inactive when absent
    assert res["stop_reason"] in ("MAX_OBSERVATIONS", "MAX_ELAPSED")
    conn = sqlite3.connect(db)
    po = conn.execute("SELECT COUNT(*) FROM gateg8_paper_ledger WHERE status='PAPER_OPEN'").fetchone()[0]
    grp = conn.execute("SELECT COUNT(*) FROM gateg8_proxy_basis").fetchone()[0]
    conn.close()
    assert po >= 1 and grp >= 4                         # full rolling+Slice1+Slice2 still functional
