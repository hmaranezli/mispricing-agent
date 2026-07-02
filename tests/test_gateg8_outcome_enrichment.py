"""
Gate G8 — one-shot outcome-enrichment adapter (OFFLINE, RED-first).

Reads a completed G8 paper-capture SQLite DB strictly read-only, reuses the committed
G6 Gamma+CLOB resolution evaluator (tools.gateg6_terminal_evaluator), and writes ONE
immutable JSON evidence artifact describing HYPOTHETICAL hold-to-resolution outcome for
the single canonical PAPER_OPEN row. No order, no fill, no realized PnL, effective_n=1.

All tests are offline: fetchers/clocks are injected, network is trapped. The adapter is
never run against the real DB and never calls a live endpoint.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys

import pytest

from tools import gateg6_terminal_evaluator as ev
from tools import gateg8_outcome_enrichment as oe

# --- canonical identity mirroring the accepted W1 run (ledger id=2) ---------
CID = "0x645c8e24e0fd7f761878b6334effd100c10359a22ea686fdb3bffe1cf536970c"
SLUG = "btc-updown-15m-1783007100"
WINDOW = "1783007100"
WINDOW_START_MS = 1783007100000
MARKET_END_S = 1783008000
AFTER_END_S = 1783008001
BEFORE_END_S = 1783007999
YES_TOKEN = "24647447160189003697904254632633789702118144743647744980828026055461052945235"
NO_TOKEN = "48259078501983614986411433669896891408942044982698717894942509039116670012796"
HELD_QTY = "57.294545454545454545454545454545454545454545454545"
ENTRY_COST = "25.986400000000000000000000000000000000000000000000"
ENTRY_ASK = "0.43634171109418634171109418634171109418634171109419"
ENTRY_NOTIONAL = "25.000000000000000000000000000000000000000000000000"
ENTRY_FEE = "0.98640"
FEE_RATE = "0.07"
ENTRY_TS_MS = 1783007139879
NO_NET_EDGE = "0.047190611247935670632762004542479162868967826327628"
YES_NET_EDGE = "-0.097800620895054228642409123100488809987525835974750"

PNL_WON = "31.308145454545454545454545454545454545454545454545"
PNL_LOST = "-25.986400000000000000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# fixture DB builder (tests may create files; the adapter may not)
# ---------------------------------------------------------------------------
def make_db(tmp_path, *, name="src.sqlite3", selected_side="NO",
            selected_token_id=NO_TOKEN, held_token_id=NO_TOKEN, n_open=1,
            n_exit=3, window_start_ms=WINDOW_START_MS, window=WINDOW,
            held_qty=HELD_QTY, entry_cost=ENTRY_COST, extra_held_tuple=False):
    """Build a minimal read-only-style G8 capture DB with the columns the adapter reads."""
    db = str(tmp_path / name)
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE gateg8_paper_ledger("
        "id INTEGER PRIMARY KEY, condition_id TEXT, slug TEXT, asset TEXT, window TEXT, "
        "window_start_ms INTEGER, selected_side TEXT, selected_token_id TEXT, "
        "yes_token_id TEXT, no_token_id TEXT, selected_filled_qty TEXT, "
        "no_exec_ask_vwap TEXT, yes_exec_ask_vwap TEXT, no_net_edge TEXT, yes_net_edge TEXT, "
        "paper_decision_ts INTEGER, status TEXT)")
    conn.execute(
        "CREATE TABLE gateg8_exit_evidence("
        "id INTEGER PRIMARY KEY, entry_ledger_id INTEGER, held_token_id TEXT, held_qty TEXT, "
        "entry_cost TEXT, entry_ask_vwap TEXT, fee_rate TEXT, entry_notional TEXT, "
        "entry_fee TEXT, entry_ts_ms INTEGER)")
    for _ in range(n_open):
        conn.execute(
            "INSERT INTO gateg8_paper_ledger(condition_id,slug,asset,window,window_start_ms,"
            "selected_side,selected_token_id,yes_token_id,no_token_id,selected_filled_qty,"
            "no_exec_ask_vwap,yes_exec_ask_vwap,no_net_edge,yes_net_edge,paper_decision_ts,status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (CID, SLUG, "BTC", window, window_start_ms, selected_side, selected_token_id,
             YES_TOKEN, NO_TOKEN, held_qty, ENTRY_ASK, ENTRY_ASK, NO_NET_EDGE, YES_NET_EDGE,
             ENTRY_TS_MS, "PAPER_OPEN"))
    ledger_id = conn.execute("SELECT id FROM gateg8_paper_ledger LIMIT 1").fetchone()
    ledger_id = ledger_id[0] if ledger_id else 1
    for i in range(n_exit):
        conn.execute(
            "INSERT INTO gateg8_exit_evidence(entry_ledger_id,held_token_id,held_qty,entry_cost,"
            "entry_ask_vwap,fee_rate,entry_notional,entry_fee,entry_ts_ms)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (ledger_id, held_token_id, held_qty, entry_cost, ENTRY_ASK, FEE_RATE,
             ENTRY_NOTIONAL, ENTRY_FEE, ENTRY_TS_MS))
    if extra_held_tuple:  # a second, DIFFERENT immutable tuple -> must refuse
        conn.execute(
            "INSERT INTO gateg8_exit_evidence(entry_ledger_id,held_token_id,held_qty,entry_cost,"
            "entry_ask_vwap,fee_rate,entry_notional,entry_fee,entry_ts_ms)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (ledger_id, held_token_id, "99.0", entry_cost, ENTRY_ASK, FEE_RATE,
             ENTRY_NOTIONAL, ENTRY_FEE, ENTRY_TS_MS))
    conn.commit()
    conn.close()
    return db


# ---------------------------------------------------------------------------
# injected fetch fakes
# ---------------------------------------------------------------------------
class Fetch:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error
        self.calls = 0
        self.args = []

    def __call__(self, *a):
        self.calls += 1
        self.args.append(a)
        if self.error is not None:
            raise self.error
        return self.payload


def gamma_payload(winner="Down"):
    prices = ["0", "1"] if winner == "Down" else ["1", "0"]
    return [{"slug": SLUG, "conditionId": CID, "closed": True,
             "umaResolutionStatus": "resolved", "outcomes": ["Up", "Down"],
             "clobTokenIds": [YES_TOKEN, NO_TOKEN], "outcomePrices": prices,
             "resolutionSource": "chainlink"}]


def clob_payload(winner="Down"):
    return {"condition_id": CID, "closed": True, "tokens": [
        {"token_id": YES_TOKEN, "winner": winner == "Up", "outcome": "Up"},
        {"token_id": NO_TOKEN, "winner": winner == "Down", "outcome": "Down"}]}


def arm(monkeypatch):
    monkeypatch.setenv(ev.EVAL_ARM_ENV, ev.EVAL_ARM_TOKEN)


def run(db, out, *, gf, cf, now_s=AFTER_END_S, monkeypatch=None):
    if monkeypatch is not None:
        # prove the adapter never falls back to the committed LIVE fetchers
        monkeypatch.setattr(ev, "gamma_fetch_live",
                            lambda *a: (_ for _ in ()).throw(AssertionError("live gamma")))
        monkeypatch.setattr(ev, "clob_fetch_live",
                            lambda *a: (_ for _ in ()).throw(AssertionError("live clob")))
    return oe.run(db, out_path=out, gamma_fetch=gf, clob_fetch=cf,
                  now_s_provider=lambda: now_s, now_ms_provider=lambda: now_s * 1000,
                  checkpoint_sha="TESTSHA")


def load(out):
    with open(out, encoding="utf-8") as f:
        return json.load(f)


# ===========================================================================
# 1. exactly one attempted fetch per source
# ===========================================================================
def test_single_fetch_per_source(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf, cf = Fetch(gamma_payload("Down")), Fetch(clob_payload("Down"))
    run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 1 and cf.calls == 1


# ===========================================================================
# 2. evaluator-consumed parsed payloads preserved verbatim in the artifact
# ===========================================================================
def test_payload_preservation(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gp, cp = gamma_payload("Down"), clob_payload("Down")
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gp), cf=Fetch(cp), monkeypatch=monkeypatch)
    art = load(out)
    assert art["resolution_evidence"]["gamma"]["parsed_payload"] == gp
    assert art["resolution_evidence"]["clob"]["parsed_payload"] == cp


# ===========================================================================
# 3. unresolved / fail-closed status => null PnL, status preserved verbatim
# ===========================================================================
def test_unresolved_null_pnl(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    not_final = [{"slug": SLUG, "conditionId": CID, "closed": False,
                  "outcomes": ["Up", "Down"], "clobTokenIds": [YES_TOKEN, NO_TOKEN],
                  "outcomePrices": ["0.4", "0.6"]}]
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(not_final), cf=Fetch(clob_payload("Down")), monkeypatch=monkeypatch)
    art = load(out)
    assert art["g6_status"] == ev.ST_RES_NOT_FINAL
    assert art["outcome"]["resolved"] is False
    assert art["outcome"]["held_side_won"] is None
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


# ===========================================================================
# 4. exact WON Decimal string
# ===========================================================================
def test_won_exact_decimal(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gamma_payload("Down")), cf=Fetch(clob_payload("Down")),
        monkeypatch=monkeypatch)
    art = load(out)
    pnl = art["hypothetical_hold_to_resolution_pnl"]
    assert art["g6_status"] == ev.ST_RESOLVED
    assert art["outcome"]["held_side_won"] is True
    assert pnl["pnl_if_won"] == PNL_WON
    assert pnl["pnl_for_outcome"] == PNL_WON
    assert isinstance(pnl["pnl_for_outcome"], str)   # never a JSON number


# ===========================================================================
# 5. exact LOST Decimal string
# ===========================================================================
def test_lost_exact_decimal(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gamma_payload("Up")), cf=Fetch(clob_payload("Up")),
        monkeypatch=monkeypatch)
    art = load(out)
    pnl = art["hypothetical_hold_to_resolution_pnl"]
    assert art["g6_status"] == ev.ST_RESOLVED
    assert art["outcome"]["held_side_won"] is False
    assert pnl["pnl_if_lost"] == PNL_LOST
    assert pnl["pnl_for_outcome"] == PNL_LOST


# ===========================================================================
# 6. DB identity inconsistency => refusal, zero fetches, no artifact
# ===========================================================================
def test_db_identity_inconsistency_refused(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path, selected_token_id="9999")   # != no_token_id
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    out = str(tmp_path / "art.json")
    with pytest.raises(oe.EnrichmentRefused):
        run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0
    assert not os.path.exists(out)


def test_multiple_open_rows_refused(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path, n_open=2)
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    with pytest.raises(oe.EnrichmentRefused):
        run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0


def test_ambiguous_held_tuple_refused(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path, extra_held_tuple=True)   # two distinct held tuples
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    with pytest.raises(oe.EnrichmentRefused):
        run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0


# ===========================================================================
# 7. foreign / missing token mismatch statuses preserved
# ===========================================================================
def test_foreign_token_outcome_ambiguous(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    bad = gamma_payload("Down")
    bad[0]["clobTokenIds"] = [YES_TOKEN, "9999"]   # foreign token at Down index
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(bad), cf=Fetch(clob_payload("Down")), monkeypatch=monkeypatch)
    art = load(out)
    assert art["g6_status"] == ev.ST_OUTCOME_AMBIGUOUS
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


def test_price_token_mismatch_preserved(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    cp = {"condition_id": CID, "closed": True, "tokens": [
        {"token_id": "111", "winner": False, "outcome": "Up"},
        {"token_id": "222", "winner": True, "outcome": "Down"}]}   # cand token absent
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gamma_payload("Down")), cf=Fetch(cp), monkeypatch=monkeypatch)
    art = load(out)
    assert art["g6_status"] == ev.ST_PRICE_TOKEN_MISMATCH
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


# ===========================================================================
# 8. existing artifact => refusal, sentinel intact, zero fetches, no stray temp
# ===========================================================================
def test_existing_artifact_refused(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    out = str(tmp_path / "art.json")
    with open(out, "wb") as f:
        f.write(b"SENTINEL")
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    with pytest.raises(oe.EnrichmentRefused):
        run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0
    with open(out, "rb") as f:
        assert f.read() == b"SENTINEL"
    assert [p for p in os.listdir(tmp_path) if ".tmp." in p] == []


# ===========================================================================
# 9. source DB never written; mode=ro connection URI
# ===========================================================================
def test_source_db_unchanged_and_mode_ro(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    before = hashlib.sha256(open(db, "rb").read()).hexdigest()
    seen = {}
    real_connect = sqlite3.connect

    def spy_connect(target, *a, **k):
        seen["target"] = str(target)
        seen["uri"] = k.get("uri", False)
        return real_connect(target, *a, **k)

    monkeypatch.setattr(oe.sqlite3, "connect", spy_connect)
    run(db, str(tmp_path / "art.json"), gf=Fetch(gamma_payload("Down")),
        cf=Fetch(clob_payload("Down")), monkeypatch=monkeypatch)
    after = hashlib.sha256(open(db, "rb").read()).hexdigest()
    assert before == after
    assert seen["uri"] is True and "mode=ro" in seen["target"]


# ===========================================================================
# 10. vocabulary validation excludes raw external payloads
# ===========================================================================
def test_vocabulary_excludes_external_payloads(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gp = gamma_payload("Down")
    gp[0]["resolutionSource"] = "realized_pnl alpha risk-free"   # banned words in EXTERNAL data
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gp), cf=Fetch(clob_payload("Down")), monkeypatch=monkeypatch)
    art = load(out)
    # adapter did NOT refuse over external vocabulary; payload preserved verbatim
    assert art["resolution_evidence"]["gamma"]["parsed_payload"][0]["resolutionSource"] \
        == "realized_pnl alpha risk-free"
    # adapter-authored narrative stays clean
    assert "realized" not in art["hypothetical_hold_to_resolution_pnl"]["semantics"].lower()
    assert art["no_order_no_fill_no_realized_pnl"] is True


# ===========================================================================
# 11 & 17. import hygiene: no network, no forbidden runtime modules
# ===========================================================================
def _subprocess(code):
    return subprocess.run([sys.executable, "-c", code], cwd="/root/mispricing_agent",
                          capture_output=True, text=True, timeout=60)


def test_import_no_network_side_effect():
    # trap only actual outbound connections (not socket construction / ssl class definition)
    r = _subprocess(
        "import socket\n"
        "def _no_connect(self, *a, **k):\n"
        "    raise AssertionError('network at import')\n"
        "socket.socket.connect = _no_connect\n"
        "import urllib.request\n"
        "urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw("
        "AssertionError('network at import'))\n"
        "import tools.gateg8_outcome_enrichment as m\n"
        "print('IMPORT_OK')\n")
    assert r.returncode == 0, r.stderr
    assert "network at import" not in r.stderr
    assert "IMPORT_OK" in r.stdout


def test_import_no_forbidden_modules():
    r = _subprocess(
        "import tools.gateg8_outcome_enrichment as m\n"
        "import sys\n"
        "bad = [n for n in sys.modules if any(k in n for k in ("
        "'gateg8_paper_forward_capture','gateg5_telemetry_runner','gateg9',"
        "'gateg8_exit_evidence','gateg8_proxy_basis'))]\n"
        "print('FORBIDDEN=' + repr(bad))\n")
    assert r.returncode == 0, r.stderr
    assert "FORBIDDEN=[]" in r.stdout


# ===========================================================================
# 12. pre-market-end refusal, zero fetches
# ===========================================================================
def test_pre_market_end_refused(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    with pytest.raises(oe.EnrichmentRefused):
        run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, now_s=BEFORE_END_S,
            monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0


# ===========================================================================
# 13. VOID_OR_REFUND => null PnL
# ===========================================================================
def test_void_or_refund_null_pnl(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    void = [{"slug": SLUG, "conditionId": CID, "closed": True,
             "umaResolutionStatus": "resolved", "outcomes": ["Up", "Down"],
             "clobTokenIds": [YES_TOKEN, NO_TOKEN], "outcomePrices": ["0.5", "0.5"]}]
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(void), cf=Fetch(clob_payload("Down")), monkeypatch=monkeypatch)
    art = load(out)
    assert art["g6_status"] == ev.ST_VOID_OR_REFUND
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


# ===========================================================================
# 14. transport-failure paths (gamma / clob) => one attempt each, fail-closed, null PnL
# ===========================================================================
def test_gamma_transport_failure(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf = Fetch(error=ev.TransportError("gamma down"))
    cf = Fetch(clob_payload("Down"))
    out = str(tmp_path / "art.json")
    run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    art = load(out)
    assert gf.calls == 1 and cf.calls == 1          # both attempted once, no retry
    assert art["g6_status"] == ev.ST_RES_MISSING
    assert art["resolution_evidence"]["gamma"]["error"] is not None
    assert art["resolution_evidence"]["gamma"]["parsed_payload"] is None
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


def test_clob_transport_failure(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf = Fetch(gamma_payload("Down"))
    cf = Fetch(error=ev.TransportError("clob down"))
    out = str(tmp_path / "art.json")
    run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    art = load(out)
    assert gf.calls == 1 and cf.calls == 1
    assert art["g6_status"] == ev.ST_CLOB_MISSING
    assert art["resolution_evidence"]["clob"]["error"] is not None
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


# --- unexpected (non-TransportError) fetch exceptions: normalized fail-closed --------------
def test_gamma_unexpected_exception(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf = Fetch(error=RuntimeError("gamma boom"))
    cf = Fetch(clob_payload("Down"))
    out = str(tmp_path / "art.json")
    run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    art = load(out)
    assert gf.calls == 1 and cf.calls == 1               # CLOB still attempted once; no retry
    assert art["g6_status"] == ev.ST_RES_MISSING          # evaluator got a normalized TransportError
    err = art["resolution_evidence"]["gamma"]["error"]
    assert "RuntimeError" in err and "gamma boom" in err  # original class/message preserved
    assert art["resolution_evidence"]["gamma"]["parsed_payload"] is None
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


def test_clob_unexpected_exception(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf = Fetch(gamma_payload("Down"))
    cf = Fetch(error=RuntimeError("clob boom"))
    out = str(tmp_path / "art.json")
    run(db, out, gf=gf, cf=cf, monkeypatch=monkeypatch)
    art = load(out)
    assert gf.calls == 1 and cf.calls == 1
    assert art["g6_status"] == ev.ST_CLOB_MISSING
    err = art["resolution_evidence"]["clob"]["error"]
    assert "RuntimeError" in err and "clob boom" in err
    assert art["hypothetical_hold_to_resolution_pnl"]["pnl_for_outcome"] is None


def test_fetch_once_does_not_swallow_baseexception(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    gf = Fetch(error=KeyboardInterrupt())
    cf = Fetch(clob_payload("Down"))
    with pytest.raises(KeyboardInterrupt):
        run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, monkeypatch=monkeypatch)


# ===========================================================================
# 15. arm-gate refusal before any fetch
# ===========================================================================
def test_arm_gate_refused(monkeypatch, tmp_path):
    monkeypatch.delenv(ev.EVAL_ARM_ENV, raising=False)
    db = make_db(tmp_path)
    gf, cf = Fetch(gamma_payload()), Fetch(clob_payload())
    with pytest.raises(oe.EnrichmentRefused):
        run(db, str(tmp_path / "art.json"), gf=gf, cf=cf, monkeypatch=monkeypatch)
    assert gf.calls == 0 and cf.calls == 0


# ===========================================================================
# 16. atomic publish: no overwrite, sentinel intact, no stray temp
# ===========================================================================
def test_atomic_publish_no_overwrite(tmp_path):
    out = str(tmp_path / "art.json")
    with open(out, "wb") as f:
        f.write(b"SENTINEL")
    with pytest.raises(FileExistsError):
        oe._atomic_publish(out, b'{"x":1}')
    with open(out, "rb") as f:
        assert f.read() == b"SENTINEL"
    assert [p for p in os.listdir(tmp_path) if ".tmp." in p] == []


def test_atomic_publish_writes_and_cleans_temp(tmp_path):
    out = str(tmp_path / "art.json")
    oe._atomic_publish(out, b'{"x":1}')
    with open(out, "rb") as f:
        assert f.read() == b'{"x":1}'
    assert [p for p in os.listdir(tmp_path) if ".tmp." in p] == []


@pytest.mark.parametrize("failing", ["write", "fsync"])
def test_atomic_publish_cleans_temp_on_io_failure(monkeypatch, tmp_path, failing):
    out = str(tmp_path / "art.json")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(oe.os, failing, boom)
    with pytest.raises(OSError, match="disk full"):     # original exception propagates
        oe._atomic_publish(out, b'{"x":1}')
    assert not os.path.exists(out)                       # no artifact published
    assert [p for p in os.listdir(tmp_path) if ".tmp." in p] == []   # no temp leaked


# ===========================================================================
# JSON contract: mandatory fields present, Decimals are strings
# ===========================================================================
def test_json_contract_mandatory_fields(monkeypatch, tmp_path):
    arm(monkeypatch)
    db = make_db(tmp_path)
    out = str(tmp_path / "art.json")
    run(db, out, gf=Fetch(gamma_payload("Down")), cf=Fetch(clob_payload("Down")),
        monkeypatch=monkeypatch)
    art = load(out)
    for k in ("artifact_kind", "schema_version", "generated_ts_ms", "checkpoint_sha",
              "identity", "source_db", "held_position", "resolution_evidence",
              "g6_evaluation", "g6_status", "outcome",
              "hypothetical_hold_to_resolution_pnl"):
        assert k in art, k
    assert art["effective_n"] == 1
    assert art["no_order_no_fill_no_realized_pnl"] is True
    assert art["identity"]["condition_id"] == CID
    assert art["identity"]["entry_ledger_id"] is not None
    assert art["source_db"]["sha256"] == hashlib.sha256(open(db, "rb").read()).hexdigest()
    assert art["held_position"]["held_qty"] == HELD_QTY
    assert art["held_position"]["entry_cost"] == ENTRY_COST
    # every hypothetical PnL value is a JSON string (or null), never a number
    pnl = art["hypothetical_hold_to_resolution_pnl"]
    for key in ("pnl_if_won", "pnl_if_lost"):
        assert isinstance(pnl[key], str)
