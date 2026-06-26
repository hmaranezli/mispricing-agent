"""tests/test_miami_oneshot_runner.py — TDD for Miami v3 Sub-slice B one-shot live runner.

The runner's tested core performs exactly one read-only one-shot: YES book, NO book, Hyperliquid
reference, and condition_id metadata — all via INJECTED fetcher callables (fakes in tests; no live
network). It adapts results into assemble_snapshot_inputs, calls compute_decision_row, merges note
markers + operator_fee_cost into row['notes'], and prints a compact summary (full dump only under
--full/--verbose). CSV append only under --append + --csv-path.

Exit codes: 0 success, 1 fetch error, 2 validation/cross-check, 3 internal.

First RED: module tools.miami_oneshot_runner does not exist -> ImportError.
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.miami_oneshot_runner as runner
from tools.miami_oneshot_runner import main

_NOW = "2026-06-26T17:50:00Z"
YES_PSB = {"bids": [{"price": 0.81, "size": 50}], "asks": [{"price": 0.83, "size": 50}]}
NO_PSB = {"bids": [{"price": 0.17, "size": 150}], "asks": [{"price": 0.19, "size": 150}]}
THIN_YES_PSB = {"bids": [{"price": 0.81, "size": 50}], "asks": [{"price": 0.83, "size": 4}]}


def _metadata(**over):
    md = {"tokens": [{"outcome": "Up", "token_id": "YESTOK"},
                     {"outcome": "Down", "token_id": "NOTOK"}],
          "strike": 65000.0, "expiry": "2026-06-26T18:00:00Z", "error_code": None}
    md.update(over)
    return md


def _fakes(*, yes_psb=YES_PSB, no_psb=NO_PSB, price=65135.0, src_ts=None, md=None,
           yes_err=None, no_err=None, ref_err=None, md_raises=False):
    calls = {"book": [], "ref": [], "md": []}

    def book(tid):
        calls["book"].append(tid)
        if tid == "YESTOK":
            return {"parsed_safe_book": yes_psb if yes_err is None else None, "error_code": yes_err}
        return {"parsed_safe_book": no_psb if no_err is None else None, "error_code": no_err}

    def ref(asset):
        calls["ref"].append(asset)
        r = {"price": price if ref_err is None else None, "error_code": ref_err}
        if src_ts:
            r["source_event_ts"] = src_ts
        return r

    def meta(cid):
        calls["md"].append(cid)
        if md_raises:
            raise RuntimeError("boom")
        return md if md is not None else _metadata()

    return book, ref, meta, calls


def _argv(overrides=None, flags=()):
    base = {
        "--yes-token-id": "YESTOK", "--no-token-id": "NOTOK", "--condition-id": "0xCID",
        "--asset": "BTC", "--timeframe": "1h", "--strike": "65000.0",
        "--expiry": "2026-06-26T18:00:00Z", "--intended-stake-usd": "5.0",
        "--base-url": "https://clob.example.com", "--fee-cost": "0.01",
    }
    if overrides:
        base.update(overrides)
    argv = []
    for k, v in base.items():
        if v is None:
            continue
        argv += [k, str(v)]
    return argv + list(flags)


def _run(argv, fakes=None, now=_NOW):
    if fakes is None:
        fakes = _fakes()
    book, ref, meta, calls = fakes
    out = io.StringIO()
    code = main(argv, book_fetcher=book, reference_fetcher=ref, metadata_fetcher=meta,
                now_fn=lambda: now, out=out)
    return code, out.getvalue(), calls


# ===========================================================================
# Rule 4 — exit codes
# ===========================================================================

def test_success_exit_0():
    code, out, _ = _run(_argv())
    assert code == 0


def test_fetch_error_exit_1():
    code, out, calls = _run(_argv(), fakes=_fakes(yes_err="http_429"))
    assert code == 1


def test_crosscheck_failure_exit_2():
    code, out, _ = _run(_argv(), fakes=_fakes(md=_metadata(strike=64000.0)))
    assert code == 2


def test_internal_error_exit_3():
    code, out, _ = _run(_argv(), fakes=_fakes(md_raises=True))
    assert code == 3


# ===========================================================================
# Rule 1 — metadata source / cross-check
# ===========================================================================

def test_condition_id_required():
    code, out, calls = _run(_argv({"--condition-id": None}))
    assert code == 2


def test_metadata_fetched_with_condition_id():
    code, out, calls = _run(_argv())
    assert calls["md"] == ["0xCID"]


def test_metadata_strike_mismatch_fail_closed():
    code, out, _ = _run(_argv(), fakes=_fakes(md=_metadata(strike=1.0)))
    assert code == 2


def test_metadata_fetch_reject_exit_1():
    code, out, _ = _run(_argv(), fakes=_fakes(md=_metadata(error_code="clob_market_http_error")))
    assert code == 1


# ===========================================================================
# one-shot: each fetcher called exactly once
# ===========================================================================

def test_one_shot_each_fetcher_called_once():
    code, out, calls = _run(_argv())
    assert calls["book"] == ["YESTOK", "NOTOK"]
    assert calls["ref"] == ["BTC"]
    assert calls["md"] == ["0xCID"]


# ===========================================================================
# Rule 2 — reference fidelity (markers persist in final notes)
# ===========================================================================

def test_basis_and_degraded_markers_in_notes():
    code, out, _ = _run(_argv())  # no source_event_ts -> degraded
    assert "basis_risk_accepted_hyperliquid_vs_settlement_oracle" in out
    assert "degraded_ts_override" in out


def test_trusted_ts_has_basis_no_degraded():
    code, out, _ = _run(_argv(), fakes=_fakes(src_ts="2026-06-26T17:49:59Z"))
    assert "basis_risk_accepted_hyperliquid_vs_settlement_oracle" in out
    assert "degraded_ts_override" not in out


# ===========================================================================
# Rule 6 — fee cost required, >0, audited into notes
# ===========================================================================

def test_fee_cost_required():
    code, out, calls = _run(_argv({"--fee-cost": None}))
    assert code == 2


def test_fee_cost_zero_fails_before_any_fetch():
    code, out, calls = _run(_argv({"--fee-cost": "0"}))
    assert code == 2
    assert calls["book"] == [] and calls["ref"] == [] and calls["md"] == []


def test_fee_cost_negative_fails_before_any_fetch():
    code, out, calls = _run(_argv({"--fee-cost": "-0.01"}))
    assert code == 2
    assert calls["book"] == []


def test_operator_fee_cost_audited_in_notes():
    code, out, _ = _run(_argv({"--fee-cost": "0.02"}))
    assert "operator_fee_cost=0.02" in out


# ===========================================================================
# Rule 5 — CSV strictly opt-in
# ===========================================================================

def test_append_without_csv_path_fails_before_fetch():
    code, out, calls = _run(_argv(flags=("--append",)))
    assert code == 2
    assert calls["book"] == [] and calls["md"] == []


def test_default_is_print_only_no_csv(monkeypatch):
    appends = []
    monkeypatch.setattr(runner, "append_decision_row",
                        lambda row, path, create_parents=False: appends.append(path))
    code, out, _ = _run(_argv())
    assert code == 0 and appends == []


def test_append_with_path_calls_writer_once(monkeypatch, tmp_path):
    appends = []
    monkeypatch.setattr(runner, "append_decision_row",
                        lambda row, path, create_parents=False: appends.append((path, row)))
    p = str(tmp_path / "log.csv")
    code, out, _ = _run(_argv({"--csv-path": p}, flags=("--append",)))
    assert code == 0
    assert len(appends) == 1 and appends[0][0] == p
    # appended row carries the audited fee + markers in its notes
    assert "operator_fee_cost=0.01" in appends[0][1]["notes"]


# ===========================================================================
# Rule 3 — compact output, rejection reason, full dump gating
# ===========================================================================

def test_compact_summary_contains_required_fields():
    code, out, _ = _run(_argv())
    for field in ("candidate", "selected_side_candidate", "yes_adjusted_edge", "no_adjusted_edge",
                  "liquidity_status", "is_pin_risk", "reference_staleness_ms",
                  "trade_allowed", "operator_decision_required", "notes"):
        assert field in out


def test_compact_summary_not_full_dump_by_default():
    code, out, _ = _run(_argv())
    assert "yes_spread_cost" not in out   # a 48-row-only field absent in compact mode


def test_full_flag_dumps_all_fields():
    code, out, _ = _run(_argv(flags=("--full",)))
    assert "yes_spread_cost" in out and "no_market_edge" in out


def test_candidate_false_prints_pin_rejection_reason():
    # spot essentially at strike -> pin
    code, out, _ = _run(_argv(), fakes=_fakes(price=65000.4))
    assert "candidate" in out
    assert "pin_risk" in out


def test_candidate_false_prints_liquidity_rejection_reason():
    # not pin (spot 65135), thin book (avail 4) + large stake -> insufficient
    code, out, _ = _run(_argv({"--intended-stake-usd": "30.0"}),
                        fakes=_fakes(yes_psb=THIN_YES_PSB))
    assert "insufficient_liquidity_or_weak_fill" in out


def test_crosscheck_failure_does_not_fabricate_decision_row():
    code, out, _ = _run(_argv(), fakes=_fakes(md=_metadata(strike=64000.0)))
    assert code == 2
    assert "selected_side_candidate" not in out   # no decision row fabricated
    assert "crosscheck" in out.lower() or "mismatch" in out.lower() or "strike" in out.lower()


def test_governance_fields_in_output():
    code, out, _ = _run(_argv())
    assert "trade_allowed" in out and "False" in out
    assert "operator_decision_required" in out


# ===========================================================================
# No live API: fetchers are required (no hidden network default)
# ===========================================================================

def test_main_requires_injected_fetchers():
    with pytest.raises(TypeError):
        main(_argv())  # missing book_fetcher/reference_fetcher/metadata_fetcher


# ===========================================================================
# Source scan
# ===========================================================================

def test_source_scan_no_forbidden_surfaces():
    src = open(runner.__file__, "r", encoding="utf-8").read()
    low = src.lower()
    for banned in ("place_order", "submit_order", "order_placement", "wallet", "signing",
                   "scheduler", " cron", "while true", "s1_storage", "autonomous"):
        assert banned not in low, f"forbidden term {banned!r} present"
    import_lines = "\n".join(ln for ln in src.splitlines()
                             if ln.strip().startswith(("import ", "from "))).lower()
    for forbidden in ("execution", "council", "scout", "sqlite", "aiohttp", "requests", "socket"):
        assert forbidden not in import_lines, f"must not import {forbidden!r}"
