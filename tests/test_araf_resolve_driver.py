"""tests/test_araf_resolve_driver.py — B1 ARAF discover/fetch driver (paper-only, A3-pure devamı).

Driver boundary (onaylı): RECOVERY_REQUIRED/SUBMITTED_UNKNOWN order_intents keşfi → (sonraki RED'ler)
get_order/get_trades → adapt_live_trades_page → decide_araf_resolution → record_araf_resolution.
İlk faz: yalnız discover (pure DB-read). positions/order_intents-terminal/confirm_fill_atomic YOK.

İlk RED structural: `execution.araf_resolve_driver.discover_eligible_intents` henüz yok → ImportError.
Eligible filtre ilk fazda yalnız status IN UNRESOLVED_STATES (reconciliation_status filtresi YOK).
Canlı API/DB yok — tmp_path SQLite + production init_schema.
"""
import sqlite3

import aiosqlite
import pytest


def _insert_intent(conn, iid, status):
    """order_intents'e test-local minimal satır (schema.py kolonları). status NOT NULL."""
    conn.execute(
        """INSERT INTO order_intents
               (order_intent_id, slug, market_token_id, side, intended_price, intended_size,
                status, exchange_order_id, reconciliation_status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (iid, f"slug-{iid}", f"tok-{iid}", "BUY", 0.42, 10.0,
         status, f"0xexch-{iid}", "pending", "2026-06-13T00:00:00+00:00"))


@pytest.mark.asyncio
async def test_discover_eligible_intents_returns_unresolved_only(tmp_path):
    """discover_eligible_intents → yalnız UNRESOLVED_STATES (SUBMITTED_UNKNOWN/RECOVERY_REQUIRED);
    terminal (FILLED) HARİÇ. Dönen satırlar gerekli alanları taşır; sonuç deterministic (id-sıralı)."""
    # Import test GÖVDESİNDE → modül yoksa temiz "1 failed" (collection error DEĞİL).
    from execution.araf_resolve_driver import discover_eligible_intents

    db = str(tmp_path / "araf_driver.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    boot = sqlite3.connect(db)
    try:
        _insert_intent(boot, "iid-a-unknown", "SUBMITTED_UNKNOWN")
        _insert_intent(boot, "iid-b-recovery", "RECOVERY_REQUIRED")
        _insert_intent(boot, "iid-c-filled", "FILLED")   # terminal → dönmemeli
        boot.commit()
    finally:
        boot.close()

    rows = await discover_eligible_intents(db)

    # Yalnız iki unresolved; FILLED yok. Deterministic: order_intent_id'ye göre sırala.
    ids = sorted(r["order_intent_id"] for r in rows)
    assert ids == ["iid-a-unknown", "iid-b-recovery"], f"yalnız unresolved beklenir: {ids}"

    statuses = {r["status"] for r in rows}
    assert statuses == {"SUBMITTED_UNKNOWN", "RECOVERY_REQUIRED"}, f"status seti: {statuses}"
    assert "iid-c-filled" not in ids, "terminal FILLED intent dönmemeli"

    # Her satır driver fetch'i için gerekli alanları taşımalı.
    by_id = {r["order_intent_id"]: r for r in rows}
    r = by_id["iid-a-unknown"]
    for field in ("order_intent_id", "exchange_order_id", "slug", "market_token_id",
                  "side", "intended_size", "intended_price", "status"):
        _ = r[field]   # mapping-by-name erişimi (dict veya sqlite3.Row) — yoksa KeyError/RED
    assert r["exchange_order_id"] == "0xexch-iid-a-unknown"
    assert r["slug"] == "slug-iid-a-unknown"
    assert r["market_token_id"] == "tok-iid-a-unknown"
    assert r["side"] == "BUY"
    assert r["status"] == "SUBMITTED_UNKNOWN"


class _StubClient:
    """İmza-uyumlu async stub (driver enjekte edilen client'ı await eder). Çağrıları kaydeder —
    NOT: gerçek ClobClient SENKRON; bu async stub, driver'ın async-client-port beklentisini
    yansıtır (production'da sync ClobClient için ince async adapter gerekecek = GREEN açık-kararı)."""

    def __init__(self, order, page):
        self._order = order
        self._page = page
        self.get_order_calls = []
        self.get_trades_calls = []

    async def get_order(self, order_id):
        self.get_order_calls.append(order_id)
        return self._order

    async def get_trades_paginated(self, params, next_cursor=None):
        self.get_trades_calls.append((params, next_cursor))
        return self._page


@pytest.mark.asyncio
async def test_resolve_intent_filled_writes_shadow(tmp_path):
    """Eligible intent + stub client (CONFIRMED taker full-fill, next_cursor=LTE=) →
    resolve_intent_to_shadow → araf_resolution_shadow FILLED + accounting evidence;
    order_intents/positions DOKUNULMAZ (A3-pure). Stub client çağrılmış olmalı.

    İlk RED structural: resolve_intent_to_shadow henüz yok → ImportError."""
    # Import test GÖVDESİNDE → fonksiyon yoksa temiz "1 failed" (collection error DEĞİL).
    from execution.araf_resolve_driver import resolve_intent_to_shadow

    db = str(tmp_path / "araf_orch_filled.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    intent_row = {
        "order_intent_id": "iid-orch-filled-1",
        "exchange_order_id": "0xorder-orch-filled-1",
        "slug": "slug-orch-1",
        "market_token_id": "tok-orch-1",
        "side": "BUY",
        "intended_size": "10",
        "intended_price": "0.42",
        "status": "SUBMITTED_UNKNOWN",
    }

    # get_order lifecycle dict (resolver target_raw için original_size).
    order = {
        "order_id": "0xorder-orch-filled-1",
        "status": "ORDER_STATUS_MATCHED",
        "original_size": "10",
        "size_matched": "10",
    }
    # get_trades_paginated canlı-şekilli page. NOT: trade'e "side":"BUY" eklendi — resolver taker
    # yön doğrulaması (intent side ile) için ZORUNLU; aksi halde FILLED değil RECOVERY_REQUIRED olur.
    page = {
        "trades": [
            {
                "id": "trade-orch-001",
                "taker_order_id": "0xorder-orch-filled-1",
                "status": "CONFIRMED",
                "side": "BUY",
                "size": "10",
                "price": "0.42",
                "fee_rate_bps": "0",
                "maker_orders": [],
            }
        ],
        "next_cursor": "LTE=",
        "limit": 300,
        "count": 1,
    }
    client = _StubClient(order, page)

    result = await resolve_intent_to_shadow(client, intent_row, db_path=db)
    assert result == "RECORDED", f"FILLED resolution RECORDED bekler: {result!r}"

    # Stub client çağrıldı mı?
    assert client.get_order_calls == ["0xorder-orch-filled-1"], \
        f"get_order çağrısı: {client.get_order_calls}"
    assert len(client.get_trades_calls) >= 1, "get_trades_paginated çağrılmalı"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT resolution_state, matched_size, avg_price, matched_trade_ids, accounting_source "
            "FROM araf_resolution_shadow WHERE order_intent_id=?", ("iid-orch-filled-1",)).fetchall()
        assert len(rows) == 1, f"tek shadow satırı: {len(rows)}"
        r = rows[0]
        assert r[0] == "FILLED", f"resolution_state: {r[0]!r}"
        assert r[1] == "10", f"matched_size: {r[1]!r}"
        assert r[2] == "0.42", f"avg_price: {r[2]!r}"
        assert r[3] == "trade-orch-001", f"matched_trade_ids: {r[3]!r}"
        assert r[4] == "CONFIRMED_TRADE", f"accounting_source: {r[4]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_resolve_intent_missing_exchange_order_id_writes_recovery_shadow(tmp_path):
    """exchange_order_id NULL → client ÇAĞRILMAZ (fetch için order_id yok); explicit shadow
    RECOVERY_REQUIRED + recovery_reason="MISSING_EXCHANGE_ORDER_ID", accounting NULL. order_intents/
    positions dokunulmaz. Skip YOK (gözlemlenebilir fail-closed)."""
    from execution.araf_resolve_driver import resolve_intent_to_shadow

    db = str(tmp_path / "araf_orch_missing.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    intent_row = {
        "order_intent_id": "iid-missing-exchange-1",
        "exchange_order_id": None,
        "slug": "slug-missing-1",
        "market_token_id": "tok-missing-1",
        "side": "BUY",
        "intended_size": "10",
        "intended_price": "0.42",
        "status": "SUBMITTED_UNKNOWN",
    }
    # Stub'a geçerli order/page verilir ama NULL yolunda HİÇ çağrılmamalı.
    order = {"order_id": "0xirrelevant", "status": "ORDER_STATUS_MATCHED", "original_size": "10"}
    page = {"trades": [], "next_cursor": "LTE=", "limit": 300, "count": 0}
    client = _StubClient(order, page)

    result = await resolve_intent_to_shadow(client, intent_row, db_path=db)
    assert result == "RECORDED", f"explicit recovery shadow RECORDED bekler: {result!r}"

    # KRİTİK: order_id yokken client ÇAĞRILMAMALI.
    assert client.get_order_calls == [], f"get_order çağrılmamalı: {client.get_order_calls}"
    assert client.get_trades_calls == [], f"get_trades_paginated çağrılmamalı: {client.get_trades_calls}"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT exchange_order_id, resolution_state, matched_size, avg_price, fee_rate_bps, "
            "matched_trade_ids, accounting_source, recovery_reason FROM araf_resolution_shadow "
            "WHERE order_intent_id=?", ("iid-missing-exchange-1",)).fetchall()
        assert len(rows) == 1, f"tek shadow satırı: {len(rows)}"
        r = rows[0]
        assert r[0] is None, f"exchange_order_id NULL: {r[0]!r}"
        assert r[1] == "RECOVERY_REQUIRED", f"resolution_state: {r[1]!r}"
        assert r[2] is None, f"matched_size NULL: {r[2]!r}"
        assert r[3] is None, f"avg_price NULL: {r[3]!r}"
        assert r[4] is None, f"fee_rate_bps NULL: {r[4]!r}"
        assert r[5] is None, f"matched_trade_ids NULL: {r[5]!r}"
        assert r[6] is None, f"accounting_source NULL: {r[6]!r}"
        assert r[7] == "MISSING_EXCHANGE_ORDER_ID", f"recovery_reason: {r[7]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_resolve_intent_incomplete_scan_pagination_writes_recovery_shadow(tmp_path):
    """adapted next_cursor != "LTE=" (çok sayfa, tarama eksik) → terminal karar VERME; CONFIRMED
    full-fill olsa bile FILLED yazma. Explicit shadow RECOVERY_REQUIRED + recovery_reason=
    "INCOMPLETE_SCAN_PAGINATION", accounting NULL. client çağrılır ama terminal undercount riski
    yüzünden FILLED engellenir. order_intents/positions dokunulmaz."""
    from execution.araf_resolve_driver import resolve_intent_to_shadow

    db = str(tmp_path / "araf_orch_pagination.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    intent_row = {
        "order_intent_id": "iid-pagination-1",
        "exchange_order_id": "0xorder-pagination-1",
        "slug": "slug-pag-1",
        "market_token_id": "tok-pag-1",
        "side": "BUY",
        "intended_size": "10",
        "intended_price": "0.42",
        "status": "SUBMITTED_UNKNOWN",
    }
    order = {"order_id": "0xorder-pagination-1", "status": "ORDER_STATUS_MATCHED",
             "original_size": "10", "size_matched": "10"}
    # CONFIRMED full-fill VAR ama next_cursor != "LTE=" → tarama eksik (sonraki sayfalar olabilir).
    page = {
        "trades": [
            {
                "id": "trade-pag-001",
                "taker_order_id": "0xorder-pagination-1",
                "status": "CONFIRMED",
                "side": "BUY",
                "size": "10",
                "price": "0.42",
                "fee_rate_bps": "0",
                "maker_orders": [],
            }
        ],
        "next_cursor": "MzAw",   # base64("300") — END_CURSOR ("LTE=") DEĞİL
        "limit": 300,
        "count": 1,
    }
    client = _StubClient(order, page)

    result = await resolve_intent_to_shadow(client, intent_row, db_path=db)
    assert result == "RECORDED", f"recovery shadow RECORDED bekler: {result!r}"

    # client çağrıldı (NULL yolundan farklı — fetch yapıldı sonra pagination guard devreye girdi).
    assert client.get_order_calls == ["0xorder-pagination-1"], f"get_order: {client.get_order_calls}"
    assert len(client.get_trades_calls) >= 1, "get_trades_paginated çağrılmalı"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT resolution_state, matched_size, avg_price, fee_rate_bps, matched_trade_ids, "
            "accounting_source, recovery_reason FROM araf_resolution_shadow "
            "WHERE order_intent_id=?", ("iid-pagination-1",)).fetchall()
        assert len(rows) == 1, f"tek shadow satırı: {len(rows)}"
        r = rows[0]
        # Pagination eksik → FILLED DEĞİL (undercount riski); terminal yazma engellendi.
        assert r[0] == "RECOVERY_REQUIRED", f"resolution_state: {r[0]!r}"
        assert r[1] is None, f"matched_size NULL: {r[1]!r}"
        assert r[2] is None, f"avg_price NULL: {r[2]!r}"
        assert r[3] is None, f"fee_rate_bps NULL: {r[3]!r}"
        assert r[4] is None, f"matched_trade_ids NULL: {r[4]!r}"
        assert r[5] is None, f"accounting_source NULL: {r[5]!r}"
        assert r[6] == "INCOMPLETE_SCAN_PAGINATION", f"recovery_reason: {r[6]!r}"

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 0, \
            "order_intents'e yazım YOK (A3-pure)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()


def _insert_intent_full(conn, iid, exch, status):
    """order_intents test-local satır, explicit order_intent_id + exchange_order_id."""
    conn.execute(
        """INSERT INTO order_intents
               (order_intent_id, slug, market_token_id, side, intended_price, intended_size,
                status, exchange_order_id, reconciliation_status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (iid, f"slug-{iid}", f"tok-{iid}", "BUY", 0.42, 10.0,
         status, exch, "pending", "2026-06-14T00:00:00+00:00"))


def _confirmed_full_fill_page(taker_order_id):
    """CONFIRMED taker full-fill (10@0.42), tarama TAM (next_cursor=LTE=)."""
    return {
        "trades": [
            {
                "id": f"trade-{taker_order_id}",
                "taker_order_id": taker_order_id,
                "status": "CONFIRMED",
                "side": "BUY",
                "size": "10",
                "price": "0.42",
                "fee_rate_bps": "0",
                "maker_orders": [],
            }
        ],
        "next_cursor": "LTE=",
        "limit": 300,
        "count": 1,
    }


class _BatchStubClient:
    """order_id-keyed async stub: get_order/get_trades_paginated order_id'ye göre döner, çağrı kaydeder."""

    def __init__(self, orders, pages):
        self.orders = orders   # order_id -> order dict
        self.pages = pages     # order_id -> page dict
        self.get_order_calls = []
        self.get_trades_calls = []

    async def get_order(self, order_id):
        self.get_order_calls.append(order_id)
        return self.orders[order_id]

    async def get_trades_paginated(self, params, next_cursor=None):
        self.get_trades_calls.append((params, next_cursor))
        return self.pages[params["order_id"]]


@pytest.mark.asyncio
async def test_run_araf_resolution_discovers_and_resolves_all_eligible_intents(tmp_path):
    """run_araf_resolution batch entrypoint: discover_eligible_intents → her eligible intent için
    resolve_intent_to_shadow. Yalnız UNRESOLVED intent'ler shadow'a yazılır; terminal (FILLED)
    discover dışı. positions/order_intents update YOK (paper-only batch).

    İlk RED structural: run_araf_resolution henüz yok → ImportError."""
    from execution.araf_resolve_driver import run_araf_resolution

    db = str(tmp_path / "araf_orch_batch.db")
    from db.schema import init_schema
    async with aiosqlite.connect(db) as conn:
        await init_schema(conn)
        await conn.commit()

    boot = sqlite3.connect(db)
    try:
        _insert_intent_full(boot, "iid-batch-a", "ord-batch-a", "SUBMITTED_UNKNOWN")
        _insert_intent_full(boot, "iid-batch-b", "ord-batch-b", "RECOVERY_REQUIRED")
        _insert_intent_full(boot, "iid-batch-terminal", "ord-batch-terminal", "FILLED")  # discover dışı
        boot.commit()
    finally:
        boot.close()

    order_a = {"order_id": "ord-batch-a", "status": "ORDER_STATUS_MATCHED", "original_size": "10"}
    order_b = {"order_id": "ord-batch-b", "status": "ORDER_STATUS_MATCHED", "original_size": "10"}
    client = _BatchStubClient(
        orders={"ord-batch-a": order_a, "ord-batch-b": order_b},
        pages={"ord-batch-a": _confirmed_full_fill_page("ord-batch-a"),
               "ord-batch-b": _confirmed_full_fill_page("ord-batch-b")},
    )

    await run_araf_resolution(client, db_path=db)

    # Yalnız iki eligible için get_order çağrıldı (terminal hariç).
    assert sorted(client.get_order_calls) == ["ord-batch-a", "ord-batch-b"], \
        f"get_order çağrıları: {client.get_order_calls}"

    conn = sqlite3.connect(db)
    try:
        sids = sorted(row[0] for row in conn.execute(
            "SELECT order_intent_id FROM araf_resolution_shadow").fetchall())
        assert sids == ["iid-batch-a", "iid-batch-b"], f"shadow satırları: {sids}"
        # terminal intent için shadow YOK.
        assert "iid-batch-terminal" not in sids

        assert conn.execute("SELECT COUNT(*) FROM order_intents").fetchone()[0] == 3, \
            "order_intents 3 kalmalı (update/silme YOK)"
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0, \
            "positions'a yazım YOK (A3-pure)"
    finally:
        conn.close()
