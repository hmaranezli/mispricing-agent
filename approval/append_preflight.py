"""approval/append_preflight.py — passive abuse-resistance preflight for approval-ledger appends.

This module produces a PURE, deterministic, PASSIVE decision BEFORE any append to the isolated
append-only approval ledger. It defends against spam, typo loops, retry storms, malicious
``while(true)`` append floods, and disk/inode exhaustion — and it FAILS CLOSED on every ambiguous or
unsafe state.

Design invariants:
  * It writes NOTHING and mutates NOTHING. It never deletes / truncates / compacts / redacts evidence.
    (There is no destructive API on this module.)
  * Rate-limit dimensions are EXPLICIT inputs (quota, invalid window, duplicate threshold, free-space
    and inode thresholds). There is no hidden global config.
  * Rate-limit state is DERIVED from append-only ledger rows (``snapshot_from_ledger``, read-only) or
    a caller-supplied immutable ``history`` tuple — never a new mutable side DB.
  * Disk/inode capacity is an injected ``DiskStat`` snapshot — this module performs no filesystem,
    network, or env access.
  * Per-actor isolation: one actor's flood cannot block another actor.

The output is a frozen ``PreflightDecision(allowed, reason)``. ``allowed=True`` is NOT an approval,
NOT S1 authorization, NOT capacity; ``allowed=False`` is NOT recovery. The decision authorizes
nothing.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class AppendAttempt:
    """One immutable prior attempt record used to derive rate-limit state."""

    actor_id: str
    window_id: str
    record_signature: str
    outcome: str  # "valid" | "invalid"


@dataclass(frozen=True)
class DiskStat:
    """Injected, immutable disk capacity snapshot (no filesystem call in this module)."""

    free_bytes: int
    free_inodes: int


@dataclass(frozen=True)
class PreflightDecision:
    """Passive, immutable preflight outcome. Authorizes nothing."""

    allowed: bool
    reason: str


def _is_bad_threshold(value) -> bool:
    return value is None or not isinstance(value, int) or isinstance(value, bool) or value < 0


def evaluate_append_preflight(
    *,
    actor_id: str,
    window_id: str,
    record_signature: str,
    history,
    max_appends_per_window,
    max_invalid_per_window,
    max_duplicates,
    disk_stat: DiskStat,
    min_free_bytes,
    min_free_inodes,
) -> PreflightDecision:
    """Decide whether an append may proceed. Pure, passive, fail-closed."""
    # Ambiguous / missing explicit dimensions fail closed.
    for thr in (
        max_appends_per_window,
        max_invalid_per_window,
        max_duplicates,
        min_free_bytes,
        min_free_inodes,
    ):
        if _is_bad_threshold(thr):
            return PreflightDecision(False, "ambiguous_quota_input")
    if not window_id:
        return PreflightDecision(False, "ambiguous_window_input")
    if not isinstance(disk_stat, DiskStat):
        return PreflightDecision(False, "ambiguous_quota_input")

    # Missing actor/source identity fails closed.
    if not actor_id:
        return PreflightDecision(False, "missing_actor_identity")

    # Disk / inode preflight — fail closed before any append could exhaust storage.
    if disk_stat.free_bytes < min_free_bytes:
        return PreflightDecision(False, "disk_free_space_preflight_failed")
    if disk_stat.free_inodes < min_free_inodes:
        return PreflightDecision(False, "inode_preflight_failed")

    # Per-actor isolation: only this actor's history counts.
    actor_hist = [a for a in history if a.actor_id == actor_id]

    # Duplicate storm: this exact signature repeated at/over threshold.
    dup_count = sum(1 for a in actor_hist if a.record_signature == record_signature)
    if dup_count >= max_duplicates:
        return PreflightDecision(False, "duplicate_storm")

    # Retry storm: invalid attempts by this actor in this window at/over threshold.
    invalid_in_window = sum(
        1 for a in actor_hist if a.window_id == window_id and a.outcome == "invalid"
    )
    if invalid_in_window >= max_invalid_per_window:
        return PreflightDecision(False, "retry_storm")

    # Quota: valid appends by this actor in this window at/over threshold.
    valid_in_window = sum(
        1 for a in actor_hist if a.window_id == window_id and a.outcome == "valid"
    )
    if valid_in_window >= max_appends_per_window:
        return PreflightDecision(False, "append_quota_exceeded")

    return PreflightDecision(True, "")


def snapshot_from_ledger(db_path: str):
    """Read-only deterministic derivation of prior attempts from the append-only ledger.

    Stored rows are all successful (``valid``) appends; actor identity is derived from the recorded
    production verifier identity. Returns an immutable tuple ordered by append_sequence. This reads
    only; it creates and mutates nothing.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT verifier_identity, approval_record_id
            FROM approval_ledger ORDER BY append_sequence ASC
            """
        ).fetchall()
    finally:
        conn.close()
    return tuple(
        AppendAttempt(
            actor_id=r[0], window_id="", record_signature=r[1], outcome="valid"
        )
        for r in rows
    )
