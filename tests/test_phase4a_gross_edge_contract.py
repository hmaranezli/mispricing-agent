"""tests/test_phase4a_gross_edge_contract.py — Phase 4A Gross Edge v0 (TDD, offline).

Phase 4A v0 = OFFLINE internal YES/NO complement-consistency metrics from Phase 3 JSONL snapshots.
NO live fetch, NO endpoints, NO net-edge/PnL/slippage/fees/impact, NO execution/paper/economics/
profitability claims. Each Phase 3 row carries ONE token's book; a YES/NO pair requires >=2 distinct
two-sided tokens for the same market_slug, near in time — else marked ineligible (no guessing).

İlk RED: tools/phase4a_gross_edge_engine henüz yok → ImportError.
"""
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase4a_gross_edge_engine as E  # noqa: E402

ENGINE_PATH = os.path.join(TOOLS_DIR, "phase4a_gross_edge_engine.py")


def _row(slug, token, ts, bids, asks, asset="BTC", interval="5m"):
    return {"asset": asset, "interval": interval, "market_slug": slug, "token_id": token,
            "utc_timestamp_ms": ts, "bids": bids, "asks": asks}


def _two_sided(bid, ask):
    return [[bid, 100]], [[ask, 100]]


def _write(tmp_path, rows, name="in.jsonl"):
    p = tmp_path / name
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return str(p)


def _pair_rows(slug="btc-updown-5m-1", ts=1000, yes=(0.51, 0.49), no=(0.50, 0.48)):
    yb, ya = yes
    nb, na = no
    by, ay = _two_sided(yb, ya)
    bn, an = _two_sided(nb, na)
    return [_row(slug, "0xYES", ts, by, ay), _row(slug, "0xNO", ts + 100, bn, an)]


def _run(tmp_path, rows, **kw):
    inp = _write(tmp_path, rows) if isinstance(rows, list) else rows
    return E.run(input_path=inp, output_dir=str(tmp_path), timestamp_fn=lambda: kw.get("ts", 9999))


# ---- formulas ----

def test_complement_metrics_buy_both():
    m = E.complement_metrics(0.51, 0.49, 0.50, 0.48)   # yes_bid,yes_ask,no_bid,no_ask
    assert m["buy_both_gross_edge"] == pytest.approx(0.03)   # 1 - (0.49+0.48)


def test_complement_metrics_sell_both():
    m = E.complement_metrics(0.51, 0.49, 0.50, 0.48)
    assert m["sell_both_gross_edge"] == pytest.approx(0.01)  # (0.51+0.50) - 1


def test_complement_metrics_gap():
    m = E.complement_metrics(0.51, 0.49, 0.50, 0.48)
    assert m["ask_sum"] == pytest.approx(0.97)
    assert m["bid_sum"] == pytest.approx(1.01)
    assert m["complement_gap"] == pytest.approx(0.97 - 1.01)


# ---- eligible pairing ----

def test_eligible_pair_from_two_rows(tmp_path):
    summary = _run(tmp_path, _pair_rows())
    assert summary["verdict"] == "GROSS_EDGE_SAMPLE_ONLY"
    assert summary["eligible_pairs"] == 1
    with open(summary["output_jsonl"]) as f:
        rec = json.loads(f.readline())
    assert rec["anchor_type"] == "YES_NO_COMPLEMENT"
    assert rec["market_slug"] == "btc-updown-5m-1"
    assert rec["buy_both_gross_edge"] == pytest.approx(0.03)


def test_no_pair_when_only_yes(tmp_path):
    rows = [_pair_rows()[0]]   # only the YES token row
    summary = _run(tmp_path, rows)
    assert summary["verdict"] == "GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS"
    assert summary["eligible_pairs"] == 0
    assert summary["ineligible_reasons"].get("NO_COMPLEMENT_TOKEN", 0) >= 1


def test_one_sided_book_rejected(tmp_path):
    yes = _pair_rows()[0]
    no_one_sided = _row("btc-updown-5m-1", "0xNO", 1100, [[0.50, 100]], [])  # no asks
    summary = _run(tmp_path, [yes, no_one_sided])
    assert summary["eligible_pairs"] == 0
    assert summary["ineligible_reasons"].get("ONE_SIDED_BOOK", 0) >= 1


def test_wide_spread_rejected(tmp_path):
    # YES spread huge: bid 0.10 ask 0.90 -> ~ (0.8/0.5)*1e4 bps >> 500
    yes = _row("btc-updown-5m-1", "0xYES", 1000, [[0.10, 100]], [[0.90, 100]])
    no = _row("btc-updown-5m-1", "0xNO", 1050, [[0.50, 100]], [[0.51, 100]])
    summary = _run(tmp_path, [yes, no])
    assert summary["eligible_pairs"] == 0
    assert summary["ineligible_reasons"].get("SPREAD_TOO_WIDE", 0) >= 1


def test_timestamp_delta_rejected(tmp_path):
    a, b = _pair_rows()
    b["utc_timestamp_ms"] = a["utc_timestamp_ms"] + 999999   # delta > 5000ms
    summary = _run(tmp_path, [a, b])
    assert summary["eligible_pairs"] == 0
    assert summary["ineligible_reasons"].get("PAIR_DELTA_EXCEEDED", 0) >= 1


def test_lineage_incomplete_rejected(tmp_path):
    a, b = _pair_rows()
    del b["token_id"]
    summary = _run(tmp_path, [a, b])
    assert summary["eligible_pairs"] == 0
    # only YES remains lineage-complete -> no complement
    assert (summary["ineligible_reasons"].get("LINEAGE_INCOMPLETE", 0) >= 1
            or summary["ineligible_reasons"].get("NO_COMPLEMENT_TOKEN", 0) >= 1)


# ---- malformed JSON ----

def test_malformed_json_counted_not_corrupting(tmp_path):
    p = tmp_path / "in.jsonl"
    rows = _pair_rows()
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(rows[0]) + "\n")
        f.write("{not valid json\n")
        f.write(json.dumps(rows[1]) + "\n")
    summary = E.run(input_path=str(p), output_dir=str(tmp_path), timestamp_fn=lambda: 1)
    assert summary["rows_malformed"] == 1
    assert summary["rows_valid_json"] == 2
    assert summary["eligible_pairs"] == 1   # the valid pair still produced


# ---- verdicts ----

def test_no_eligible_verdict_when_empty(tmp_path):
    summary = _run(tmp_path, [])
    assert summary["verdict"] in ("GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS", "GROSS_EDGE_FAILED")


def test_sample_only_verdict(tmp_path):
    summary = _run(tmp_path, _pair_rows())
    assert summary["verdict"] == "GROSS_EDGE_SAMPLE_ONLY"


# ---- output location + schema flags ----

def test_output_defaults_under_data_output():
    assert E.OUT_DIR.replace(os.sep, "/").rstrip("/").endswith("data/output")


def test_summary_has_no_readiness_or_profitability_claims(tmp_path):
    summary = _run(tmp_path, _pair_rows())
    with open(summary["output_summary"]) as f:
        s = f.read()
    assert "EXECUTION_READY" not in s
    assert "ECONOMICS_READY_FOR_PAPER" not in s
    assert "net_edge" not in s
    assert summary["official_f1b"] is False
    assert summary["profitability"] is False
    assert summary["phase"] == "4A_gross_edge"


def test_record_schema_flags(tmp_path):
    summary = _run(tmp_path, _pair_rows())
    with open(summary["output_jsonl"]) as f:
        rec = json.loads(f.readline())
    for k in ("phase", "asset", "interval", "market_slug", "yes_token_id", "no_token_id",
              "yes_best_bid", "yes_best_ask", "no_best_bid", "no_best_ask", "ask_sum", "bid_sum",
              "buy_both_gross_edge", "sell_both_gross_edge", "complement_gap", "yes_spread_bps",
              "no_spread_bps", "pair_timestamp_delta_ms", "eligibility_flags", "anchor_type",
              "official_f1b", "profitability"):
        assert k in rec, f"missing record field {k!r}"
    assert rec["phase"] == "4A_gross_edge"
    assert rec["official_f1b"] is False
    assert rec["profitability"] is False


# ---- safety / isolation ----

def test_engine_no_forbidden_or_readiness_literals():
    with open(ENGINE_PATH, encoding="utf-8") as f:
        src = f.read()
    for bad in ("EXECUTION_READY", "ECONOMICS_READY_FOR_PAPER", "api_key", "api_secret",
                "private_key", "place_order", "get_balance", "os.environ", "getenv"):
        assert bad not in src, f"engine must not contain {bad!r}"


def test_cli_accepts_output_dir(tmp_path):
    inp = _write(tmp_path, _pair_rows())
    outdir = tmp_path / "out"
    outdir.mkdir()
    r = subprocess.run([sys.executable, ENGINE_PATH, "--input", str(inp), "--output-dir", str(outdir)],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert any(f.startswith("phase4a_gross_edge_") for f in os.listdir(outdir))


def test_engine_not_imported_by_production():
    res = subprocess.run(["grep", "-rIl", "--include=*.py", "phase4a_gross_edge", REPO],
                         capture_output=True, text=True)
    hits = [ln for ln in res.stdout.splitlines()
            if ln.strip() and "/tools/" not in ln and "/tests/" not in ln
            and "/data/output/" not in ln and "/graphify-out/" not in ln and "/.git/" not in ln]
    assert hits == [], f"phase4a engine must not be imported by production: {hits}"
