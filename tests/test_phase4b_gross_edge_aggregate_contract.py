"""tests/test_phase4b_gross_edge_aggregate_contract.py — Phase 4B aggregate analyzer (TDD, offline).

Phase 4B v0 = OFFLINE statistical aggregation of Phase 4A gross-edge artifacts (records + summaries).
NO live fetch, NO endpoints, NO net-edge/PnL/slippage/market-impact, NO execution/paper/economics/
profitability/readiness claims. tmp_path fixtures only; never reads real data/output/.

İlk RED: tools/phase4b_gross_edge_aggregate henüz yok → ImportError.
"""
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS_DIR)

import phase4b_gross_edge_aggregate as B  # noqa: E402

ENGINE_PATH = os.path.join(TOOLS_DIR, "phase4b_gross_edge_aggregate.py")


def _record(buy, sell, yspr=400.0, nspr=410.0, delta=2000):
    return {"phase": "4A_gross_edge", "buy_both_gross_edge": buy, "sell_both_gross_edge": sell,
            "yes_spread_bps": yspr, "no_spread_bps": nspr, "pair_timestamp_delta_ms": delta,
            "anchor_type": "YES_NO_COMPLEMENT"}


def _write_records(tmp_path, name, records):
    p = tmp_path / name
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


def _write_summary(tmp_path, name, candidate, eligible, ineligible):
    p = tmp_path / name
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"phase": "4A_gross_edge", "candidate_pairs": candidate, "eligible_pairs": eligible,
                   "ineligible_reasons": ineligible}, f)
    return p


def _run(tmp_path):
    return B.run(input_dir=str(tmp_path), output_dir=str(tmp_path), timestamp_fn=lambda: 7777)


# ---- aggregation across multiple artifacts ----

def test_aggregation_across_multiple_artifacts(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [_record(-0.01, -0.01), _record(-0.02, 0.0)])
    _write_records(tmp_path, "phase4a_gross_edge_2.jsonl", [_record(0.03, 0.01)])
    _write_summary(tmp_path, "phase4a_gross_edge_summary_1.json", 4, 2, {"SPREAD_TOO_WIDE": 1})
    _write_summary(tmp_path, "phase4a_gross_edge_summary_2.json", 2, 1, {"NO_COMPLEMENT_TOKEN": 1})
    s = _run(tmp_path)
    assert s["verdict"] == "PHASE4B_AGGREGATE_SAMPLE_ONLY"
    assert s["summaries_read"] == 2
    assert s["records_read"] == 3
    assert s["candidate_pairs_total"] == 6
    assert s["eligible_pairs_total"] == 3
    assert s["gross_edge_distribution"]["buy_both_gross_edge"]["count"] == 3


# ---- malformed json ----

def test_malformed_records_counted_and_skipped(tmp_path):
    p = tmp_path / "phase4a_gross_edge_x.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(_record(-0.01, -0.01)) + "\n")
        f.write("{bad json\n")
        f.write(json.dumps(_record(-0.02, 0.0)) + "\n")
    s = _run(tmp_path)
    assert s["rows_malformed"] == 1
    assert s["records_read"] == 2
    assert s["gross_edge_distribution"]["buy_both_gross_edge"]["count"] == 2


# ---- empty directory ----

def test_empty_directory(tmp_path):
    s = _run(tmp_path)
    assert s["verdict"] == "PHASE4B_NO_ELIGIBLE_RECORDS"
    assert s["records_read"] == 0
    assert s["summaries_read"] == 0


# ---- ineligible summing + rejection rate ----

def test_ineligible_reasons_sum_and_rejection_rate(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [_record(-0.01, -0.01), _record(-0.02, 0.0),
                                                            _record(0.03, 0.01)])
    _write_summary(tmp_path, "phase4a_gross_edge_summary_1.json", 4, 3, {"SPREAD_TOO_WIDE": 1})
    _write_summary(tmp_path, "phase4a_gross_edge_summary_2.json", 2, 0, {"NO_COMPLEMENT_TOKEN": 2})
    s = _run(tmp_path)
    assert s["ineligible_reasons_total"] == {"SPREAD_TOO_WIDE": 1, "NO_COMPLEMENT_TOKEN": 2}
    # ineligible=3, eligible=3 -> 3/(3+3) = 0.5
    assert s["rejection_rate"] == pytest.approx(0.5)


# ---- stats ----

def test_mean_stdev_percentiles(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl",
                   [_record(-0.01, 0.0), _record(-0.02, 0.0), _record(-0.03, 0.0)])
    s = _run(tmp_path)
    d = s["gross_edge_distribution"]["buy_both_gross_edge"]
    assert d["count"] == 3
    assert d["mean"] == pytest.approx(-0.02)
    assert d["p50"] == pytest.approx(-0.02, abs=1e-6)
    assert d["stdev"] == pytest.approx(0.01, abs=1e-6)
    assert d["min"] == pytest.approx(-0.03)
    assert d["max"] == pytest.approx(-0.01)


# ---- missing optional fields handled ----

def test_missing_spread_and_delta_fields_safe(tmp_path):
    rec = {"phase": "4A_gross_edge", "buy_both_gross_edge": -0.01, "sell_both_gross_edge": 0.0}
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [rec])
    s = _run(tmp_path)
    assert s["verdict"] == "PHASE4B_AGGREGATE_SAMPLE_ONLY"
    # spread/delta distributions degrade to count 0, not crash
    assert s["spread_bps_distribution"]["count"] == 0
    assert s["pair_timestamp_delta_ms_distribution"]["count"] == 0
    assert s["gross_edge_distribution"]["buy_both_gross_edge"]["count"] == 1


def test_spread_distribution_combines_yes_and_no(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [_record(-0.01, 0.0, yspr=400.0, nspr=420.0)])
    s = _run(tmp_path)
    assert s["spread_bps_distribution"]["count"] == 2   # yes + no


# ---- output ----

def test_output_defaults_under_data_output():
    assert B.OUT_DIR.replace(os.sep, "/").rstrip("/").endswith("data/output")


def test_output_written_and_no_readiness_literals(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [_record(-0.01, -0.01)])
    s = _run(tmp_path)
    assert os.path.exists(s["output_path"])
    with open(s["output_path"]) as f:
        txt = f.read()
    for bad in ("EXECUTION_READY", "ECONOMICS_READY_FOR_PAPER", "PAPER_READY", "net_edge", "pnl"):
        assert bad not in txt
    assert s["official_f1b"] is False
    assert s["profitability"] is False
    assert s["phase"] == "4B_gross_edge_aggregate"


# ---- safety / isolation ----

def test_engine_no_forbidden_literals():
    with open(ENGINE_PATH, encoding="utf-8") as f:
        src = f.read()
    for bad in ("EXECUTION_READY", "ECONOMICS_READY_FOR_PAPER", "net_edge", "api_key", "api_secret",
                "private_key", "place_order", "get_balance", "os.environ", "getenv"):
        assert bad not in src, f"engine must not contain {bad!r}"


def test_cli_accepts_output_dir(tmp_path):
    _write_records(tmp_path, "phase4a_gross_edge_1.jsonl", [_record(-0.01, -0.01)])
    _write_summary(tmp_path, "phase4a_gross_edge_summary_1.json", 4, 1, {})
    outdir = tmp_path / "out"
    outdir.mkdir()
    r = subprocess.run([sys.executable, ENGINE_PATH, "--input-dir", str(tmp_path),
                        "--output-dir", str(outdir)], capture_output=True, text=True)
    assert r.returncode == 0
    assert any(f.startswith("phase4b_gross_edge_aggregate_") for f in os.listdir(outdir))


def test_engine_not_imported_by_production():
    res = subprocess.run(["grep", "-rIl", "--include=*.py", "phase4b_gross_edge", REPO],
                         capture_output=True, text=True)
    hits = [ln for ln in res.stdout.splitlines()
            if ln.strip() and "/tools/" not in ln and "/tests/" not in ln
            and "/data/output/" not in ln and "/graphify-out/" not in ln and "/.git/" not in ln]
    assert hits == [], f"phase4b engine must not be imported by production: {hits}"
