"""tools/phase4a_gross_edge_engine.py — Phase 4A Gross Edge v0 (offline analysis).

Reads Phase 3 JSONL snapshots and computes INTERNAL YES/NO complement-consistency metrics ONLY.
Each Phase 3 row carries one token's book; a YES/NO pair requires >=2 distinct two-sided tokens for the
same market_slug, near in time. If a pair cannot be derived, the slug is marked ineligible with an
explicit reason (no guessing). YES/NO labels are assigned deterministically (sorted token_id); the
complement metrics (ask_sum/bid_sum/buy_both/sell_both/complement_gap) are label-invariant.

OFFLINE ONLY: no live fetch, no endpoints, no market-data fetch, no auth/secrets, no orders/balances/
trading. NO net-edge / PnL / slippage / fees / market-impact. NOT execution/paper/economics ready; no
profitability/alpha claim. Anchor is YES_NO_COMPLEMENT (internal), not an external oracle/reference basket.

CLI: python3 tools/phase4a_gross_edge_engine.py --input data/output/<phase3_jsonl_file>
"""
import json
import os
import sys
import time

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")

PAIR_MAX_DELTA_MS = 5000
MAX_SPREAD_BPS = 500
LINEAGE_FIELDS = ("asset", "interval", "market_slug", "token_id", "utc_timestamp_ms")


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def best_bid(bids):
    """Highest bid price from [[price,size],...]; None if absent/invalid."""
    prices = [lvl[0] for lvl in (bids or [])
              if isinstance(lvl, (list, tuple)) and len(lvl) >= 1 and _is_number(lvl[0]) and lvl[0] > 0]
    return max(prices) if prices else None


def best_ask(asks):
    """Lowest ask price from [[price,size],...]; None if absent/invalid."""
    prices = [lvl[0] for lvl in (asks or [])
              if isinstance(lvl, (list, tuple)) and len(lvl) >= 1 and _is_number(lvl[0]) and lvl[0] > 0]
    return min(prices) if prices else None


def spread_bps(bid, ask):
    if not (_is_number(bid) and _is_number(ask)) or bid <= 0 or ask <= 0:
        return None
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid * 1e4 if mid else None


def complement_metrics(yes_bid, yes_ask, no_bid, no_ask):
    """Label-invariant internal complement metrics (no external reference)."""
    ask_sum = yes_ask + no_ask
    bid_sum = yes_bid + no_bid
    return {
        "ask_sum": round(ask_sum, 6),
        "bid_sum": round(bid_sum, 6),
        "buy_both_gross_edge": round(1.0 - ask_sum, 6),
        "sell_both_gross_edge": round(bid_sum - 1.0, 6),
        "complement_gap": round(ask_sum - bid_sum, 6),
    }


def _lineage_ok(row):
    return isinstance(row, dict) and all(
        row.get(f) not in (None, "") for f in LINEAGE_FIELDS)


def parse_rows(path):
    """Returns (rows, rows_read, rows_valid_json, rows_malformed). rows carry _line index."""
    rows = []
    rows_read = rows_valid = rows_malformed = 0
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rows_read += 1
            try:
                r = json.loads(line)
            except Exception:
                rows_malformed += 1
                continue
            rows_valid += 1
            if isinstance(r, dict):
                r["_line"] = ln
            rows.append(r)
    return rows, rows_read, rows_valid, rows_malformed


def _two_sided_view(row):
    """Return (bid, ask) if both sides present, else (None|val) — used to test two-sidedness."""
    return best_bid(row.get("bids")), best_ask(row.get("asks"))


def _pair_one_slug(slug_rows):
    """For one market_slug's rows return (record_or_None, reason_or_None).

    Requires >=2 distinct lineage-complete tokens; picks the cross-token row pair with minimal
    timestamp delta; applies two-sided / delta / spread filters.
    """
    lineage_rows = [r for r in slug_rows if _lineage_ok(r)]
    if not lineage_rows:
        return None, "LINEAGE_INCOMPLETE"
    distinct_tokens = sorted({r["token_id"] for r in lineage_rows})
    if len(distinct_tokens) < 2:
        return None, "NO_COMPLEMENT_TOKEN"

    yes_tok, no_tok = distinct_tokens[0], distinct_tokens[1]  # deterministic label assignment

    def two_sided_rows(tok):
        out = []
        for r in lineage_rows:
            if r["token_id"] != tok:
                continue
            b, a = _two_sided_view(r)
            if _is_number(b) and _is_number(a):
                out.append((r, b, a))
        return out

    yrows = two_sided_rows(yes_tok)
    nrows = two_sided_rows(no_tok)
    if not yrows or not nrows:
        return None, "ONE_SIDED_BOOK"

    # cross pair with minimal |ts delta|
    best = None
    for (yr, yb, ya) in yrows:
        for (nr, nb, na) in nrows:
            d = abs(yr["utc_timestamp_ms"] - nr["utc_timestamp_ms"])
            if best is None or d < best[0]:
                best = (d, yr, yb, ya, nr, nb, na)
    delta, yr, yb, ya, nr, nb, na = best
    if delta > PAIR_MAX_DELTA_MS:
        return None, "PAIR_DELTA_EXCEEDED"

    y_spread = spread_bps(yb, ya)
    n_spread = spread_bps(nb, na)
    if y_spread is None or n_spread is None or y_spread > MAX_SPREAD_BPS or n_spread > MAX_SPREAD_BPS:
        return None, "SPREAD_TOO_WIDE"

    cm = complement_metrics(yb, ya, nb, na)
    record = {
        "phase": "4A_gross_edge",
        "source_rows": [yr.get("_line"), nr.get("_line")],
        "asset": yr.get("asset"),
        "interval": yr.get("interval"),
        "market_slug": yr.get("market_slug"),
        "yes_token_id": yes_tok,
        "no_token_id": no_tok,
        "yes_best_bid": yb,
        "yes_best_ask": ya,
        "no_best_bid": nb,
        "no_best_ask": na,
        "ask_sum": cm["ask_sum"],
        "bid_sum": cm["bid_sum"],
        "buy_both_gross_edge": cm["buy_both_gross_edge"],
        "sell_both_gross_edge": cm["sell_both_gross_edge"],
        "complement_gap": cm["complement_gap"],
        "yes_spread_bps": round(y_spread, 4),
        "no_spread_bps": round(n_spread, 4),
        "pair_timestamp_delta_ms": delta,
        "eligibility_flags": ["ELIGIBLE"],
        "anchor_type": "YES_NO_COMPLEMENT",
        "official_f1b": False,
        "profitability": False,
    }
    return record, None


def run(*, input_path, output_dir=OUT_DIR, timestamp_fn=None):
    if timestamp_fn is None:
        timestamp_fn = lambda: int(time.time())  # noqa: E731
    now = timestamp_fn()
    jsonl_path = os.path.join(output_dir, f"phase4a_gross_edge_{now}.jsonl")
    summary_path = os.path.join(output_dir, f"phase4a_gross_edge_summary_{now}.json")

    ineligible = {}
    records = []
    rows_read = rows_valid = rows_malformed = 0
    fatal = None
    candidate_pairs = 0

    try:
        rows, rows_read, rows_valid, rows_malformed = parse_rows(input_path)
        by_slug = {}
        for r in rows:
            if isinstance(r, dict) and r.get("market_slug"):
                by_slug.setdefault(r["market_slug"], []).append(r)
            else:
                ineligible["LINEAGE_INCOMPLETE"] = ineligible.get("LINEAGE_INCOMPLETE", 0) + 1
        for slug, slug_rows in by_slug.items():
            distinct = {r.get("token_id") for r in slug_rows if _lineage_ok(r)}
            if len(distinct) >= 2:
                candidate_pairs += 1
            rec, reason = _pair_one_slug(slug_rows)
            if rec is not None:
                records.append(rec)
            else:
                ineligible[reason] = ineligible.get(reason, 0) + 1
    except Exception as e:
        fatal = type(e).__name__

    buys = [r["buy_both_gross_edge"] for r in records]
    sells = [r["sell_both_gross_edge"] for r in records]

    if fatal:
        verdict = "GROSS_EDGE_FAILED"
    elif records:
        verdict = "GROSS_EDGE_SAMPLE_ONLY"
    else:
        verdict = "GROSS_EDGE_NO_ELIGIBLE_SNAPSHOTS"

    summary = {
        "verdict": verdict,
        "phase": "4A_gross_edge",
        "input_path": input_path,
        "output_jsonl": jsonl_path,
        "output_summary": summary_path,
        "rows_read": rows_read,
        "rows_valid_json": rows_valid,
        "rows_malformed": rows_malformed,
        "candidate_pairs": candidate_pairs,
        "eligible_pairs": len(records),
        "ineligible_reasons": dict(sorted(ineligible.items())),
        "max_buy_both_gross_edge": round(max(buys), 6) if buys else None,
        "max_sell_both_gross_edge": round(max(sells), 6) if sells else None,
        "mean_buy_both_gross_edge": round(sum(buys) / len(buys), 6) if buys else None,
        "mean_sell_both_gross_edge": round(sum(sells) / len(sells), 6) if sells else None,
        "anchor_type": "YES_NO_COMPLEMENT",
        "official_f1b": False,
        "profitability": False,
        "fatal_error": fatal,
        "generated_at_unix": now,
    }

    if not fatal:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


if __name__ == "__main__":  # pragma: no cover
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--input":
        s = run(input_path=args[1])
        print(json.dumps(s, indent=2))
    else:
        raise SystemExit("usage: phase4a_gross_edge_engine.py --input <phase3_jsonl_file>")
