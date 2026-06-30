"""
analysis.forensic.gateg7_prelaunch — pure pre-launch observability/classification tooling.

Pure, OFFLINE, network-free, import-safe. These helpers are OBSERVATIONAL only: they never
feed the runner's decision path (candidate selection / fair value / entry_edge / fill
decision / stake / admission). They support the bounded-live completion report:

  * RequestCounters         — request-attempt counters (instrumented by the runner).
  * classify_terminal       — one of MECHANICAL_PASS / INSUFFICIENT_PROXY_COVERAGE /
                              MECHANICAL_FAIL / EXTERNAL_TIMEOUT_FAIL.
  * audit_proxy_accounting  — exactly one proxy row XOR one PROXY_DIAG per committed signal.
  * classify_heartbeat      — heartbeat-staleness (stale threshold 420s; HEARTBEAT_EVERY_S=300).

No alpha / PnL / G6 / trading interpretation. MECHANICAL / INFRA-ONLY.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

# --- terminal classifications ---
MECHANICAL_PASS = "MECHANICAL_PASS"
INSUFFICIENT_PROXY_COVERAGE = "INSUFFICIENT_PROXY_COVERAGE"
MECHANICAL_FAIL = "MECHANICAL_FAIL"
EXTERNAL_TIMEOUT_FAIL = "EXTERNAL_TIMEOUT_FAIL"
OPERATOR_ABORT = "OPERATOR_ABORT"

# Wrapper exit codes that mean external/emergency termination (124=timeout, 137=SIGKILL,
# 143=SIGTERM). Never converted to 0; always EXTERNAL_TIMEOUT_FAIL.
EXTERNAL_TERMINATION_CODES = frozenset({124, 137, 143})

# --- heartbeat statuses ---
STUCK_OR_BLOCKED_PROCESS = "STUCK_OR_BLOCKED_PROCESS"
HEALTHY_OR_NOT_RUNNING = "HEALTHY_OR_NOT_RUNNING"

# A clean internal bounded stop (no external/emergency termination).
CLEAN_INTERNAL_STOPS = frozenset({"MAX_OBSERVATIONS", "MAX_ELAPSED"})

DEFAULT_STALE_THRESHOLD_MS = 420_000   # 420s; HEARTBEAT_EVERY_S=300 + one slow-cycle headroom


@dataclass
class RequestCounters:
    """Observational request-attempt counters. Incremented IMMEDIATELY before each network
    call (failed attempts count once; retries are forbidden so are never counted). Pure data
    holder — carries no decision logic and is kept outside signal_log / mark_path."""
    gamma_get_attempts: int = 0
    clob_book_get_attempts: int = 0
    hl_post_attempts: int = 0
    coinbase_get_attempts: int = 0
    kraken_get_attempts: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def classify_terminal(*, external_exit_code=None, external_terminated=False, stop_reason=None,
                      signal_chain_ok: bool, mark_chain_ok: bool, proxy_accounting_ok: bool,
                      unexpected_count: int = 0, core_isolation_ok: bool = True,
                      target_assets=(), covered_assets=()) -> str:
    """Pure terminal classifier producing exactly one classification.

    Priority (headline): (1) external/emergency termination outranks everything (never PASS);
    (2) integrity/core/accounting failure; (3) clean operator abort; (4) insufficient coverage;
    (5) mechanical pass. A clean internal stop with full integrity and full coverage is the only
    MECHANICAL_PASS.
    """
    if external_terminated or external_exit_code in EXTERNAL_TERMINATION_CODES:
        return EXTERNAL_TIMEOUT_FAIL

    integrity_ok = (signal_chain_ok and mark_chain_ok and proxy_accounting_ok
                    and core_isolation_ok and unexpected_count == 0)
    if not integrity_ok:
        return MECHANICAL_FAIL

    if stop_reason == OPERATOR_ABORT:             # clean operator stop; never PASS
        return OPERATOR_ABORT

    if stop_reason not in CLEAN_INTERNAL_STOPS:   # abnormal stop, no external timeout
        return MECHANICAL_FAIL

    missing = [a for a in target_assets if a not in set(covered_assets)]
    if missing:
        return INSUFFICIENT_PROXY_COVERAGE
    return MECHANICAL_PASS


def is_external_termination(exit_code) -> bool:
    """True iff a wrapper exit code denotes external/emergency termination (124/137/143)."""
    return exit_code in EXTERNAL_TERMINATION_CODES


def record_exit_code(path: str, exit_code: int) -> None:
    """Persist the EXACT wrapper exit code (never coerced) to an isolated artifact."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(int(exit_code)))


def read_exit_code(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return int(f.read().strip())


def audit_proxy_accounting(committed_signal_ids, proxy_row_signal_ids,
                           proxy_diag_signal_ids) -> dict:
    """Pure proxy accounting: each committed signal_id must have EXACTLY one proxy row XOR one
    PROXY_DIAG. Detects missing / duplicate rows / multiple PROXY_DIAG / both (double-counted) /
    orphan rows / orphan diags. Returns a report dict with sorted lists and an `ok` flag."""
    committed = set(committed_signal_ids)
    row_counts = Counter(proxy_row_signal_ids)
    diag_counts = Counter(proxy_diag_signal_ids)

    missing, duplicate_rows, multi_diag, double_counted = [], [], [], []
    for sid in committed:
        r, d = row_counts.get(sid, 0), diag_counts.get(sid, 0)
        if r + d == 0:
            missing.append(sid)
        if r > 1:
            duplicate_rows.append(sid)
        if d > 1:
            multi_diag.append(sid)
        if r >= 1 and d >= 1:
            double_counted.append(sid)
    orphan_rows = [sid for sid in row_counts if sid not in committed]
    orphan_diag = [sid for sid in diag_counts if sid not in committed]

    report = {
        "missing": sorted(missing),
        "duplicate_rows": sorted(duplicate_rows),
        "multi_diag": sorted(multi_diag),
        "double_counted": sorted(double_counted),
        "orphan_rows": sorted(orphan_rows),
        "orphan_diag": sorted(orphan_diag),
        "committed_count": len(committed),
        "proxy_row_count": sum(row_counts.values()),
        "proxy_diag_count": sum(diag_counts.values()),
    }
    report["ok"] = not any(report[k] for k in
                           ("missing", "duplicate_rows", "multi_diag", "double_counted",
                            "orphan_rows", "orphan_diag"))
    return report


def classify_heartbeat(*, pid_alive: bool, last_heartbeat_ts_ms: int, now_ts_ms: int,
                       stale_threshold_ms: int = DEFAULT_STALE_THRESHOLD_MS) -> dict:
    """Pure heartbeat-staleness classifier (infra/mechanical telemetry only — NEVER alpha/model
    failure). PID alive AND heartbeat age strictly greater than the stale threshold (420s) =>
    STUCK_OR_BLOCKED_PROCESS; otherwise HEALTHY_OR_NOT_RUNNING."""
    age = now_ts_ms - last_heartbeat_ts_ms
    if pid_alive and age > stale_threshold_ms:
        status = STUCK_OR_BLOCKED_PROCESS
    else:
        status = HEALTHY_OR_NOT_RUNNING
    return {
        "status": status,
        "pid_alive": pid_alive,
        "heartbeat_age_ms": age,
        "stale_threshold_ms": stale_threshold_ms,
    }
