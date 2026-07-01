"""
analysis.forensic.gateg7_paper_pnl — pure paper edge/PnL evaluator (entry-time only).

PAPER/SHADOW evaluation of stored G.5/G7-lite entry-time evidence, answering whether the
diagnostic entry_edge would have produced positive or negative net PnL hold-to-resolution.
NOT tradeable alpha. Pure: no network, no DB, no clock — resolution/fee config are passed in
by the caller (the live evaluator in tools/), never fetched here.

Candidate selection reads ONLY entry-time signal_log fields (fill_decision/exec_ask_vwap/
exec_fill_qty_avail/entry_edge) and has no resolution/outcome parameter anywhere — structurally
lookahead-free. The stored fill_decision precedence (UNFILLED_QUOTE_STALE / UNFILLED_ENTRY_DEPTH_
FAIL take priority over UNFILLED_EDGE_LOST in normalize_signal) means FILLED_ACTIVE/UNFILLED_
EDGE_LOST rows have ALREADY passed the executable-ask + sufficient-depth + non-stale-quote checks
at signal time; selecting on fill_decision reuses that without relabeling it.
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from analysis.forensic import gateg5_plumbing as _plumb
from analysis.forensic.gateg5_plumbing import walk_ask_ladder_for_stake, ladder_to_decimal_json, \
    parse_ask_ladder

_WINDOW_RE = re.compile(r"updown-15m-(\d+)")
_ELIGIBLE_DECISIONS = frozenset({"FILLED_ACTIVE", "UNFILLED_EDGE_LOST"})

# fee status sentinels
FEE_VERIFIED_ZERO = "VERIFIED_ZERO_FEE"
FEE_VERIFIED_RATE = "VERIFIED_FEE_RATE"
FEE_METADATA_MISSING = "NOT_COMPUTED_FEE_METADATA_MISSING"   # also doubles as the net_pnl sentinel
FEE_UNSUPPORTED_SCHEDULE = "FEE_NOT_COMPUTED_UNSUPPORTED_SCHEDULE"  # feeSchedule missing/exponent!=1/not takerOnly

# bidirectional selection outcomes
NO_PAPER_ENTRY = "NO_PAPER_ENTRY"
EDGE_TIE_NO_ENTRY = "EDGE_TIE_NO_ENTRY"
NOT_ADMITTED_UNSUPPORTED_FEE = "NOT_ADMITTED_UNSUPPORTED_FEE"

# G8 forward dual-book capture statuses (paper/shadow only; never an order)
PAPER_OPEN = "PAPER_OPEN"
DUAL_BOOK_SKEW_EXCEEDED = "DUAL_BOOK_SKEW_EXCEEDED"
FUTURE_TIMESTAMP_REJECTED = "FUTURE_TIMESTAMP_REJECTED"
STALE_QUOTE_REJECTED = "STALE_QUOTE_REJECTED"
INSUFFICIENT_DEPTH_REJECTED = "INSUFFICIENT_DEPTH_REJECTED"
DUPLICATE_CONDITION_SKIPPED = "DUPLICATE_CONDITION_SKIPPED"

# Reuse the EXISTING quote-staleness guard constant (never invent a new threshold).
QUOTE_STALE_MS = _plumb.QUOTE_STALE_MS

_FIVE_DP = Decimal("0.00001")


class OutcomeBindingError(Exception):
    """Missing/duplicate/ambiguous/unknown outcome label -> fail closed. Never guessed."""


_YES_UP_LABELS = frozenset({"yes", "up"})
_NO_DOWN_LABELS = frozenset({"no", "down"})


def bind_yes_no_tokens(outcomes, token_ids) -> dict:
    """Bind YES/Up and NO/Down tokens by NORMALIZED label (case/whitespace-insensitive),
    NEVER by a fixed array index. Works regardless of outcome/token ordering. Rejects
    missing, duplicate, ambiguous, or unknown labels -- never falls back to a guess.

    Token-ID integrity (checked BEFORE any label binding, so a malformed carrier value
    fails closed before a caller could ever issue a network GET for it): both token_ids
    must be strings, non-empty after stripping, and distinct from each other. No numeric
    format is assumed or regex-validated -- token IDs are opaque carrier values."""
    if not isinstance(outcomes, list) or not isinstance(token_ids, list) \
            or len(outcomes) != 2 or len(token_ids) != 2:
        raise OutcomeBindingError(
            f"expected exactly 2 outcomes and 2 token_ids: {outcomes!r} / {token_ids!r}")
    cleaned_tokens = []
    for t in token_ids:
        if not isinstance(t, str):
            raise OutcomeBindingError(f"non-string token_id: {t!r}")
        stripped = t.strip()
        if not stripped:
            raise OutcomeBindingError(f"empty/whitespace-only token_id: {t!r}")
        cleaned_tokens.append(stripped)
    if cleaned_tokens[0] == cleaned_tokens[1]:
        raise OutcomeBindingError(f"duplicate token_id: {token_ids!r}")
    norm = []
    for o in outcomes:
        if not isinstance(o, str):
            raise OutcomeBindingError(f"non-string outcome label: {o!r}")
        n = o.strip().lower()
        if n in _YES_UP_LABELS:
            norm.append("YES")
        elif n in _NO_DOWN_LABELS:
            norm.append("NO")
        else:
            raise OutcomeBindingError(f"unknown outcome label: {o!r}")
    if norm.count("YES") != 1 or norm.count("NO") != 1:
        raise OutcomeBindingError(f"missing/duplicate/ambiguous outcome labels: {outcomes!r}")
    yes_idx, no_idx = norm.index("YES"), norm.index("NO")
    return {"yes_index": yes_idx, "no_index": no_idx,
            "yes_token_id": cleaned_tokens[yes_idx], "no_token_id": cleaned_tokens[no_idx]}


def _d(v):
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


def window_of(slug):
    m = _WINDOW_RE.search(slug or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# candidate selection — entry-time only, no lookahead, never relabels
# ---------------------------------------------------------------------------
def select_eligible_candidates(rows):
    """Rows with an executable ask, sufficient depth and a non-stale quote at signal time
    (fill_decision in FILLED_ACTIVE/UNFILLED_EDGE_LOST) and a usable executable price/qty.
    Never mutates fill_decision. No resolution/outcome input exists in this signature."""
    out = []
    for r in rows:
        if r.get("fill_decision") not in _ELIGIBLE_DECISIONS:
            continue
        ask = _d(r.get("exec_ask_vwap"))
        qty = _d(r.get("exec_fill_qty_avail"))
        if ask is None or qty is None or ask <= 0 or qty <= 0:
            continue
        out.append(r)
    return out


def dedup_earliest_by_condition(rows):
    """One representative per condition_id: the earliest ts_signal_ms."""
    best = {}
    for r in rows:
        cid = r["condition_id"]
        ts = r.get("ts_signal_ms")
        if cid not in best or (ts is not None and ts < best[cid].get("ts_signal_ms")):
            best[cid] = r
    return list(best.values())


def effective_n_windows(rows):
    return {
        "unique_condition_ids": len({r["condition_id"] for r in rows}),
        "unique_windows": len({window_of(r.get("slug")) for r in rows if window_of(r.get("slug"))}),
    }


def shadow_buckets(rows):
    """Threshold buckets over entry_edge, in the required order."""
    thresholds = [(">0", Decimal("0"), True), (">=0.03", Decimal("0.03"), False),
                  (">=0.05", Decimal("0.05"), False), (">=0.10", Decimal("0.10"), False),
                  (">=0.15", Decimal("0.15"), False), (">=0.25", Decimal("0.25"), False)]
    out = {}
    for label, thr, strict in thresholds:
        sel = []
        for r in rows:
            e = _d(r.get("entry_edge"))
            if e is None:
                continue
            if (e > thr) if strict else (e >= thr):
                sel.append(r)
        out[label] = sel
    return out


# ---------------------------------------------------------------------------
# $25 quantity clamp
# ---------------------------------------------------------------------------
def clamp_fill_qty(exec_fill_qty_avail: Decimal, exec_ask_vwap: Decimal,
                   stake: Decimal = Decimal("25")) -> Decimal:
    """filled_qty = min(exec_fill_qty_avail, stake/exec_ask_vwap). Zero ask -> zero qty."""
    if exec_ask_vwap is None or exec_ask_vwap <= 0:
        return Decimal("0")
    stake_qty = stake / exec_ask_vwap
    return min(exec_fill_qty_avail, stake_qty)


# ---------------------------------------------------------------------------
# fee config — verified-zero / verified-rate / unverifiable (never silent zero)
# ---------------------------------------------------------------------------
def parse_fee_config(market: dict | None) -> dict:
    """Read feesEnabled + feeSchedule from a raw Gamma market dict.

    feeSchedule is AUTHORITATIVE over takerBaseFee: takerBaseFee is NEVER divided/used here
    (Gamma exposes both an integer takerBaseFee AND a decimal feeSchedule.rate on the same
    payload; they are not proven to be the same unit/quantity, so only feeSchedule.rate is
    trusted). rebateRate is maker-rebate metadata only and MUST NOT reduce the taker fee.

    feesEnabled is False -> VERIFIED_ZERO_FEE, fee_rate=0 (an explicit verified signal).
    feesEnabled is True and feeSchedule has exponent==1, takerOnly==True, numeric rate
        (this taker-at-ask paper path only supports that shape) -> VERIFIED_FEE_RATE,
        fee_rate=feeSchedule.rate exactly.
    feesEnabled is True but feeSchedule is missing/unparseable/exponent!=1/takerOnly!=True
        -> FEE_NOT_COMPUTED_UNSUPPORTED_SCHEDULE, fee_rate=None (candidate not admitted).
    feesEnabled missing, or no market at all -> NOT_COMPUTED_FEE_METADATA_MISSING,
        fee_rate=None. Never silently 0.
    """
    if not isinstance(market, dict):
        return {"fee_rate": None, "fee_status": FEE_METADATA_MISSING}
    enabled = market.get("feesEnabled")
    if enabled is False:
        return {"fee_rate": Decimal("0"), "fee_status": FEE_VERIFIED_ZERO}
    if enabled is True:
        schedule = market.get("feeSchedule")
        if isinstance(schedule, dict):
            rate = _d(schedule.get("rate"))
            if (rate is not None and schedule.get("exponent") == 1
                    and schedule.get("takerOnly") is True):
                return {"fee_rate": rate, "fee_status": FEE_VERIFIED_RATE}
        return {"fee_rate": None, "fee_status": FEE_UNSUPPORTED_SCHEDULE}
    return {"fee_rate": None, "fee_status": FEE_METADATA_MISSING}


# ---------------------------------------------------------------------------
# fee formula — quadratic, no spread term, rounded to 5dp
# ---------------------------------------------------------------------------
def entry_fee_quadratic(filled_qty: Decimal, fee_rate: Decimal, p: Decimal) -> Decimal:
    """entry_fee = filled_qty * fee_rate * p * (1-p), rounded to 5 decimal places.
    Depends ONLY on (filled_qty, fee_rate, p) — the executable ask already embeds spread,
    so no separate spread term is ever subtracted here."""
    fee = filled_qty * fee_rate * p * (Decimal("1") - p)
    return fee.quantize(_FIVE_DP, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# PnL — win/loss payout, gross/net (fee=None -> net sentinel, never silently 0)
# ---------------------------------------------------------------------------
def compute_pnl(*, filled_qty: Decimal, exec_ask_vwap: Decimal, won: bool, fee) -> dict:
    entry_notional = filled_qty * exec_ask_vwap
    payout = filled_qty * (Decimal("1") if won else Decimal("0"))
    gross_pnl = payout - entry_notional
    net_pnl = (gross_pnl - fee) if fee is not None else FEE_METADATA_MISSING
    return {"entry_notional": entry_notional, "payout": payout,
            "gross_pnl": gross_pnl, "net_pnl": net_pnl}


# ---------------------------------------------------------------------------
# cohort aggregation
# ---------------------------------------------------------------------------
def _median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return Decimal("0")
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / Decimal("2")


def aggregate_bucket(results: list) -> dict:
    candidates = len(results)
    resolved_rows = [r for r in results if r.get("status") == "RESOLVED"]
    resolved = len(resolved_rows)
    wins = sum(1 for r in resolved_rows if r.get("matched"))
    losses = resolved - wins
    nets = [r["net_pnl"] for r in resolved_rows if isinstance(r.get("net_pnl"), Decimal)]
    winner_nets = [r["net_pnl"] for r in resolved_rows
                   if r.get("matched") and isinstance(r.get("net_pnl"), Decimal)]
    loser_nets = [r["net_pnl"] for r in resolved_rows
                  if r.get("matched") is False and isinstance(r.get("net_pnl"), Decimal)]
    windows = {window_of(r.get("slug")) for r in results if window_of(r.get("slug"))}
    return {
        "candidates": candidates, "resolved": resolved, "wins": wins, "losses": losses,
        "win_rate": f"{wins}/{resolved}",
        "net_pnl_computable": len(nets),
        "total_net_pnl": sum(nets, Decimal("0")),
        "mean_net_pnl": (sum(nets, Decimal("0")) / len(nets)) if nets else Decimal("0"),
        "median_net_pnl": _median(nets),
        # never label a negative result "best win": best_win is None unless there IS a win.
        "best_win": max(winner_nets) if winner_nets else None,
        "least_loss": max(loser_nets) if loser_nets else None,     # smallest-magnitude loss
        "worst_loss": min(loser_nets) if loser_nets else None,
        "unique_windows": len(windows),
    }


def compute_side_execution(ask_levels, intended_stake: Decimal = Decimal("25")) -> dict:
    """Entry-time executable price/qty for one side's ask ladder, via the PROVEN
    stake-clamped ladder walk (validated/merged/sorted; no synthetic depth)."""
    levels = parse_ask_ladder(ladder_to_decimal_json(ask_levels))
    fill = walk_ask_ladder_for_stake(levels, intended_stake)
    return {"exec_ask_vwap": fill.exec_ask_vwap, "filled_qty": fill.filled_qty,
            "depth_sufficient": fill.depth_sufficient}


def _evaluate_side(fair_component: Decimal, ask_levels, fee_cfg: dict, cost_buffer: Decimal,
                   intended_stake: Decimal) -> dict:
    exec_info = compute_side_execution(ask_levels, intended_stake)
    ask, qty = exec_info["exec_ask_vwap"], exec_info["filled_qty"]
    gross_edge = fair_component - ask
    fee_rate = fee_cfg.get("fee_rate")
    if fee_rate is None:
        return {"exec_ask_vwap": str(ask), "filled_qty": str(qty), "gross_edge": str(gross_edge),
                "fee_per_share": None, "net_edge": None, "admitted": False,
                "not_admitted_reason": fee_cfg.get("fee_status")}
    fee = entry_fee_quadratic(qty, fee_rate, ask) if qty > 0 else Decimal("0")
    fee_per_share = (fee / qty) if qty > 0 else Decimal("0")
    net_edge = gross_edge - fee_per_share - cost_buffer
    return {"exec_ask_vwap": str(ask), "filled_qty": str(qty), "gross_edge": str(gross_edge),
            "fee_per_share": str(fee_per_share), "net_edge": net_edge, "admitted": True,
            "not_admitted_reason": None}


def evaluate_bidirectional_entry(*, fair_yes, yes_ask_levels, no_ask_levels, yes_fee_config,
                                 no_fee_config, cost_buffer: Decimal = Decimal("0"),
                                 intended_stake: Decimal = Decimal("25"),
                                 reference_age_ms=None, tte_s=None) -> dict:
    """Pure, entry-time-only bidirectional selection. Takes BOTH token books (already fetched
    at the SAME decision cycle by the caller); no resolution/outcome input exists in this
    signature -- structurally no-lookahead. NEVER defaults to NO/Down: the side with the
    larger strictly positive net edge wins; ties and non-positive edges fail closed.
    reference_age_ms/tte_s are recorded as diagnostics only (not used in selection)."""
    fair_yes = Decimal(str(fair_yes))
    yes = _evaluate_side(fair_yes, yes_ask_levels, yes_fee_config, cost_buffer, intended_stake)
    no = _evaluate_side(Decimal("1") - fair_yes, no_ask_levels, no_fee_config, cost_buffer,
                        intended_stake)

    yes_ne, no_ne = yes["net_edge"], no["net_edge"]
    if yes_ne is None and no_ne is None:
        selected, reason = None, NOT_ADMITTED_UNSUPPORTED_FEE
    elif yes_ne is None:
        selected, reason = ("NO", None) if no_ne > 0 else (None, NO_PAPER_ENTRY)
    elif no_ne is None:
        selected, reason = ("YES", None) if yes_ne > 0 else (None, NO_PAPER_ENTRY)
    elif yes_ne <= 0 and no_ne <= 0:
        selected, reason = None, NO_PAPER_ENTRY
    elif yes_ne == no_ne:
        selected, reason = None, EDGE_TIE_NO_ENTRY
    elif yes_ne > no_ne:
        selected, reason = "YES", None
    else:
        selected, reason = "NO", None

    return {"fair_yes": str(fair_yes), "reference_age_ms": reference_age_ms, "tte_s": tte_s,
            "yes": yes, "no": no, "selected_side": selected, "no_entry_reason": reason}


def realized_effective_n(resolved_rows: list) -> dict:
    """Realized effective-N counts RESOLVED unique 15m windows only (not all candidates).
    Correlated (same-window, multi-asset) windows are flagged — those are NOT independent
    trials and must not be double-counted toward statistical confidence."""
    windows: dict[str, set] = {}
    for r in resolved_rows:
        w = window_of(r.get("slug"))
        if w:
            windows.setdefault(w, set()).add(r.get("asset"))
    correlated = {w: sorted(a) for w, a in windows.items() if len(a) > 1}
    return {"resolved_unique_windows": len(windows), "correlated_windows": correlated}


# ===========================================================================
# G8 — forward dual-book paper decision (pure; caller supplies already-fetched books +
# already-computed fair_yes/tte_s; NO resolution/outcome parameter anywhere -> no-lookahead)
# ===========================================================================
def build_paper_decision(*, market: dict, yes_book: dict, no_book: dict, fair_yes,
                         feed_ts: int, tte_s: int, max_skew_ms: int, decision_ts: int,
                         hl_capture_started_ms: int = None, hl_capture_completed_ms: int = None,
                         intended_stake: Decimal = Decimal("25"),
                         cost_buffer: Decimal = Decimal("0")) -> dict:
    """Pure: no network/DB/clock. Binds YES/NO tokens by label (never index), enforces the
    dual-book skew bound, rejects any input with a capture/quote timestamp AFTER decision_ts
    (no-lookahead) or a stale quote (reusing QUOTE_STALE_MS) or insufficient executable depth,
    reads feeSchedule canonically (never takerBaseFee), then delegates the actual edge math to
    the COMMITTED evaluate_bidirectional_entry (never duplicated). `decision_ts` must be
    created by the caller only after every input (both books + HL fair-value) is available.

    `hl_capture_started_ms`/`hl_capture_completed_ms` are OPTIONAL diagnostic timestamps
    bracketing the caller's complete HL fair-value input acquisition/calculation. When
    supplied, `hl_capture_completed_ms` joins the SAME no-lookahead ordering check as the
    dual-book capture completions (decision_ts must be >= all three); they are never used in
    edge/fee/selection math, only persisted as entry-time evidence.
    """
    cid, slug = market["conditionId"], market.get("slug")
    binding = bind_yes_no_tokens(market["outcomes"], market["clobTokenIds"])   # fail closed first

    skew_ms = abs(yes_book["capture_completed_ms"] - no_book["capture_completed_ms"])
    if skew_ms > max_skew_ms:
        return {"status": DUAL_BOOK_SKEW_EXCEEDED, "dual_book_skew_ms": skew_ms,
                "condition_id": cid, "slug": slug}

    no_lookahead_checks = [("yes_quote_ts_ms", yes_book["quote_ts_ms"]),
                           ("yes_capture_completed_ms", yes_book["capture_completed_ms"]),
                           ("no_quote_ts_ms", no_book["quote_ts_ms"]),
                           ("no_capture_completed_ms", no_book["capture_completed_ms"]),
                           ("hl_feed_ts", feed_ts)]
    if hl_capture_completed_ms is not None:
        no_lookahead_checks.append(("hl_capture_completed_ms", hl_capture_completed_ms))
    for field, ts in no_lookahead_checks:
        if ts > decision_ts:
            return {"status": FUTURE_TIMESTAMP_REJECTED, "field": field,
                    "condition_id": cid, "slug": slug}

    for side_label, book in (("YES", yes_book), ("NO", no_book)):
        if (decision_ts - book["quote_ts_ms"]) > QUOTE_STALE_MS:
            return {"status": STALE_QUOTE_REJECTED, "side": side_label,
                    "condition_id": cid, "slug": slug}

    yes_exec = compute_side_execution(yes_book["asks"], intended_stake)
    no_exec = compute_side_execution(no_book["asks"], intended_stake)
    if not yes_exec["depth_sufficient"] or not no_exec["depth_sufficient"]:
        return {"status": INSUFFICIENT_DEPTH_REJECTED, "condition_id": cid, "slug": slug}

    fee_cfg = parse_fee_config(market)     # canonical feeSchedule; never takerBaseFee (see above)
    decision = evaluate_bidirectional_entry(
        fair_yes=fair_yes, yes_ask_levels=yes_book["asks"], no_ask_levels=no_book["asks"],
        yes_fee_config=fee_cfg, no_fee_config=fee_cfg, cost_buffer=cost_buffer,
        intended_stake=intended_stake, reference_age_ms=decision_ts - feed_ts, tte_s=tte_s)

    selected = decision["selected_side"]
    selected_leg = decision["yes"] if selected == "YES" else decision["no"] if selected == "NO" else None
    selected_token = (binding["yes_token_id"] if selected == "YES"
                      else binding["no_token_id"] if selected == "NO" else None)
    selected_notional = (str(Decimal(selected_leg["exec_ask_vwap"]) * Decimal(selected_leg["filled_qty"]))
                         if selected_leg else None)

    return {
        "status": PAPER_OPEN if selected else NO_PAPER_ENTRY,
        "condition_id": cid, "slug": slug, "asset": market.get("asset"), "window": window_of(slug),
        "paper_decision_ts": decision_ts, "fair_yes": decision["fair_yes"],
        "reference_age_ms": decision["reference_age_ms"], "tte_s": decision["tte_s"],
        "yes_token_id": binding["yes_token_id"], "no_token_id": binding["no_token_id"],
        "yes_quote_ts_ms": yes_book["quote_ts_ms"], "no_quote_ts_ms": no_book["quote_ts_ms"],
        "yes_capture_started_ms": yes_book["capture_started_ms"],
        "yes_capture_completed_ms": yes_book["capture_completed_ms"],
        "no_capture_started_ms": no_book["capture_started_ms"],
        "no_capture_completed_ms": no_book["capture_completed_ms"],
        "dual_book_skew_ms": skew_ms,
        "hl_capture_started_ms": hl_capture_started_ms,
        "hl_capture_completed_ms": hl_capture_completed_ms,
        "yes_exec_ask_vwap": decision["yes"]["exec_ask_vwap"], "yes_filled_qty": decision["yes"]["filled_qty"],
        "no_exec_ask_vwap": decision["no"]["exec_ask_vwap"], "no_filled_qty": decision["no"]["filled_qty"],
        "fee_rate": (str(fee_cfg["fee_rate"]) if fee_cfg["fee_rate"] is not None else None),
        "fee_exponent": (1 if fee_cfg["fee_status"] == FEE_VERIFIED_RATE else None),
        "yes_gross_edge": decision["yes"]["gross_edge"],
        "yes_net_edge": (str(decision["yes"]["net_edge"]) if decision["yes"]["net_edge"] is not None else None),
        "no_gross_edge": decision["no"]["gross_edge"],
        "no_net_edge": (str(decision["no"]["net_edge"]) if decision["no"]["net_edge"] is not None else None),
        "selected_side": selected, "selected_token_id": selected_token,
        "no_entry_reason": decision["no_entry_reason"],
        "selected_filled_qty": (str(selected_leg["filled_qty"]) if selected_leg else None),
        "selected_entry_notional": selected_notional,
        "raw_decision": decision,
    }


def enforce_one_entry_per_condition(decisions: list) -> list:
    """At most ONE PAPER_OPEN per condition_id (the first encountered). Any additional
    PAPER_OPEN for an already-opened condition_id is downgraded to DUPLICATE_CONDITION_SKIPPED
    (recorded as evidence, never a second position). Non-PAPER_OPEN rows pass through untouched."""
    seen_open = set()
    out = []
    for d in decisions:
        if d.get("status") == PAPER_OPEN:
            cid = d["condition_id"]
            if cid in seen_open:
                d = dict(d)
                d["status"] = DUPLICATE_CONDITION_SKIPPED
                out.append(d)
                continue
            seen_open.add(cid)
        out.append(d)
    return out
