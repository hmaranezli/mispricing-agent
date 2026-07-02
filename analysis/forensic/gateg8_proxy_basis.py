"""analysis/forensic/gateg8_proxy_basis.py — G8 Proxy-Basis Evidence (Slice 2).

PER-SOURCE RAW reference evidence for one G8 PAPER_OPEN entry, so a later analysis can diagnose
whether the Polymarket-vs-Hyperliquid model edge is distorted by reference-source basis. Four
reference kinds per entry: HL window-strike, HL current, Kraken USD spot, Coinbase USD spot.

HARD BOUNDARIES:
  * Pure: no network, no clock, no G9/wallet/signing/capital/order path. (The tool performs the
    concurrent public spot GET and passes the resulting ticks in; this module only shapes + writes.)
  * Every persisted value is RAW and SOURCE-SPECIFIC. NEVER a blend / midpoint / consensus /
    agreement score, and NEVER a persisted derived basis delta (all deltas are recomputable from
    the raw rows). Decimal is stored as canonical TEXT; no REAL column.
  * HL rows carry the transported model value (value_raw NULL; candle-start ts labelled
    CANDLE_START_FOR_CLOSE_VALUE) -- reused from the in-memory G8 decision, never a new HL request.
  * Kraken/Coinbase rows carry NO source-event timestamp (source_event_ts_ms NULL,
    NO_SOURCE_EVENT_TS_CAPTURE_BRACKET_ONLY); freshness is never fabricated. A failed leg becomes a
    complete REJECTED row (sanitized provenance) -- absence-of-data is recorded, never invented.
  * Append-only ATOMIC GROUP: write_proxy_basis_group writes all four rows in ONE savepoint (all or
    zero). An identical complete batch replay is a no-op; any differing/partial pre-existing group
    fails closed. Never UPDATE/UPSERT/REPLACE, never retry/backfill.
"""
from __future__ import annotations

import os
import re
import sqlite3

PROXY_ARM_ENV = "GATEG8_PROXY_BASIS"
PROXY_ARM_TOKEN = "CAPTURE-CONFIRMED"

PHASE_ENTRY = "ENTRY"
REF_HL_WINDOW_STRIKE = "HL_WINDOW_STRIKE"
REF_HL_CURRENT = "HL_CURRENT"
REF_KRAKEN_SPOT = "KRAKEN_SPOT"
REF_COINBASE_SPOT = "COINBASE_SPOT"

TS_CANDLE_START_FOR_CLOSE = "CANDLE_START_FOR_CLOSE_VALUE"
TS_CAPTURE_BRACKET_ONLY = "NO_SOURCE_EVENT_TS_CAPTURE_BRACKET_ONLY"

CAP_OK = "OK"
CAP_REJECTED = "REJECTED"


class ProxyBasisConflictError(Exception):
    """A proxy-basis group already exists that differs from, or only partially matches, the batch
    being written. Fail closed -- never overwrite or complete historical evidence."""


_PROXY_BASIS_COLS = [
    # identity / provenance
    "capture_run_id", "source_ledger_id", "entry_ledger_id",
    "condition_id", "slug", "asset", "window", "phase", "reference_kind",
    # source-specific raw evidence
    "instrument", "value_raw", "value_decimal_text",
    # timestamp honesty
    "source_event_ts_ms", "timestamp_semantic",
    "capture_started_ms", "capture_completed_ms",
    # classification
    "capture_status", "failure_provenance",
]

_PROXY_INTEGER_COLS = frozenset({
    "source_ledger_id", "entry_ledger_id", "source_event_ts_ms",
    "capture_started_ms", "capture_completed_ms",
})

_URL_RE = re.compile(r"https?://\S+")
_HEX_RE = re.compile(r"0x[0-9a-fA-F]{12,}")
_LONGNUM_RE = re.compile(r"\d{16,}")


def is_armed() -> bool:
    return os.environ.get(PROXY_ARM_ENV, "") == PROXY_ARM_TOKEN


def _sanitize(exc, cap: int = 200) -> str:
    """Redact URLs, 0x-hashes and long token/condition IDs; collapse whitespace; length-cap."""
    msg = str(exc)
    msg = _URL_RE.sub("[URL]", msg)
    msg = _HEX_RE.sub("[HEX]", msg)
    msg = _LONGNUM_RE.sub("[ID]", msg)
    msg = " ".join(msg.split())
    return (msg[:cap] + "...[truncated]") if len(msg) > cap else msg


def _val(x):
    return str(x) if x is not None else None


def _col_decl(col: str) -> str:
    if col == "capture_run_id":
        return "capture_run_id TEXT NOT NULL"
    return f"{col} INTEGER" if col in _PROXY_INTEGER_COLS else f"{col} TEXT"


def init_proxy_basis_table(conn) -> None:
    """Append-only proxy-basis table (TEXT/INTEGER only; never REAL).
    UNIQUE(capture_run_id, source_ledger_id, reference_kind) is the row identity; a secondary
    non-unique (condition_id, phase) index supports analysis."""
    cols_sql = ",".join(_col_decl(c) for c in _PROXY_BASIS_COLS)
    conn.execute(f"CREATE TABLE IF NOT EXISTS gateg8_proxy_basis(id INTEGER PRIMARY KEY, {cols_sql})")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_g8_proxy_basis_identity "
                 "ON gateg8_proxy_basis(capture_run_id, source_ledger_id, reference_kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_g8_proxy_basis_cond "
                 "ON gateg8_proxy_basis(condition_id, phase)")
    conn.commit()


def _base_row(capture_run_id, source_ledger_id, entry_ledger_id, market_ident, reference_kind) -> dict:
    row = {c: None for c in _PROXY_BASIS_COLS}
    row.update({
        "capture_run_id": capture_run_id,
        "source_ledger_id": source_ledger_id,
        "entry_ledger_id": entry_ledger_id,
        "condition_id": market_ident.get("condition_id"),
        "slug": market_ident.get("slug"),
        "asset": market_ident.get("asset"),
        "window": market_ident.get("window"),
        "phase": PHASE_ENTRY,
        "reference_kind": reference_kind,
    })
    return row


def _hl_row(*, capture_run_id, source_ledger_id, entry_ledger_id, market_ident, reference_kind,
            instrument, value, source_event_ts_ms, capture_started_ms, capture_completed_ms) -> dict:
    row = _base_row(capture_run_id, source_ledger_id, entry_ledger_id, market_ident, reference_kind)
    row.update({
        "instrument": instrument,
        "value_raw": None,                              # HL value is transported, not a raw payload
        "value_decimal_text": _val(value),
        "source_event_ts_ms": source_event_ts_ms,
        "timestamp_semantic": TS_CANDLE_START_FOR_CLOSE,
        "capture_started_ms": capture_started_ms,
        "capture_completed_ms": capture_completed_ms,
        "capture_status": CAP_OK,
    })
    return row


def build_hl_reference_rows(*, capture_run_id, source_ledger_id, entry_ledger_id, market_ident,
                            window_strike, window_strike_ts_ms, window_strike_started_ms,
                            window_strike_completed_ms, current_price, current_ts_ms,
                            current_started_ms, current_completed_ms) -> list:
    """Two HL rows (window-strike + current) from the ALREADY-captured in-memory G8 values. No
    network. `source_event_ts_ms` is the candle-start timestamp attached to a close value."""
    instrument = f"hl-1m-candle-close:{market_ident.get('asset')}"
    common = dict(capture_run_id=capture_run_id, source_ledger_id=source_ledger_id,
                  entry_ledger_id=entry_ledger_id, market_ident=market_ident, instrument=instrument)
    strike = _hl_row(reference_kind=REF_HL_WINDOW_STRIKE, value=window_strike,
                     source_event_ts_ms=window_strike_ts_ms,
                     capture_started_ms=window_strike_started_ms,
                     capture_completed_ms=window_strike_completed_ms, **common)
    current = _hl_row(reference_kind=REF_HL_CURRENT, value=current_price,
                      source_event_ts_ms=current_ts_ms, capture_started_ms=current_started_ms,
                      capture_completed_ms=current_completed_ms, **common)
    return [strike, current]


def build_spot_reference_row(*, reference_kind, tick, capture_started_ms, capture_completed_ms,
                             capture_run_id, source_ledger_id, entry_ledger_id, market_ident) -> dict:
    """One complete raw spot reference row from a public_spot_fetchers tick. A rejected/malformed
    tick becomes a complete REJECTED row (sanitized provenance) -- never a fabricated price. Carries
    NO source-event timestamp; only the capture bracket."""
    row = _base_row(capture_run_id, source_ledger_id, entry_ledger_id, market_ident, reference_kind)
    pair = tick.get("pair")
    if reference_kind == REF_COINBASE_SPOT:
        instrument = f"coinbase-v2-spot:{pair}"
    elif reference_kind == REF_KRAKEN_SPOT:
        instrument = f"kraken:{pair}"
    else:
        instrument = str(pair)
    row.update({
        "instrument": instrument,
        "source_event_ts_ms": None,                     # these endpoints carry no usable event ts
        "timestamp_semantic": TS_CAPTURE_BRACKET_ONLY,
        "capture_started_ms": capture_started_ms,
        "capture_completed_ms": capture_completed_ms,
    })
    reject = tick.get("reject_reason")
    price = tick.get("price_decimal_text")
    if reject is not None or price is None:
        row["capture_status"] = CAP_REJECTED
        row["failure_provenance"] = _sanitize(reject if reject is not None else "missing_price")
        return row
    row["capture_status"] = CAP_OK
    row["value_raw"] = _val(tick.get("price_raw"))      # actual extracted source price string
    row["value_decimal_text"] = _val(price)
    return row


_KIND_IDX = _PROXY_BASIS_COLS.index("reference_kind")


def write_proxy_basis_group(conn, rows) -> str:
    """Append-only ATOMIC group writer keyed on (capture_run_id, source_ledger_id).

    - no existing rows for the key -> insert the whole group in ONE savepoint, return "RECORDED";
    - a complete existing group byte-identical to this batch -> no-op, return "ALREADY_RECORDED";
    - a differing OR partial (wrong-count / wrong-kinds) existing group -> ProxyBasisConflictError,
      zero mutation.

    All four rows commit or zero commit. Never UPDATE/UPSERT/REPLACE, never retry/backfill.
    """
    if not rows:
        raise ProxyBasisConflictError("empty proxy-basis group")
    capture_run_id = rows[0]["capture_run_id"]
    source_ledger_id = rows[0]["source_ledger_id"]
    for r in rows:
        if r["capture_run_id"] != capture_run_id or r["source_ledger_id"] != source_ledger_id:
            raise ProxyBasisConflictError("heterogeneous proxy-basis group key")

    payloads = {r["reference_kind"]: tuple(r.get(c) for c in _PROXY_BASIS_COLS) for r in rows}
    select_sql = (f"SELECT {','.join(_PROXY_BASIS_COLS)} FROM gateg8_proxy_basis "
                  "WHERE capture_run_id=? AND source_ledger_id=?")

    def _adjudicate(existing_rows) -> str:
        existing = {t[_KIND_IDX]: tuple(t) for t in existing_rows}
        if len(existing) != len(payloads) or set(existing) != set(payloads):
            raise ProxyBasisConflictError(
                f"partial/mismatched proxy-basis group for capture_run_id={capture_run_id} "
                f"source_ledger_id={source_ledger_id}")
        for kind, pl in payloads.items():
            if existing[kind] != pl:
                raise ProxyBasisConflictError(
                    f"proxy-basis conflict for capture_run_id={capture_run_id} "
                    f"source_ledger_id={source_ledger_id} reference_kind={kind}")
        return "ALREADY_RECORDED"

    existing_rows = conn.execute(select_sql, (capture_run_id, source_ledger_id)).fetchall()
    if existing_rows:
        return _adjudicate(existing_rows)

    insert_sql = (f"INSERT INTO gateg8_proxy_basis({','.join(_PROXY_BASIS_COLS)}) "
                  f"VALUES ({','.join('?' for _ in _PROXY_BASIS_COLS)})")
    conn.execute("SAVEPOINT g8_proxy_write")
    try:
        for r in rows:
            conn.execute(insert_sql, tuple(r.get(c) for c in _PROXY_BASIS_COLS))
    except sqlite3.IntegrityError:
        # a concurrent/reentrant insert of the SAME group raced us: re-check as a whole group
        conn.execute("ROLLBACK TO g8_proxy_write")
        conn.execute("RELEASE g8_proxy_write")
        existing_rows = conn.execute(select_sql, (capture_run_id, source_ledger_id)).fetchall()
        if existing_rows:
            return _adjudicate(existing_rows)
        raise
    except Exception:
        # any other mid-batch failure: roll the whole group back (all-or-zero) and propagate
        conn.execute("ROLLBACK TO g8_proxy_write")
        conn.execute("RELEASE g8_proxy_write")
        raise
    conn.execute("RELEASE g8_proxy_write")
    conn.commit()
    return "RECORDED"
