"""tools/phase3_exec_logic.py — Phase 3 execution-sampling PURE LOGIC (read-only research).

PUBLIC_REFERENCE_BASKET / Phase 3 = EXECUTION readiness ONLY. SAF/OFFLINE: book parsing, slippage walk,
diversity accounting, percentiles, per-cell aggregation (NO cross-asset/interval merging) ve verdict.
Hiçbir network/secret/auth/order/balance YOK — bu modül yalnız veri yapıları üzerinde çalışır.
Production'a (main_loop/config/trading) BAĞLI DEĞİL.

Phase 3 KÂR/ALPHA İSPATLAMAZ. ECONOMICS_READY_FOR_PAPER yalnız sonraki Phase 4 (gross_edge) + Phase 5
(net_edge) ile gelir. NOT official_f1b.

Confirmed human-owned parameters (caller doğruladı):
  PER_SLUG_CAP        5m=20, 15m=10
  MIN_UNIQUE_SLUGS    ETH5m=20, SOL5m=10, XRP5m=10, ETH15m=8
  MIN_TWO_SIDED_RATIO 0.70
  MIN_FILL_RATIO      0.90 for $25/$50/$150 ; $500/$1000 report-only
  MAX_P95_SPREAD_BPS  ETH5m=30, SOL5m=60, XRP5m=60 ; ETH15m control/report-only (not gating)
"""

LINEAGE_FIELDS = ("asset", "interval", "market_slug", "token_id", "utc_timestamp_ms")
NOTIONAL_TIERS = (25, 50, 150, 500, 1000)
GATING_TIERS = ("25", "50", "150")
REPORT_ONLY_TIERS = ("500", "1000")
MIN_TWO_SIDED_RATIO = 0.70
MIN_FILL_RATIO = 0.90

CELL_PARAMS = {
    "ETH|5m":  {"target_n": 300, "min_unique_slugs": 20, "per_slug_cap": 20,
                "max_p95_spread_bps": 30, "spread_gating": True},
    "SOL|5m":  {"target_n": 150, "min_unique_slugs": 10, "per_slug_cap": 20,
                "max_p95_spread_bps": 60, "spread_gating": True},
    "XRP|5m":  {"target_n": 150, "min_unique_slugs": 10, "per_slug_cap": 20,
                "max_p95_spread_bps": 60, "spread_gating": True},
    "ETH|15m": {"target_n": 100, "min_unique_slugs": 8, "per_slug_cap": 10,
                "max_p95_spread_bps": None, "spread_gating": False},  # control / report-only
}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---- spread ----

def spread_bps(best_bid, best_ask):
    """(ask - bid) / mid * 1e4. Geçersiz/non-positive → ValueError."""
    if not (_is_number(best_bid) and _is_number(best_ask)):
        raise ValueError("bid/ask numeric olmalı")
    if best_bid <= 0 or best_ask <= 0:
        raise ValueError("bid/ask pozitif olmalı")
    mid = (best_bid + best_ask) / 2.0
    return (best_ask - best_bid) / mid * 1e4


# ---- slippage walk ----

def slippage_walk(levels, notional):
    """Buy-side walk: `levels` = ucuzdan pahalıya [(price,size)]. `notional` $ doldurulur.

    Döner: {slippage_bps (vwap vs best), filled_notional, fully_filled, flag}. Tam dolmazsa
    flag=DEPTH_TOO_THIN. Boş book → slippage_bps None, flag DEPTH_TOO_THIN.
    """
    if not levels or not _is_number(notional) or notional <= 0:
        return {"slippage_bps": None, "filled_notional": 0.0, "fully_filled": False,
                "flag": "DEPTH_TOO_THIN" if levels is not None else None}
    best = levels[0][0]
    spent = 0.0
    shares = 0.0
    cost = 0.0
    for price, size in levels:
        if not (_is_number(price) and _is_number(size)) or price <= 0 or size <= 0:
            continue
        level_notional = price * size
        take = min(level_notional, notional - spent)
        if take <= 0:
            break
        take_shares = take / price
        shares += take_shares
        cost += take_shares * price
        spent += take
        if spent >= notional - 1e-9:
            break
    fully = spent >= notional - 1e-9
    slip = ((cost / shares) - best) / best * 1e4 if shares > 0 and best else None
    return {"slippage_bps": round(slip, 4) if slip is not None else None,
            "filled_notional": round(spent, 4), "fully_filled": fully,
            "flag": None if fully else "DEPTH_TOO_THIN"}


# ---- book classification ----

def classify_book(snapshot):
    """LINEAGE_MISSING | INSUFFICIENT_BOOK_DATA | ONE_SIDED_BOOK | TWO_SIDED."""
    if not isinstance(snapshot, dict):
        return "LINEAGE_MISSING"
    for f in LINEAGE_FIELDS:
        v = snapshot.get(f)
        if v is None or (f != "utc_timestamp_ms" and v == ""):
            return "LINEAGE_MISSING"
    bids = snapshot.get("bids") or []
    asks = snapshot.get("asks") or []
    if not bids and not asks:
        return "INSUFFICIENT_BOOK_DATA"
    if not bids or not asks:
        return "ONE_SIDED_BOOK"
    return "TWO_SIDED"


# ---- diversity / cap / classification ----

def apply_per_slug_cap(snapshots, cap):
    """Her market_slug için en çok `cap` snapshot tut (giriş sırasıyla). (kept, dropped_count)."""
    if cap <= 0:
        raise ValueError("cap > 0 olmalı")
    seen = {}
    kept = []
    dropped = 0
    for s in snapshots:
        slug = s.get("market_slug")
        seen[slug] = seen.get(slug, 0)
        if seen[slug] < cap:
            kept.append(s)
            seen[slug] += 1
        else:
            dropped += 1
    return kept, dropped


def diversity_status(unique_slugs, min_unique_slugs):
    return "OK" if unique_slugs >= min_unique_slugs else "INSUFFICIENT_MARKET_DIVERSITY"


def classify_snapshot_types(snapshots):
    """İlk görülen slug → new_market_cross_section, sonrakiler → same_slug_time_series."""
    seen = set()
    out = []
    for s in snapshots:
        slug = s.get("market_slug")
        if slug in seen:
            out.append("same_slug_time_series")
        else:
            seen.add(slug)
            out.append("new_market_cross_section")
    return out


# ---- percentiles ----

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


def percentiles(vals):
    if not vals:
        return None
    s = sorted(vals)
    return {"n": len(s), "p50": round(_pct(s, .5), 4), "p90": round(_pct(s, .9), 4),
            "p95": round(_pct(s, .95), 4), "min": round(s[0], 4), "max": round(s[-1], 4)}


# ---- per-cell aggregation (NO merging) ----

def aggregate_cell(snapshots):
    """Tek (asset, interval) hücresi için microstructure özeti. Karışık hücre → ValueError."""
    if not snapshots:
        raise ValueError("boş snapshot listesi")
    cells = {(s.get("asset"), s.get("interval")) for s in snapshots}
    if len(cells) != 1:
        raise ValueError(f"cell merging yasak: {cells}")
    asset, interval = next(iter(cells))

    spreads = []
    tier_slips = {str(n): [] for n in NOTIONAL_TIERS}
    tier_fills = {str(n): [] for n in NOTIONAL_TIERS}
    top_ask_notional = []
    counts = {"TWO_SIDED": 0, "ONE_SIDED_BOOK": 0, "INSUFFICIENT_BOOK_DATA": 0, "LINEAGE_MISSING": 0}
    per_slug = {}
    lineage_complete = True

    for s in snapshots:
        tag = classify_book(s)
        counts[tag] = counts.get(tag, 0) + 1
        if tag == "LINEAGE_MISSING":
            lineage_complete = False
        slug = s.get("market_slug")
        per_slug[slug] = per_slug.get(slug, 0) + 1
        if tag != "TWO_SIDED":
            continue
        bids = s["bids"]; asks = s["asks"]
        best_bid = max(p for p, _ in bids)
        best_ask = min(p for p, _ in asks)
        spreads.append(spread_bps(best_bid, best_ask))
        asks_sorted = sorted(asks, key=lambda x: x[0])
        top_ask_notional.append(asks_sorted[0][0] * asks_sorted[0][1])
        for n in NOTIONAL_TIERS:
            w = slippage_walk(asks_sorted, n)
            if w["slippage_bps"] is not None:
                tier_slips[str(n)].append(w["slippage_bps"])
            tier_fills[str(n)].append(1.0 if w["fully_filled"] else 0.0)

    n = len(snapshots)
    two_sided = counts.get("TWO_SIDED", 0)
    fill_ratios = {str(nt): (sum(tier_fills[str(nt)]) / len(tier_fills[str(nt)])
                             if tier_fills[str(nt)] else 0.0) for nt in NOTIONAL_TIERS}
    unique_slugs = len(per_slug)
    key = f"{asset}|{interval}"
    cap = CELL_PARAMS.get(key, {}).get("per_slug_cap")
    per_slug_cap_respected = (max(per_slug.values()) <= cap) if (cap and per_slug) else True
    min_unique = CELL_PARAMS.get(key, {}).get("min_unique_slugs", 0)

    types = classify_snapshot_types(snapshots)
    return {
        "asset": asset, "interval": interval, "n": n,
        "unique_slugs": unique_slugs,
        "snapshots_per_slug": dict(sorted(per_slug.items())),
        "snapshots_per_slug_pctiles": percentiles(list(per_slug.values())),
        "snapshot_type_split": {"new_market_cross_section": types.count("new_market_cross_section"),
                                "same_slug_time_series": types.count("same_slug_time_series")},
        "book_tag_counts": counts,
        "two_sided_ratio": round(two_sided / n, 4) if n else 0.0,
        "spread_bps_pctiles": percentiles(spreads),
        "p95_spread_bps": (percentiles(spreads) or {}).get("p95") if spreads else None,
        "slippage_bps_by_tier": {str(nt): percentiles(tier_slips[str(nt)]) for nt in NOTIONAL_TIERS},
        "fill_ratios": fill_ratios,
        "top_ask_fillable_notional_pctiles": percentiles(top_ask_notional),
        "per_slug_cap_respected": per_slug_cap_respected,
        "diversity_status": diversity_status(unique_slugs, min_unique),
        "lineage_complete": lineage_complete,
    }


# ---- verdict ----

def verdict(report):
    """EXECUTION_READY yalnız TÜM kriterler geçince; aksi EXECUTION_NOT_READY + failures listesi.

    Phase 3 KÂR/ALPHA değerlendirmez ve ECONOMICS_READY_FOR_PAPER üretemez.
    """
    key = f"{report['asset']}|{report['interval']}"
    p = CELL_PARAMS[key]
    fails = []
    if report.get("n", 0) < p["target_n"]:
        fails.append("n_below_target")
    if report.get("unique_slugs", 0) < p["min_unique_slugs"]:
        fails.append("insufficient_market_diversity")
    if report.get("diversity_status") == "INSUFFICIENT_MARKET_DIVERSITY" \
            and "insufficient_market_diversity" not in fails:
        fails.append("insufficient_market_diversity")
    if report.get("two_sided_ratio", 0.0) < MIN_TWO_SIDED_RATIO:
        fails.append("two_sided_ratio_low")
    if p["spread_gating"]:
        p95 = report.get("p95_spread_bps")
        if p95 is not None and p["max_p95_spread_bps"] is not None and p95 > p["max_p95_spread_bps"]:
            fails.append("spread_too_wide")
    for tier in GATING_TIERS:
        if report.get("fill_ratios", {}).get(tier, 0.0) < MIN_FILL_RATIO:
            fails.append(f"depth_too_thin_{tier}")
    if not report.get("lineage_complete", False):
        fails.append("lineage_missing")
    status = "EXECUTION_READY" if not fails else "EXECUTION_NOT_READY"
    return status, fails
