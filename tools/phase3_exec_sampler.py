"""tools/phase3_exec_sampler.py — Phase 3 execution-sampling research runner (read-only).

PUBLIC_REFERENCE_BASKET / Phase 3 execution-readiness sampler. READ-ONLY public data ONLY:
  - Gamma open-market discovery (data.shortterm)            : public, no auth
  - public CLOB /book snapshot (data.clob_price.get_book)   : public, no auth
NO secrets, NO .env, NO private CLOB auth, NO orders, NO balances, NO trading, NO Telegram/restart.
NOT wired to main_loop/config. Pure logic + microstructure aggregation come from phase3_exec_logic.

Phase 3C = a BOUNDED, one-shot, READ-ONLY DRY RUN (<=4 public requests) that smoke-tests the
discovery -> book -> snapshot -> aggregate plumbing on ETH 5m at micro scale. Phase 3D = a bounded
pilot (<=11 requests). Both prove EXECUTION plumbing only, NOT economics/profitability. Dry-run /
pilot verdicts are CLOSED sets and NEVER emit a readiness verdict.

The full-scale `_sample_cell` remains NotImplemented. The guarded CLI runs ONLY `--dry-run-eth5m` or
`--pilot-eth5m`; anything else refuses with SystemExit. NOT official_f1b. NO profitability/alpha claim.
"""
import collections
import json
import os
import sys
import tempfile
import time

# tools/ -> repo root on path (for data.* helpers) + tools/ itself (for phase3_exec_logic)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phase3_exec_logic as P  # pure offline logic (no network)

# tools/ holds source; generated artifacts default under <repo_root>/data/output (overridable per call).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_REPO_ROOT, "data", "output")

# ---- Phase 3C dry-run hard bounds ----
MAX_TOTAL_REQUESTS = 4         # 1 Gamma discovery + up to 3 public CLOB /book
MAX_SLUGS = 3
MAX_SNAPSHOTS_PER_SLUG = 1
PACING_S = 2.0                 # >= 2.0 s between CLOB book calls
DRY_RUN_ASSET = "ETH"
DRY_RUN_INTERVAL = "5m"
ALLOWED_VERDICTS = ("SAMPLE_ONLY", "INSUFFICIENT_SAMPLE", "DRY_RUN_FAILED")


class BudgetExceeded(Exception):
    """Raised by RequestBudget.spend when a request would exceed the hard ceiling."""


class RateLimited(Exception):
    """Raised by a public fetch adapter on HTTP 429-style throttling (caller backs off + stops)."""


# ---- Phase 3D pilot bounds (revised first-pilot parameters) ----
PILOT_TARGET_SNAPSHOTS = 10
MIN_PILOT_SNAPSHOTS = 5
MAX_DISCOVERY_REQUESTS = 1
MAX_BOOK_REQUESTS = 10
PILOT_MAX_TOTAL_REQUESTS = 11
PILOT_PACING_S = 2.0
TS_INTERVAL_S = 20.0
MIN_PILOT_UNIQUE_SLUGS = 2
PILOT_VERDICTS = ("PILOT_SAMPLE_ONLY", "PILOT_INSUFFICIENT_MARKET_DIVERSITY",
                  "PILOT_RATE_LIMITED_PARTIAL", "PILOT_FAILED")

# ---- Phase 3D3 multi-asset bounded discovery bounds (BTC/ETH/SOL/XRP, 5m) ----
PILOT_3D3_ASSETS = ("BTC", "ETH", "SOL", "XRP")
PILOT_3D3_INTERVAL = "5m"
PILOT_3D3_TARGET_SNAPSHOTS = 10
PILOT_3D3_MIN_SNAPSHOTS = 5
PILOT_3D3_MAX_DISCOVERY_REQUESTS = 1
PILOT_3D3_MAX_BOOK_REQUESTS = 19      # allow attempts beyond target to tolerate one-sided books
PILOT_3D3_MAX_TOTAL_REQUESTS = 20     # hard ceiling (1 discovery + <=19 books)
# pacing + diversity floor reuse PILOT_PACING_S / TS_INTERVAL_S / MIN_PILOT_UNIQUE_SLUGS unchanged.


class RequestBudget:
    """Single shared request-budget state. One instance is threaded through ALL public HTTP helper
    calls; the counter never resets inside per-slug/book loops. spend() aborts BEFORE the request."""

    def __init__(self, max_total):
        self.max_total = max_total
        self.count = 0

    def spend(self, kind):
        if self.count + 1 > self.max_total:
            raise BudgetExceeded(f"request budget {self.max_total} would be exceeded by {kind!r}")
        self.count += 1
        return self.count


def build_snapshot(asset, interval, market_slug, token_id, bids, asks):
    """Pure record builder (only clock read is the timestamp). Safe to unit-test offline."""
    return {
        "asset": asset, "interval": interval, "market_slug": market_slug,
        "token_id": token_id, "utc_timestamp_ms": int(time.time() * 1000),
        "bids": bids, "asks": asks,
    }


def _dryrun_verdict(usable_books, ran_clean):
    """CLOSED set only — never a readiness verdict, never a paper-economics verdict."""
    if not ran_clean:
        return "DRY_RUN_FAILED"
    if usable_books >= 1:
        return "SAMPLE_ONLY"
    return "INSUFFICIENT_SAMPLE"


def _normalize_levels(book):
    """raw CLOB /book -> ([(price,size)] bids desc, [(price,size)] asks asc) via pure parsers."""
    from data import clob_price  # pure parse fns; import lazily to keep module offline-importable
    return clob_price.sorted_bids(book), clob_price.sorted_asks(book)


async def dry_run_eth5m(*, discover_fn, fetch_book_fn, sleep_fn=None, out_dir=OUT_DIR,
                        now_unix=None, pacing_s=PACING_S, budget=None, _dry_paths_tmp=False):
    """Bounded ETH-5m read-only dry run. discover_fn/fetch_book_fn/sleep_fn are INJECTED so this is
    fully testable offline; the CLI wires the real public adapters. <=4 requests, <=3 slugs, 1 snap/slug.
    """
    if sleep_fn is None:
        import asyncio
        sleep_fn = asyncio.sleep
    budget = budget if budget is not None else RequestBudget(MAX_TOTAL_REQUESTS)
    if _dry_paths_tmp:
        out_dir = tempfile.mkdtemp(prefix="phase3_dryrun_")
    if now_unix is None:
        now_unix = int(time.time())

    jsonl_path = os.path.join(out_dir, f"phase3_dryrun_snapshots_{now_unix}.jsonl")
    summary_path = os.path.join(out_dir, f"phase3_dryrun_summary_{now_unix}.json")

    failure_modes = []
    slugs_attempted = []
    snapshots = []
    books_ok = 0
    books_failed = 0
    ran_clean = True

    def _summary(verdict):
        return {
            "verdict": verdict,
            "request_count": budget.count,
            "max_total_requests": budget.max_total,
            "asset": DRY_RUN_ASSET,
            "interval": DRY_RUN_INTERVAL,
            "slugs_attempted": len(slugs_attempted),
            "snapshots_written": len(snapshots),
            "books_ok": books_ok,
            "books_failed": books_failed,
            "failure_modes": sorted(set(failure_modes)),
            "output_jsonl": jsonl_path,
            "output_summary": summary_path,
            "timestamp_utc": now_unix,
            "official_f1b": False,
            "profitability": False,
            "phase": "3C_dry_run",
        }

    # no-overwrite guard: refuse if either timestamped output already exists
    if os.path.exists(jsonl_path) or os.path.exists(summary_path):
        failure_modes.append("OUTPUT_EXISTS_NO_OVERWRITE")
        return _summary("DRY_RUN_FAILED")  # write nothing -> prior outputs untouched

    # discovery (spends 1 Gamma request)
    try:
        markets = await discover_fn(budget)
    except BudgetExceeded:
        failure_modes.append("BUDGET_EXCEEDED")
        return _summary("DRY_RUN_FAILED")
    except Exception as e:
        failure_modes.append(f"DISCOVERY_ERROR:{type(e).__name__}")
        return _summary("DRY_RUN_FAILED")

    markets = list(markets or [])[:MAX_SLUGS]
    books_attempted = 0
    try:
        for m in markets:
            slug = m.get("market_slug")
            token = m.get("token_id")
            slugs_attempted.append(slug)
            # abort BEFORE a request that would exceed the budget
            if budget.count + 1 > budget.max_total:
                failure_modes.append("BUDGET_STOP")
                break
            if books_attempted > 0:
                await sleep_fn(pacing_s)  # >= 2.0 s between CLOB book calls
            try:
                book = await fetch_book_fn(token, budget)
            except BudgetExceeded:
                failure_modes.append("BUDGET_STOP")
                break
            except Exception as e:
                books_failed += 1
                failure_modes.append(f"BOOK_FETCH_ERROR:{type(e).__name__}")
                books_attempted += 1
                continue
            books_attempted += 1
            bids, asks = _normalize_levels(book)
            snap = build_snapshot(DRY_RUN_ASSET, DRY_RUN_INTERVAL, slug, token, bids, asks)
            tag = P.classify_book(snap)
            if tag == "TWO_SIDED":
                books_ok += 1
                snapshots.append(snap)  # max 1 per slug (one book fetched per slug)
            else:
                books_failed += 1
                failure_modes.append(tag)
    except Exception as e:  # unexpected fatal
        ran_clean = False
        failure_modes.append(f"FATAL:{type(e).__name__}")

    verdict = _dryrun_verdict(usable_books=books_ok, ran_clean=ran_clean)
    summary = _summary(verdict)

    # write outputs (timestamped, never overwriting — guarded above)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for s in snapshots:
            f.write(json.dumps(s) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


# ---- Phase 3D bounded pilot (injectable; live path guarded by CLI, not run in tests) ----

def _pilot_plan(markets):
    """Build a bounded sampling plan: cross-market first (1/slug), then time-series fill to target.

    Returns list of (market_dict, label) where label in {"new","ts"}; capped at min(target, book cap).
    """
    cap = min(PILOT_TARGET_SNAPSHOTS, MAX_BOOK_REQUESTS)
    unique = []
    seen = set()
    for m in markets:
        slug = m.get("market_slug")
        if slug not in seen:
            seen.add(slug)
            unique.append(m)
    plan = [(m, "new") for m in unique][:cap]
    i = 0
    while len(plan) < cap and unique:
        plan.append((unique[i % len(unique)], "ts"))
        i += 1
    return plan


async def pilot_eth5m(*, discover_fn, fetch_book_fn, sleep_fn=None, output_dir=OUT_DIR,
                      timestamp_fn=None, budget=None):
    """Bounded ETH-5m read-only pilot. All collaborators INJECTED so this is fully offline-testable.
    <=11 requests (1 discovery + <=10 books), >=2.0s pacing (TS_INTERVAL_S for same-slug time-series),
    append-only JSONL flushed per snapshot, partial summary on rate-limit/abort/exception, no-overwrite.
    Pilot verdict is a CLOSED set; never a readiness or paper-economics verdict.
    """
    if sleep_fn is None:
        import asyncio
        sleep_fn = asyncio.sleep
    if timestamp_fn is None:
        timestamp_fn = lambda: int(time.time())  # noqa: E731
    budget = budget if budget is not None else RequestBudget(PILOT_MAX_TOTAL_REQUESTS)
    now_unix = timestamp_fn()

    jsonl_path = os.path.join(output_dir, f"phase3d_pilot_snapshots_{now_unix}.jsonl")
    summary_path = os.path.join(output_dir, f"phase3d_pilot_summary_{now_unix}.json")

    failure_modes = []
    discovery_requests = 0
    book_requests = 0
    books_ok = 0
    books_failed = 0
    snapshots = []          # (slug, label)
    per_slug = {}
    rate_limited = False
    fatal = None

    def _emit(verdict, partial):
        type_split = {"new_market_cross_section": sum(1 for _, lab in snapshots if lab == "new"),
                      "same_slug_time_series": sum(1 for _, lab in snapshots if lab == "ts")}
        summary = {
            "verdict": verdict,
            "target_snapshots": PILOT_TARGET_SNAPSHOTS,
            "snapshots_written": len(snapshots),
            "unique_slugs": len({s for s, _ in snapshots}),
            "snapshots_per_slug": dict(sorted(per_slug.items())),
            "snapshot_type_split": type_split,
            "request_count": budget.count,
            "max_total_requests": budget.max_total,
            "discovery_requests": discovery_requests,
            "book_requests": book_requests,
            "books_ok": books_ok,
            "books_failed": books_failed,
            "asset": DRY_RUN_ASSET,
            "interval": DRY_RUN_INTERVAL,
            "failure_modes": sorted(set(failure_modes)),
            "partial": bool(partial),
            "output_jsonl": jsonl_path,
            "output_summary": summary_path,
            "timestamp_utc": now_unix,
            "official_f1b": False,
            "profitability": False,
            "phase": "3D_pilot",
        }
        with open(summary_path, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)
        return summary

    # no-overwrite guard: refuse if either timestamped output already exists (write nothing)
    if os.path.exists(jsonl_path) or os.path.exists(summary_path):
        failure_modes.append("OUTPUT_EXISTS_NO_OVERWRITE")
        # do not touch existing files; emit summary only if summary path itself is free
        if os.path.exists(summary_path):
            return {"verdict": "PILOT_FAILED", "failure_modes": ["OUTPUT_EXISTS_NO_OVERWRITE"],
                    "output_jsonl": jsonl_path, "output_summary": summary_path, "partial": True,
                    "snapshots_written": 0, "official_f1b": False, "profitability": False,
                    "phase": "3D_pilot", "asset": DRY_RUN_ASSET, "interval": DRY_RUN_INTERVAL,
                    "target_snapshots": PILOT_TARGET_SNAPSHOTS, "snapshots_per_slug": {},
                    "snapshot_type_split": {"new_market_cross_section": 0, "same_slug_time_series": 0},
                    "unique_slugs": 0, "request_count": budget.count,
                    "max_total_requests": budget.max_total, "discovery_requests": 0,
                    "book_requests": 0, "books_ok": 0, "books_failed": 0, "timestamp_utc": now_unix}
        return _emit("PILOT_FAILED", partial=True)

    # discovery (spends 1 Gamma; sub-cap MAX_DISCOVERY_REQUESTS)
    try:
        markets = await discover_fn(budget)
        discovery_requests = 1
    except BudgetExceeded:
        failure_modes.append("BUDGET_STOP")
        return _emit("PILOT_FAILED", partial=True)
    except Exception as e:
        failure_modes.append(f"DISCOVERY_ERROR:{type(e).__name__}")
        return _emit("PILOT_FAILED", partial=True)

    plan = _pilot_plan(list(markets or []))
    if not plan:
        failure_modes.append("NO_OPEN_MARKETS")
        return _emit("PILOT_FAILED", partial=True)

    try:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            from data import clob_price  # pure parsers; lazy import
            for idx, (m, label) in enumerate(plan):
                if book_requests >= MAX_BOOK_REQUESTS:
                    failure_modes.append("BOOK_CAP_STOP")
                    break
                if budget.count + 1 > budget.max_total:
                    failure_modes.append("BUDGET_STOP")
                    break
                if idx > 0:
                    await sleep_fn(TS_INTERVAL_S if label == "ts" else PILOT_PACING_S)
                slug = m.get("market_slug")
                token = m.get("token_id")
                try:
                    book = await fetch_book_fn(token, budget)
                except RateLimited:
                    rate_limited = True
                    failure_modes.append("RATE_LIMITED")
                    break
                except BudgetExceeded:
                    failure_modes.append("BUDGET_STOP")
                    break
                book_requests += 1
                bids = clob_price.sorted_bids(book)
                asks = clob_price.sorted_asks(book)
                snap = build_snapshot(DRY_RUN_ASSET, DRY_RUN_INTERVAL, slug, token, bids, asks)
                tag = P.classify_book(snap)
                if tag == "TWO_SIDED":
                    f.write(json.dumps(snap) + "\n")
                    f.flush()
                    books_ok += 1
                    snapshots.append((slug, label))
                    per_slug[slug] = per_slug.get(slug, 0) + 1
                else:
                    books_failed += 1
                    failure_modes.append(tag)
    except Exception as e:  # truly unexpected (e.g. fetch adapter raised non-RateLimited)
        fatal = type(e).__name__
        failure_modes.append(f"FATAL:{fatal}")

    # verdict (closed set)
    unique_written = len({s for s, _ in snapshots})
    if fatal:
        verdict, partial = "PILOT_FAILED", True
    elif rate_limited:
        verdict, partial = "PILOT_RATE_LIMITED_PARTIAL", True
    elif books_ok == 0:
        failure_modes.append("INSUFFICIENT_BOOK_DATA")
        verdict, partial = "PILOT_FAILED", True
    elif unique_written < MIN_PILOT_UNIQUE_SLUGS:
        verdict = "PILOT_INSUFFICIENT_MARKET_DIVERSITY"
        partial = books_ok < PILOT_TARGET_SNAPSHOTS
    elif books_ok >= MIN_PILOT_SNAPSHOTS:
        verdict = "PILOT_SAMPLE_ONLY"
        partial = books_ok < PILOT_TARGET_SNAPSHOTS
    else:
        verdict, partial = "PILOT_FAILED", True
    return _emit(verdict, partial=partial)


# ---- Phase 3D3 multi-asset bounded discovery (injectable; live path guarded by CLI, not run in tests) ----

def _pilot_3d3_plan(markets):
    """Fair (round-robin) plan over BTC/ETH/SOL/XRP: one book per asset BEFORE any time-series repeat.

    Returns [(market_dict, label)] with label in {"new","ts"}; length capped at PILOT_3D3_MAX_BOOK_REQUESTS.
    Phase 1 interleaves one distinct slug per asset per round (prevents asset starvation); Phase 2 fills
    with time-series repeats, also round-robin across assets.
    """
    cap = PILOT_3D3_MAX_BOOK_REQUESTS
    unique_by_asset = collections.OrderedDict()
    seen = set()
    for m in markets:
        slug = m.get("market_slug")
        if slug in seen:
            continue
        seen.add(slug)
        unique_by_asset.setdefault(m.get("asset"), []).append(m)

    plan = []
    idxs = {a: 0 for a in unique_by_asset}
    progress = True
    while len(plan) < cap and progress:           # phase 1: cross-market, one per asset per round
        progress = False
        for a, ms in unique_by_asset.items():
            if idxs[a] < len(ms) and len(plan) < cap:
                plan.append((ms[idxs[a]], "new"))
                idxs[a] += 1
                progress = True
    if any(unique_by_asset.values()):             # phase 2: time-series round-robin fill
        assets = list(unique_by_asset.keys())
        counters = {a: 0 for a in assets}
        rr = 0
        while len(plan) < cap:
            a = assets[rr % len(assets)]
            rr += 1
            ms = unique_by_asset[a]
            if not ms:
                continue
            plan.append((ms[counters[a] % len(ms)], "ts"))
            counters[a] += 1
    return plan


async def pilot_3d3_multi_asset(*, discover_fn, fetch_book_fn, sleep_fn=None, output_dir=OUT_DIR,
                                timestamp_fn=None, budget=None):
    """Bounded multi-asset (BTC/ETH/SOL/XRP, 5m) read-only pilot. Fair round-robin scheduling prevents
    asset starvation: at least one book attempt per asset (when candidates exist) before time-series
    repeats. <=20 requests (1 discovery + <=19 books); stops at PILOT_3D3_TARGET_SNAPSHOTS successful
    two-sided books. Verdict gate is IDENTICAL to pilot_eth5m (unique_slugs < MIN_PILOT_UNIQUE_SLUGS ->
    PILOT_INSUFFICIENT_MARKET_DIVERSITY; never relabeled SAMPLE_ONLY). All collaborators injectable.
    """
    if sleep_fn is None:
        import asyncio
        sleep_fn = asyncio.sleep
    if timestamp_fn is None:
        timestamp_fn = lambda: int(time.time())  # noqa: E731
    budget = budget if budget is not None else RequestBudget(PILOT_3D3_MAX_TOTAL_REQUESTS)
    now_unix = timestamp_fn()

    jsonl_path = os.path.join(output_dir, f"phase3d3_pilot_snapshots_{now_unix}.jsonl")
    summary_path = os.path.join(output_dir, f"phase3d3_pilot_summary_{now_unix}.json")

    failure_modes = []
    discovery_requests = 0
    book_requests = 0
    books_ok = 0
    books_failed = 0
    snapshots = []                 # (slug, label, asset)
    per_slug = {}
    books_by_asset = collections.Counter()
    snapshots_by_asset = collections.Counter()
    assets_seen = []
    rate_limited = False
    fatal = None

    def _emit(verdict, partial):
        type_split = {"new_market_cross_section": sum(1 for _, lab, _ in snapshots if lab == "new"),
                      "same_slug_time_series": sum(1 for _, lab, _ in snapshots if lab == "ts")}
        summary = {
            "verdict": verdict,
            "phase": "3D3_pilot",
            "assets": list(PILOT_3D3_ASSETS),
            "interval": PILOT_3D3_INTERVAL,
            "target_snapshots": PILOT_3D3_TARGET_SNAPSHOTS,
            "snapshots_written": len(snapshots),
            "unique_slugs": len({s for s, _, _ in snapshots}),
            "snapshots_per_slug": dict(sorted(per_slug.items())),
            "snapshot_type_split": type_split,
            "assets_seen": sorted(set(assets_seen)),
            "unique_assets": len(set(assets_seen)),
            "books_by_asset": dict(sorted(books_by_asset.items())),
            "snapshots_by_asset": dict(sorted(snapshots_by_asset.items())),
            "request_count": budget.count,
            "max_total_requests": budget.max_total,
            "discovery_requests": discovery_requests,
            "book_requests": book_requests,
            "books_ok": books_ok,
            "books_failed": books_failed,
            "failure_modes": sorted(set(failure_modes)),
            "partial": bool(partial),
            "output_jsonl": jsonl_path,
            "output_summary": summary_path,
            "timestamp_utc": now_unix,
            "official_f1b": False,
            "profitability": False,
        }
        with open(summary_path, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2)
        return summary

    if os.path.exists(jsonl_path) or os.path.exists(summary_path):
        failure_modes.append("OUTPUT_EXISTS_NO_OVERWRITE")
        if os.path.exists(summary_path):
            failure_modes_only = {"verdict": "PILOT_FAILED", "failure_modes": ["OUTPUT_EXISTS_NO_OVERWRITE"],
                                  "output_jsonl": jsonl_path, "output_summary": summary_path,
                                  "partial": True, "phase": "3D3_pilot", "official_f1b": False,
                                  "profitability": False}
            return failure_modes_only
        return _emit("PILOT_FAILED", partial=True)

    try:
        markets = await discover_fn(budget)
        discovery_requests = 1
    except BudgetExceeded:
        failure_modes.append("BUDGET_STOP")
        return _emit("PILOT_FAILED", partial=True)
    except Exception as e:
        failure_modes.append(f"DISCOVERY_ERROR:{type(e).__name__}")
        return _emit("PILOT_FAILED", partial=True)

    markets = list(markets or [])
    assets_seen = [m.get("asset") for m in markets if m.get("asset")]
    plan = _pilot_3d3_plan(markets)
    if not plan:
        failure_modes.append("NO_OPEN_MARKETS")
        return _emit("PILOT_FAILED", partial=True)

    try:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            from data import clob_price  # pure parsers; lazy import
            attempts = 0
            for m, label in plan:
                if books_ok >= PILOT_3D3_TARGET_SNAPSHOTS:
                    break
                if book_requests >= PILOT_3D3_MAX_BOOK_REQUESTS:
                    failure_modes.append("BOOK_CAP_STOP")
                    break
                if budget.count + 1 > budget.max_total:
                    failure_modes.append("BUDGET_STOP")
                    break
                if attempts > 0:
                    await sleep_fn(TS_INTERVAL_S if label == "ts" else PILOT_PACING_S)
                attempts += 1
                slug = m.get("market_slug")
                token = m.get("token_id")
                asset = m.get("asset")
                try:
                    book = await fetch_book_fn(token, budget)
                except RateLimited:
                    rate_limited = True
                    failure_modes.append("RATE_LIMITED")
                    break
                except BudgetExceeded:
                    failure_modes.append("BUDGET_STOP")
                    break
                book_requests += 1
                books_by_asset[asset] += 1
                bids = clob_price.sorted_bids(book)
                asks = clob_price.sorted_asks(book)
                snap = build_snapshot(asset, PILOT_3D3_INTERVAL, slug, token, bids, asks)
                tag = P.classify_book(snap)
                if tag == "TWO_SIDED":
                    f.write(json.dumps(snap) + "\n")
                    f.flush()
                    books_ok += 1
                    snapshots.append((slug, label, asset))
                    per_slug[slug] = per_slug.get(slug, 0) + 1
                    snapshots_by_asset[asset] += 1
                else:
                    books_failed += 1
                    failure_modes.append(tag)
    except Exception as e:
        fatal = type(e).__name__
        failure_modes.append(f"FATAL:{fatal}")

    unique_written = len({s for s, _, _ in snapshots})
    if fatal:
        verdict, partial = "PILOT_FAILED", True
    elif rate_limited:
        verdict, partial = "PILOT_RATE_LIMITED_PARTIAL", True
    elif books_ok == 0:
        failure_modes.append("INSUFFICIENT_BOOK_DATA")
        verdict, partial = "PILOT_FAILED", True
    elif unique_written < MIN_PILOT_UNIQUE_SLUGS:
        verdict = "PILOT_INSUFFICIENT_MARKET_DIVERSITY"
        partial = books_ok < PILOT_3D3_TARGET_SNAPSHOTS
    elif books_ok >= PILOT_3D3_MIN_SNAPSHOTS:
        verdict = "PILOT_SAMPLE_ONLY"
        partial = books_ok < PILOT_3D3_TARGET_SNAPSHOTS
    else:
        verdict, partial = "PILOT_FAILED", True
    return _emit(verdict, partial=partial)


async def _real_discover_3d3(budget):  # pragma: no cover - live path, not run in this task
    """One Gamma request, best-effort: open BTC/ETH/SOL/XRP 5m markets tagged by asset, with token ids."""
    import aiohttp
    from data import shortterm
    budget.spend("gamma")
    timeout = aiohttp.ClientTimeout(total=12)
    out = []
    async with aiohttp.ClientSession(timeout=timeout,
                                     headers={"User-Agent": "phase3d3-pilot/1.0"}) as s:
        slug = shortterm.slugs_for_now(assets=tuple(a.lower() for a in PILOT_3D3_ASSETS),
                                       interval=5, lookback=1)[0]
        async with s.get(shortterm.GAMMA, params={"slug": slug}) as r:
            if r.status != 200:
                return out
            data = await r.json()
    arr = data if isinstance(data, list) else data.get("data", [])
    for m in arr:
        if m.get("closed") is True:
            continue
        tokens = shortterm._parse_token_ids(m.get("clobTokenIds"))
        mslug = (m.get("slug") or "")
        asset = next((a for a in PILOT_3D3_ASSETS if mslug.lower().startswith(a.lower())), None)
        if tokens and asset:
            out.append({"asset": asset, "market_slug": mslug, "token_id": tokens[0]})
    return out


# ---- full-scale (later, approved) sampling: intentionally NOT implemented/run here ----

async def _sample_cell(*args, **kwargs):  # pragma: no cover - scaffold, not implemented/run here
    raise NotImplementedError("Phase 3 full-scale live sampling is not implemented/run in this stage.")


def aggregate_and_verdict(snapshots_by_cell):
    """Offline full-scale aggregate + readiness verdict via pure logic (NOT used by the 3C dry run)."""
    out = {}
    for key, snaps in snapshots_by_cell.items():
        report = P.aggregate_cell(snaps)
        status, fails = P.verdict(report)
        out[key] = {"report": report, "verdict": status, "failures": fails}
    return out


# ---- real public adapters (used ONLY by the guarded CLI; not invoked in tests) ----

async def _real_discover(budget):  # pragma: no cover - live path, not run in this task
    """One Gamma request -> up to MAX_SLUGS open ETH 5m markets with clob token ids."""
    import aiohttp
    from data import shortterm
    budget.spend("gamma")
    timeout = aiohttp.ClientTimeout(total=12)
    out = []
    async with aiohttp.ClientSession(timeout=timeout,
                                     headers={"User-Agent": "phase3-dryrun/1.0"}) as s:
        # single request: most recent ETH 5m candidate slug, expand to a few open markets
        slug = shortterm.slugs_for_now(assets=("eth",), interval=5, lookback=MAX_SLUGS)[0]
        async with s.get(shortterm.GAMMA, params={"slug": slug}) as r:
            if r.status != 200:
                return out
            data = await r.json()
    arr = data if isinstance(data, list) else data.get("data", [])
    for m in arr[:MAX_SLUGS]:
        if m.get("closed") is True:
            continue
        tokens = shortterm._parse_token_ids(m.get("clobTokenIds"))
        if tokens:
            out.append({"market_slug": m.get("slug"), "token_id": tokens[0]})
    return out


async def _real_fetch_book(token_id, budget):  # pragma: no cover - live path, not run in this task
    from data import clob_price
    budget.spend("book")
    return await clob_price.get_book(token_id)


if __name__ == "__main__":  # pragma: no cover
    _args = sys.argv[1:]
    if _args == ["--dry-run-eth5m"]:
        import asyncio
        _summary = asyncio.run(dry_run_eth5m(discover_fn=_real_discover,
                                             fetch_book_fn=_real_fetch_book,
                                             sleep_fn=asyncio.sleep))
        print(json.dumps(_summary, indent=2))
    elif _args == ["--pilot-eth5m"]:
        import asyncio
        _summary = asyncio.run(pilot_eth5m(discover_fn=_real_discover,
                                           fetch_book_fn=_real_fetch_book,
                                           sleep_fn=asyncio.sleep))
        print(json.dumps(_summary, indent=2))
    elif _args == ["--pilot-3d3-multi-asset"]:
        import asyncio
        _summary = asyncio.run(pilot_3d3_multi_asset(discover_fn=_real_discover_3d3,
                                                     fetch_book_fn=_real_fetch_book,
                                                     sleep_fn=asyncio.sleep))
        print(json.dumps(_summary, indent=2))
    else:
        raise SystemExit("usage: phase3_exec_sampler.py "
                         "[--dry-run-eth5m | --pilot-eth5m | --pilot-3d3-multi-asset] "
                         "(refused: no other invocation is permitted)")
