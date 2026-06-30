#!/usr/bin/env python3
"""
Gate G7 — Paper Edge/PnL Vertical Evaluator.

Loads entry-time candidates from an existing G.5/G7-lite telemetry DB (READ-ONLY), reuses
the PROVEN G.6 Gamma+CLOB winner-consensus resolution path UNMODIFIED, computes a paper
hold-to-resolution PnL with a verified (never-assumed) fee, and reports shadow threshold
buckets + a diagnosis when net PnL is negative.

WARNING: PAPER/SHADOW evaluation only. NOT tradeable alpha. NOT a live order. NO wallet,
signing, or capital. The HL-vs-Chainlink source-basis confounder remains unresolved.

HARD BOUNDARIES:
  * PUBLIC read-only GET only (Gamma + CLOB, same proven G.6 path). NO auth/wallet/orders.
  * DB opened READ-ONLY/immutable; NO DB writes. NO S1 access.
  * Exactly ONE Gamma fetch + ONE CLOB fetch per unique condition_id (fee metadata is read
    from the SAME cached Gamma response used for resolution — no extra network call).
  * No polling, retry, or waiting loop. One-shot evaluation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from decimal import Decimal

from analysis.forensic import gateg7_paper_pnl as pp
from tools.gateg6_terminal_evaluator import (
    ST_RESOLVED, TransportError, gamma_fetch_live, clob_fetch_live,
    evaluate_candidate as g6_evaluate_candidate,
)

DEFAULT_STAKE = Decimal("25")
ALPHA_WARNING = "PAPER/SHADOW evaluation, NOT tradeable alpha. HL-vs-Chainlink basis unresolved."
_COLS = ["signal_id", "asset", "side", "slug", "condition_id", "token_id", "outcome_index",
         "outcome_label", "ts_signal", "ts_signal_ms", "market_end_ts", "exec_ask_vwap",
         "exec_fill_qty_avail", "entry_edge", "fill_decision", "reference_age_ms", "tte_s"]


def load_all_signal_rows(db_path: str) -> list:
    """READ-ONLY/immutable load of every signal_log row (all fill_decisions, all assets).
    No end-time prefilter — the resolution fetch itself fails closed for not-yet-ended
    markets (RESOLUTION_NOT_FINAL), which is the honest, fail-closed behavior we want."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    try:
        rows = conn.execute(f"SELECT {','.join(_COLS)} FROM signal_log").fetchall()
    finally:
        conn.close()
    return [dict(zip(_COLS, r)) for r in rows]


def _match_gamma_market(payload, slug, condition_id):
    """Find the matched market dict in a Gamma response (mirrors evaluate_candidate's own
    slug+conditionId filter) so fee fields can be read from the SAME payload."""
    markets = payload if isinstance(payload, list) else [payload]
    for m in markets:
        if isinstance(m, dict) and m.get("slug") == slug and m.get("conditionId") == condition_id:
            return m
    return None


def evaluate_full_candidate(cand, *, gamma_fetch=gamma_fetch_live, clob_fetch=clob_fetch_live):
    """One resolution + fee + PnL evaluation. Exactly one Gamma GET + (when resolution
    proceeds) one CLOB GET per condition_id — fee fields piggyback on the cached Gamma
    response via a memoizing wrapper, never a separate fetch."""
    cache: dict = {}

    def cached_gamma_fetch(slug, condition_id):
        if "payload" not in cache:
            cache["payload"] = gamma_fetch(slug, condition_id)
        return cache["payload"]

    g6_result = g6_evaluate_candidate(cand, gamma_fetch=cached_gamma_fetch, clob_fetch=clob_fetch)

    fee_market = _match_gamma_market(cache.get("payload"), cand.get("slug"), cand["condition_id"])
    fee_cfg = pp.parse_fee_config(fee_market)

    result = dict(g6_result)
    result["fee_status"] = fee_cfg["fee_status"]
    result["fee_rate"] = str(fee_cfg["fee_rate"]) if fee_cfg["fee_rate"] is not None else None

    if g6_result["status"] != ST_RESOLVED:
        result["net_pnl"] = None
        return result

    exec_ask = pp._d(cand["exec_ask_vwap"])
    qty_avail = pp._d(cand.get("exec_fill_qty_avail")) or Decimal("0")
    filled_qty = pp.clamp_fill_qty(qty_avail, exec_ask, DEFAULT_STAKE)
    fee = (pp.entry_fee_quadratic(filled_qty, fee_cfg["fee_rate"], exec_ask)
           if fee_cfg["fee_rate"] is not None else None)
    pnl = pp.compute_pnl(filled_qty=filled_qty, exec_ask_vwap=exec_ask,
                         won=g6_result["matched"], fee=fee)

    result.update({"filled_qty": str(filled_qty), "entry_notional": str(pnl["entry_notional"]),
                   "fee": (str(fee) if fee is not None else None),
                   "gross_pnl": str(pnl["gross_pnl"]), "net_pnl": pnl["net_pnl"]})
    return result


def diagnose_negative_pnl(deduped_candidates, results_by_signal_id):
    """Attribute a negative-PnL cohort using STORED entry-time evidence only. Never proposes
    infrastructure work — purely descriptive statistics over fields already in signal_log."""
    resolved = [(c, results_by_signal_id[c["signal_id"]]) for c in deduped_candidates
                if results_by_signal_id.get(c["signal_id"], {}).get("status") == ST_RESOLVED]
    losers = [(c, r) for c, r in resolved if r.get("matched") is False]
    winners = [(c, r) for c, r in resolved if r.get("matched") is True]
    if not resolved:
        return {"note": "no resolved candidates; diagnosis requires settled outcomes"}

    def _mean(xs):
        xs = [x for x in xs if x is not None]
        return str(sum(xs, Decimal("0")) / len(xs)) if xs else None

    loser_edges = [pp._d(c["entry_edge"]) for c, _ in losers]
    winner_edges = [pp._d(c["entry_edge"]) for c, _ in winners]
    loser_ages = [int(c["reference_age_ms"]) for c, _ in losers if c.get("reference_age_ms") is not None]
    fee_drags = [pp._d(r["gross_pnl"]) - r["net_pnl"] for c, r in resolved
                 if isinstance(r.get("net_pnl"), Decimal) and r.get("gross_pnl") is not None]
    tte_losers = [pp._d(c.get("tte_s")) for c, _ in losers if c.get("tte_s") is not None]

    return {
        "wrong_directional_model": {
            "loser_count": len(losers), "winner_count": len(winners),
            "mean_entry_edge_losers": _mean(loser_edges), "mean_entry_edge_winners": _mean(winner_edges),
        },
        "ask_spread_depth_cost": {
            "mean_exec_ask_vwap_losers": _mean([pp._d(c["exec_ask_vwap"]) for c, _ in losers]),
            "note": "executable ask already embeds spread; no separate spread fee charged",
        },
        "stale_reference": {"mean_reference_age_ms_losers": (sum(loser_ages) / len(loser_ages))
                            if loser_ages else None},
        "proxy_hl_basis": {"note": "HL-vs-Chainlink source-basis confounder unresolved; "
                                   "entry_edge is HL-basis diagnostic, not Chainlink-aligned"},
        "entry_timing": {"mean_tte_s_losers": _mean(tte_losers)},
        "fee_drag": {"mean_fee_drag": _mean(fee_drags), "count_fee_unverifiable":
                     sum(1 for _, r in resolved if r.get("net_pnl") == pp.FEE_METADATA_MISSING)},
    }


def build_telegram_summary(cohort, bucket_reports, diagnosis, verdict):
    lines = [f"G7 Paper Edge/PnL Smoke — {verdict}",
             f"Entries(>0 edge): {cohort['candidates']} | Resolved: {cohort['resolved']} "
             f"({cohort['wins']}W/{cohort['losses']}L, {cohort['win_rate']})",
             f"Effective-N: {cohort['unique_windows']} windows",
             f"Net PnL total: ${cohort['total_net_pnl']} (mean ${cohort['mean_net_pnl']})"]
    for label in (">0", ">=0.03", ">=0.05", ">=0.10", ">=0.15", ">=0.25"):
        b = bucket_reports.get(label, {})
        lines.append(f"  {label}: n={b.get('candidates', 0)} resolved={b.get('resolved', 0)} "
                     f"net=${b.get('total_net_pnl', '0')}")
    if cohort.get("best_win") is not None:
        lines.append(f"Best win: ${cohort['best_win']} | Worst loss: ${cohort['worst_loss']}")
    if diagnosis and "note" not in diagnosis:
        lines.append("Diagnosis: " + json.dumps(diagnosis, default=str))
    lines.append(ALPHA_WARNING)
    return "\n".join(lines)


def run_evaluation(db_path: str, *, gamma_fetch=gamma_fetch_live, clob_fetch=clob_fetch_live) -> dict:
    """One-shot evaluation. No polling, no retry, no wait."""
    all_rows = load_all_signal_rows(db_path)
    eligible = pp.select_eligible_candidates(all_rows)
    deduped = pp.dedup_earliest_by_condition(eligible)
    eff_n = pp.effective_n_windows(deduped)
    buckets = pp.shadow_buckets(deduped)

    base_cohort = buckets[">0"]    # broadest bucket; every narrower bucket is its subset
    results_by_signal_id = {}
    for cand in base_cohort:
        results_by_signal_id[cand["signal_id"]] = evaluate_full_candidate(
            cand, gamma_fetch=gamma_fetch, clob_fetch=clob_fetch)

    bucket_reports = {}
    for label, cands in buckets.items():
        results = [results_by_signal_id[c["signal_id"]] for c in cands
                  if c["signal_id"] in results_by_signal_id]
        bucket_reports[label] = pp.aggregate_bucket(results)

    cohort = bucket_reports[">0"]
    diagnosis = None
    if cohort["resolved"] > 0 and cohort["total_net_pnl"] < 0:
        diagnosis = diagnose_negative_pnl(base_cohort, results_by_signal_id)

    if cohort["resolved"] == 0:
        verdict = "INSUFFICIENT_RESOLVED_N"
    elif cohort["total_net_pnl"] > 0:
        verdict = "EDGE_PROMISING"
    else:
        verdict = "EDGE_NEGATIVE_DIAGNOSE"

    return {
        "warning": ALPHA_WARNING, "effective_n": eff_n, "verdict": verdict,
        "cohort": cohort, "bucket_reports": bucket_reports, "diagnosis": diagnosis,
        "telegram_summary": build_telegram_summary(cohort, bucket_reports, diagnosis, verdict),
        "per_candidate": [results_by_signal_id[c["signal_id"]] for c in base_cohort],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args(argv)
    sys.stderr.write("Gate G7 Paper Edge/PnL Evaluator — public read-only, no DB write, no S1.\n")
    report = run_evaluation(args.db)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
