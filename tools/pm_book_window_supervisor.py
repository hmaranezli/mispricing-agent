"""tools/pm_book_window_supervisor.py — rotating-window PM book characterization supervisor.

Collects consecutive BTC 5m Polymarket PM-book windows by orchestrating the ratified diagnostic
runner across one window at a time. This module is INFRASTRUCTURE ONLY — it gathers serial
interval evidence; it computes no signal of any kind and performs no order placement.

Design:
  * Window slugs are derived from UTC Unix epoch seconds only (no local timezone / DST / wall-clock
    string math).
  * Read-only market/token discovery lives HERE (the runner stays discovery-free). The production
    discovery seam uses the Gamma markets endpoint for market lookup and the CLOB ``/markets``
    endpoint for explicit outcome->token mapping; both are passed in as an injected ``lookup_fn``
    so tests use fakes and no network is touched.
  * A window launches only if it can finish its FULL per-window target before an expiry buffer
    (full-target-only policy); otherwise it is skipped.
  * Tokens are taken from explicit outcome fields only — never inferred from array position.
  * Every decision is appended to a flush+fsync JSONL manifest (append-only, never rewritten).
  * The runner is invoked through the ratified CLI shape with EXPLICIT slug/tokens/paths only.

Production discovery endpoints (documented; the injected lookup_fn wraps these):
  GAMMA_MARKETS_URL — market discovery
  CLOB_MARKETS_URL  — explicit outcome->token mapping

Claim boundary: cross-window data is concatenated serial evidence from DISTINCT markets — no
continuity, no interpolation across gaps, no near-sync / atomic snapshot claim, no raw HTTP DB
preservation claim.
"""
from __future__ import annotations

import json
import os
from collections import Counter

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
CLOB_MARKETS_URL = "https://clob.polymarket.com/markets"

WINDOW_SECONDS = 300
CYCLE_SLEEP_FLOOR_SECONDS = 1.0
COOLDOWN_FLOOR_SECONDS = 5.0

SKIP_REASONS = frozenset({
    "gamma_http_error", "gamma_timeout", "gamma_malformed_json", "gamma_market_missing",
    "clob_market_http_error", "clob_market_timeout", "clob_market_malformed_json",
    "market_inactive", "market_closed", "condition_id_missing", "outcome_missing",
    "mapping_missing", "mapping_ambiguous", "token_id_empty", "token_id_non_numeric",
    "token_ids_equal", "insufficient_freshness_budget", "duplicate_window",
    "no_fresh_window", "expiry_mismatch",
})


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def compute_window_start(now_epoch_seconds) -> int:
    """Floor a UTC epoch-seconds value to its 5-minute window start. Epoch math only."""
    return (int(now_epoch_seconds) // WINDOW_SECONDS) * WINDOW_SECONDS


def slug_for_window(asset: str, timeframe: str, window_start: int) -> str:
    """Build the Polymarket Up/Down slug for a window (e.g. ``btc-updown-5m-<window_start>``)."""
    return f"{asset.lower()}-updown-{timeframe}-{window_start}"


def estimate_run_seconds(*, max_captures: int, cycle_sleep_seconds: float,
                         expected_capture_span_seconds: float,
                         launch_overhead_seconds: float) -> float:
    """Estimate wall-clock seconds for a full per-window run: overhead + captures + inter-sleeps."""
    return (launch_overhead_seconds
            + max_captures * expected_capture_span_seconds
            + max(0, max_captures - 1) * cycle_sleep_seconds)


def _validate_mapping(tokens):
    """Resolve (yes_token, no_token) from explicit outcome fields, or return ('skip', reason)."""
    if not isinstance(tokens, list) or any("outcome" not in t for t in tokens):
        return ("skip", "outcome_missing")
    counts = Counter(t.get("outcome") for t in tokens)
    if "Up" not in counts or "Down" not in counts:
        return ("skip", "mapping_missing")
    if counts["Up"] > 1 or counts["Down"] > 1:
        return ("skip", "mapping_ambiguous")
    by_outcome = {t["outcome"]: str(t.get("token_id", "")) for t in tokens}
    yes, no = by_outcome["Up"], by_outcome["Down"]
    if yes == "" or no == "":
        return ("skip", "token_id_empty")
    if not yes.isdigit() or not no.isdigit():
        return ("skip", "token_id_non_numeric")
    if yes == no:
        return ("skip", "token_ids_equal")
    return ("ok", yes, no)


def resolve_window(*, lookup_result, computed_expiry_epoch, now_epoch,
                   estimated_run_seconds, expiry_buffer_seconds):
    """Decide a single window. Returns ('ok', yes, no, capped_duration) or ('skip', reason)."""
    if not isinstance(lookup_result, dict):
        return ("skip", "gamma_malformed_json")
    if lookup_result.get("skip_reason"):
        return ("skip", lookup_result["skip_reason"])
    if not lookup_result.get("active"):
        return ("skip", "market_inactive")
    if lookup_result.get("closed"):
        return ("skip", "market_closed")
    if not lookup_result.get("condition_id"):
        return ("skip", "condition_id_missing")
    if lookup_result.get("expiry_epoch") != computed_expiry_epoch:
        return ("skip", "expiry_mismatch")

    mapped = _validate_mapping(lookup_result.get("tokens"))
    if mapped[0] == "skip":
        return mapped
    _, yes, no = mapped

    remaining = computed_expiry_epoch - now_epoch
    if estimated_run_seconds + expiry_buffer_seconds > remaining:
        return ("skip", "insufficient_freshness_budget")
    capped_duration = remaining - expiry_buffer_seconds
    return ("ok", yes, no, capped_duration)


def build_runner_argv(params: dict, *, python_exe: str,
                      module: str = "tools.pm_book_diag_runner") -> list:
    """Build the ratified runner CLI argv from explicit params. No discovery flags."""
    return [
        python_exe, "-m", module,
        "--market-slug", params["market_slug"],
        "--yes-token-id", params["yes_token_id"],
        "--no-token-id", params["no_token_id"],
        "--asset", params["asset"],
        "--timeframe", params["timeframe"],
        "--db-path", params["db_path"],
        "--base-url", params["base_url"],
        "--cycle-sleep-seconds", str(params["cycle_sleep_seconds"]),
        "--max-captures", str(params["max_captures"]),
        "--duration-seconds", str(params["duration_seconds"]),
    ]


# ---------------------------------------------------------------------------
# Append-only JSONL manifest
# ---------------------------------------------------------------------------

class JsonlManifestWriter:
    """Append-only JSONL manifest. One line per event, monotonic event_id, flush + fsync per append."""

    def __init__(self, path: str, *, fsync_fn=os.fsync):
        self.path = path
        self._fsync = fsync_fn
        self._seq = 0
        self._fh = open(path, "a", encoding="utf-8")

    def append(self, record: dict) -> int:
        self._seq += 1
        rec = dict(record)
        rec["event_id"] = self._seq
        self._fh.write(json.dumps(rec) + "\n")
        self._fh.flush()
        try:
            self._fsync(self._fh.fileno())
        except (OSError, ValueError):
            pass  # fsync unsupported on this fd/platform — flush already durable enough
        return self._seq

    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subprocess cleanup
# ---------------------------------------------------------------------------

async def _terminate_child(child, *, cleanup_timeout_seconds, sleep_fn, now_fn) -> dict:
    """Graceful-terminate then kill-after-timeout a child process. Leaves no orphan."""
    if child.returncode is not None:
        return {"already_exited": True, "killed": False, "returncode": child.returncode}
    child.terminate()
    if child.returncode is not None:
        return {"killed": False, "returncode": child.returncode}
    deadline = now_fn() + cleanup_timeout_seconds
    while child.returncode is None and now_fn() < deadline:
        await sleep_fn(0.05)
    if child.returncode is None:
        child.kill()
        return {"killed": True, "returncode": child.returncode}
    return {"killed": False, "returncode": child.returncode}


# ---------------------------------------------------------------------------
# Supervisor loop
# ---------------------------------------------------------------------------

async def run_window_supervisor(*, asset: str, timeframe: str, base_url: str, db_dir: str,
                                cycle_sleep_seconds: float, per_window_max_captures: int,
                                expiry_buffer_seconds: float, inter_window_cooldown_seconds: float,
                                expected_capture_span_seconds: float, launch_overhead_seconds: float,
                                lookup_fn, launch_fn, manifest, now_epoch_fn, sleep_fn,
                                max_windows=None, max_total_captures=None,
                                max_total_duration_seconds=None,
                                run_id: str = "run", db_path_fn=None, out_path_fn=None) -> dict:
    """Drive consecutive single-window runner launches. Serial interval evidence only.

    ``lookup_fn(slug) -> dict`` and ``launch_fn(params) -> dict`` are REQUIRED injected seams so no
    network or subprocess is touched implicitly. Returns a summary dict.
    """
    # ---- fail-fast contract checks -------------------------------------------
    if not asset:
        raise ValueError("asset must be non-empty")
    if not timeframe:
        raise ValueError("timeframe must be non-empty")
    if not base_url:
        raise ValueError("base_url must be non-empty")
    if not db_dir:
        raise ValueError("db_dir must be non-empty")
    if cycle_sleep_seconds < CYCLE_SLEEP_FLOOR_SECONDS:
        raise ValueError(f"cycle_sleep_seconds must be >= {CYCLE_SLEEP_FLOOR_SECONDS}")
    if inter_window_cooldown_seconds < COOLDOWN_FLOOR_SECONDS:
        raise ValueError(f"inter_window_cooldown_seconds must be >= {COOLDOWN_FLOOR_SECONDS}")
    if per_window_max_captures < 1:
        raise ValueError("per_window_max_captures must be >= 1")
    if expiry_buffer_seconds < 0:
        raise ValueError("expiry_buffer_seconds must be >= 0")
    if max_windows is None and max_total_captures is None and max_total_duration_seconds is None:
        raise ValueError("at least one stop condition required")

    est = estimate_run_seconds(max_captures=per_window_max_captures,
                               cycle_sleep_seconds=cycle_sleep_seconds,
                               expected_capture_span_seconds=expected_capture_span_seconds,
                               launch_overhead_seconds=launch_overhead_seconds)

    seen = set()
    launched = 0
    total_captures = 0
    window_index = 0
    start = now_epoch_fn()
    stop_reason = None

    while True:
        if max_windows is not None and launched >= max_windows:
            stop_reason = "max_windows"
            break
        if max_total_captures is not None and total_captures >= max_total_captures:
            stop_reason = "max_total_captures"
            break
        if max_total_duration_seconds is not None and (now_epoch_fn() - start) >= max_total_duration_seconds:
            stop_reason = "max_total_duration"
            break

        now = now_epoch_fn()
        ws = compute_window_start(now)
        target = None
        for off in (0, WINDOW_SECONDS, 2 * WINDOW_SECONDS):
            cw = ws + off
            slug = slug_for_window(asset, timeframe, cw)
            if slug not in seen:
                target = (cw, slug)
                break
        if target is None:
            stop_reason = "no_fresh_window"
            break

        cw, slug = target
        seen.add(slug)
        window_index += 1
        computed_expiry = cw + WINDOW_SECONDS

        lookup_started = now_epoch_fn()
        lookup = await lookup_fn(slug)
        lookup_finished = now_epoch_fn()

        decision = resolve_window(lookup_result=lookup, computed_expiry_epoch=computed_expiry,
                                  now_epoch=lookup_finished, estimated_run_seconds=est,
                                  expiry_buffer_seconds=expiry_buffer_seconds)

        cond_id = lookup.get("condition_id") if isinstance(lookup, dict) else None

        if decision[0] == "skip":
            manifest.append({
                "event_type": "skip", "run_id": run_id, "window_index": window_index,
                "market_slug": slug, "condition_id": cond_id, "expiry": computed_expiry,
                "lookup_started_at": lookup_started, "lookup_finished_at": lookup_finished,
                "skip_reason": decision[1],
            })
            await sleep_fn(inter_window_cooldown_seconds)
            continue

        _, yes, no, capped_duration = decision
        db_path = db_path_fn(slug) if db_path_fn else os.path.join(db_dir, f"pm_{slug}.db")
        out_path = out_path_fn(slug) if out_path_fn else os.path.join(db_dir, f"pm_{slug}.out")
        params = {
            "market_slug": slug, "yes_token_id": yes, "no_token_id": no,
            "asset": asset, "timeframe": timeframe, "db_path": db_path,
            "base_url": base_url, "cycle_sleep_seconds": cycle_sleep_seconds,
            "max_captures": per_window_max_captures, "duration_seconds": capped_duration,
            "out_path": out_path,
        }

        launch_started = now_epoch_fn()
        manifest.append({
            "event_type": "launch", "run_id": run_id, "window_index": window_index,
            "market_slug": slug, "condition_id": cond_id, "expiry": computed_expiry,
            "launch_started_at": launch_started, "yes_token_id": yes, "no_token_id": no,
            "db_path": db_path, "out_path": out_path,
        })

        result = await launch_fn(params)
        launch_finished = now_epoch_fn()
        launched += 1
        total_captures += int(result.get("captures") or 0)

        manifest.append({
            "event_type": "window_result", "run_id": run_id, "window_index": window_index,
            "market_slug": slug, "launch_finished_at": launch_finished,
            "exit_code": result.get("exit_code"), "captures": result.get("captures"),
            "stop_reason": result.get("stop_reason"),
            "db_file_exists": result.get("db_file_exists"),
            "db_row_count": result.get("db_row_count"),
        })

        await sleep_fn(inter_window_cooldown_seconds)

    manifest.append({
        "event_type": "supervisor_stop", "run_id": run_id, "stop_reason": stop_reason,
        "windows_launched": launched, "total_captures": total_captures,
    })
    return {"windows_launched": launched, "total_captures": total_captures, "stop_reason": stop_reason}
