"""tests/test_depth_enricher.py — Shadow Mode depth telemetri TDD."""
import asyncio
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE positions (
            position_id TEXT PRIMARY KEY,
            shares REAL,
            pm_entry_price REAL,
            entry_top_book_size REAL,
            entry_depth_for_size REAL,
            entry_est_exit_price REAL,
            entry_depth_slippage_pct REAL,
            entry_book_levels_used INTEGER
        )
    """)
    conn.execute(
        "INSERT INTO positions (position_id, shares, pm_entry_price) VALUES (?,?,?)",
        ("pos-1", 2.5, 0.50),
    )
    conn.commit()
    conn.close()
    return db


def _read_pos(db: Path, position_id: str = "pos-1") -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM positions WHERE position_id=?", (position_id,)
    ).fetchone()
    conn.close()
    return dict(row)


BOOK_DEEP = {
    "bids": [
        {"price": "0.50", "size": "10"},
        {"price": "0.48", "size": "5"},
    ],
    "asks": [{"price": "0.52", "size": "8"}],
}

BOOK_THIN = {
    "bids": [{"price": "0.50", "size": "1"}],  # 1 share < 2.5 position
    "asks": [{"price": "0.52", "size": "8"}],
}


# ── testler ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enrich_populates_depth_fields(tmp_path):
    """Normal derin kitap → tüm depth alanları DB'e yazılmalı."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock, return_value=BOOK_DEEP):
        await enrich_entry_depth("pos-1", "tok-YES", 2.5, 0.50, db_path=db)

    row = _read_pos(db)
    assert row["entry_top_book_size"] == pytest.approx(10.0)
    assert row["entry_depth_for_size"] == pytest.approx(2.5)
    assert row["entry_est_exit_price"] == pytest.approx(0.50)
    assert row["entry_book_levels_used"] == 1
    # slippage: (0.50 - 0.50) / 0.50 = 0
    assert row["entry_depth_slippage_pct"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_enrich_thin_book_multi_level(tmp_path):
    """İnce kitap: 2+ level gerekiyor."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    book = {
        "bids": [
            {"price": "0.50", "size": "1"},
            {"price": "0.46", "size": "2"},
        ],
        "asks": [],
    }
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock, return_value=book):
        await enrich_entry_depth("pos-1", "tok-NO", 2.5, 0.50, db_path=db)

    row = _read_pos(db)
    assert row["entry_top_book_size"] == pytest.approx(1.0)
    assert row["entry_book_levels_used"] == 2
    # weighted: (1*0.50 + 1.5*0.46) / 2.5 = (0.50 + 0.69) / 2.5 = 0.476
    assert row["entry_est_exit_price"] == pytest.approx(0.476)
    # slippage negative: exit price < entry price
    assert row["entry_depth_slippage_pct"] < 0


@pytest.mark.asyncio
async def test_enrich_get_book_none_leaves_nulls(tmp_path):
    """get_book None dönerse → alanlar NULL kalmalı, exception olmamalı."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock, return_value=None):
        await enrich_entry_depth("pos-1", "tok-YES", 2.5, 0.50, db_path=db)

    row = _read_pos(db)
    assert row["entry_top_book_size"] is None
    assert row["entry_depth_for_size"] is None


@pytest.mark.asyncio
async def test_enrich_network_exception_leaves_nulls(tmp_path):
    """get_book exception → sessizce geç, NULL bırak, trade bloklanmaz."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock,
               side_effect=Exception("network error")):
        await enrich_entry_depth("pos-1", "tok-YES", 2.5, 0.50, db_path=db)

    row = _read_pos(db)
    assert row["entry_top_book_size"] is None


@pytest.mark.asyncio
async def test_enrich_empty_bids_leaves_nulls(tmp_path):
    """Bids boş → NULL bırak."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock,
               return_value={"bids": [], "asks": []}):
        await enrich_entry_depth("pos-1", "tok-YES", 2.5, 0.50, db_path=db)

    row = _read_pos(db)
    assert row["entry_top_book_size"] is None


@pytest.mark.asyncio
async def test_enrich_wrong_position_id_is_noop(tmp_path):
    """Yanlış position_id → DB değişmez, exception yok."""
    from data.depth_enricher import enrich_entry_depth

    db = _make_db(tmp_path)
    with patch("data.depth_enricher.get_book", new_callable=AsyncMock, return_value=BOOK_DEEP):
        await enrich_entry_depth("pos-NONEXISTENT", "tok", 2.5, 0.50, db_path=db)

    row = _read_pos(db)  # pos-1 değişmemeli
    assert row["entry_top_book_size"] is None
