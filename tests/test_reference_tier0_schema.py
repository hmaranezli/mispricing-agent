"""tests/test_reference_tier0_schema.py — Tier-0 evidence schema (TDD, additive).

The PUBLIC_REFERENCE_BASKET Tier-0 collector needs three append-only tables created additively by
`db.schema.init_schema`, with STRICT numeric discipline: NO SQL REAL column for any economic quantity
(price/spread/basis) — Decimal values live in TEXT columns (the araf_resolution_shadow precedent).
Timing is INTEGER ms / TEXT ISO. `not_official_chainlink` defaults to 1.

First RED: the three tables do not exist yet → table_info returns empty → assertions fail.
"""
import asyncio
import os
import sys

import pytest
import aiosqlite

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.schema import init_schema

_TABLES = ("reference_price_ticks", "proxy_reference_basket_ticks", "perp_basis_ticks")

# Economic quantities that must NEVER be stored as REAL (Decimal-as-TEXT discipline).
_ECON_COLS = {
    "reference_price_ticks": {"price_raw", "price_decimal_text"},
    "proxy_reference_basket_ticks": {"spot_reference_decimal_text", "spread_bps_decimal_text"},
    "perp_basis_ticks": {"perp_price_decimal_text", "spot_reference_decimal_text",
                         "basis_bps_decimal_text"},
}


async def _columns(conn, table):
    async with conn.execute(f"PRAGMA table_info({table})") as cur:
        return {row[1]: row[2] for row in await cur.fetchall()}  # name -> declared type


@pytest.mark.asyncio
async def test_three_tables_created_additively(tmp_path):
    async with aiosqlite.connect(str(tmp_path / "t.db")) as conn:
        await init_schema(conn)
        for t in _TABLES:
            cols = await _columns(conn, t)
            assert cols, f"table {t} must be created by init_schema"


@pytest.mark.asyncio
async def test_no_real_columns_anywhere_in_tier0_tables(tmp_path):
    async with aiosqlite.connect(str(tmp_path / "t.db")) as conn:
        await init_schema(conn)
        for t in _TABLES:
            cols = await _columns(conn, t)
            reals = {n for n, typ in cols.items() if (typ or "").upper() == "REAL"}
            assert reals == set(), f"{t} must have NO REAL columns; found {reals}"


@pytest.mark.asyncio
async def test_economic_columns_are_text(tmp_path):
    async with aiosqlite.connect(str(tmp_path / "t.db")) as conn:
        await init_schema(conn)
        for t, econ in _ECON_COLS.items():
            cols = await _columns(conn, t)
            for c in econ:
                assert cols.get(c) == "TEXT", f"{t}.{c} must be TEXT (Decimal string), got {cols.get(c)}"


@pytest.mark.asyncio
async def test_not_official_chainlink_defaults_to_one(tmp_path):
    async with aiosqlite.connect(str(tmp_path / "t.db")) as conn:
        await init_schema(conn)
        await conn.execute(
            "INSERT INTO proxy_reference_basket_ticks (basket_id, asset, anchor_ts) "
            "VALUES ('b1','BTC','2026-06-25T00:00:00Z')")
        await conn.commit()
        async with conn.execute(
            "SELECT not_official_chainlink FROM proxy_reference_basket_ticks WHERE basket_id='b1'"
        ) as cur:
            row = await cur.fetchone()
        assert row[0] == 1, "not_official_chainlink must default to 1"


@pytest.mark.asyncio
async def test_existing_tables_untouched(tmp_path):
    """Additive slice must not drop/alter existing core tables."""
    async with aiosqlite.connect(str(tmp_path / "t.db")) as conn:
        await init_schema(conn)
        for t in ("shadow_positions", "model_decision_events", "order_intents", "positions"):
            cols = await _columns(conn, t)
            assert cols, f"existing table {t} must still exist"
