"""tools/phase4b_gross_edge_aggregate.py — Phase 4B aggregate gross-edge analyzer (offline).

Aggregates Phase 4A artifacts in a directory:
  - records:   phase4a_gross_edge_*.jsonl       (one eligible YES/NO complement pair per line)
  - summaries: phase4a_gross_edge_summary_*.json (per-run candidate/eligible/ineligible counts)
into statistical distributions for buy_both_gross_edge, sell_both_gross_edge, pair_timestamp_delta_ms,
and spread_bps (yes+no combined; robust to missing fields).

OFFLINE ONLY: no live fetch, no endpoints, no market-data fetch, no auth/secrets, no trading.
NO net-edge / PnL / slippage / market-impact. NOT execution/paper/economics ready; no profitability/
alpha claim. Distributions are internal complement-consistency diagnostics, NOT trading signals.

CLI: python3 tools/phase4b_gross_edge_aggregate.py --input-dir data/output
"""
import glob
import json
import os
import statistics
import sys
import time

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _pct(sorted_vals, q):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    fr = idx - lo
    return sorted_vals[lo] * (1 - fr) + sorted_vals[hi] * fr


def _dist(vals):
    s = sorted(v for v in vals if _is_number(v))
    if not s:
        return {"count": 0, "mean": None, "stdev": None, "min": None, "max": None,
                "p05": None, "p50": None, "p95": None}
    n = len(s)
    return {
        "count": n,
        "mean": round(sum(s) / n, 6),
        "stdev": round(statistics.stdev(s), 6) if n >= 2 else 0.0,
        "min": round(s[0], 6),
        "max": round(s[-1], 6),
        "p05": round(_pct(s, 0.05), 6),
        "p50": round(_pct(s, 0.50), 6),
        "p95": round(_pct(s, 0.95), 6),
    }


def run(*, input_dir, output_dir=OUT_DIR, timestamp_fn=None):
    if timestamp_fn is None:
        timestamp_fn = lambda: int(time.time())  # noqa: E731
    now = timestamp_fn()
    output_path = os.path.join(output_dir, f"phase4b_gross_edge_aggregate_{now}.json")

    fatal = None
    summary_files = []
    record_files = []
    summaries_read = 0
    records_read = 0
    rows_malformed = 0
    candidate_total = 0
    eligible_total_from_summaries = 0
    have_summaries = False
    ineligible_total = {}
    buys, sells, deltas, spreads = [], [], [], []

    try:
        all_json = sorted(glob.glob(os.path.join(input_dir, "phase4a_gross_edge_summary_*.json")))
        summary_files = all_json
        all_jsonl = sorted(glob.glob(os.path.join(input_dir, "phase4a_gross_edge_*.jsonl")))
        record_files = all_jsonl

        for sf in summary_files:
            try:
                with open(sf, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                rows_malformed += 1
                continue
            summaries_read += 1
            have_summaries = True
            if _is_number(d.get("candidate_pairs")):
                candidate_total += d["candidate_pairs"]
            if _is_number(d.get("eligible_pairs")):
                eligible_total_from_summaries += d["eligible_pairs"]
            for reason, cnt in (d.get("ineligible_reasons") or {}).items():
                if _is_number(cnt):
                    ineligible_total[reason] = ineligible_total.get(reason, 0) + cnt

        for rf in record_files:
            with open(rf, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        rows_malformed += 1
                        continue
                    records_read += 1
                    if _is_number(rec.get("buy_both_gross_edge")):
                        buys.append(rec["buy_both_gross_edge"])
                    if _is_number(rec.get("sell_both_gross_edge")):
                        sells.append(rec["sell_both_gross_edge"])
                    if _is_number(rec.get("pair_timestamp_delta_ms")):
                        deltas.append(rec["pair_timestamp_delta_ms"])
                    for k in ("yes_spread_bps", "no_spread_bps"):
                        if _is_number(rec.get(k)):
                            spreads.append(rec[k])
    except Exception as e:
        fatal = type(e).__name__

    eligible_pairs_total = eligible_total_from_summaries if have_summaries else records_read
    ineligible_count = sum(ineligible_total.values())
    denom = ineligible_count + eligible_pairs_total
    rejection_rate = round(ineligible_count / denom, 6) if denom > 0 else None

    if fatal:
        verdict = "PHASE4B_FAILED"
    elif eligible_pairs_total > 0:
        verdict = "PHASE4B_AGGREGATE_SAMPLE_ONLY"
    else:
        verdict = "PHASE4B_NO_ELIGIBLE_RECORDS"

    out = {
        "verdict": verdict,
        "phase": "4B_gross_edge_aggregate",
        "input_dir": input_dir,
        "output_path": output_path,
        "input_phase4a_summary_files": [os.path.basename(p) for p in summary_files],
        "input_phase4a_record_files": [os.path.basename(p) for p in record_files],
        "summaries_read": summaries_read,
        "records_read": records_read,
        "rows_malformed": rows_malformed,
        "candidate_pairs_total": candidate_total if have_summaries else None,
        "eligible_pairs_total": eligible_pairs_total,
        "ineligible_reasons_total": dict(sorted(ineligible_total.items())),
        "rejection_rate": rejection_rate,
        "gross_edge_distribution": {
            "buy_both_gross_edge": _dist(buys),
            "sell_both_gross_edge": _dist(sells),
        },
        "pair_timestamp_delta_ms_distribution": _dist(deltas),
        "spread_bps_distribution": _dist(spreads),
        "anchor_type": "YES_NO_COMPLEMENT",
        "official_f1b": False,
        "profitability": False,
        "fatal_error": fatal,
        "generated_at_unix": now,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return out


def _parse_cli(args):
    """--input-dir <dir> [--output-dir <dir>]. Returns (input_dir, output_dir) or raises SystemExit."""
    input_dir = None
    output_dir = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--input-dir":
            if i + 1 >= len(args):
                raise SystemExit("usage: --input-dir requires a dir")
            input_dir = args[i + 1]; i += 2
        elif a == "--output-dir":
            if i + 1 >= len(args):
                raise SystemExit("usage: --output-dir requires a dir")
            output_dir = args[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument: {a}")
    if input_dir is None:
        raise SystemExit("usage: phase4b_gross_edge_aggregate.py --input-dir <dir> [--output-dir <dir>]")
    return input_dir, output_dir


if __name__ == "__main__":  # pragma: no cover
    _indir, _outdir = _parse_cli(sys.argv[1:])
    s = run(input_dir=_indir, output_dir=_outdir or OUT_DIR)
    print(json.dumps(s, indent=2))
