"""analysis/reference_basket.py — PUBLIC_REFERENCE_BASKET normalizer (provisional research only).

SAF / OFFLINE. Hiçbir canlı fetch, client, secret veya env bağımlılığı YOK. Bu modül, halka açık spot
referans kaynaklarını (Coinbase + Kraken, YALNIZCA USD) iki-kaynak midpoint + spread guard ile normalize
eder ve perp referansını (Hyperliquid) AYRI girdi olarak alıp temiz public basis = HL_perp - spot_reference
hesaplar. İki kaynak olduğu için trimmed median KULLANILMAZ. USD ve USDT KARIŞTIRILMAZ; spot ve perp ham
KARIŞTIRILMAZ.

Kalite durumları:
  - OK                      : iki USD spot kaynağı, spread eşiğin altında, taze.
  - DEGRADED_SINGLE_SOURCE  : yalnızca bir kullanılabilir USD spot kaynağı (diğeri eksik/USDT/perp/bayat).
  - MISSING_REFERENCE       : kullanılabilir USD spot kaynağı yok.
  - SPREAD_GUARD_FAIL       : iki kaynak var ama spread eşiği aştı — referans SESSİZCE onaylanmaz.

5m/15m -> CORE_READY_FOR_5M15M; 4h -> LIMITED_TIMING_APPROX (native 4h ayrıca hesaplanana kadar).

NOT official_f1b. NOT Chainlink basis. Kâr/arbitraj/trading iddiası YOK.
"""

_CORE_READY_INTERVALS = ("5m", "15m")

# Audited 4h source lineage tokens (caller-supplied, in-memory; NOT read from any file here).
_EXPECTED_CB_4H_LINEAGE = "AGGREGATED_FROM_1H"
_EXPECTED_KR_4H_LINEAGE = "NATIVE_INTERVAL_240"


def _is_number(v) -> bool:
    """Numeric int/float — bool REDDEDİLİR (True/False fiyat değildir)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _metadata() -> dict:
    return {
        "provisional": True,
        "public_reference_basket": True,
        "official_f1b": False,
        "chainlink_basis": False,
        "profitability": False,
    }


def _interval_readiness(interval) -> str:
    if interval in _CORE_READY_INTERVALS:
        return "CORE_READY_FOR_5M15M"
    if interval == "4h":
        return "LIMITED_TIMING_APPROX"
    return "UNKNOWN"


def _resolve_4h_readiness(ctx):
    """4h readiness from caller-supplied IN-MEMORY audit/lineage context (no file reads).

    Returns (readiness_str, audited_block_or_None, flags). Default/partial/missing → LIMITED_TIMING_APPROX.
    CORE_READY_FOR_4H only when ctx.ready is True AND coinbase lineage == AGGREGATED_FROM_1H AND kraken
    lineage == NATIVE_INTERVAL_240. Ready-but-mismatched/missing lineage is NEVER silently blessed:
    stays LIMITED and emits quality_flags.
    """
    if not isinstance(ctx, dict):
        return "LIMITED_TIMING_APPROX", None, []
    cb = ctx.get("coinbase_lineage")
    kr = ctx.get("kraken_lineage")
    ready = ctx.get("ready", False) is True
    audited = {"ready_input": ready, "coinbase_lineage": cb, "kraken_lineage": kr}
    if not ready:
        return "LIMITED_TIMING_APPROX", audited, []
    flags = []
    if cb != _EXPECTED_CB_4H_LINEAGE:
        flags.append(f"4h_coinbase_lineage_invalid:{cb}")
    if kr != _EXPECTED_KR_4H_LINEAGE:
        flags.append(f"4h_kraken_lineage_invalid:{kr}")
    if flags:
        return "LIMITED_TIMING_APPROX", audited, flags
    return "CORE_READY_FOR_4H", audited, []


def normalize_reference_basket(spot_sources, perp=None, *, spread_bps_threshold,
                               anchor_ms=None, freshness_tolerance_ms=None, interval=None,
                               audited_4h_context=None):
    """Public reference basket'i SAF/OFFLINE normalize eder (yukarıdaki sözleşme).

    spot_sources: {name: {"price", "quote"="USD", "market"="spot", "ts_ms"}} — USD-only core.
    perp:         {"price", "quote"="USD", "market"="perp", "ts_ms"} | None — AYRI girdi.
    spread_bps_threshold: >0 olmalı (aksi ValueError).
    anchor_ms + freshness_tolerance_ms verilirse: |ts - anchor| > tolerance olan kaynak BAYAT → dışlanır.
    """
    if not _is_number(spread_bps_threshold) or spread_bps_threshold <= 0:
        raise ValueError("spread_bps_threshold pozitif numeric olmalı")
    if not isinstance(spot_sources, dict):
        raise ValueError("spot_sources dict olmalı")

    quality_flags = []
    excluded = []
    usable = {}  # name -> price

    for name in sorted(spot_sources):
        src = spot_sources[name]
        if not isinstance(src, dict):
            excluded.append({"name": name, "reason": "malformed"})
            quality_flags.append(f"malformed_source:{name}")
            continue
        price = src.get("price")
        quote = src.get("quote", "USD")
        market = src.get("market", "spot")
        ts = src.get("ts_ms")

        if not _is_number(price):
            excluded.append({"name": name, "reason": "missing_or_nonnumeric_price"})
            quality_flags.append(f"missing_source:{name}")
            continue
        if quote != "USD":
            excluded.append({"name": name, "reason": f"quote_mismatch:{quote}"})
            quality_flags.append(f"quote_mismatch:{name}:{quote}")
            continue
        if market != "spot":
            excluded.append({"name": name, "reason": f"spot_perp_mixing:{market}"})
            quality_flags.append(f"spot_perp_mixing:{name}:{market}")
            continue
        if anchor_ms is not None and freshness_tolerance_ms is not None:
            if not _is_number(ts) or abs(ts - anchor_ms) > freshness_tolerance_ms:
                excluded.append({"name": name, "reason": "stale_or_misaligned_ts"})
                quality_flags.append(f"stale_source:{name}")
                continue
        usable[name] = float(price)

    used = sorted(usable)
    spot_reference = None
    spread_bps = None
    spread_guard_passed = None
    status = "MISSING_REFERENCE"

    if len(used) == 1:
        spot_reference = usable[used[0]]
        status = "DEGRADED_SINGLE_SOURCE"
    elif len(used) >= 2:
        # exactly two core sources expected (Coinbase + Kraken): midpoint + spread guard, no trimmed median
        prices = [usable[n] for n in used]
        spot_reference = sum(prices) / len(prices)
        lo, hi = min(prices), max(prices)
        mid = (lo + hi) / 2.0
        spread_bps = abs(hi - lo) / mid * 1e4 if mid else None
        if spread_bps is not None and spread_bps > spread_bps_threshold:
            status = "SPREAD_GUARD_FAIL"
            spread_guard_passed = False
            quality_flags.append(f"spread_guard_fail:{round(spread_bps, 4)}bps>{spread_bps_threshold}")
        else:
            status = "OK"
            spread_guard_passed = True

    # clean basis = HL_perp - spot_reference (perp is a SEPARATE input; never mixed into spot)
    perp_reference = None
    basis_bps = None
    if isinstance(perp, dict):
        p_price = perp.get("price")
        p_quote = perp.get("quote", "USD")
        p_market = perp.get("market", "perp")
        if not _is_number(p_price):
            quality_flags.append("perp_missing_or_nonnumeric")
        elif p_quote != "USD":
            quality_flags.append(f"perp_quote_mismatch:{p_quote}")
        elif p_market != "perp":
            quality_flags.append(f"perp_market_not_perp:{p_market}")
        else:
            perp_reference = float(p_price)
            if _is_number(spot_reference) and spot_reference:
                basis_bps = (perp_reference - spot_reference) / spot_reference * 1e4

    # interval readiness: 5m/15m unchanged; 4h stays LIMITED unless caller supplies audited context
    audited_4h = None
    if interval == "4h":
        interval_readiness, audited_4h, readiness_flags = _resolve_4h_readiness(audited_4h_context)
        quality_flags.extend(readiness_flags)
    else:
        interval_readiness = _interval_readiness(interval)

    return {
        "status": status,
        "spot_reference": spot_reference,
        "spread_bps": spread_bps,
        "spread_guard_passed": spread_guard_passed,
        "spread_bps_threshold": spread_bps_threshold,
        "perp_reference": perp_reference,
        "basis_bps": basis_bps,
        "used_spot_sources": used,
        "excluded_sources": excluded,
        "quality_flags": quality_flags,
        "interval_readiness": interval_readiness,
        "audited_4h": audited_4h,
        "metadata": _metadata(),
    }
